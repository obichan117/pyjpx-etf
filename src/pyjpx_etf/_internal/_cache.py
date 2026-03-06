"""Generic 2-tier cache: memory → disk (JSON with TTL) → fetch."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable


class TieredCache:
    """Memory + disk cache with TTL, backed by a fetch function.

    Parameters
    ----------
    disk_path : Path
        JSON file for disk persistence.
    ttl : int
        Time-to-live in seconds for the disk cache.
    key : str
        JSON key under which data is stored (e.g. "names", "fees").
    fetcher : callable
        Zero-arg function that returns fresh data.
    """

    def __init__(
        self,
        disk_path: Path,
        ttl: int,
        key: str,
        fetcher: Callable[[], Any],
    ) -> None:
        self._disk_path = disk_path
        self._ttl = ttl
        self._key = key
        self._fetcher = fetcher
        self._memory: Any | None = None

    def get(self, *, refresh: bool = False) -> Any:
        """Return cached data. Lookup: memory → disk → fetch.

        Pass ``refresh=True`` to skip caches and fetch fresh data.
        Returns an empty dict if fetch fails (graceful degradation).
        """
        if not refresh and self._memory is not None:
            return self._memory

        if not refresh:
            disk = self._load_disk()
            if disk is not None:
                self._memory = disk
                return self._memory

        try:
            data = self._fetcher()
            self._memory = data
            self._save_disk(data)
            return self._memory
        except Exception:
            if self._memory is None:
                self._memory = {}
            return self._memory

    def reset(self) -> None:
        """Clear in-memory cache. Intended for testing."""
        self._memory = None

    def _load_disk(self) -> Any | None:
        try:
            raw = json.loads(self._disk_path.read_text(encoding="utf-8"))
            if time.time() - raw["timestamp"] < self._ttl:
                return raw[self._key]
        except Exception:
            pass
        return None

    def _save_disk(self, data: Any) -> None:
        try:
            self._disk_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"timestamp": time.time(), self._key: data}
            self._disk_path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass
