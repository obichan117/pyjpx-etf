"""SQLite write queries — used by the pipeline only."""

from __future__ import annotations

import sqlite3

from ..models import Holding
from .db_core import _SCHEMA_SQL


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript(_SCHEMA_SQL)


def upsert_etf(
    conn: sqlite3.Connection,
    code: str,
    *,
    name_ja: str | None = None,
    name_en: str | None = None,
    fee: float | None = None,
) -> None:
    """Insert or update an ETF in the etfs table."""
    conn.execute(
        "INSERT INTO etfs (code, name_ja, name_en, fee) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(code) DO UPDATE SET "
        "name_ja = COALESCE(excluded.name_ja, etfs.name_ja), "
        "name_en = COALESCE(excluded.name_en, etfs.name_en), "
        "fee = COALESCE(excluded.fee, etfs.fee)",
        (code, name_ja, name_en, fee),
    )


def insert_pcf_info(
    conn: sqlite3.Connection,
    code: str,
    date: str,
    *,
    name: str | None = None,
    cash_component: float | None = None,
    shares_outstanding: int | None = None,
) -> None:
    """Insert or replace PCF info for a given ETF and date."""
    conn.execute(
        "INSERT OR REPLACE INTO pcf_info "
        "(code, date, name, cash_component, shares_outstanding) "
        "VALUES (?, ?, ?, ?, ?)",
        (code, date, name, cash_component, shares_outstanding),
    )


def insert_holdings(
    conn: sqlite3.Connection,
    code: str,
    date: str,
    holdings: list[Holding],
) -> None:
    """Insert holdings for a given ETF and date."""
    conn.executemany(
        "INSERT OR REPLACE INTO pcf_holdings "
        "(code, date, holding_code, name, isin, exchange, currency, "
        "shares, price, weight) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                code,
                date,
                h.code,
                h.name,
                h.isin,
                h.exchange,
                h.currency,
                h.shares,
                h.price,
                h.weight,
            )
            for h in holdings
        ],
    )


def upsert_security(
    conn: sqlite3.Connection,
    code: str,
    *,
    name_ja: str | None = None,
    name_en: str | None = None,
) -> None:
    """Insert or update a security in the securities table."""
    conn.execute(
        "INSERT INTO securities (code, name_ja, name_en) VALUES (?, ?, ?) "
        "ON CONFLICT(code) DO UPDATE SET "
        "name_ja = COALESCE(excluded.name_ja, securities.name_ja), "
        "name_en = COALESCE(excluded.name_en, securities.name_en)",
        (code, name_ja, name_en),
    )


def update_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set a metadata key-value pair."""
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (key, value),
    )
