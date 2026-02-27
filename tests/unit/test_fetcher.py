from unittest.mock import MagicMock, patch

import pytest
import requests

from pyjpx_etf._internal.fetcher import _looks_like_csv, fetch_pcf
from pyjpx_etf.exceptions import ETFNotFoundError, FetchError

VALID_CSV = """\
ETF Code,ETF Name,Fund Cash Component,Shares Outstanding,Fund Date
1306,TOPIX ETF,496973797639.0,8133974978,20260227

Code,Name,ISIN,Exchange,Currency,Shares Amount,Stock Price
1332,NISSUI CORPORATION,JP3718800000,TSE,JPY,7647000.0,1506.5
"""

HTML_RESPONSE = """\
<html>
</head>
<body>
<p>PCF file download service is available from 7:50 to 23:55 (JST) during weekdays.</p>
</body></html>
"""


def _mock_response(status_code: int, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestLooksLikeCSV:
    def test_valid_csv(self):
        assert _looks_like_csv(VALID_CSV) is True

    def test_html_response(self):
        assert _looks_like_csv(HTML_RESPONSE) is False

    def test_empty_string(self):
        assert _looks_like_csv("") is False

    def test_whitespace_html(self):
        assert _looks_like_csv("  <html>...</html>  ") is False


@patch("pyjpx_etf._internal.fetcher.config")
@patch("pyjpx_etf._internal.fetcher.requests.get")
class TestFetchPCF:
    def _setup_config(self, mock_config, urls=None):
        mock_config.provider_urls = (
            urls
            if urls is not None
            else [
                "https://provider1/{code}.csv",
                "https://provider2/{code}.csv",
            ]
        )
        mock_config.timeout = 30
        mock_config.request_delay = 0.0

    def test_success_first_provider(self, mock_get, mock_config):
        self._setup_config(mock_config)
        mock_get.return_value = _mock_response(200, VALID_CSV)

        result = fetch_pcf("1306")
        assert result == VALID_CSV
        mock_get.assert_called_once_with(
            "https://provider1/1306.csv", timeout=30
        )

    def test_fallback_to_second_provider(self, mock_get, mock_config):
        self._setup_config(mock_config)
        mock_get.side_effect = [
            _mock_response(404),
            _mock_response(200, VALID_CSV),
        ]

        result = fetch_pcf("1306")
        assert result == VALID_CSV
        assert mock_get.call_count == 2

    def test_all_404_raises_not_found(self, mock_get, mock_config):
        self._setup_config(mock_config)
        mock_get.side_effect = [
            _mock_response(404),
            _mock_response(404),
        ]

        with pytest.raises(ETFNotFoundError, match="not found on any provider"):
            fetch_pcf("0000")

    def test_network_error_raises_fetch_error(self, mock_get, mock_config):
        self._setup_config(mock_config)
        mock_get.side_effect = [
            requests.ConnectionError("Connection refused"),
            requests.ConnectionError("Connection refused"),
        ]

        with pytest.raises(FetchError, match="Request failed"):
            fetch_pcf("1306")

    def test_server_error_then_404_raises_fetch_error(self, mock_get, mock_config):
        """When a server error precedes a 404, raise FetchError not ETFNotFoundError."""
        self._setup_config(mock_config)
        mock_get.side_effect = [
            _mock_response(500),
            _mock_response(404),
        ]

        with pytest.raises(FetchError, match="HTTP 500"):
            fetch_pcf("1306")

    def test_404_then_server_error_raises_fetch_error(self, mock_get, mock_config):
        """Mixed errors: not all 404 → should raise FetchError."""
        self._setup_config(mock_config)
        mock_get.side_effect = [
            _mock_response(404),
            _mock_response(500),
        ]

        with pytest.raises(FetchError, match="HTTP 500"):
            fetch_pcf("1306")

    def test_html_200_falls_through_to_next_provider(self, mock_get, mock_config):
        """ICE returns 200 with HTML outside business hours; should try next."""
        self._setup_config(mock_config)
        mock_get.side_effect = [
            _mock_response(200, HTML_RESPONSE),
            _mock_response(200, VALID_CSV),
        ]

        result = fetch_pcf("1306")
        assert result == VALID_CSV
        assert mock_get.call_count == 2

    def test_all_html_200_raises_fetch_error(self, mock_get, mock_config):
        """All providers return HTML instead of CSV."""
        self._setup_config(mock_config)
        mock_get.side_effect = [
            _mock_response(200, HTML_RESPONSE),
            _mock_response(200, HTML_RESPONSE),
        ]

        with pytest.raises(FetchError, match="Non-CSV response"):
            fetch_pcf("1306")

    def test_request_delay_applied(self, mock_get, mock_config):
        self._setup_config(mock_config)
        mock_config.request_delay = 0.1
        mock_get.side_effect = [
            _mock_response(404),
            _mock_response(200, VALID_CSV),
        ]

        with patch("pyjpx_etf._internal.fetcher.time.sleep") as mock_sleep:
            fetch_pcf("1306")
            mock_sleep.assert_called_once_with(0.1)

    def test_no_delay_on_first_request(self, mock_get, mock_config):
        self._setup_config(mock_config)
        mock_config.request_delay = 1.0
        mock_get.return_value = _mock_response(200, VALID_CSV)

        with patch("pyjpx_etf._internal.fetcher.time.sleep") as mock_sleep:
            fetch_pcf("1306")
            mock_sleep.assert_not_called()

    def test_no_providers_raises_fetch_error(self, mock_get, mock_config):
        self._setup_config(mock_config, urls=[])

        with pytest.raises(FetchError, match="No provider URLs"):
            fetch_pcf("1306")
        mock_get.assert_not_called()
