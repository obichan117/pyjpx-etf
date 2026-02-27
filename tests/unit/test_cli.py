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
        assert _resolve_code("sox") == "2644"

    def test_alias_fang(self):
        assert _resolve_code("fang") == "2243"

    def test_alias_jpsox1(self):
        assert _resolve_code("jpsox1") == "200A"

    def test_alias_jpsox2(self):
        assert _resolve_code("jpsox2") == "316A"

    def test_alias_pbr(self):
        assert _resolve_code("pbr") == "2080"

    def test_alias_div50(self):
        assert _resolve_code("div50") == "1489"

    def test_alias_div70(self):
        assert _resolve_code("div70") == "1577"

    def test_alias_div100(self):
        assert _resolve_code("div100") == "1698"

    def test_alias_core30(self):
        assert _resolve_code("core30") == "1311"

    def test_raw_code_passthrough(self):
        assert _resolve_code("1306") == "1306"

    def test_unknown_alias_passthrough(self):
        assert _resolve_code("unknown") == "unknown"


@patch("pyjpx_etf.etf.get_fees", return_value={})
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestCLI:
    def setup_method(self):
        config.lang = "en"

    def test_output_contains_etf_info(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "1306" in out
        assert "TOPIX ETF" in out

    def test_output_contains_holdings(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "NISSUI" in out
        assert "TOYOTA" in out

    def test_weight_has_one_decimal(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "60.6%" in out

    def test_fee_absent_when_none(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "Fee" not in out
        assert "信託報酬" not in out

    def test_nav_shown(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "Nav:" in out
        assert "億" in out

    def test_nav_between_title_and_table(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        title_pos = out.index("TOPIX ETF")
        nav_pos = out.index("Nav:")
        table_pos = out.index("Code")
        assert title_pos < nav_pos < table_pos


@patch("pyjpx_etf.etf.get_fees", return_value={})
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value=MOCK_JAPANESE_NAMES)
class TestCLIEnFlag:
    def setup_method(self):
        config.lang = "ja"

    def test_en_flag_shows_english(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306", "--en"]):
            main()
        out = capsys.readouterr().out
        assert "TOPIX ETF" in out
        assert "NISSUI" in out

    def test_default_shows_japanese(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "TOPIX連動型上場投資信託" in out
        assert "ニッスイ" in out


MOCK_FEES = {"1306": 0.06}


@patch("pyjpx_etf.etf.get_fees", return_value=MOCK_FEES)
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value=MOCK_JAPANESE_NAMES)
class TestCLIFee:
    def test_fee_shown_in_japanese(self, mock_master, mock_fetch, mock_fees, capsys):
        config.lang = "ja"
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "信託報酬: 0.06%" in out

    def test_fee_shown_in_english(self, mock_master, mock_fetch, mock_fees, capsys):
        config.lang = "ja"
        with patch("sys.argv", ["etf", "1306", "--en"]):
            main()
        out = capsys.readouterr().out
        assert "Fee: 0.06%" in out

    def test_nav_and_fee_on_same_line(self, mock_master, mock_fetch, mock_fees, capsys):
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


@patch("pyjpx_etf.etf.get_fees", return_value={})
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestCLIAllFlag:
    def setup_method(self):
        config.lang = "en"

    def test_default_shows_top_10(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        # Mock CSV has 2 holdings — both shown in top 10
        assert "NISSUI" in out
        assert "TOYOTA" in out

    def test_all_flag_shows_all(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306", "-a"]):
            main()
        out = capsys.readouterr().out
        assert "NISSUI" in out
        assert "TOYOTA" in out

    def test_all_long_flag(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "1306", "--all"]):
            main()
        out = capsys.readouterr().out
        assert "NISSUI" in out
        assert "TOYOTA" in out


@patch("pyjpx_etf.etf.get_fees", return_value={})
@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
@patch("pyjpx_etf.etf.get_japanese_names", return_value={})
class TestCLIAlias:
    def setup_method(self):
        config.lang = "en"

    def test_alias_resolves_to_code(self, mock_master, mock_fetch, mock_fees, capsys):
        with patch("sys.argv", ["etf", "topix"]):
            main()
        mock_fetch.assert_called_once_with("1306")
