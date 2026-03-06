"""Tests for sync.py — download DB from GitHub Releases."""

from unittest.mock import MagicMock, patch

import pytest

from pyjpx_etf.config import config
from pyjpx_etf.exceptions import DatabaseError
from pyjpx_etf.sync import sync


@pytest.fixture(autouse=True)
def _db_path(tmp_path):
    original = config.db_path
    config.db_path = tmp_path / "pcf.db"
    yield
    config.db_path = original


class TestSync:
    @patch("pyjpx_etf.sync.requests.get")
    def test_downloads_db(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"x" * 100]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value.__enter__ = lambda s: mock_resp
        mock_get.return_value = mock_resp

        path = sync(force=True)
        assert path.is_file()
        assert path.read_bytes() == b"x" * 100

    @patch("pyjpx_etf.sync.requests.get")
    def test_skips_if_fresh(self, mock_get, tmp_path):
        # Create a "fresh" DB file
        db_file = config.db_path
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_bytes(b"existing")

        path = sync()
        assert path == db_file
        mock_get.assert_not_called()

    @patch("pyjpx_etf.sync.requests.get")
    def test_force_redownloads(self, mock_get, tmp_path):
        db_file = config.db_path
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_bytes(b"existing")

        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "0"}
        mock_resp.iter_content.return_value = [b"new"]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        path = sync(force=True)
        assert path.read_bytes() == b"new"

    @patch("pyjpx_etf.sync.requests.get")
    def test_raises_on_failure(self, mock_get, tmp_path):
        import requests

        mock_get.side_effect = requests.RequestException("network error")
        with pytest.raises(DatabaseError, match="Failed to download"):
            sync(force=True)
