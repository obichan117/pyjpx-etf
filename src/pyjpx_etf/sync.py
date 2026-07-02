"""Download PCF database from GitHub Releases."""

from __future__ import annotations

import os
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

from .config import _DB_RELEASE_URL, config
from .exceptions import DatabaseError

__all__ = ["sync"]


def _remote_mtime() -> float | None:
    """Last-Modified of the release asset as a Unix timestamp, or None."""
    try:
        resp = requests.head(
            _DB_RELEASE_URL, allow_redirects=True, timeout=config.timeout
        )
        resp.raise_for_status()
        last_modified = resp.headers.get("last-modified")
        if last_modified:
            return parsedate_to_datetime(last_modified).timestamp()
    except (requests.RequestException, TypeError, ValueError):
        pass
    return None


def sync(*, force: bool = False) -> Path:
    """Download pcf.db from GitHub Releases.

    Freshness is determined by comparing the release asset's Last-Modified
    header to the local file's mtime: if the remote asset is not newer than
    the local copy, the download is skipped. If the freshness check can't be
    performed (offline, header unavailable), the local copy is kept as a
    graceful degradation.

    Parameters
    ----------
    force : bool
        Re-download even if the local copy matches the remote (i.e. skip the
        freshness check).

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
        remote = _remote_mtime()
        if remote is None or remote <= dest.stat().st_mtime:
            # offline / header unavailable → keep local copy (graceful degradation)
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
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )
        if total > 0:
            print(file=sys.stderr)  # newline after progress
        tmp.rename(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    last_modified = resp.headers.get("last-modified")
    if last_modified:
        try:
            ts = parsedate_to_datetime(last_modified).timestamp()
            os.utime(dest, (ts, ts))
        except (TypeError, ValueError):
            pass  # leave mtime as-is

    return dest
