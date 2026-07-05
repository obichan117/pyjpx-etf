"""ETF concentration: rank ETFs by top-holding weight."""

from __future__ import annotations

import pandas as pd

from ._internal.db import concentration_stats
from .exceptions import DatabaseError

__all__ = ["concentration"]

_VALID_BY = ("top1", "top3", "top10")


def concentration(*, n: int = 20, by: str = "top1") -> pd.DataFrame:
    """Rank ETFs by portfolio concentration (top-holding weight).

    Parameters
    ----------
    n : int
        Number of results to return.
    by : str
        Concentration stat to sort by: ``"top1"``, ``"top3"``, or ``"top10"``.

    Returns
    -------
    pd.DataFrame
        Columns: ``code``, ``name``, ``top_code``, ``top_name``, ``top1``,
        ``top3``, ``top10``, ``n_holdings``, ``aum``. Weights (``top1``,
        ``top3``, ``top10``) are fractions (e.g. ``0.22`` for 22%).

    Raises
    ------
    ValueError
        If ``by`` is not one of ``"top1"``, ``"top3"``, ``"top10"``.
    DatabaseError
        If the local database does not exist. Run ``etf sync`` first.
    """
    if by not in _VALID_BY:
        raise ValueError(f"by must be one of {_VALID_BY}, got {by!r}")

    from ._internal.db import db_exists
    from .etf import _ensure_db

    _ensure_db()
    if not db_exists():
        raise DatabaseError("Local database not found. Check your network connection.")
    return concentration_stats(n=n, by=by)
