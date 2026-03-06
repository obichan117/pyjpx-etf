"""Tests for sync.py — download DB from GitHub Releases."""

import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

from pyjpx_etf.config import config
from pyjpx_etf.exceptions import DatabaseError
from pyjpx_etf.sync import sync

_sync_mod = sys.modules["pyjpx_etf.sync"]


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
    def test_skips_if_fresh(self, mock_requests):
        db_file = config.db_path
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_bytes(b"existing")

        path = sync()
        assert path == db_file
        mock_requests.get.assert_not_called()

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
