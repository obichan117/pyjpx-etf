"""Tests for sync.py — download DB from GitHub Releases."""

import gzip
import importlib
import os
import time
from email.utils import parsedate_to_datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from pyjpx_etf.config import _DB_FULL_URL, _DB_LATEST_URL, _DB_LEGACY_URL, config
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


def _gz_response(payload: bytes, headers: dict | None = None) -> MagicMock:
    """Mock GET response serving *payload* gzipped."""
    gz = gzip.compress(payload)
    resp = MagicMock()
    resp.headers = {"content-length": str(len(gz)), **(headers or {})}
    resp.iter_content.return_value = [gz]
    resp.raise_for_status.return_value = None
    return resp


def _mock_exceptions(mock_requests) -> None:
    """except-clauses in sync.py need the real exception classes."""
    mock_requests.RequestException = requests.RequestException
    mock_requests.HTTPError = requests.HTTPError


class TestSync:
    @patch.object(_sync_mod, "requests")
    def test_downloads_and_decompresses(self, mock_requests):
        _mock_exceptions(mock_requests)
        mock_requests.get.return_value = _gz_response(b"x" * 100)

        path = sync(force=True)
        assert path == config.db_path
        assert path.read_bytes() == b"x" * 100
        assert mock_requests.get.call_args[0][0] == _DB_LATEST_URL

    @patch.object(_sync_mod, "requests")
    def test_full_downloads_to_separate_file(self, mock_requests):
        _mock_exceptions(mock_requests)
        mock_requests.get.return_value = _gz_response(b"full-db")

        path = sync(force=True, full=True)
        assert path.name == "pcf-full.db"
        assert path.read_bytes() == b"full-db"
        assert mock_requests.get.call_args[0][0] == _DB_FULL_URL

    @patch.object(_sync_mod, "requests")
    def test_falls_back_to_legacy_asset_on_404(self, mock_requests):
        _mock_exceptions(mock_requests)
        resp_404 = MagicMock()
        resp_404.raise_for_status.side_effect = requests.HTTPError(
            response=MagicMock(status_code=404)
        )
        resp_legacy = MagicMock()
        resp_legacy.headers = {"content-length": "6"}
        resp_legacy.iter_content.return_value = [b"legacy"]
        resp_legacy.raise_for_status.return_value = None
        mock_requests.get.side_effect = [resp_404, resp_legacy]

        path = sync(force=True)
        assert path.read_bytes() == b"legacy"  # served uncompressed
        urls = [c[0][0] for c in mock_requests.get.call_args_list]
        assert urls == [_DB_LATEST_URL, _DB_LEGACY_URL]

    @patch.object(_sync_mod, "requests")
    def test_skips_when_remote_not_newer(self, mock_requests):
        _mock_exceptions(mock_requests)
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
        _mock_exceptions(mock_requests)
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
        mock_requests.get.return_value = _gz_response(b"new")

        path = sync()
        assert path.read_bytes() == b"new"
        mock_requests.get.assert_called_once()

    @patch.object(_sync_mod, "requests")
    def test_offline_keeps_local(self, mock_requests):
        _mock_exceptions(mock_requests)
        db_file = config.db_path
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_bytes(b"existing")

        mock_requests.head.side_effect = requests.RequestException("offline")

        path = sync()
        assert path == db_file
        assert path.read_bytes() == b"existing"
        mock_requests.get.assert_not_called()

    @patch.object(_sync_mod, "requests")
    def test_download_sets_mtime_from_remote(self, mock_requests):
        _mock_exceptions(mock_requests)
        last_modified = "Wed, 01 Jul 2026 23:00:00 GMT"
        mock_requests.get.return_value = _gz_response(
            b"new", headers={"last-modified": last_modified}
        )

        path = sync(force=True)
        assert path.stat().st_mtime == pytest.approx(
            parsedate_to_datetime(last_modified).timestamp()
        )

    @patch.object(_sync_mod, "requests")
    def test_force_redownloads(self, mock_requests):
        _mock_exceptions(mock_requests)
        db_file = config.db_path
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_bytes(b"existing")

        mock_requests.get.return_value = _gz_response(b"new")

        path = sync(force=True)
        assert path.read_bytes() == b"new"

    @patch.object(_sync_mod, "requests")
    def test_raises_on_failure(self, mock_requests):
        _mock_exceptions(mock_requests)
        mock_requests.get.side_effect = requests.RequestException("network error")
        with pytest.raises(DatabaseError, match="Failed to download"):
            sync(force=True)
