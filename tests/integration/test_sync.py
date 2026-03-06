"""Integration tests for sync (downloading DB from GitHub Releases).

These tests require the db-latest release to exist on GitHub.
They are skipped if the release returns 404.
"""

import pytest
import requests

from pyjpx_etf import sync
from pyjpx_etf._internal.db import db_exists
from pyjpx_etf.config import _DB_RELEASE_URL


def _release_exists() -> bool:
    """Check if the db-latest release is available."""
    try:
        resp = requests.head(_DB_RELEASE_URL, timeout=10, allow_redirects=True)
        return resp.status_code == 200
    except requests.RequestException:
        return False


_skip_no_release = pytest.mark.skipif(
    not _release_exists(),
    reason="db-latest release not published yet",
)


@pytest.mark.integration
@_skip_no_release
class TestSync:
    def test_sync_downloads_db(self, tmp_path, monkeypatch):
        from pyjpx_etf.config import config

        monkeypatch.setattr(config, "db_path", tmp_path / "pcf.db")
        assert not db_exists()

        path = sync(force=True)

        assert path.exists()
        assert path.stat().st_size > 0
        assert db_exists()

    def test_sync_skips_fresh_db(self, tmp_path, monkeypatch):
        from pyjpx_etf.config import config

        monkeypatch.setattr(config, "db_path", tmp_path / "pcf.db")
        path1 = sync(force=True)
        mtime1 = path1.stat().st_mtime

        path2 = sync(force=False)
        mtime2 = path2.stat().st_mtime

        assert mtime1 == mtime2  # not re-downloaded

    def test_sync_force_redownloads(self, tmp_path, monkeypatch):
        from pyjpx_etf.config import config
        import time

        monkeypatch.setattr(config, "db_path", tmp_path / "pcf.db")
        path1 = sync(force=True)
        mtime1 = path1.stat().st_mtime

        time.sleep(1.1)

        path2 = sync(force=True)
        mtime2 = path2.stat().st_mtime

        assert mtime2 > mtime1
