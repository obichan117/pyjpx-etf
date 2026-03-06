"""Reverse stock search: find ETFs holding a given stock."""

from __future__ import annotations

import pandas as pd

from ._internal.db import search_by_holding
from .exceptions import DatabaseError


def search(
    stock_code: str, *, n: int = 10, date: str | None = None
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

    Returns
    -------
    pd.DataFrame
        Columns: ``code``, ``name``, ``weight``, ``shares``.

    Raises
    ------
    DatabaseError
        If the local database does not exist. Run ``etf sync`` first.
    """
    from ._internal.db import db_exists
    from .etf import _ensure_db

    _ensure_db()
    if not db_exists():
        raise DatabaseError(
            "Local database not found. Check your network connection."
        )
    return search_by_holding(stock_code, n=n, date=date)
