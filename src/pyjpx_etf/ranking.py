"""ETF ranking by period returns."""

from __future__ import annotations

import pandas as pd

from ._internal.rakuten import PERIOD_COLUMNS, get_rakuten_data
from .config import config

_VALID_PERIODS = tuple(PERIOD_COLUMNS.keys())


def ranking(period: str = "1m", n: int = 10) -> pd.DataFrame:
    """Return a DataFrame of TSE ETFs ranked by return for the given period.

    Parameters
    ----------
    period : str
        One of ``1m``, ``3m``, ``6m``, ``1y``, ``3y``, ``5y``, ``10y``, ``ytd``.
    n : int
        Positive for top N (descending), negative for worst N (ascending),
        0 for all (sorted descending).

    Returns
    -------
    pd.DataFrame
        Columns: ``code``, ``name``, ``return``, ``fee``, ``dividend_yield``.
    """
    if period not in _VALID_PERIODS:
        raise ValueError(
            f"period must be one of {_VALID_PERIODS}, got {period!r}"
        )

    data = get_rakuten_data()
    if not data:
        return pd.DataFrame(columns=["code", "name", "return", "fee", "dividend_yield"])

    name_key = "name_ja" if config.lang == "ja" else "name_en"

    rows = []
    for code, entry in data.items():
        ret = entry.get(period)
        if ret is None:
            continue
        rows.append(
            {
                "code": code,
                "name": entry.get(name_key, ""),
                "return": ret,
                "fee": entry.get("fee"),
                "dividend_yield": entry.get("dividend_yield"),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    ascending = n < 0
    df = df.sort_values("return", ascending=ascending).reset_index(drop=True)

    if n == 0:
        return df

    return df.head(abs(n)).reset_index(drop=True)
