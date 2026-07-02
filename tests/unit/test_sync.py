"""Tests for sync.py — download DB from GitHub Releases."""

import importlib
import os
import time
from email.utils import parsedate_to_datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from pyjpx_etf.config import config
from pyjpx_etf.exceptions import DatabaseError
from pyjpx_etf.sync import sync

# pyjpx_etf.sync is shadowed by the function in __init__.py.
_sync_mod = importlib.import_module("pyjpx_etf.sync")


@pytest.fixture(autouse=True)
def _db_path(tmp_path):
    original = config.db_path
    config.db_path = tmp_path / "pcf.db"
    yield
    config.db_path = original


class TestSync:
    @patch.object(_sync_mod, "requests")
    def test_downloads_db(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"x" * 100]
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        path = sync(force=True)
        assert path.is_file()
        assert path.read_bytes() == b"x" * 100

    @patch.object(_sync_mod, "requests")
    def test_skips_when_remote_not_newer(self, mock_requests):
        db_file = config.db_path
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_bytes(b"existing")

        mock_head_resp = MagicMock()
        mock_head_resp.raise_for_status.return_value = None
        # Last-Modified older than the local file's mtime.
        old_mtime = db_file.stat().st_mtime - 3600
        mock_head_resp.headers = {
            "last-modified": time.strftime(
                "%a, %d %b %Y %H:%M:%S GMT", time.gmtime(old_mtime)
            )
        }
        mock_requests.head.return_value = mock_head_resp

        path = sync()
        assert path == db_file
        mock_requests.get.assert_not_called()

    @patch.object(_sync_mod, "requests")
    def test_downloads_when_remote_newer(self, mock_requests):
        db_file = config.db_path
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_bytes(b"existing")
        old_mtime = time.time() - 2 * 24 * 3600
        os.utime(db_file, (old_mtime, old_mtime))

        mock_head_resp = MagicMock()
        mock_head_resp.raise_for_status.return_value = None
        mock_head_resp.headers = {
            "last-modified": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        }
        mock_requests.head.return_value = mock_head_resp

        mock_get_resp = MagicMock()
        mock_get_resp.headers = {"content-length": "3"}
        mock_get_resp.iter_content.return_value = [b"new"]
        mock_get_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_get_resp

        path = sync()
        assert path.read_bytes() == b"new"
        mock_requests.get.assert_called_once()

    @patch.object(_sync_mod, "requests")
    def test_offline_keeps_local(self, mock_requests):
        db_file = config.db_path
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_bytes(b"existing")

        mock_requests.RequestException = requests.RequestException
        mock_requests.head.side_effect = requests.RequestException("offline")

        path = sync()
        assert path == db_file
        assert path.read_bytes() == b"existing"
        mock_requests.get.assert_not_called()

    @patch.object(_sync_mod, "requests")
    def test_download_sets_mtime_from_remote(self, mock_requests):
        mock_resp = MagicMock()
        last_modified = "Wed, 01 Jul 2026 23:00:00 GMT"
        mock_resp.headers = {"content-length": "3", "last-modified": last_modified}
        mock_resp.iter_content.return_value = [b"new"]
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        path = sync(force=True)
        assert path.stat().st_mtime == pytest.approx(
            parsedate_to_datetime(last_modified).timestamp()
        )

    @patch.object(_sync_mod, "requests")
    def test_force_redownloads(self, mock_requests):
        db_file = config.db_path
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_bytes(b"existing")

        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "0"}
        mock_resp.iter_content.return_value = [b"new"]
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        path = sync(force=True)
        assert path.read_bytes() == b"new"

    @patch.object(_sync_mod, "requests")
    def test_raises_on_failure(self, mock_requests):
        mock_requests.get.side_effect = requests.RequestException(
            "network error",
        )
        mock_requests.RequestException = requests.RequestException
        with pytest.raises(DatabaseError, match="Failed to download"):
            sync(force=True)
