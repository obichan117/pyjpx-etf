"""Tests for _internal/cli_screen.py — ETF screener logic and formatting."""

from __future__ import annotations

import pandas as pd

from pyjpx_etf._internal.cli_screen import (
    _compute_signals,
    _fmt,
    _fmt_yen,
    _safe_round,
    _screen,
    _truncate_name,
    ROLLING_WINDOW,
)


# ---------------------------------------------------------------------------
# Mock OHLCV data — 25 rows so rolling(20) produces values
# ---------------------------------------------------------------------------

def _make_ohlcv(
    base_close: float = 1000.0,
    base_volume: int = 10000,
    rows: int = 25,
) -> pd.DataFrame:
    """Generate synthetic OHLCV DataFrame."""
    data = []
    for i in range(rows):
        close = base_close + i * 10
        data.append({
            "date": f"2026-01-{i + 1:02d}",
            "open": close - 5,
            "high": close + 20,
            "low": close - 10,
            "close": close,
            "volume": base_volume + i * 100,
        })
    return pd.DataFrame(data)


def _make_spike_ohlcv() -> pd.DataFrame:
    """OHLCV with a big spike on the last day."""
    df = _make_ohlcv()
    # Make last row have huge range and volume
    df.loc[df.index[-1], "high"] = 2000
    df.loc[df.index[-1], "low"] = 1000
    df.loc[df.index[-1], "volume"] = 500000
    return df


MOCK_NAMES = {"1306": "TOPIX ETF", "2644": "半導体ETF", "9999": "Spike ETF"}
MOCK_FEES = {"1306": 0.06, "2644": 0.30}
MOCK_AUM = {"1306": 31.2e12, "2644": 5e10}


# ---------------------------------------------------------------------------
# _compute_signals
# ---------------------------------------------------------------------------


class TestComputeSignals:
    def test_adds_expected_columns(self):
        df = _make_ohlcv()
        result = _compute_signals(df)
        for col in ("range_pct", "atr", "range_ratio", "vol_ratio",
                     "return_pct", "turnover", "turnover_ratio"):
            assert col in result.columns

    def test_range_pct_calculation(self):
        df = _make_ohlcv()
        result = _compute_signals(df)
        row = result.iloc[-1]
        expected = (row["high"] - row["low"]) / row["close"] * 100
        assert abs(row["range_pct"] - expected) < 1e-9

    def test_turnover_calculation(self):
        df = _make_ohlcv()
        result = _compute_signals(df)
        row = result.iloc[-1]
        assert abs(row["turnover"] - row["close"] * row["volume"]) < 1e-9

    def test_rolling_values_nan_before_window(self):
        df = _make_ohlcv()
        result = _compute_signals(df)
        # First ROLLING_WINDOW-1 rows should have NaN for atr
        assert pd.isna(result.iloc[ROLLING_WINDOW - 2]["atr"])
        assert not pd.isna(result.iloc[ROLLING_WINDOW - 1]["atr"])

    def test_coerces_string_columns(self):
        df = _make_ohlcv()
        df["close"] = df["close"].astype(str)
        df["volume"] = df["volume"].astype(str)
        result = _compute_signals(df)
        assert not pd.isna(result.iloc[-1]["range_pct"])


# ---------------------------------------------------------------------------
# _screen
# ---------------------------------------------------------------------------


class TestScreen:
    def test_sorts_by_stat_descending(self):
        ohlcv = {
            "1306": _make_ohlcv(base_close=1000),
            "2644": _make_ohlcv(base_close=500),
        }
        result = _screen(ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM,
                         sort_by="range_pct", top=10)
        assert not result.empty
        # Should be sorted descending
        vals = result["range_pct"].tolist()
        assert vals == sorted(vals, reverse=True)

    def test_top_limits_results(self):
        ohlcv = {
            "1306": _make_ohlcv(base_close=1000),
            "2644": _make_ohlcv(base_close=500),
            "9999": _make_spike_ohlcv(),
        }
        result = _screen(ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM,
                         sort_by="range_pct", top=2)
        assert len(result) == 2

    def test_skips_short_series(self):
        ohlcv = {"1306": _make_ohlcv(rows=5)}  # too few rows
        result = _screen(ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM,
                         sort_by="range_pct", top=10)
        assert result.empty

    def test_includes_aum_and_fee(self):
        ohlcv = {"1306": _make_ohlcv()}
        result = _screen(ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM,
                         sort_by="range_pct", top=10)
        assert result.iloc[0]["aum"] == 31.2e12
        assert result.iloc[0]["fee"] == 0.06

    def test_db_only_stat_aum(self):
        result = _screen({}, MOCK_NAMES, MOCK_FEES, MOCK_AUM,
                         sort_by="aum", top=10)
        assert not result.empty
        vals = result["aum"].tolist()
        assert vals == sorted(vals, reverse=True)

    def test_db_only_stat_fee_ascending(self):
        result = _screen({}, MOCK_NAMES, MOCK_FEES, MOCK_AUM,
                         sort_by="fee", top=10)
        assert not result.empty
        vals = result["fee"].tolist()
        assert vals == sorted(vals)

    def test_return_pct_sorted_by_abs(self):
        ohlcv = {
            "1306": _make_ohlcv(base_close=1000),
            "9999": _make_spike_ohlcv(),
        }
        result = _screen(ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM,
                         sort_by="return_pct", top=10)
        if len(result) >= 2:
            assert abs(result.iloc[0]["return_pct"]) >= abs(
                result.iloc[1]["return_pct"]
            )


# ---------------------------------------------------------------------------
# _safe_round
# ---------------------------------------------------------------------------


class TestSafeRound:
    def test_normal_value(self):
        assert _safe_round(3.14159, 2) == 3.14

    def test_nan_returns_none(self):
        assert _safe_round(float("nan")) is None

    def test_none_returns_none(self):
        assert _safe_round(None) is None


# ---------------------------------------------------------------------------
# _fmt
# ---------------------------------------------------------------------------


class TestFmt:
    def test_formats_value(self):
        assert _fmt(3.14, 8) == "    3.14"

    def test_none_shows_dash(self):
        result = _fmt(None, 8)
        assert "-" in result

    def test_suffix(self):
        result = _fmt(2.5, 6, 1, "x")
        assert result.endswith("x")


# ---------------------------------------------------------------------------
# _fmt_yen
# ---------------------------------------------------------------------------


class TestFmtYen:
    def setup_method(self):
        from pyjpx_etf.config import config

        self._original_lang = config.lang
        config.lang = "ja"

    def teardown_method(self):
        from pyjpx_etf.config import config

        config.lang = self._original_lang

    def test_cho_ja(self):
        result = _fmt_yen(1.5e12, 10)
        assert "兆" in result

    def test_oku_ja(self):
        result = _fmt_yen(5e10, 10)
        assert "億" in result

    def test_man_ja(self):
        result = _fmt_yen(3e6, 10)
        assert "万" in result

    def test_trillion_en(self):
        from pyjpx_etf.config import config

        config.lang = "en"
        result = _fmt_yen(1.5e12, 10)
        assert "T" in result

    def test_billion_en(self):
        from pyjpx_etf.config import config

        config.lang = "en"
        result = _fmt_yen(5e10, 10)
        assert "B" in result

    def test_million_en(self):
        from pyjpx_etf.config import config

        config.lang = "en"
        result = _fmt_yen(3e6, 10)
        assert "M" in result

    def test_small(self):
        result = _fmt_yen(5000, 10)
        assert "5,000" in result

    def test_none_shows_dash(self):
        result = _fmt_yen(None, 10)
        assert "-" in result


# ---------------------------------------------------------------------------
# _truncate_name
# ---------------------------------------------------------------------------


class TestTruncateName:
    def test_short_name_unchanged(self):
        assert _truncate_name("TOPIX", 20) == "TOPIX"

    def test_long_name_truncated(self):
        long_name = "A" * 50
        result = _truncate_name(long_name, 10)
        assert result.endswith("…")
        assert len(result) <= 11  # 10 chars + ellipsis

    def test_japanese_name_width(self):
        name = "日経半導体株ＥＴＦ"  # each char ~2 cols
        result = _truncate_name(name, 10)
        assert result.endswith("…")
