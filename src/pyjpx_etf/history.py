"""Historical weight tracking for ETF holdings."""

from __future__ import annotations

import pandas as pd

from ._internal.db import read_history
from .exceptions import DatabaseError

__all__ = ["history"]


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

    Notes
    -----
    Full history requires the full-history database (``etf sync --full``).
    Without it, this falls back to the default database, which may contain
    only each ETF's latest snapshot.
    """
    import sys

    from ._internal.db import db_exists, full_db_exists
    from .etf import _ensure_db

    _ensure_db()
    if not full_db_exists():
        if not db_exists():
            raise DatabaseError(
                "Local database not found. Check your network connection."
            )
        print(
            "Hint: full weight history requires `etf sync --full` "
            "(falling back to the default DB, which may hold only the "
            "latest snapshot).",
            file=sys.stderr,
        )
    return read_history(etf_code, holding_code)
