"""JPX ETF fee (信託報酬) data: fetch, parse, and cache."""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd
import requests

from ..config import _JPX_FEE_URL, config
from ._cache import TieredCache


def _fetch_fee_html() -> str:
    """Fetch the JPX ETF fee page and return raw HTML."""
    resp = requests.get(_JPX_FEE_URL, timeout=config.timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def _parse_fee_string(s: str) -> float | None:
    """Extract the first decimal number from a fee string.

    Handles: "0.048%", "0.06%（注10）", full-width ％, etc.
    Returns the numeric value (e.g. 0.06) or None if unparseable.
    """
    if not isinstance(s, str):
        return None
    # Normalize full-width characters
    s = s.replace("％", "%")
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if match:
        return float(match.group(1))
    return None


def _parse_fee_html(html: str) -> dict[str, float]:
    """Parse JPX ETF fee page HTML into ``{code: fee}``."""
    tables = pd.read_html(io.StringIO(html))
    fees: dict[str, float] = {}
    for df in tables:
        # Find tables that have both コード and 信託報酬 columns
        # Normalize whitespace to handle "信託 報酬" vs "信託報酬"
        code_col = None
        fee_col = None
        for col in df.columns:
            col_norm = "".join(str(col).split())
            if code_col is None and col_norm == "コード":
                code_col = col
            if "信託報酬" in col_norm:
                fee_col = col
        if code_col is None or fee_col is None:
            continue
        for _, row in df.iterrows():
            code = str(row[code_col]).strip()
            # pandas may coerce 4-digit codes to int — normalize
            if code.endswith(".0"):
                code = code[:-2]
            if not code or code == "nan":
                continue
            # Accept numeric codes (e.g. "1306") and alphanumeric (e.g. "200A")
            if not code.isalnum():
                continue
            fee = _parse_fee_string(str(row[fee_col]))
            if fee is not None:
                fees[code] = fee
    return fees


def _fetch_and_parse() -> dict[str, float]:
    return _parse_fee_html(_fetch_fee_html())


_cache = TieredCache(
    disk_path=Path.home() / ".cache" / "pyjpx-etf" / "fees.json",
    ttl=7 * 24 * 3600,
    key="fees",
    fetcher=_fetch_and_parse,
)

_reset_cache = _cache.reset


def get_fees(*, refresh: bool = False) -> dict[str, float]:
    """Return ``{code: fee}`` from the JPX ETF fee page.

    Lookup order: memory cache → disk cache (if < 1 week) → network fetch.
    Pass ``refresh=True`` to skip both caches and fetch fresh data.
    Returns an empty dict if the fetch or parse fails (graceful degradation).
    """
    return _cache.get(refresh=refresh)
