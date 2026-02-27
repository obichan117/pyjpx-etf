import warnings
from unittest.mock import call, patch

import pandas as pd
import pytest

from pyjpx_etf import ETF, config

MOCK_CSV = """\
ETF Code,ETF Name,Fund Cash Component,Shares Outstanding,Fund Date
1306,TOPIX ETF,496973797639.0,8133974978,20260227

Code,Name,ISIN,Exchange,Currency,Shares Amount,Stock Price
1332,NISSUI CORPORATION,JP3718800000,TSE,JPY,7647000.0,1506.5
7203,TOYOTA MOTOR,JP3633400001,TSE,JPY,3000000.0,2500.0
"""


@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestETFClass:
    def setup_method(self):
        config.lang = "en"

    def test_info(self, mock_master, mock_fetch):
        e = ETF("1306")
        assert e.info.code == "1306"
        assert e.info.name == "TOPIX ETF"
        mock_fetch.assert_called_once_with("1306")

    def test_holdings(self, mock_master, mock_fetch):
        e = ETF("1306")
        assert len(e.holdings) == 2
        assert e.holdings[0].code == "1332"

    def test_lazy_loading(self, mock_master, mock_fetch):
        e = ETF("1306")
        mock_fetch.assert_not_called()
        _ = e.info
        mock_fetch.assert_called_once()

    def test_single_fetch(self, mock_master, mock_fetch):
        e = ETF("1306")
        _ = e.info
        _ = e.holdings
        mock_fetch.assert_called_once()

    def test_to_dataframe(self, mock_master, mock_fetch):
        e = ETF("1306")
        df = e.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "weight" in df.columns
        assert "code" in df.columns

    def test_repr(self, mock_master, mock_fetch):
        e = ETF("1306")
        assert repr(e) == "ETF('1306')"

    def test_code_coerced_to_str(self, mock_master, mock_fetch):
        e = ETF(1306)
        _ = e.info
        mock_fetch.assert_called_once_with("1306")

    def test_top(self, mock_master, mock_fetch):
        e = ETF("1306")
        df = e.top(1)
        assert len(df) == 1
        assert list(df.columns) == ["code", "name", "weight"]
        assert df.iloc[0]["code"] == "1332"  # higher market value

    def test_top_default(self, mock_master, mock_fetch):
        e = ETF("1306")
        df = e.top()
        assert len(df) == 2  # only 2 holdings, top 10 returns all

    def test_top_weight_is_percentage(self, mock_master, mock_fetch):
        e = ETF("1306")
        df = e.top()
        assert df["weight"].sum() == pytest.approx(100.0)


MOCK_JAPANESE_NAMES = {
    "1306": "TOPIX連動型上場投資信託",
    "1332": "ニッスイ",
    "7203": "トヨタ自動車",
}


@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value=MOCK_JAPANESE_NAMES)
class TestETFJapaneseName:
    def setup_method(self):
        config.lang = "ja"

    def test_info_name_is_japanese(self, mock_master, mock_fetch):
        e = ETF("1306")
        assert e.info.name == "TOPIX連動型上場投資信託"

    def test_holdings_names_are_japanese(self, mock_master, mock_fetch):
        e = ETF("1306")
        assert e.holdings[0].name == "ニッスイ"
        assert e.holdings[1].name == "トヨタ自動車"

    def test_english_when_lang_en(self, mock_master, mock_fetch):
        config.lang = "en"
        e = ETF("1306")
        assert e.info.name == "TOPIX ETF"
        assert e.holdings[0].name == "NISSUI CORPORATION"


@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestETFJapaneseNameFallback:
    def setup_method(self):
        config.lang = "ja"

    def test_falls_back_to_english_when_master_empty(self, mock_master, mock_fetch):
        e = ETF("1306")
        assert e.info.name == "TOPIX ETF"
        assert e.holdings[0].name == "NISSUI CORPORATION"


@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestETFNav:
    def setup_method(self):
        config.lang = "en"

    def test_nav_returns_int(self, mock_master, mock_fetch):
        e = ETF("1306")
        assert isinstance(e.nav, int)

    def test_nav_equals_cash_plus_market_value(self, mock_master, mock_fetch):
        e = ETF("1306")
        cash = 496_973_797_639.0
        mv1 = 7_647_000.0 * 1506.5  # NISSUI
        mv2 = 3_000_000.0 * 2500.0  # TOYOTA
        expected = round(cash + mv1 + mv2)
        assert e.nav == expected

    def test_nav_triggers_load(self, mock_master, mock_fetch):
        e = ETF("1306")
        mock_fetch.assert_not_called()
        _ = e.nav
        mock_fetch.assert_called_once()


@patch("pyjpx_etf.etf.get_fees", return_value={"1306": 0.06})
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestETFFee:
    def setup_method(self):
        config.lang = "en"

    def test_fee_returns_float(self, mock_master, mock_fetch, mock_fees):
        e = ETF("1306")
        assert e.fee == 0.06

    def test_fee_returns_none_when_missing(self, mock_master, mock_fetch, mock_fees):
        e = ETF("9999")
        assert e.fee is None

    def test_fee_cached_after_first_access(self, mock_master, mock_fetch, mock_fees):
        e = ETF("1306")
        _ = e.fee
        _ = e.fee
        mock_fees.assert_called_once()

    def test_fee_independent_of_load(self, mock_master, mock_fetch, mock_fees):
        e = ETF("1306")
        _ = e.fee
        mock_fetch.assert_not_called()


PARTIAL_NAMES = {"1306": "TOPIX連動型上場投資信託"}
FULL_NAMES = {
    "1306": "TOPIX連動型上場投資信託",
    "1332": "ニッスイ",
    "7203": "トヨタ自動車",
}


class TestRefreshOnMiss:
    def setup_method(self):
        config.lang = "ja"

    @patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
    @patch(
        "pyjpx_etf.etf.get_japanese_names",
        side_effect=[PARTIAL_NAMES, FULL_NAMES],
    )
    def test_refreshes_when_codes_missing(self, mock_master, mock_fetch):
        e = ETF("1306")
        assert e.info.name == "TOPIX連動型上場投資信託"
        assert e.holdings[0].name == "ニッスイ"
        assert e.holdings[1].name == "トヨタ自動車"
        assert mock_master.call_count == 2
        mock_master.assert_has_calls([call(), call(refresh=True)])

    @patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
    @patch(
        "pyjpx_etf.etf.get_japanese_names",
        return_value=FULL_NAMES,
    )
    def test_no_refresh_when_all_codes_present(self, mock_master, mock_fetch):
        e = ETF("1306")
        _ = e.info
        mock_master.assert_called_once_with()

    @patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
    @patch(
        "pyjpx_etf.etf.get_japanese_names",
        side_effect=[PARTIAL_NAMES, PARTIAL_NAMES],
    )
    def test_warns_when_codes_still_missing_after_refresh(
        self, mock_master, mock_fetch
    ):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            e = ETF("1306")
            _ = e.info
        assert len(w) == 1
        assert "1332" in str(w[0].message)
        assert "7203" in str(w[0].message)
