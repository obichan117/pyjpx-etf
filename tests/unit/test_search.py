"""Tests for search.py — reverse stock search."""

from unittest.mock import patch

import pandas as pd
import pytest

from pyjpx_etf.exceptions import DatabaseError
from pyjpx_etf.search import search


class TestSearch:
    @patch("pyjpx_etf._internal.db_core.db_path")
    def test_raises_without_db(self, mock_path, tmp_path):
        mock_path.return_value = tmp_path / "nonexistent.db"
        with pytest.raises(DatabaseError, match="Local database not found"):
            search("7203")

    @patch("pyjpx_etf.search.search_by_holding")
    @patch("pyjpx_etf._internal.db_core.db_path")
    def test_delegates_to_db(self, mock_path, mock_search, tmp_path):
        # Create a fake DB file so db_exists() returns True
        fake_db = tmp_path / "test.db"
        fake_db.write_bytes(b"fake")
        mock_path.return_value = fake_db
        mock_search.return_value = pd.DataFrame(
            [{"code": "1306", "name": "TOPIX", "weight": 0.6, "shares": 1000}]
        )
        df = search("7203", n=5)
        mock_search.assert_called_once_with("7203", n=5, date=None)
        assert len(df) == 1
        assert df.iloc[0]["code"] == "1306"

    @patch("pyjpx_etf.search.search_by_holding")
    @patch("pyjpx_etf._internal.db_core.db_path")
    def test_passes_date(self, mock_path, mock_search, tmp_path):
        fake_db = tmp_path / "test.db"
        fake_db.write_bytes(b"fake")
        mock_path.return_value = fake_db
        mock_search.return_value = pd.DataFrame()
        search("7203", date="2026-03-01")
        mock_search.assert_called_once_with("7203", n=10, date="2026-03-01")
