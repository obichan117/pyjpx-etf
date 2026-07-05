"""Tests for _internal/screen/ (signals + display) — screener logic and formatting."""

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from pyjpx_etf._internal.screen import main_screen
from pyjpx_etf._internal.screen.display import (
    _fmt,
    _fmt_yen,
    _truncate_name,
)
from pyjpx_etf._internal.screen.signals import (
    ROLLING_WINDOW,
    _compute_signals,
    _safe_round,
    _screen,
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
        data.append(
            {
                "date": f"2026-01-{i + 1:02d}",
                "open": close - 5,
                "high": close + 20,
                "low": close - 10,
                "close": close,
                "volume": base_volume + i * 100,
            }
        )
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
        for col in (
            "range_pct",
            "atr",
            "range_ratio",
            "vol_ratio",
            "return_pct",
            "turnover",
            "turnover_ratio",
        ):
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
        result = _screen(
            ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM, sort_by="range_pct", top=10
        )
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
        result = _screen(
            ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM, sort_by="range_pct", top=2
        )
        assert len(result) == 2

    def test_skips_short_series(self):
        ohlcv = {"1306": _make_ohlcv(rows=5)}  # too few rows
        result = _screen(
            ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM, sort_by="range_pct", top=10
        )
        assert result.empty

    def test_includes_aum_and_fee(self):
        ohlcv = {"1306": _make_ohlcv()}
        result = _screen(
            ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM, sort_by="range_pct", top=10
        )
        assert result.iloc[0]["aum"] == 31.2e12
        assert result.iloc[0]["fee"] == 0.06

    def test_db_only_stat_aum(self):
        result = _screen({}, MOCK_NAMES, MOCK_FEES, MOCK_AUM, sort_by="aum", top=10)
        assert not result.empty
        vals = result["aum"].tolist()
        assert vals == sorted(vals, reverse=True)

    def test_db_only_stat_fee_ascending(self):
        result = _screen({}, MOCK_NAMES, MOCK_FEES, MOCK_AUM, sort_by="fee", top=10)
        assert not result.empty
        vals = result["fee"].tolist()
        assert vals == sorted(vals)

    def test_return_pct_sorted_by_abs(self):
        ohlcv = {
            "1306": _make_ohlcv(base_close=1000),
            "9999": _make_spike_ohlcv(),
        }
        result = _screen(
            ohlcv, MOCK_NAMES, MOCK_FEES, MOCK_AUM, sort_by="return_pct", top=10
        )
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


# ---------------------------------------------------------------------------
# main_screen — lazy extras guard
# ---------------------------------------------------------------------------


def _make_fee_db(tmp_path):
    """Build a minimal pcf.db with rows for a `--by fee` screen."""
    from pyjpx_etf._internal.db_core import _SCHEMA_SQL

    db_file = tmp_path / "pcf.db"
    conn = sqlite3.connect(db_file)
    conn.executescript(_SCHEMA_SQL)
    conn.execute(
        "INSERT INTO etfs (code, name_ja, name_en, fee) VALUES (?, ?, ?, ?)",
        ("1306", "TOPIX ETF", "TOPIX ETF", 0.06),
    )
    conn.execute(
        "INSERT INTO etfs (code, name_ja, name_en, fee) VALUES (?, ?, ?, ?)",
        ("2644", "半導体ETF", "Semiconductor ETF", 0.30),
    )
    conn.execute(
        "INSERT INTO pcf_info (code, date, name, cash_component, shares_outstanding) "
        "VALUES (?, ?, ?, ?, ?)",
        ("1306", "2026-06-30", "TOPIX ETF", 1000.0, 100000),
    )
    conn.execute(
        "INSERT INTO pcf_info (code, date, name, cash_component, shares_outstanding) "
        "VALUES (?, ?, ?, ?, ?)",
        ("2644", "2026-06-30", "半導体ETF", 500.0, 50000),
    )
    conn.execute(
        "INSERT INTO pcf_holdings "
        "(code, date, holding_code, name, isin, exchange, currency, shares, "
        "price, weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "1306",
            "2026-06-30",
            "7203",
            "TOYOTA",
            "JP001",
            "TSE",
            "JPY",
            1000.0,
            2500.0,
            0.6,
        ),
    )
    conn.commit()
    conn.close()
    return db_file


class TestMainScreenExtrasGuard:
    def test_ohlcv_stat_without_extras_exits(self, tmp_path, monkeypatch, capsys):
        """An OHLCV stat with pyjquants/pykabutan missing prints the install
        hint and exits with code 1, before ever touching the DB queries."""
        import importlib.util as _importlib_util

        original_find_spec = _importlib_util.find_spec

        def fake_find_spec(name, *args, **kwargs):
            if name in ("pyjquants", "pykabutan"):
                return None
            return original_find_spec(name, *args, **kwargs)

        monkeypatch.setattr("importlib.util.find_spec", fake_find_spec)

        # DB existence is checked before the extras guard, so an empty file
        # is enough to get past it — the guard fires before any query runs.
        db_file = tmp_path / "pcf.db"
        db_file.touch()

        with pytest.raises(SystemExit) as exc_info:
            main_screen(["--by", "range_pct", "--db", str(db_file)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "pip install 'pyjpx-etf[screen]'" in err

    def test_fee_stat_skips_guard_without_extras(self, tmp_path, monkeypatch, capsys):
        """`--by fee` is a DB-only stat, so it must work even when
        pyjquants/pykabutan are unavailable."""
        monkeypatch.setattr(
            "importlib.util.find_spec",
            lambda name, *args, **kwargs: None,
        )

        db_file = _make_fee_db(tmp_path)

        main_screen(["--by", "fee", "--db", str(db_file)])

        out = capsys.readouterr().out
        assert "ETF Screener" in out
        assert "1306" in out
        assert "2644" in out


# ---------------------------------------------------------------------------
# main_screen — concentration stats (top1/top3/top10)
# ---------------------------------------------------------------------------


def _make_concentration_db(tmp_path):
    """Build a minimal pcf.db with a concentrated and a diversified ETF."""
    from pyjpx_etf._internal.db_core import _SCHEMA_SQL

    db_file = tmp_path / "pcf.db"
    conn = sqlite3.connect(db_file)
    conn.executescript(_SCHEMA_SQL)
    conn.execute(
        "INSERT INTO etfs (code, name_ja, name_en, fee) VALUES (?, ?, ?, ?)",
        ("9001", "集中ETF", "Concentrated ETF", 0.10),
    )
    conn.execute(
        "INSERT INTO etfs (code, name_ja, name_en, fee) VALUES (?, ?, ?, ?)",
        ("9002", "分散ETF", "Diversified ETF", 0.20),
    )
    conn.execute(
        "INSERT INTO pcf_info (code, date, name, cash_component, shares_outstanding) "
        "VALUES (?, ?, ?, ?, ?)",
        ("9001", "2026-06-30", "Concentrated ETF", 1000.0, 1000),
    )
    conn.execute(
        "INSERT INTO pcf_info (code, date, name, cash_component, shares_outstanding) "
        "VALUES (?, ?, ?, ?, ?)",
        ("9002", "2026-06-30", "Diversified ETF", 1000.0, 1000),
    )
    conn.execute(
        "INSERT INTO pcf_holdings "
        "(code, date, holding_code, name, isin, exchange, currency, shares, "
        "price, weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "9001",
            "2026-06-30",
            "1111",
            "BigCo",
            "JP101",
            "TSE",
            "JPY",
            100.0,
            1000.0,
            0.22,
        ),
    )
    conn.execute(
        "INSERT INTO pcf_holdings "
        "(code, date, holding_code, name, isin, exchange, currency, shares, "
        "price, weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "9001",
            "2026-06-30",
            "2222",
            "SmallCo",
            "JP102",
            "TSE",
            "JPY",
            100.0,
            100.0,
            0.03,
        ),
    )
    for i in range(20):
        conn.execute(
            "INSERT INTO pcf_holdings "
            "(code, date, holding_code, name, isin, exchange, currency, shares, "
            "price, weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "9002",
                "2026-06-30",
                f"{3000 + i}",
                f"Stock{i}",
                f"JP20{i}",
                "TSE",
                "JPY",
                10.0,
                100.0,
                0.02,
            ),
        )
    conn.commit()
    conn.close()
    return db_file


class TestMainScreenConcentration:
    def test_by_top1_shows_topstock_and_orders_concentrated_first(
        self, tmp_path, capsys
    ):
        db_file = _make_concentration_db(tmp_path)
        main_screen(["--by", "top1", "--db", str(db_file), "--en"])
        out = capsys.readouterr().out
        assert "TopStock" in out
        assert "9001" in out
        assert "9002" in out
        assert out.index("9001") < out.index("9002")
