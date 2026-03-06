"""Tests for history.py — historical weight tracking."""

import importlib
from unittest.mock import patch

import pandas as pd
import pytest

from pyjpx_etf.exceptions import DatabaseError
from pyjpx_etf.history import history

# pyjpx_etf.history is shadowed by the function in __init__.py.
_history_mod = importlib.import_module("pyjpx_etf.history")


class TestHistory:
    @patch("pyjpx_etf._internal.db_core.db_path")
    def test_raises_without_db(self, mock_path, tmp_path):
        mock_path.return_value = tmp_path / "nonexistent.db"
        with pytest.raises(DatabaseError, match="Local database not found"):
            history("1306")

    @patch.object(_history_mod, "read_history")
    @patch("pyjpx_etf._internal.db_core.db_path")
    def test_with_holding_code(self, mock_path, mock_read, tmp_path):
        fake_db = tmp_path / "test.db"
        fake_db.write_bytes(b"fake")
        mock_path.return_value = fake_db
        mock_read.return_value = pd.DataFrame(
            [{"date": "2026-03-01", "weight": 0.6, "shares": 1000, "price": 2500}]
        )
        df = history("1306", "7203")
        mock_read.assert_called_once_with("1306", "7203")
        assert len(df) == 1

    @patch.object(_history_mod, "read_history")
    @patch("pyjpx_etf._internal.db_core.db_path")
    def test_overview(self, mock_path, mock_read, tmp_path):
        fake_db = tmp_path / "test.db"
        fake_db.write_bytes(b"fake")
        mock_path.return_value = fake_db
        mock_read.return_value = pd.DataFrame(
            [{"code": "7203", "name": "TOYOTA", "weight": 0.6, "weight_change": 0.05}]
        )
        df = history("1306")
        mock_read.assert_called_once_with("1306", None)
        assert "weight_change" in df.columns
