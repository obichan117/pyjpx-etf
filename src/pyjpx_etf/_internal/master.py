"""JPX master list: code → Japanese security name."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

from ..config import _JPX_MASTER_URL, config
from ._cache import TieredCache


def _fetch_master_xls() -> bytes:
    """Fetch the JPX master XLS and return raw bytes."""
    resp = requests.get(_JPX_MASTER_URL, timeout=config.timeout)
    resp.raise_for_status()
    return resp.content


def _parse_master_xls(content: bytes) -> dict[str, str]:
    """Parse JPX master XLS bytes into ``{code: japanese_name}``."""
    # xlrd is required for .xls format (see pyproject.toml)
    df = pd.read_excel(
        io.BytesIO(content),
        header=None,
        dtype=str,
    )
    # Column 1 = security code (4-digit string), column 2 = Japanese name
    lookup: dict[str, str] = {}
    for _, row in df.iterrows():
        code = str(row.iloc[1]).strip()
        name = str(row.iloc[2]).strip()
        if code and name and code != "nan" and name != "nan":
            lookup[code] = name
    return lookup


def _fetch_and_parse() -> dict[str, str]:
    return _parse_master_xls(_fetch_master_xls())


_cache = TieredCache(
    disk_path=Path.home() / ".cache" / "pyjpx-etf" / "master.json",
    ttl=7 * 24 * 3600,
    key="names",
    fetcher=_fetch_and_parse,
)

_reset_cache = _cache.reset


def get_japanese_names(*, refresh: bool = False) -> dict[str, str]:
    """Return ``{code: japanese_name}`` from the JPX master list.

    Lookup order: memory cache → disk cache (if < 1 week) → network fetch.
    Pass ``refresh=True`` to skip both caches and fetch fresh data.
    Returns an empty dict if the fetch or parse fails (graceful degradation).
    """
    return _cache.get(refresh=refresh)
