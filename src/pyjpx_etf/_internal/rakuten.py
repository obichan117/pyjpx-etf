"""Rakuten Securities ETF data: fetch, parse, and cache."""

from __future__ import annotations

import csv
import io
import json
import time
from pathlib import Path

import requests

from ..config import _RAKUTEN_URL, config

# Column indices (headerless CSV)
_COL_TICKER = 0  # e.g. "1306.T"
_COL_CODE = 1  # e.g. "01306" (zero-padded)
_COL_NAME_EN = 2
_COL_MARKET = 3  # "東証" for TSE
_COL_FEE = 5  # expense ratio (%)
_COL_RETURN_1M = 9
_COL_RETURN_3M = 10
_COL_RETURN_6M = 11
_COL_RETURN_1Y = 12
_COL_RETURN_3Y = 13
_COL_RETURN_5Y = 14
_COL_RETURN_10Y = 15
_COL_RETURN_YTD = 17
_COL_DIVIDEND_YIELD = 19
_COL_NAME_JA = 22

PERIOD_COLUMNS: dict[str, int] = {
    "1m": _COL_RETURN_1M,
    "3m": _COL_RETURN_3M,
    "6m": _COL_RETURN_6M,
    "1y": _COL_RETURN_1Y,
    "3y": _COL_RETURN_3Y,
    "5y": _COL_RETURN_5Y,
    "10y": _COL_RETURN_10Y,
    "ytd": _COL_RETURN_YTD,
}

_CACHE_TTL = 24 * 3600  # 1 day in seconds
_CACHE_FILE = Path.home() / ".cache" / "pyjpx-etf" / "rakuten.json"

_memory_cache: dict[str, dict] | None = None


def _reset_cache() -> None:
    """Reset in-memory cache. Intended for testing."""
    global _memory_cache  # noqa: PLW0603
    _memory_cache = None


def _fetch_rakuten_csv() -> str:
    """Fetch the Rakuten ETF CSV and return raw text."""
    resp = requests.get(_RAKUTEN_URL, timeout=config.timeout)
    resp.raise_for_status()
    resp.encoding = "utf-8-sig"
    return resp.text


def _parse_float(s: str) -> float | None:
    """Parse a string to float, returning None for empty/invalid values."""
    s = s.strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_code(raw: str) -> str:
    """Strip leading zeros from a code string, handling alphanumeric codes."""
    raw = raw.strip()
    stripped = raw.lstrip("0")
    return stripped if stripped else raw


def _parse_rakuten_csv(text: str) -> dict[str, dict]:
    """Parse headerless Rakuten CSV, filter to TSE only, normalize codes.

    Returns ``{code: {fee, name_ja, name_en, dividend_yield, 1m, 3m, ...}}``.
    """
    result: dict[str, dict] = {}
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) <= _COL_NAME_JA:
            continue
        if row[_COL_MARKET].strip() != "東証ETF":
            continue

        code = _normalize_code(row[_COL_CODE])
        if not code:
            continue

        entry: dict = {
            "name_ja": row[_COL_NAME_JA].strip(),
            "name_en": row[_COL_NAME_EN].strip(),
            "fee": _parse_float(row[_COL_FEE]),
            "dividend_yield": _parse_float(row[_COL_DIVIDEND_YIELD]),
        }
        for period, col_idx in PERIOD_COLUMNS.items():
            entry[period] = _parse_float(row[col_idx])

        result[code] = entry
    return result


def _load_disk_cache() -> dict[str, dict] | None:
    """Read disk cache if it exists and is fresh. Return None otherwise."""
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - data["timestamp"] < _CACHE_TTL:
            return data["rakuten"]
    except Exception:
        pass
    return None


def _save_disk_cache(rakuten: dict[str, dict]) -> None:
    """Write data to disk cache. Fail silently on any error."""
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": time.time(), "rakuten": rakuten}
        _CACHE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def get_rakuten_data(*, refresh: bool = False) -> dict[str, dict]:
    """Return ``{code: {...}}`` from the Rakuten ETF CSV.

    Lookup order: memory cache → disk cache (if < 1 day) → network fetch.
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
        data = _parse_rakuten_csv(_fetch_rakuten_csv())
        _memory_cache = data
        _save_disk_cache(data)
        return _memory_cache
    except Exception:
        if _memory_cache is None:
            _memory_cache = {}
        return _memory_cache
