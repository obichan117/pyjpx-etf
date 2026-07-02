"""pcf.db inputs for the ETF screener.

Read-only queries against the local pcf.db — no extras dependency.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _get_etf_codes(db_path: Path) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT code FROM pcf_info ORDER BY code"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def _get_etf_names(db_path: Path) -> dict[str, str]:
    from ...config import config

    name_col = "name_ja" if config.lang == "ja" else "name_en"
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(f"SELECT code, {name_col} FROM etfs").fetchall()
        return {r[0]: r[1] or "" for r in rows}
    finally:
        conn.close()


def _get_etf_fees(db_path: Path) -> dict[str, float]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT code, fee FROM etfs WHERE fee IS NOT NULL"
        ).fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        conn.close()


def _get_etf_aum(db_path: Path) -> dict[str, float]:
    """Compute AUM for each ETF from the latest date in pcf_info + pcf_holdings."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("""
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
        """).fetchall()
        return {r[0]: r[1] for r in rows if r[1] is not None}
    finally:
        conn.close()
