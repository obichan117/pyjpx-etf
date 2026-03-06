"""SQLite read queries — used by the public API."""

from __future__ import annotations

import datetime

import pandas as pd

from ..models import ETFInfo, Holding
from .db_core import db_exists, get_connection


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
        row = conn.execute(
            "SELECT fee FROM etfs WHERE code = ?", (code,)
        ).fetchone()
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
    if not db_exists():
        return pd.DataFrame(columns=["code", "name", "weight", "shares"])
    try:
        conn = get_connection()
    except Exception:
        return pd.DataFrame(columns=["code", "name", "weight", "shares"])
    try:
        if date is None:
            sql = """
                SELECT h.code, e.name_ja, e.name_en,
                    h.weight, h.shares, h.name AS holding_name
                FROM pcf_holdings h
                LEFT JOIN etfs e ON h.code = e.code
                WHERE h.holding_code = ?
                  AND h.date = (
                      SELECT MAX(h2.date) FROM pcf_holdings h2
                      WHERE h2.code = h.code AND h2.holding_code = h.holding_code
                  )
                ORDER BY h.weight DESC
                LIMIT ?
            """
            rows = conn.execute(sql, (holding_code, n)).fetchall()
        else:
            sql = """
                SELECT h.code, e.name_ja, e.name_en,
                    h.weight, h.shares, h.name AS holding_name
                FROM pcf_holdings h
                LEFT JOIN etfs e ON h.code = e.code
                WHERE h.holding_code = ? AND h.date = ?
                ORDER BY h.weight DESC
                LIMIT ?
            """
            rows = conn.execute(sql, (holding_code, date, n)).fetchall()
        if not rows:
            return pd.DataFrame(columns=["code", "name", "weight", "shares"])

        from ..config import config

        name_key = "name_ja" if config.lang == "ja" else "name_en"
        return pd.DataFrame(
            [
                {
                    "code": r["code"],
                    "name": r[name_key] or r["holding_name"] or "",
                    "weight": r["weight"],
                    "shares": r["shares"],
                }
                for r in rows
            ]
        )
    finally:
        conn.close()


def read_history(
    etf_code: str, holding_code: str | None = None
) -> pd.DataFrame:
    """Return weight history for an ETF.

    If holding_code given: time series of that stock's weight in the ETF.
    If None: latest top holdings with weight change from earliest date.
    """
    if not db_exists():
        return pd.DataFrame()
    try:
        conn = get_connection()
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
                return pd.DataFrame(
                    columns=["code", "name", "weight", "weight_change"]
                )
            earliest = dates[0]["date"]
            latest = dates[-1]["date"]

            latest_rows = conn.execute(
                "SELECT holding_code, name, weight FROM pcf_holdings "
                "WHERE code = ? AND date = ? ORDER BY weight DESC LIMIT 20",
                (etf_code, latest),
            ).fetchall()
            if not latest_rows:
                return pd.DataFrame(
                    columns=["code", "name", "weight", "weight_change"]
                )

            earliest_weights: dict[str, float] = {}
            if earliest != latest:
                for r in conn.execute(
                    "SELECT holding_code, weight FROM pcf_holdings "
                    "WHERE code = ? AND date = ?",
                    (etf_code, earliest),
                ).fetchall():
                    earliest_weights[r["holding_code"]] = r["weight"]

            return pd.DataFrame(
                [
                    {
                        "code": r["holding_code"],
                        "name": r["name"] or "",
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
