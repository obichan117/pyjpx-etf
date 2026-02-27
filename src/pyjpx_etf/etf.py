"""ETF class — main entry point."""

from __future__ import annotations

import pandas as pd

from ._internal.fetcher import fetch_pcf
from ._internal.parser import parse_pcf
from .models import ETFInfo, Holding


class ETF:
    """Fetch and access JPX ETF portfolio composition data.

    Data is lazy-loaded from PCF providers on first property access.

    Usage::

        import pyjpx_etf as etf

        e = etf.ETF("1306")
        e.info.name          # "TOPIX ETF"
        e.holdings[:5]       # first 5 holdings
        e.to_dataframe()     # pandas DataFrame
    """

    def __init__(self, code: str) -> None:
        self._code = str(code)
        self._info: ETFInfo | None = None
        self._holdings: list[Holding] | None = None

    def _load(self) -> None:
        csv_text = fetch_pcf(self._code)
        self._info, self._holdings = parse_pcf(csv_text)

    @property
    def info(self) -> ETFInfo:
        if self._info is None:
            self._load()
        return self._info  # type: ignore[return-value]

    @property
    def holdings(self) -> list[Holding]:
        if self._holdings is None:
            self._load()
        return self._holdings  # type: ignore[return-value]

    def to_dataframe(self) -> pd.DataFrame:
        """Return holdings as a pandas DataFrame."""
        return pd.DataFrame([h.to_dict() for h in self.holdings])

    def __repr__(self) -> str:
        return f"ETF('{self._code}')"
