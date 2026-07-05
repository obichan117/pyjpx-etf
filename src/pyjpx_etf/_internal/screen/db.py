"""pcf.db inputs for the ETF screener.

Read-only queries against the local pcf.db — no extras dependency.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..db_read import _AUM_SQL, _CONCENTRATION_SQL


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
        rows = conn.execute(_AUM_SQL).fetchall()
        return {r[0]: r[1] for r in rows if r[1] is not None}
    finally:
        conn.close()


def _get_concentration(db_path: Path) -> dict[str, dict]:
    """Compute top1/top3/top10 concentration stats for each ETF."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(_CONCENTRATION_SQL).fetchall()
        return {
            r["code"]: {
                "top_code": r["top_code"],
                "top_name": r["top_name"],
                "top1": r["top1"],
                "top3": r["top3"],
                "top10": r["top10"],
                "n_holdings": r["n_holdings"],
            }
            for r in rows
        }
    finally:
        conn.close()
