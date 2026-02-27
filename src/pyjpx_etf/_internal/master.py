"""JPX master list: code → Japanese security name."""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

import pandas as pd
import requests

from ..config import _JPX_MASTER_URL, config

_CACHE_TTL = 7 * 24 * 3600  # 1 week in seconds
_CACHE_FILE = Path.home() / ".cache" / "pyjpx-etf" / "master.json"

_memory_cache: dict[str, str] | None = None


def _fetch_master() -> dict[str, str]:
    """Fetch the JPX master XLS and return ``{code: japanese_name}``."""
    resp = requests.get(_JPX_MASTER_URL, timeout=config.timeout)
    resp.raise_for_status()

    df = pd.read_excel(
        io.BytesIO(resp.content),
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


def _load_disk_cache() -> dict[str, str] | None:
    """Read disk cache if it exists and is fresh. Return None otherwise."""
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - data["timestamp"] < _CACHE_TTL:
            return data["names"]
    except Exception:
        pass
    return None


def _save_disk_cache(names: dict[str, str]) -> None:
    """Write names to disk cache. Fail silently on any error."""
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": time.time(), "names": names}
        _CACHE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def get_japanese_names(*, refresh: bool = False) -> dict[str, str]:
    """Return ``{code: japanese_name}`` from the JPX master list.

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
        names = _fetch_master()
        _memory_cache = names
        _save_disk_cache(names)
        return _memory_cache
    except Exception:
        if _memory_cache is None:
            _memory_cache = {}
        return _memory_cache
