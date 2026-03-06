"""Historical weight tracking for ETF holdings."""

from __future__ import annotations

import pandas as pd

from ._internal.db import read_history
from .exceptions import DatabaseError


def history(etf_code: str, holding_code: str | None = None) -> pd.DataFrame:
    """Return weight history for an ETF.

    Parameters
    ----------
    etf_code : str
        The ETF code (e.g. "1306").
    holding_code : str | None
        If given, returns weight of that stock over time.
        If None, returns top holdings with weight change from earliest date.

    Returns
    -------
    pd.DataFrame
        If holding_code given: ``date``, ``weight``, ``shares``, ``price``.
        If None: ``code``, ``name``, ``weight``, ``weight_change``.

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
    return read_history(etf_code, holding_code)
