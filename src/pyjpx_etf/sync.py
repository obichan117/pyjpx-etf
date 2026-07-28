"""Download PCF database from GitHub Releases."""

from __future__ import annotations

import gzip
import os
import shutil
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

from .config import _DB_FULL_URL, _DB_LATEST_URL, _DB_LEGACY_URL, config
from .exceptions import DatabaseError

__all__ = ["sync"]


def _remote_mtime(url: str) -> float | None:
    """Last-Modified of the release asset as a Unix timestamp, or None."""
    try:
        resp = requests.head(url, allow_redirects=True, timeout=config.timeout)
        resp.raise_for_status()
        last_modified = resp.headers.get("last-modified")
        if last_modified:
            return parsedate_to_datetime(last_modified).timestamp()
    except (requests.RequestException, TypeError, ValueError):
        pass
    return None


def _download(url: str, dest: Path, *, gunzip: bool) -> requests.Response:
    """Stream *url* to *dest* (decompressing if *gunzip*), atomically."""
    resp = requests.get(url, stream=True, timeout=config.timeout)
    resp.raise_for_status()

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
                        f"\rDownloading {dest.name}: {mb:.1f} MB ({pct}%)",
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )
        if total > 0:
            print(file=sys.stderr)  # newline after progress
        if gunzip:
            unpacked = dest.with_suffix(".tmp2")
            try:
                with gzip.open(tmp, "rb") as src, open(unpacked, "wb") as out:
                    shutil.copyfileobj(src, out)
                unpacked.rename(dest)
            finally:
                unpacked.unlink(missing_ok=True)
                tmp.unlink(missing_ok=True)
        else:
            tmp.rename(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return resp


def sync(*, force: bool = False, full: bool = False) -> Path:
    """Download the PCF database from GitHub Releases.

    By default this fetches the small latest-snapshot-only database (a few
    MB), which is all that ``ETF``, ``search``, ``concentration`` and
    ``screen`` need. Pass ``full=True`` to download the full append-only
    history database (hundreds of MB) required by ``history()``; it is
    stored as a separate ``pcf-full.db`` file so daily syncs never
    overwrite it.

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
    full : bool
        Download the full-history database instead of the latest snapshot.

    Returns
    -------
    Path
        Path to the downloaded database file.

    Raises
    ------
    DatabaseError
        If the download fails.
    """
    from ._internal.db import db_path, full_db_path

    url = _DB_FULL_URL if full else _DB_LATEST_URL
    dest = full_db_path() if full else db_path()

    if not force and dest.is_file():
        remote = _remote_mtime(url)
        if remote is None:
            # The .gz asset may not be published yet — check the legacy one.
            remote = _remote_mtime(_DB_LEGACY_URL)
        if remote is None or remote <= dest.stat().st_mtime:
            # offline / header unavailable → keep local copy (graceful degradation)
            return dest

    dest.parent.mkdir(parents=True, exist_ok=True)

    print("Syncing ETF database...", file=sys.stderr, flush=True)

    try:
        try:
            resp = _download(url, dest, gunzip=True)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                # .gz assets not published yet — fall back to the legacy
                # uncompressed full DB (works for both latest and full).
                resp = _download(_DB_LEGACY_URL, dest, gunzip=False)
            else:
                raise
    except requests.RequestException as e:
        raise DatabaseError(
            f"Failed to download database: {e}. "
            "The database may not be published yet. "
            "Run the pipeline first or check the GitHub release."
        ) from e

    last_modified = resp.headers.get("last-modified")
    if last_modified:
        try:
            ts = parsedate_to_datetime(last_modified).timestamp()
            os.utime(dest, (ts, ts))
        except (TypeError, ValueError):
            pass  # leave mtime as-is

    return dest
