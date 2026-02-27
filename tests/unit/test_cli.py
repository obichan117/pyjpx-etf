from unittest.mock import patch

from pyjpx_etf.cli import main

MOCK_CSV = """\
ETF Code,ETF Name,Fund Cash Component,Shares Outstanding,Fund Date
1306,TOPIX ETF,496973797639.0,8133974978,20260227

Code,Name,ISIN,Exchange,Currency,Shares Amount,Stock Price
1332,NISSUI CORPORATION,JP3718800000,TSE,JPY,7647000.0,1506.5
7203,TOYOTA MOTOR,JP3633400001,TSE,JPY,3000000.0,2500.0
"""


@patch("pyjpx_etf.etf.fetch_pcf", return_value=MOCK_CSV)
class TestCLI:
    def test_output_contains_etf_info(self, mock_fetch, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "1306" in out
        assert "TOPIX ETF" in out

    def test_output_contains_holdings(self, mock_fetch, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "NISSUI" in out
        assert "TOYOTA" in out

    def test_weight_has_one_decimal(self, mock_fetch, capsys):
        with patch("sys.argv", ["etf", "1306"]):
            main()
        out = capsys.readouterr().out
        assert "60.6%" in out
