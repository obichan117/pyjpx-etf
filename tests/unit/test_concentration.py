"""Tests for concentration.py — ETF concentration ranking."""

import importlib
from unittest.mock import patch

import pandas as pd
import pytest

from pyjpx_etf.concentration import concentration
from pyjpx_etf.exceptions import DatabaseError

# pyjpx_etf.concentration is shadowed by the function in __init__.py.
_concentration_mod = importlib.import_module("pyjpx_etf.concentration")


class TestConcentration:
    def test_invalid_by_raises(self):
        with pytest.raises(ValueError, match="by must be one of"):
            concentration(by="bogus")

    @patch("pyjpx_etf._internal.db_core.db_path")
    def test_raises_without_db(self, mock_path, tmp_path):
        mock_path.return_value = tmp_path / "nonexistent.db"
        with pytest.raises(DatabaseError, match="Local database not found"):
            concentration()

    @patch.object(_concentration_mod, "concentration_stats")
    @patch("pyjpx_etf._internal.db_core.db_path")
    def test_delegates_to_db(self, mock_path, mock_stats, tmp_path):
        fake_db = tmp_path / "test.db"
        fake_db.write_bytes(b"fake")
        mock_path.return_value = fake_db
        mock_stats.return_value = pd.DataFrame(
            [
                {
                    "code": "282A",
                    "name": "X",
                    "top_code": "285A",
                    "top_name": "Y",
                    "top1": 0.22,
                    "top3": 0.3,
                    "top10": 0.5,
                    "n_holdings": 30,
                    "aum": 1e11,
                }
            ]
        )
        df = concentration(n=5, by="top1")
        mock_stats.assert_called_once_with(n=5, by="top1")
        assert len(df) == 1
        assert df.iloc[0]["code"] == "282A"

    @patch.object(_concentration_mod, "concentration_stats")
    @patch("pyjpx_etf._internal.db_core.db_path")
    def test_defaults(self, mock_path, mock_stats, tmp_path):
        fake_db = tmp_path / "test.db"
        fake_db.write_bytes(b"fake")
        mock_path.return_value = fake_db
        mock_stats.return_value = pd.DataFrame()
        concentration()
        mock_stats.assert_called_once_with(n=20, by="top1")
