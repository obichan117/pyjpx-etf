from unittest.mock import patch

import pandas as pd
import pytest

from pyjpx_etf import config
from pyjpx_etf.ranking import ranking

MOCK_RAKUTEN = {
    "1306": {
        "name_ja": "TOPIX連動型上場投資信託",
        "name_en": "TOPIX ETF",
        "fee": 0.06,
        "dividend_yield": 1.95,
        "1m": 2.50,
        "3m": 3.10,
        "6m": 5.20,
        "1y": 10.50,
        "3y": 30.00,
        "5y": 50.00,
        "10y": 100.00,
        "ytd": 1.20,
    },
    "2644": {
        "name_ja": "半導体ETF",
        "name_en": "Semiconductor ETF",
        "fee": 0.41,
        "dividend_yield": 0.50,
        "1m": 5.10,
        "3m": 8.20,
        "6m": 12.30,
        "1y": 25.00,
        "3y": None,
        "5y": None,
        "10y": None,
        "ytd": 3.50,
    },
    "1321": {
        "name_ja": "日経225連動型上場投資信託",
        "name_en": "Nikkei 225 ETF",
        "fee": 0.20,
        "dividend_yield": 1.50,
        "1m": -1.00,
        "3m": 1.50,
        "6m": 3.00,
        "1y": 8.00,
        "3y": 20.00,
        "5y": 40.00,
        "10y": 80.00,
        "ytd": -0.50,
    },
}


@patch("pyjpx_etf.ranking.get_rakuten_data", return_value=MOCK_RAKUTEN)
class TestRanking:
    def setup_method(self):
        config.lang = "ja"

    def test_default_returns_dataframe(self, mock_data):
        df = ranking()
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["code", "name", "return", "fee", "dividend_yield"]

    def test_default_top_10_sorted_desc(self, mock_data):
        df = ranking()
        assert len(df) == 3  # only 3 ETFs in mock
        assert df.iloc[0]["code"] == "2644"  # highest 1m return
        assert df.iloc[2]["code"] == "1321"  # lowest 1m return

    def test_positive_n(self, mock_data):
        df = ranking(n=2)
        assert len(df) == 2
        assert df.iloc[0]["code"] == "2644"

    def test_negative_n_worst(self, mock_data):
        df = ranking(n=-2)
        assert len(df) == 2
        assert df.iloc[0]["code"] == "1321"  # worst first

    def test_zero_n_returns_all(self, mock_data):
        df = ranking(n=0)
        assert len(df) == 3

    def test_period_1y(self, mock_data):
        df = ranking(period="1y")
        assert df.iloc[0]["return"] == 25.00

    def test_filters_none_returns(self, mock_data):
        df = ranking(period="3y")
        assert len(df) == 2  # 2644 has 3y=None
        codes = set(df["code"])
        assert "2644" not in codes

    def test_japanese_names(self, mock_data):
        df = ranking()
        names = set(df["name"])
        assert "TOPIX連動型上場投資信託" in names

    def test_english_names(self, mock_data):
        config.lang = "en"
        df = ranking()
        names = set(df["name"])
        assert "TOPIX ETF" in names

    def test_invalid_period_raises(self, mock_data):
        with pytest.raises(ValueError, match="period must be one of"):
            ranking(period="2y")

    def test_ytd_period(self, mock_data):
        df = ranking(period="ytd")
        assert df.iloc[0]["return"] == 3.50

    def test_includes_fee_and_yield(self, mock_data):
        df = ranking(n=1)
        assert df.iloc[0]["fee"] == 0.41
        assert df.iloc[0]["dividend_yield"] == 0.50


@patch("pyjpx_etf.ranking.get_rakuten_data", return_value={})
class TestRankingEmpty:
    def test_empty_data_returns_empty_df(self, mock_data):
        df = ranking()
        assert df.empty
        assert list(df.columns) == ["code", "name", "return", "fee", "dividend_yield"]
