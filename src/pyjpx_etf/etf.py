"""ETF class — main entry point."""

from __future__ import annotations

import warnings
from dataclasses import replace

import pandas as pd

from ._internal.fetcher import fetch_pcf
from ._internal.master import get_japanese_names
from ._internal.parser import parse_pcf
from .config import config
from .models import ETFInfo, Holding


class ETF:
    """Fetch and access JPX ETF portfolio composition data.

    Data is lazy-loaded from PCF providers on first property access.

    Usage::

        import pyjpx_etf as etf

        e = etf.ETF("1306")
        e.info.name          # "TOPIX連動型上場投資信託"
        e.holdings[:5]       # first 5 holdings
        e.to_dataframe()     # pandas DataFrame
    """

    def __init__(self, code: str) -> None:
        self._code = str(code)
        self._info: ETFInfo | None = None
        self._holdings: list[Holding] | None = None

    def _load(self) -> None:
        csv_text = fetch_pcf(self._code)
        info, holdings = parse_pcf(csv_text)

        if config.lang == "ja":
            names = get_japanese_names()
            if names:
                # Collect all non-empty codes that need translation
                all_codes = {info.code} | {h.code for h in holdings}
                all_codes.discard("")
                missing = all_codes - names.keys()

                # Refresh once if any codes are missing
                if missing:
                    names = get_japanese_names(refresh=True)
                    missing = all_codes - names.keys()

                # Warn about codes still missing after refresh
                if missing:
                    warnings.warn(
                        f"Japanese names not found for: {sorted(missing)}",
                        stacklevel=2,
                    )

                ja_name = names.get(info.code)
                if ja_name:
                    info = replace(info, name=ja_name)

                holdings = [
                    replace(h, name=names[h.code]) if h.code in names else h
                    for h in holdings
                ]

        self._info = info
        self._holdings = holdings

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

    def top(self, n: int = 10) -> pd.DataFrame:
        """Return top N holdings by weight with code, name, and weight (%)."""
        df = self.to_dataframe()
        return (
            df.nlargest(n, "weight")[["code", "name", "weight"]]
            .assign(weight=lambda d: d["weight"] * 100)
            .reset_index(drop=True)
        )

    def __repr__(self) -> str:
        return f"ETF('{self._code}')"
