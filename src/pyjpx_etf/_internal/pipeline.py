"""Pipeline orchestrator for daily PCF snapshot. Not part of public API."""

from __future__ import annotations

import datetime
import logging
import time
from pathlib import Path

from ..config import config
from . import db

logger = logging.getLogger(__name__)


def _fetch_all_etf_codes() -> list[str]:
    """Get all ETF codes from Rakuten (ETF-only, ~400 codes)."""
    from .rakuten import get_rakuten_data

    data = get_rakuten_data(refresh=True)
    return sorted(data.keys())


def _fetch_and_store_pcf(
    conn, code: str, today: str, *, debug_dir: Path | None = None,
) -> bool:
    """Fetch PCF for a single ETF and store in DB. Returns True on success."""
    from .fetcher import fetch_pcf
    from .parser import parse_pcf

    try:
        csv_text = fetch_pcf(code)
    except Exception as e:
        logger.warning("Failed to fetch PCF for %s: %s", code, e)
        return False

    try:
        info, holdings = parse_pcf(csv_text)
    except Exception as e:
        logger.warning("Failed to parse PCF for %s: %s", code, e)
        if debug_dir is not None:
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / f"{code}.csv").write_text(csv_text)
        return False

    date_str = info.date.isoformat()
    db.insert_pcf_info(
        conn,
        code,
        date_str,
        name=info.name,
        cash_component=info.cash_component,
        shares_outstanding=info.shares_outstanding,
    )
    db.insert_holdings(conn, code, date_str, holdings)

    # Also upsert ETF name (English from PCF)
    db.upsert_etf(conn, code, name_en=info.name)

    return True


def _store_fees(conn) -> None:
    """Fetch fees from JPX + Rakuten and store in DB."""
    from .fees import get_fees
    from .rakuten import get_rakuten_data

    jpx_fees = get_fees(refresh=True)
    for code, fee in jpx_fees.items():
        db.upsert_etf(conn, code, fee=fee)

    # Rakuten as fallback for missing fees
    rakuten = get_rakuten_data(refresh=True)
    for code, entry in rakuten.items():
        fee = entry.get("fee")
        if fee is not None:
            # Only set if JPX didn't already provide one
            existing = conn.execute(
                "SELECT fee FROM etfs WHERE code = ?", (code,)
            ).fetchone()
            if existing is None or existing["fee"] is None:
                db.upsert_etf(conn, code, fee=fee)
        # Store names from Rakuten
        db.upsert_etf(
            conn,
            code,
            name_ja=entry.get("name_ja"),
            name_en=entry.get("name_en"),
        )


def _store_master_names(conn) -> None:
    """Fetch Japanese names from master list and store in DB."""
    from .master import get_japanese_names

    names = get_japanese_names(refresh=True)
    for code, name_ja in names.items():
        db.upsert_etf(conn, code, name_ja=name_ja)
        db.upsert_security(conn, code, name_ja=name_ja)


def run_pipeline(
    db_path: Path, *, debug_dir: Path | None = None,
) -> None:
    """Main pipeline entry point. Fetches all ETF data and writes to SQLite.

    If *debug_dir* is set, raw CSV files that fail to parse are saved there.
    """
    config.db_path = db_path

    conn = db.get_connection(readonly=False)
    try:
        db.init_schema(conn)

        # 1. Get all ETF codes
        logger.info("Fetching ETF master list...")
        codes = _fetch_all_etf_codes()
        logger.info("Found %d ETF codes", len(codes))

        # 2. Fetch PCF for each code
        today = datetime.date.today().isoformat()
        success = 0
        failed = 0
        for i, code in enumerate(codes):
            if i > 0 and config.request_delay > 0:
                time.sleep(config.request_delay)
            if _fetch_and_store_pcf(
                conn, code, today, debug_dir=debug_dir,
            ):
                success += 1
            else:
                failed += 1
            if (i + 1) % 50 == 0:
                logger.info("Progress: %d/%d (success=%d, failed=%d)",
                            i + 1, len(codes), success, failed)
                conn.commit()

        conn.commit()
        logger.info("PCF fetch complete: %d success, %d failed", success, failed)

        # 3. Fetch fees
        logger.info("Fetching fees...")
        _store_fees(conn)
        conn.commit()

        # 4. Fetch master names
        logger.info("Fetching master names...")
        _store_master_names(conn)
        conn.commit()

        # 5. Update meta
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        db.update_meta(conn, "version", "1")
        db.update_meta(conn, "updated_at", now)
        conn.commit()

        logger.info("Pipeline complete. DB at %s", db_path)
    finally:
        conn.close()
