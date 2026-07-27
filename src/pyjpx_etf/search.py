"""Reverse stock search: find ETFs holding a given stock."""

from __future__ import annotations

import pandas as pd

from ._internal.db import search_by_holding
from .exceptions import DatabaseError

__all__ = ["search"]


def search(
    stock_code: str,
    *,
    n: int = 10,
    date: str | None = None,
    gap: float | None = None,
) -> pd.DataFrame:
    """Find ETFs that hold a given stock, ranked by weight.

    Parameters
    ----------
    stock_code : str
        The stock code to search for (e.g. "6857" for Advantest).
    n : int
        Number of results to return.
    date : str | None
        Specific date (YYYY-MM-DD). Uses latest available if None.
    gap : float | None
        If given, adds an ``impact`` column estimating each ETF's NAV
        impact in percent: ``weight`` (fraction) × ``gap`` (percent).
        E.g. a stock that moved +8% (``gap=8.0``) with a 20% weight in an
        ETF gives an impact of +1.6%.

    Returns
    -------
    pd.DataFrame
        Columns: ``code``, ``name``, ``weight``, ``shares``, ``aum``,
        ``date`` (the snapshot date each row's weight comes from).
        Adds ``impact`` when ``gap`` is given.

    Raises
    ------
    DatabaseError
        If the local database does not exist. Run ``etf sync`` first.
    """
    from ._internal.db import db_exists
    from .etf import _ensure_db

    _ensure_db()
    if not db_exists():
        raise DatabaseError("Local database not found. Check your network connection.")
    df = search_by_holding(stock_code, n=n, date=date)
    if gap is not None:
        df = df.copy()
        df["impact"] = df["weight"] * gap
    return df
