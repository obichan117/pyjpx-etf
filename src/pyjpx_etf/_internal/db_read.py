"""SQLite read queries — used by the public API."""

from __future__ import annotations

import datetime

import pandas as pd

from ..models import ETFInfo, Holding
from .db_core import db_exists, get_connection

# Shared AUM aggregation: cash component + market value of holdings on the
# latest date. Reused by search_by_holding, concentration_stats, and the
# screener (_internal/screen/db.py imports this constant directly).
_AUM_SQL = """
    SELECT pi.code,
           pi.cash_component + COALESCE(h.total_mv, 0) AS aum
    FROM pcf_info pi
    INNER JOIN (
        SELECT code, MAX(date) AS max_date
        FROM pcf_info
        GROUP BY code
    ) latest ON pi.code = latest.code AND pi.date = latest.max_date
    LEFT JOIN (
        SELECT code, date, SUM(shares * price) AS total_mv
        FROM pcf_holdings
        GROUP BY code, date
    ) h ON pi.code = h.code AND pi.date = h.date
"""

# Top-holding concentration per ETF (top1/top3/top10 cumulative weight).
# Equities only (4-char holding_code) — excludes FX forwards/bonds rows.
# Reused by concentration_stats and the screener (_internal/screen/db.py
# imports this constant directly).
_CONCENTRATION_SQL = """
    WITH latest AS (
        SELECT code, MAX(date) AS d FROM pcf_holdings GROUP BY code
    ),
    ranked AS (
        SELECT h.code, h.holding_code, h.name, h.weight,
               ROW_NUMBER() OVER (PARTITION BY h.code ORDER BY h.weight DESC) AS rn
        FROM pcf_holdings h
        JOIN latest l ON h.code = l.code AND h.date = l.d
        WHERE h.weight IS NOT NULL AND h.weight > 0
          -- JP equities only: 4 chars starting with a digit (e.g. 6857, 285A).
          -- Excludes CASH rows, FX forwards/bonds, and foreign feeder
          -- tickers like IEMG (fund-of-fund ETFs holding one foreign ETF).
          AND TRIM(h.holding_code) GLOB '[1-9][0-9A-Z][0-9A-Z][0-9A-Z]'
    )
    SELECT r.code,
           MAX(CASE WHEN rn = 1 THEN r.holding_code END) AS top_code,
           MAX(CASE WHEN rn = 1 THEN r.name END)         AS top_name,
           SUM(CASE WHEN rn <= 1 THEN r.weight END)      AS top1,
           SUM(CASE WHEN rn <= 3 THEN r.weight END)      AS top3,
           SUM(CASE WHEN rn <= 10 THEN r.weight END)     AS top10,
           COUNT(*)                                      AS n_holdings
    FROM ranked r
    GROUP BY r.code
"""

_CONCENTRATION_COLUMNS = [
    "code",
    "name",
    "top_code",
    "top_name",
    "top1",
    "top3",
    "top10",
    "n_holdings",
    "aum",
]


def read_etf_info(code: str, date: str | None = None) -> ETFInfo | None:
    """Read ETF info from the database. Uses latest date if date is None."""
    if not db_exists():
        return None
    try:
        conn = get_connection()
    except Exception:
        return None
    try:
        if date is None:
            row = conn.execute(
                "SELECT * FROM pcf_info WHERE code = ? ORDER BY date DESC LIMIT 1",
                (code,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM pcf_info WHERE code = ? AND date = ?",
                (code, date),
            ).fetchone()
        if row is None:
            return None
        return ETFInfo(
            code=row["code"],
            name=row["name"] or "",
            cash_component=row["cash_component"] or 0.0,
            shares_outstanding=row["shares_outstanding"] or 0,
            date=datetime.date.fromisoformat(row["date"]),
        )
    finally:
        conn.close()


def read_holdings(code: str, date: str | None = None) -> list[Holding] | None:
    """Read holdings from the database. Uses latest date if date is None."""
    if not db_exists():
        return None
    try:
        conn = get_connection()
    except Exception:
        return None
    try:
        if date is None:
            latest = conn.execute(
                "SELECT MAX(date) FROM pcf_holdings WHERE code = ?", (code,)
            ).fetchone()
            if latest is None or latest[0] is None:
                return None
            date = latest[0]
        rows = conn.execute(
            "SELECT * FROM pcf_holdings WHERE code = ? AND date = ? "
            "ORDER BY weight DESC",
            (code, date),
        ).fetchall()
        if not rows:
            return None
        return [
            Holding(
                code=r["holding_code"],
                name=r["name"] or "",
                isin=r["isin"] or "",
                exchange=r["exchange"] or "",
                currency=r["currency"] or "",
                shares=r["shares"] or 0.0,
                price=r["price"] or 0.0,
                weight=r["weight"] or 0.0,
            )
            for r in rows
        ]
    finally:
        conn.close()


def read_etf_fee(code: str) -> float | None:
    """Read fee for a single ETF from the etfs table."""
    if not db_exists():
        return None
    try:
        conn = get_connection()
    except Exception:
        return None
    try:
        row = conn.execute("SELECT fee FROM etfs WHERE code = ?", (code,)).fetchone()
        if row is None:
            return None
        return row["fee"]
    finally:
        conn.close()


def read_etf_dates(code: str) -> list[datetime.date]:
    """Return all available dates for an ETF, newest first."""
    if not db_exists():
        return []
    try:
        conn = get_connection()
    except Exception:
        return []
    try:
        rows = conn.execute(
            "SELECT DISTINCT date FROM pcf_info WHERE code = ? ORDER BY date DESC",
            (code,),
        ).fetchall()
        return [datetime.date.fromisoformat(r["date"]) for r in rows]
    finally:
        conn.close()


def read_etf_list() -> dict[str, dict]:
    """Return all ETFs with name and fee. ``{code: {name_ja, name_en, fee}}``."""
    if not db_exists():
        return {}
    try:
        conn = get_connection()
    except Exception:
        return {}
    try:
        rows = conn.execute("SELECT * FROM etfs").fetchall()
        return {
            r["code"]: {
                "name_ja": r["name_ja"],
                "name_en": r["name_en"],
                "fee": r["fee"],
            }
            for r in rows
        }
    finally:
        conn.close()


def search_by_holding(
    holding_code: str, *, n: int = 10, date: str | None = None
) -> pd.DataFrame:
    """Find ETFs holding a given stock, ranked by weight descending."""
    columns = ["code", "name", "weight", "shares", "aum", "date"]
    if not db_exists():
        return pd.DataFrame(columns=columns)
    try:
        conn = get_connection()
    except Exception:
        return pd.DataFrame(columns=columns)
    try:
        if date is None:
            # Match only each ETF's latest snapshot. Scoping MAX(date) to the
            # ETF (not the (ETF, holding) pair) is what excludes stocks the
            # ETF has since dropped — history is append-only.
            sql = """
                SELECT h.code, h.date, e.name_ja, e.name_en,
                    h.weight, h.shares, h.name AS holding_name
                FROM pcf_holdings h
                LEFT JOIN etfs e ON h.code = e.code
                WHERE h.holding_code = ?
                  AND h.date = (
                      SELECT MAX(h2.date) FROM pcf_holdings h2
                      WHERE h2.code = h.code
                  )
                ORDER BY h.weight DESC
                LIMIT ?
            """
            rows = conn.execute(sql, (holding_code, n)).fetchall()
        else:
            sql = """
                SELECT h.code, h.date, e.name_ja, e.name_en,
                    h.weight, h.shares, h.name AS holding_name
                FROM pcf_holdings h
                LEFT JOIN etfs e ON h.code = e.code
                WHERE h.holding_code = ? AND h.date = ?
                ORDER BY h.weight DESC
                LIMIT ?
            """
            rows = conn.execute(sql, (holding_code, date, n)).fetchall()
        if not rows:
            return pd.DataFrame(columns=columns)

        from ..config import config

        name_key = "name_ja" if config.lang == "ja" else "name_en"
        aum_map = {
            r["code"]: r["aum"]
            for r in conn.execute(_AUM_SQL).fetchall()
            if r["aum"] is not None
        }
        return pd.DataFrame(
            [
                {
                    "code": r["code"],
                    "name": r[name_key] or r["holding_name"] or "",
                    "weight": r["weight"],
                    "shares": r["shares"],
                    "aum": aum_map.get(r["code"]),
                    "date": r["date"],
                }
                for r in rows
            ]
        )
    finally:
        conn.close()


def read_history(etf_code: str, holding_code: str | None = None) -> pd.DataFrame:
    """Return weight history for an ETF.

    If holding_code given: time series of that stock's weight in the ETF.
    If None: latest top holdings with weight change from earliest date.

    Reads the full-history DB (``etf sync --full``) when present; otherwise
    falls back to the default DB, which may hold only the latest snapshot.
    """
    from .db_core import full_db_exists

    use_full = full_db_exists()
    if not use_full and not db_exists():
        return pd.DataFrame()
    try:
        conn = get_connection(full=use_full)
    except Exception:
        return pd.DataFrame()
    try:
        if holding_code is not None:
            rows = conn.execute(
                "SELECT date, weight, shares, price FROM pcf_holdings "
                "WHERE code = ? AND holding_code = ? ORDER BY date",
                (etf_code, holding_code),
            ).fetchall()
            if not rows:
                return pd.DataFrame(columns=["date", "weight", "shares", "price"])
            return pd.DataFrame(
                [
                    {
                        "date": r["date"],
                        "weight": r["weight"],
                        "shares": r["shares"],
                        "price": r["price"],
                    }
                    for r in rows
                ]
            )
        else:
            dates = conn.execute(
                "SELECT DISTINCT date FROM pcf_holdings WHERE code = ? ORDER BY date",
                (etf_code,),
            ).fetchall()
            if not dates:
                return pd.DataFrame(columns=["code", "name", "weight", "weight_change"])
            earliest = dates[0]["date"]
            latest = dates[-1]["date"]

            latest_rows = conn.execute(
                "SELECT h.holding_code, h.name, h.weight, "
                "s.name_ja, s.name_en "
                "FROM pcf_holdings h "
                "LEFT JOIN securities s ON h.holding_code = s.code "
                "WHERE h.code = ? AND h.date = ? "
                "ORDER BY h.weight DESC LIMIT 20",
                (etf_code, latest),
            ).fetchall()
            if not latest_rows:
                return pd.DataFrame(columns=["code", "name", "weight", "weight_change"])

            earliest_weights: dict[str, float] = {}
            if earliest != latest:
                for r in conn.execute(
                    "SELECT holding_code, weight FROM pcf_holdings "
                    "WHERE code = ? AND date = ?",
                    (etf_code, earliest),
                ).fetchall():
                    earliest_weights[r["holding_code"]] = r["weight"]

            from ..config import config

            name_key = "name_ja" if config.lang == "ja" else "name_en"
            return pd.DataFrame(
                [
                    {
                        "code": r["holding_code"],
                        "name": r[name_key] or r["name"] or "",
                        "weight": r["weight"],
                        "weight_change": (
                            r["weight"] - earliest_weights.get(r["holding_code"], 0.0)
                            if earliest_weights
                            else 0.0
                        ),
                    }
                    for r in latest_rows
                ]
            )
    finally:
        conn.close()


def concentration_stats(*, n: int | None = None, by: str = "top1") -> pd.DataFrame:
    """Rank ETFs by portfolio concentration (top-holding weight).

    Weights (``top1``/``top3``/``top10``) are fractions, matching
    ``search_by_holding`` (e.g. ``0.22`` for 22%).
    """
    if not db_exists():
        return pd.DataFrame(columns=_CONCENTRATION_COLUMNS)
    try:
        conn = get_connection()
    except Exception:
        return pd.DataFrame(columns=_CONCENTRATION_COLUMNS)
    try:
        rows = conn.execute(_CONCENTRATION_SQL).fetchall()
        if not rows:
            return pd.DataFrame(columns=_CONCENTRATION_COLUMNS)

        from ..config import config

        name_key = "name_ja" if config.lang == "ja" else "name_en"
        etf_names = {
            r["code"]: r[name_key]
            for r in conn.execute("SELECT code, name_ja, name_en FROM etfs").fetchall()
        }
        aum_map = {
            r["code"]: r["aum"]
            for r in conn.execute(_AUM_SQL).fetchall()
            if r["aum"] is not None
        }

        df = pd.DataFrame(
            [
                {
                    "code": r["code"],
                    "name": etf_names.get(r["code"]) or "",
                    "top_code": r["top_code"],
                    "top_name": r["top_name"],
                    "top1": r["top1"],
                    "top3": r["top3"],
                    "top10": r["top10"],
                    "n_holdings": r["n_holdings"],
                    "aum": aum_map.get(r["code"]),
                }
                for r in rows
            ]
        )
    finally:
        conn.close()

    df = df.sort_values(by, ascending=False).reset_index(drop=True)
    if n is not None:
        df = df.head(n)
    return df.reset_index(drop=True)
