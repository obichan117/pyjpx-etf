"""ETF class — main entry point."""

from __future__ import annotations

import warnings
from dataclasses import replace

import pandas as pd

from ._internal.fees import get_fees
from ._internal.fetcher import fetch_pcf
from ._internal.master import get_japanese_names
from ._internal.rakuten import get_rakuten_data
from ._internal.parser import parse_pcf
from .config import config
from .models import ETFInfo, Holding


def _resolve_japanese_names(
    info: ETFInfo, holdings: list[Holding]
) -> tuple[ETFInfo, list[Holding]]:
    """Replace English names with Japanese names from the JPX master list.

    Fetches the master list, refreshes once if any codes are missing,
    and warns about codes still missing after refresh.
    """
    names = get_japanese_names()
    if not names:
        return info, holdings

    all_codes = {info.code} | {h.code for h in holdings}
    all_codes.discard("")
    missing = all_codes - names.keys()

    if missing:
        names = get_japanese_names(refresh=True)
        missing = all_codes - names.keys()

    if missing:
        warnings.warn(
            f"Japanese names not found for: {sorted(missing)}",
            stacklevel=3,
        )

    ja_name = names.get(info.code)
    if ja_name:
        info = replace(info, name=ja_name)

    holdings = [
        replace(h, name=names[h.code]) if h.code in names else h
        for h in holdings
    ]

    return info, holdings


_UNSET = object()  # sentinel: "not loaded yet" vs "loaded but None"


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
        self._fee: float | None | object = _UNSET

    def _load(self) -> None:
        csv_text = fetch_pcf(self._code)
        info, holdings = parse_pcf(csv_text)

        if config.lang == "ja":
            info, holdings = _resolve_japanese_names(info, holdings)

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

    @property
    def fee(self) -> float | None:
        """Trust fee (信託報酬) as a percentage value, e.g. ``0.06`` for 0.06%.

        Fetched independently from the JPX ETF list page (does not trigger PCF load).
        Returns ``None`` if the fee is unavailable.
        """
        if self._fee is _UNSET:
            fees = get_fees()
            fee = fees.get(self._code)
            if fee is None:
                rakuten = get_rakuten_data()
                entry = rakuten.get(self._code)
                if entry is not None:
                    fee = entry.get("fee")
            self._fee = fee
        return self._fee  # type: ignore[return-value]

    @property
    def nav(self) -> int:
        """Total fund net asset value in yen.

        Computed as cash_component + sum(shares * price) for all holdings.
        Triggers PCF data load on first access.
        """
        total_mv = sum(h.shares * h.price for h in self.holdings)
        return round(self.info.cash_component + total_mv)

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
