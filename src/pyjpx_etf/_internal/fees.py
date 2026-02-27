"""JPX ETF fee (信託報酬) data: fetch, parse, and cache."""

from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

from ..config import _JPX_FEE_URL, config

_CACHE_TTL = 7 * 24 * 3600  # 1 week in seconds
_CACHE_FILE = Path.home() / ".cache" / "pyjpx-etf" / "fees.json"

_memory_cache: dict[str, float] | None = None


def _reset_cache() -> None:
    """Reset in-memory cache. Intended for testing."""
    global _memory_cache  # noqa: PLW0603
    _memory_cache = None


def _fetch_fee_html() -> str:
    """Fetch the JPX ETF fee page and return raw HTML."""
    resp = requests.get(_JPX_FEE_URL, timeout=config.timeout)
    resp.raise_for_status()
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
        code_col = None
        fee_col = None
        for col in df.columns:
            col_str = str(col)
            if "コード" in col_str:
                code_col = col
            if "信託報酬" in col_str:
                fee_col = col
        if code_col is None or fee_col is None:
            continue
        for _, row in df.iterrows():
            code = str(row[code_col]).strip()
            # pandas may coerce 4-digit codes to int — normalize
            if code.endswith(".0"):
                code = code[:-2]
            if not code or code == "nan" or not code.isdigit():
                continue
            fee = _parse_fee_string(str(row[fee_col]))
            if fee is not None:
                fees[code] = fee
    return fees


def _load_disk_cache() -> dict[str, float] | None:
    """Read disk cache if it exists and is fresh. Return None otherwise."""
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - data["timestamp"] < _CACHE_TTL:
            return data["fees"]
    except Exception:
        pass
    return None


def _save_disk_cache(fees: dict[str, float]) -> None:
    """Write fees to disk cache. Fail silently on any error."""
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": time.time(), "fees": fees}
        _CACHE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def get_fees(*, refresh: bool = False) -> dict[str, float]:
    """Return ``{code: fee}`` from the JPX ETF fee page.

    Lookup order: memory cache → disk cache (if < 1 week) → network fetch.
    Pass ``refresh=True`` to skip both caches and fetch fresh data.
    Returns an empty dict if the fetch or parse fails (graceful degradation).
    """
    global _memory_cache  # noqa: PLW0603

    if not refresh and _memory_cache is not None:
        return _memory_cache

    if not refresh:
        disk = _load_disk_cache()
        if disk is not None:
            _memory_cache = disk
            return _memory_cache

    try:
        fees = _parse_fee_html(_fetch_fee_html())
        _memory_cache = fees
        _save_disk_cache(fees)
        return _memory_cache
    except Exception:
        if _memory_cache is None:
            _memory_cache = {}
        return _memory_cache
