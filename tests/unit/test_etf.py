from unittest.mock import patch

import pandas as pd
import pytest

from pyjpx_etf import ETF

MOCK_CSV = """\
ETF Code,ETF Name,Fund Cash Component,Shares Outstanding,Fund Date
1306,TOPIX ETF,496973797639.0,8133974978,20260227

Code,Name,ISIN,Exchange,Currency,Shares Amount,Stock Price
1332,NISSUI CORPORATION,JP3718800000,TSE,JPY,7647000.0,1506.5
7203,TOYOTA MOTOR,JP3633400001,TSE,JPY,3000000.0,2500.0
"""


@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
class TestETFClass:
    def test_info(self, mock_fetch):
        e = ETF("1306")
        assert e.info.code == "1306"
        assert e.info.name == "TOPIX ETF"
        mock_fetch.assert_called_once_with("1306")

    def test_holdings(self, mock_fetch):
        e = ETF("1306")
        assert len(e.holdings) == 2
        assert e.holdings[0].code == "1332"

    def test_lazy_loading(self, mock_fetch):
        e = ETF("1306")
        mock_fetch.assert_not_called()
        _ = e.info
        mock_fetch.assert_called_once()

    def test_single_fetch(self, mock_fetch):
        e = ETF("1306")
        _ = e.info
        _ = e.holdings
        mock_fetch.assert_called_once()

    def test_to_dataframe(self, mock_fetch):
        e = ETF("1306")
        df = e.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "weight" in df.columns
        assert "code" in df.columns

    def test_repr(self, mock_fetch):
        e = ETF("1306")
        assert repr(e) == "ETF('1306')"

    def test_code_coerced_to_str(self, mock_fetch):
        e = ETF(1306)
        _ = e.info
        mock_fetch.assert_called_once_with("1306")

    def test_top(self, mock_fetch):
        e = ETF("1306")
        df = e.top(1)
        assert len(df) == 1
        assert list(df.columns) == ["code", "name", "weight"]
        assert df.iloc[0]["code"] == "1332"  # higher market value

    def test_top_default(self, mock_fetch):
        e = ETF("1306")
        df = e.top()
        assert len(df) == 2  # only 2 holdings, top 10 returns all

    def test_top_weight_is_percentage(self, mock_fetch):
        e = ETF("1306")
        df = e.top()
        assert df["weight"].sum() == pytest.approx(100.0)
