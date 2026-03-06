"""Tests for _internal/pipeline.py — pipeline orchestrator."""

import datetime
from unittest.mock import patch

import pytest

from pyjpx_etf._internal import db
from pyjpx_etf._internal.pipeline import (
    _fetch_all_etf_codes,
    _fetch_and_store_pcf,
    run_pipeline,
)
from pyjpx_etf.config import config
from pyjpx_etf.models import ETFInfo, Holding


@pytest.fixture()
def tmp_db(tmp_path):
    db_file = tmp_path / "test.db"
    original = config.db_path
    config.db_path = db_file
    conn = db.get_connection(readonly=False)
    db.init_schema(conn)
    yield conn, db_file
    conn.close()
    config.db_path = original


class TestFetchAllCodes:
    @patch(
        "pyjpx_etf._internal.rakuten.get_rakuten_data",
        return_value={"2644": {}, "1306": {}},
    )
    def test_returns_sorted_codes(self, mock_data):
        codes = _fetch_all_etf_codes()
        assert codes == ["1306", "2644"]
        mock_data.assert_called_once_with(refresh=True)


class TestFetchAndStorePcf:
    @patch("pyjpx_etf._internal.parser.parse_pcf")
    @patch("pyjpx_etf._internal.fetcher.fetch_pcf", return_value="csv_text")
    def test_success(self, mock_fetch, mock_parse, tmp_db):
        info = ETFInfo(
            code="1306", name="TOPIX", cash_component=1000.0,
            shares_outstanding=100000, date=datetime.date(2026, 3, 1),
        )
        holdings = [
            Holding(code="7203", name="TOYOTA", isin="JP001", exchange="TSE",
                    currency="JPY", shares=1000.0, price=2500.0, weight=1.0),
        ]
        mock_parse.return_value = (info, holdings)
        conn, _ = tmp_db

        result = _fetch_and_store_pcf(conn, "1306", "2026-03-01")
        assert result is True
        conn.commit()

        row = conn.execute("SELECT * FROM pcf_info WHERE code='1306'").fetchone()
        assert row is not None

    @patch("pyjpx_etf._internal.fetcher.fetch_pcf", side_effect=Exception("fail"))
    def test_failure_returns_false(self, mock_fetch, tmp_db):
        conn, _ = tmp_db
        result = _fetch_and_store_pcf(conn, "9999", "2026-03-01")
        assert result is False


class TestRunPipeline:
    @patch("pyjpx_etf._internal.pipeline._store_master_names")
    @patch("pyjpx_etf._internal.pipeline._store_fees")
    @patch("pyjpx_etf._internal.pipeline._fetch_and_store_pcf", return_value=True)
    @patch(
        "pyjpx_etf._internal.pipeline._fetch_all_etf_codes",
        return_value=["1306"],
    )
    def test_runs_full_pipeline(self, mock_codes, mock_pcf, mock_fees, mock_names, tmp_path):
        db_file = tmp_path / "pipeline.db"
        run_pipeline(db_file)
        assert db_file.is_file()
        mock_codes.assert_called_once()
        mock_pcf.assert_called_once()
        mock_fees.assert_called_once()
        mock_names.assert_called_once()
