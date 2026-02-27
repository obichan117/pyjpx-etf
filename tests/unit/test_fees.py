import json
import time
from unittest.mock import MagicMock, patch

from pyjpx_etf._internal import fees

MOCK_HTML = """
<html><body>
<table>
<tr><th>コード</th><th>銘柄名</th><th>信託報酬</th></tr>
<tr><td>1306</td><td>TOPIX ETF</td><td>0.06%</td></tr>
<tr><td>2644</td><td>半導体ETF</td><td>0.4125%</td></tr>
</table>
</body></html>
"""

MOCK_HTML_FOOTNOTE = """
<html><body>
<table>
<tr><th>コード</th><th>銘柄名</th><th>信託報酬</th></tr>
<tr><td>1306</td><td>TOPIX ETF</td><td>0.06%（注10）</td></tr>
</table>
</body></html>
"""

MOCK_HTML_FULLWIDTH = """
<html><body>
<table>
<tr><th>コード</th><th>銘柄名</th><th>信託報酬</th></tr>
<tr><td>1306</td><td>TOPIX ETF</td><td>0.06％</td></tr>
</table>
</body></html>
"""


def _mock_get_ok(html=MOCK_HTML):
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _reset(tmp_path, monkeypatch):
    """Reset memory cache and redirect disk cache to tmp_path."""
    fees._reset_cache()
    monkeypatch.setattr(fees, "_CACHE_FILE", tmp_path / "fees.json")


class TestParseFeeString:
    def test_simple_percentage(self):
        assert fees._parse_fee_string("0.06%") == 0.06

    def test_with_footnote(self):
        assert fees._parse_fee_string("0.06%（注10）") == 0.06

    def test_fullwidth_percent(self):
        assert fees._parse_fee_string("0.048％") == 0.048

    def test_integer_percentage(self):
        assert fees._parse_fee_string("1%") == 1.0

    def test_returns_none_for_non_string(self):
        assert fees._parse_fee_string(None) is None

    def test_returns_none_for_no_match(self):
        assert fees._parse_fee_string("N/A") is None

    def test_returns_none_for_nan(self):
        assert fees._parse_fee_string("nan") is None


class TestParseFeeHtml:
    def test_parses_basic_table(self):
        result = fees._parse_fee_html(MOCK_HTML)
        assert result["1306"] == 0.06
        assert result["2644"] == 0.4125

    def test_handles_footnotes(self):
        result = fees._parse_fee_html(MOCK_HTML_FOOTNOTE)
        assert result["1306"] == 0.06

    def test_handles_fullwidth_percent(self):
        result = fees._parse_fee_html(MOCK_HTML_FULLWIDTH)
        assert result["1306"] == 0.06

    def test_ignores_tables_without_fee_column(self):
        html = """
        <html><body>
        <table><tr><th>コード</th><th>銘柄名</th></tr>
        <tr><td>1306</td><td>TOPIX</td></tr></table>
        </body></html>
        """
        result = fees._parse_fee_html(html)
        assert result == {}


class TestGetFees:
    @patch("pyjpx_etf._internal.fees.requests.get", return_value=_mock_get_ok())
    def test_returns_fee_dict(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        result = fees.get_fees()
        assert result["1306"] == 0.06
        assert result["2644"] == 0.4125

    @patch("pyjpx_etf._internal.fees.requests.get", return_value=_mock_get_ok())
    def test_caches_in_memory(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        fees.get_fees()
        fees.get_fees()
        mock_get.assert_called_once()

    @patch("pyjpx_etf._internal.fees.requests.get")
    def test_graceful_degradation(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        mock_get.side_effect = Exception("network error")
        result = fees.get_fees()
        assert result == {}


class TestFeeDiskCache:
    @patch("pyjpx_etf._internal.fees.requests.get", return_value=_mock_get_ok())
    def test_writes_disk_cache(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        fees.get_fees()
        cache_file = tmp_path / "fees.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert data["fees"]["1306"] == 0.06

    def test_reads_fresh_disk_cache(self, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        cache_file = tmp_path / "fees.json"
        cache_file.write_text(
            json.dumps(
                {"timestamp": time.time(), "fees": {"1306": 0.06}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = fees.get_fees()
        assert result["1306"] == 0.06

    @patch("pyjpx_etf._internal.fees.requests.get", return_value=_mock_get_ok())
    def test_expired_disk_cache_triggers_fetch(
        self, mock_get, tmp_path, monkeypatch
    ):
        _reset(tmp_path, monkeypatch)
        cache_file = tmp_path / "fees.json"
        old_ts = time.time() - fees._CACHE_TTL - 1
        cache_file.write_text(
            json.dumps(
                {"timestamp": old_ts, "fees": {"1306": 99.0}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = fees.get_fees()
        assert result["1306"] == 0.06
        mock_get.assert_called_once()

    @patch("pyjpx_etf._internal.fees.requests.get", return_value=_mock_get_ok())
    def test_refresh_bypasses_all_caches(
        self, mock_get, tmp_path, monkeypatch
    ):
        _reset(tmp_path, monkeypatch)
        fees._memory_cache = {"1306": 99.0}
        cache_file = tmp_path / "fees.json"
        cache_file.write_text(
            json.dumps(
                {"timestamp": time.time(), "fees": {"1306": 99.0}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = fees.get_fees(refresh=True)
        assert result["1306"] == 0.06
        mock_get.assert_called_once()

    def test_corrupt_disk_cache_ignored(self, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        cache_file = tmp_path / "fees.json"
        cache_file.write_text("not json", encoding="utf-8")
        with patch(
            "pyjpx_etf._internal.fees.requests.get",
            return_value=_mock_get_ok(),
        ):
            result = fees.get_fees()
        assert result["1306"] == 0.06
