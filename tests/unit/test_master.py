import json
import time
from unittest.mock import MagicMock, patch

import pandas as pd

from pyjpx_etf._internal import master

MOCK_MASTER_DF = pd.DataFrame(
    [
        ["2024/01/01", "1306", "TOPIX連動型上場投資信託", "extra"],
        ["2024/01/01", "7203", "トヨタ自動車", "extra"],
    ]
)


def _mock_get_ok():
    mock_resp = MagicMock()
    mock_resp.content = b"fake-xls-bytes"
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _reset(tmp_path, monkeypatch):
    """Reset memory cache and redirect disk cache to tmp_path."""
    master._memory_cache = None
    monkeypatch.setattr(master, "_CACHE_FILE", tmp_path / "master.json")


class TestGetJapaneseNames:
    @patch("pyjpx_etf._internal.master.pd.read_excel", return_value=MOCK_MASTER_DF)
    @patch("pyjpx_etf._internal.master.requests.get", return_value=_mock_get_ok())
    def test_returns_lookup_dict(self, mock_get, mock_read, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        result = master.get_japanese_names()
        assert result["1306"] == "TOPIX連動型上場投資信託"
        assert result["7203"] == "トヨタ自動車"

    @patch("pyjpx_etf._internal.master.pd.read_excel", return_value=MOCK_MASTER_DF)
    @patch("pyjpx_etf._internal.master.requests.get", return_value=_mock_get_ok())
    def test_caches_in_memory(self, mock_get, mock_read, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        master.get_japanese_names()
        master.get_japanese_names()
        mock_get.assert_called_once()

    @patch("pyjpx_etf._internal.master.requests.get")
    def test_graceful_degradation(self, mock_get, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        mock_get.side_effect = Exception("network error")
        result = master.get_japanese_names()
        assert result == {}

    @patch("pyjpx_etf._internal.master.pd.read_excel")
    @patch("pyjpx_etf._internal.master.requests.get", return_value=_mock_get_ok())
    def test_skips_nan_rows(self, mock_get, mock_read, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        mock_read.return_value = pd.DataFrame(
            [
                [None, None, None, None],
                ["2024/01/01", "1306", "TOPIX連動型上場投資信託", "x"],
            ]
        )
        result = master.get_japanese_names()
        assert "nan" not in result
        assert "1306" in result


class TestDiskCache:
    @patch("pyjpx_etf._internal.master.pd.read_excel", return_value=MOCK_MASTER_DF)
    @patch("pyjpx_etf._internal.master.requests.get", return_value=_mock_get_ok())
    def test_writes_disk_cache(self, mock_get, mock_read, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        master.get_japanese_names()
        cache_file = tmp_path / "master.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert data["names"]["1306"] == "TOPIX連動型上場投資信託"

    def test_reads_fresh_disk_cache(self, tmp_path, monkeypatch):
        _reset(tmp_path, monkeypatch)
        cache_file = tmp_path / "master.json"
        cache_file.write_text(
            json.dumps(
                {"timestamp": time.time(), "names": {"1306": "cached_name"}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = master.get_japanese_names()
        assert result["1306"] == "cached_name"

    @patch("pyjpx_etf._internal.master.pd.read_excel", return_value=MOCK_MASTER_DF)
    @patch("pyjpx_etf._internal.master.requests.get", return_value=_mock_get_ok())
    def test_expired_disk_cache_triggers_fetch(
        self, mock_get, mock_read, tmp_path, monkeypatch
    ):
        _reset(tmp_path, monkeypatch)
        cache_file = tmp_path / "master.json"
        old_ts = time.time() - master._CACHE_TTL - 1
        cache_file.write_text(
            json.dumps(
                {"timestamp": old_ts, "names": {"1306": "stale_name"}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = master.get_japanese_names()
        # Should have fetched fresh data, not stale
        assert result["1306"] == "TOPIX連動型上場投資信託"
        mock_get.assert_called_once()

    @patch("pyjpx_etf._internal.master.pd.read_excel", return_value=MOCK_MASTER_DF)
    @patch("pyjpx_etf._internal.master.requests.get", return_value=_mock_get_ok())
    def test_refresh_bypasses_all_caches(
        self, mock_get, mock_read, tmp_path, monkeypatch
    ):
        _reset(tmp_path, monkeypatch)
        # Seed memory cache
        master._memory_cache = {"1306": "old_memory"}
        # Seed fresh disk cache
        cache_file = tmp_path / "master.json"
        cache_file.write_text(
            json.dumps(
                {"timestamp": time.time(), "names": {"1306": "old_disk"}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = master.get_japanese_names(refresh=True)
        assert result["1306"] == "TOPIX連動型上場投資信託"
        mock_get.assert_called_once()

    def test_corrupt_disk_cache_ignored(self, tmp_path, monkeypatch):
        """Corrupt JSON on disk should be silently ignored."""
        _reset(tmp_path, monkeypatch)
        cache_file = tmp_path / "master.json"
        cache_file.write_text("not json", encoding="utf-8")
        with patch(
            "pyjpx_etf._internal.master.requests.get"
        ) as mock_get, patch(
            "pyjpx_etf._internal.master.pd.read_excel", return_value=MOCK_MASTER_DF
        ):
            mock_get.return_value = _mock_get_ok()
            result = master.get_japanese_names()
        assert result["1306"] == "TOPIX連動型上場投資信託"
