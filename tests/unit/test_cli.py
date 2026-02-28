from unittest.mock import patch

from pyjpx_etf import config
from pyjpx_etf.cli import _format_yen, _resolve_code, main

MOCK_CSV = """\
ETF Code,ETF Name,Fund Cash Component,Shares Outstanding,Fund Date
1306,TOPIX ETF,496973797639.0,8133974978,20260227

Code,Name,ISIN,Exchange,Currency,Shares Amount,Stock Price
1332,NISSUI CORPORATION,JP3718800000,TSE,JPY,7647000.0,1506.5
7203,TOYOTA MOTOR,JP3633400001,TSE,JPY,3000000.0,2500.0
"""

MOCK_JAPANESE_NAMES = {
    "1306": "TOPIX連動型上場投資信託",
    "1332": "ニッスイ",
    "7203": "トヨタ自動車",
}


class TestFormatYen:
    def test_cho(self):
        assert _format_yen(1_3000_0000_0000) == "1.3兆"

    def test_cho_integer(self):
        assert _format_yen(2_0000_0000_0000) == "2兆"

    def test_large_oku(self):
        assert _format_yen(1300_0000_0000) == "1300億"

    def test_medium_oku(self):
        assert _format_yen(52_0000_0000) == "52億"

    def test_small_oku(self):
        assert _format_yen(1500_0000) == "0.15億"

    def test_one_oku(self):
        assert _format_yen(1_0000_0000) == "1億"


class TestResolveCode:
    def test_alias_topix(self):
        assert _resolve_code("topix") == "1306"

    def test_alias_case_insensitive(self):
        assert _resolve_code("TOPIX") == "1306"

    def test_alias_225(self):
        assert _resolve_code("225") == "1321"

    def test_alias_sox(self):
        assert _resolve_code("sox") == "2243"

    def test_alias_jpsox2(self):
        assert _resolve_code("jpsox2") == "2644"

    def test_alias_jpsox1(self):
        assert _resolve_code("jpsox1") == "200A"

    def test_alias_pbr(self):
        assert _resolve_code("pbr") == "2080"

    def test_alias_div50(self):
        assert _resolve_code("div50") == "1489"

    def test_alias_div70(self):
        assert _resolve_code("div70") == "1577"

    def test_alias_core30(self):
        assert _resolve_code("core30") == "1311"

    def test_raw_code_passthrough(self):
        assert _resolve_code("1306") == "1306"

    def test_unknown_alias_passthrough(self):
        assert _resolve_code("unknown") == "unknown"


@patch("pyjpx_etf.etf.get_rakuten_data", return_value={})
@patch("pyjpx_etf.etf.get_fees", return_value={})
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestCLI:
    def setup_method(self):
        config.lang = "en"

    def test_output_contains_etf_info(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "1306" in out
        assert "TOPIX ETF" in out

    def test_output_contains_holdings(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "NISSUI" in out
        assert "TOYOTA" in out

    def test_weight_has_one_decimal(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "60.6%" in out

    def test_fee_absent_when_none(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "Fee" not in out
        assert "信託報酬" not in out

    def test_nav_shown(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "Nav:" in out
        assert "億" in out

    def test_nav_between_title_and_table(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        title_pos = out.index("TOPIX ETF")
        nav_pos = out.index("Nav:")
        table_pos = out.index("Code")
        assert title_pos < nav_pos < table_pos


@patch("pyjpx_etf.etf.get_rakuten_data", return_value={})
@patch("pyjpx_etf.etf.get_fees", return_value={})
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value=MOCK_JAPANESE_NAMES)
class TestCLIEnFlag:
    def setup_method(self):
        config.lang = "ja"

    def test_en_flag_shows_english(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306", "--en"]):
            main()
        out = capsys.readouterr().out
        assert "TOPIX ETF" in out
        assert "NISSUI" in out

    def test_default_shows_japanese(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "TOPIX連動型上場投資信託" in out
        assert "ニッスイ" in out


MOCK_FEES = {"1306": 0.06}


@patch("pyjpx_etf.etf.get_rakuten_data", return_value={})
@patch("pyjpx_etf.etf.get_fees", return_value=MOCK_FEES)
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value=MOCK_JAPANESE_NAMES)
class TestCLIFee:
    def test_fee_shown_in_japanese(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        config.lang = "ja"
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "信託報酬: 0.06%" in out

    def test_fee_shown_in_english(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        config.lang = "ja"
        with patch("sys.argv", ["etf", "1306", "--en"]):
            main()
        out = capsys.readouterr().out
        assert "Fee: 0.06%" in out

    def test_nav_and_fee_on_same_line(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        config.lang = "ja"
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        for line in out.splitlines():
            if "Nav:" in line:
                assert "信託報酬:" in line
                break
        else:
            raise AssertionError("Nav: line not found")


@patch("pyjpx_etf.etf.get_rakuten_data", return_value={})
@patch("pyjpx_etf.etf.get_fees", return_value={})
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestCLIAllFlag:
    def setup_method(self):
        config.lang = "en"

    def test_default_shows_top_10(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        # Mock CSV has 2 holdings — both shown in top 10
        assert "NISSUI" in out
        assert "TOYOTA" in out

    def test_all_flag_shows_all(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306", "-a"]):
            main()
        out = capsys.readouterr().out
        assert "NISSUI" in out
        assert "TOYOTA" in out

    def test_all_long_flag(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "1306", "--all"]):
            main()
        out = capsys.readouterr().out
        assert "NISSUI" in out
        assert "TOYOTA" in out


@patch("pyjpx_etf.etf.get_rakuten_data", return_value={})
@patch("pyjpx_etf.etf.get_fees", return_value={})
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestCLIAlias:
    def setup_method(self):
        config.lang = "en"

    def test_alias_resolves_to_code(self, mock_master, mock_fetch, mock_fees, mock_rakuten, capsys):
        with patch("sys.argv", ["etf", "topix"]):
            main()
        mock_fetch.assert_called_once_with("1306")


MOCK_RANKING_DATA = {
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
}


@patch("pyjpx_etf.ranking.get_rakuten_data", return_value=MOCK_RANKING_DATA)
class TestCLIRank:
    def setup_method(self):
        config.lang = "ja"

    def test_rank_default(self, mock_data, capsys):
        with patch("sys.argv", ["etf", "rank"]):
            main()
        out = capsys.readouterr().out
        assert "1306" in out
        assert "2644" in out
        assert "Return (1m)" in out

    def test_rank_with_count(self, mock_data, capsys):
        with patch("sys.argv", ["etf", "rank", "1"]):
            main()
        out = capsys.readouterr().out
        assert "2644" in out  # top 1 by 1m

    def test_rank_with_period(self, mock_data, capsys):
        with patch("sys.argv", ["etf", "rank", "10", "1y"]):
            main()
        out = capsys.readouterr().out
        assert "Return (1y)" in out

    def test_rank_negative_count(self, mock_data, capsys):
        with patch("sys.argv", ["etf", "rank", "-1"]):
            main()
        out = capsys.readouterr().out
        # worst 1 by 1m = 1306 (2.50 < 5.10)
        assert "1306" in out

    def test_rank_en_flag(self, mock_data, capsys):
        with patch("sys.argv", ["etf", "rank", "--en"]):
            main()
        out = capsys.readouterr().out
        assert "TOPIX ETF" in out

    def test_rank_japanese_names_default(self, mock_data, capsys):
        with patch("sys.argv", ["etf", "rank"]):
            main()
        out = capsys.readouterr().out
        assert "TOPIX連動型上場投資信託" in out
