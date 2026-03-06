"""Download PCF database from GitHub Releases."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

from .config import _DB_RELEASE_URL, config
from .exceptions import DatabaseError


def sync(*, force: bool = False) -> Path:
    """Download pcf.db from GitHub Releases.

    Parameters
    ----------
    force : bool
        Re-download even if local DB is fresh (< 1 day old).

    Returns
    -------
    Path
        Path to the downloaded database file.

    Raises
    ------
    DatabaseError
        If the download fails.
    """
    from ._internal.db import db_path

    dest = db_path()

    if not force and dest.is_file():
        age = time.time() - dest.stat().st_mtime
        if age < 24 * 3600:
            return dest

    dest.parent.mkdir(parents=True, exist_ok=True)

    print("Syncing ETF database...", file=sys.stderr, flush=True)

    try:
        resp = requests.get(_DB_RELEASE_URL, stream=True, timeout=config.timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise DatabaseError(
            f"Failed to download database: {e}. "
            "The database may not be published yet. "
            "Run the pipeline first or check the GitHub release."
        ) from e

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    tmp = dest.with_suffix(".tmp")
    try:
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 // total
                    mb = downloaded / 1_000_000
                    print(
                        f"\rDownloading pcf.db: {mb:.1f} MB ({pct}%)",
                        end="", file=sys.stderr, flush=True,
                    )
        if total > 0:
            print(file=sys.stderr)  # newline after progress
        tmp.rename(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    return dest
