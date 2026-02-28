import json
import time
from unittest.mock import MagicMock, patch

from pyjpx_etf._internal import rakuten

MOCK_CSV = (
    '"1306.T","01306","TOPIX ETF","東証ETF","TOPIX","0.06","株式","日本","2500",'
    '"2.50","3.10","5.20","10.50","30.00","50.00","100.00","80.00","1.20",'
    '"円","1.95","100.00","2026/02/27","TOPIX連動型上場投資信託","desc","50000","百万円","2026/01/30","",""\n'
    '"2644.T","02644","Global X Semiconductor JP","東証ETF","半導体","0.41","株式","日本","3000",'
    '"5.10","8.20","12.30","25.00","","","","","3.50",'
    '"円","0.50","200.00","2026/02/27","半導体ETF","desc","30000","百万円","2026/01/30","",""\n'
    '"2800.HK","02800","Tracker Fund HK","香港","Hang Seng","0.07","株式","香港","332",'
    '"2.93","-1.44","2.04","4.26","15.42","14.20","69.75","46.68","8.21",'
    '"香港ドル","2.89","26.60","2026/02/26","トラッカー","desc","148545","百万香港ドル","2026/01/30","",""\n'
)


def _mock_get_ok(text=MOCK_CSV):
    mock_resp = MagicMock()
    mock_resp.text = text
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _reset(tmp_path, monkeypatch):
    """Reset memory cache and redirect disk cache to tmp_path."""
    rakuten._reset_cache()
    monkeypatch.setattr(rakuten, "_CACHE_FILE", tmp_path / "rakuten.json")


class TestNormalizeCode:
    def test_strips_leading_zeros(self):
        assert rakuten._normalize_code("01306") == "1306"

    def test_multiple_leading_zeros(self):
        assert rakuten._normalize_code("02644") == "2644"

    def test_alphanumeric(self):
        assert rakuten._normalize_code("0200A") == "200A"

    def test_no_leading_zeros(self):
        assert rakuten._normalize_code("1306") == "1306"

    def test_whitespace_stripped(self):
        assert rakuten._normalize_code(" 01306 ") == "1306"


class TestParseFloat:
    def test_valid(self):
        assert rakuten._parse_float("2.50") == 2.50

    def test_negative(self):
        assert rakuten._parse_float("-1.44") == -1.44

    def test_empty(self):
        assert rakuten._parse_float("") is None

    def test_dash(self):
        assert rakuten._parse_float("-") is None

    def test_invalid(self):
        assert rakuten._parse_float("N/A") is None


class TestParseRakutenCsv:
    def test_parses_tse_entries_only(self):
        result = rakuten._parse_rakuten_csv(MOCK_CSV)
        assert "1306" in result
        assert "2644" in result
        assert "2800" not in result  # Hong Kong excluded

    def test_normalizes_codes(self):
        result = rakuten._parse_rakuten_csv(MOCK_CSV)
        assert "1306" in result
        assert "01306" not in result

    def test_extracts_fee(self):
        result = rakuten._parse_rakuten_csv(MOCK_CSV)
        assert result["1306"]["fee"] == 0.06
        assert result["2644"]["fee"] == 0.41

    def test_extracts_names(self):
        result = rakuten._parse_rakuten_csv(MOCK_CSV)
        assert result["1306"]["name_ja"] == "TOPIX連動型上場投資信託"
        assert result["1306"]["name_en"] == "TOPIX ETF"

    def test_extracts_returns(self):
        result = rakuten._parse_rakuten_csv(MOCK_CSV)
        assert result["1306"]["1m"] == 2.50
        assert result["1306"]["3m"] == 3.10
        assert result["1306"]["1y"] == 10.50
        assert result["1306"]["ytd"] == 1.20

    def test_missing_returns_are_none(self):
        result = rakuten._parse_rakuten_csv(MOCK_CSV)
        assert result["2644"]["3y"] is None
        assert result["2644"]["5y"] is None

    def test_extracts_dividend_yield(self):
        result = rakuten._parse_rakuten_csv(MOCK_CSV)
        assert result["1306"]["dividend_yield"] == 1.95

    def test_empty_csv(self):
        result = rakuten._parse_rakuten_csv("")
        assert result == {}


class TestGetRakutenData:
    @patch("pyjpx_etf._internal.rakuten.requests.get", return_value=_mock_get_ok())
    def test_returns_data(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        result = rakuten.get_rakuten_data()
        assert "1306" in result
        assert "2644" in result

    @patch("pyjpx_etf._internal.rakuten.requests.get", return_value=_mock_get_ok())
    def test_caches_in_memory(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        rakuten.get_rakuten_data()
        rakuten.get_rakuten_data()
        mock_get.assert_called_once()

    @patch("pyjpx_etf._internal.rakuten.requests.get")
    def test_graceful_degradation(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        mock_get.side_effect = Exception("network error")
        result = rakuten.get_rakuten_data()
        assert result == {}


class TestRakutenDiskCache:
    @patch("pyjpx_etf._internal.rakuten.requests.get", return_value=_mock_get_ok())
    def test_writes_disk_cache(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        rakuten.get_rakuten_data()
        cache_file = tmp_path / "rakuten.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert "1306" in data["rakuten"]

    def test_reads_fresh_disk_cache(self, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        cache_file = tmp_path / "rakuten.json"
        cache_data = {
            "timestamp": time.time(),
            "rakuten": {"1306": {"fee": 0.06, "name_ja": "TOPIX", "name_en": "TOPIX ETF"}},
        }
        cache_file.write_text(
            json.dumps(cache_data, ensure_ascii=False), encoding="utf-8"
        )
        result = rakuten.get_rakuten_data()
        assert result["1306"]["fee"] == 0.06

    @patch("pyjpx_etf._internal.rakuten.requests.get", return_value=_mock_get_ok())
    def test_expired_disk_cache_triggers_fetch(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        cache_file = tmp_path / "rakuten.json"
        old_ts = time.time() - rakuten._CACHE_TTL - 1
        cache_data = {
            "timestamp": old_ts,
            "rakuten": {"1306": {"fee": 99.0}},
        }
        cache_file.write_text(
            json.dumps(cache_data, ensure_ascii=False), encoding="utf-8"
        )
        result = rakuten.get_rakuten_data()
        assert result["1306"]["fee"] == 0.06
        mock_get.assert_called_once()

    @patch("pyjpx_etf._internal.rakuten.requests.get", return_value=_mock_get_ok())
    def test_refresh_bypasses_all_caches(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        rakuten._memory_cache = {"1306": {"fee": 99.0}}
        result = rakuten.get_rakuten_data(refresh=True)
        assert result["1306"]["fee"] == 0.06
        mock_get.assert_called_once()
