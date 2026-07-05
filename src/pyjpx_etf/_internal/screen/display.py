"""Rendering: column formatting and terminal output for the ETF screener.

No extras dependency — importable with pandas + cli_fmt alone.
"""

from __future__ import annotations

import pandas as pd

from ..cli_fmt import display_width, pad
from .signals import ASCENDING_STATS, ROLLING_WINDOW

NAME_MAX_WIDTH = 28  # Max display width for ETF name column


def _truncate_name(name: str, max_width: int) -> str:
    """Truncate name to fit within max_width terminal columns."""
    if display_width(name) <= max_width:
        return name
    while display_width(name) > max_width - 1:
        name = name[:-1]
    return name + "…"


def _fmt(val: float | None, width: int, decimals: int = 2, suffix: str = "") -> str:
    if val is None:
        return f"{'-':>{width}}"
    inner_w = width - len(suffix)
    return f"{val:>{inner_w}.{decimals}f}{suffix}"


def _fmt_yen(val: float | None, width: int) -> str:
    from ...config import config

    if val is None:
        return f"{'-':>{width}}"
    if config.lang == "ja":
        if abs(val) >= 1e12:
            return f"{val / 1e12:>{width - 1}.1f}兆"
        if abs(val) >= 1e8:
            return f"{val / 1e8:>{width - 1}.0f}億"
        if abs(val) >= 1e4:
            return f"{val / 1e4:>{width - 1}.0f}万"
    else:
        if abs(val) >= 1e12:
            return f"{val / 1e12:>{width - 1}.1f}T"
        if abs(val) >= 1e9:
            return f"{val / 1e9:>{width - 1}.1f}B"
        if abs(val) >= 1e6:
            return f"{val / 1e6:>{width - 1}.0f}M"
    return f"{val:>{width},.0f}"


# Column definitions: (header, width, formatter)
# Grouped by category for selecting display columns
_COL_TURNOVER = {
    "turnover": ("Turnover", 10, lambda r: _fmt_yen(r.get("turnover"), 10)),
    "turnover_ratio": ("TnR", 5, lambda r: _fmt(r.get("turnover_ratio"), 4, 1, "x")),
}
_COL_VOLATILITY = {
    "range_pct": ("Range%", 7, lambda r: _fmt(r.get("range_pct"), 7)),
    "atr": ("ATR%", 6, lambda r: _fmt(r.get("atr"), 6)),
    "range_ratio": ("Ratio", 6, lambda r: _fmt(r.get("range_ratio"), 5, 1, "x")),
}
_COL_VOLUME = {
    "vol_ratio": ("VolR", 5, lambda r: _fmt(r.get("vol_ratio"), 5, 1)),
    "volume": (
        "Volume",
        12,
        lambda r: (
            f"{int(r.get('volume', 0)):>12,}"
            if r.get("volume") is not None
            else f"{'-':>12}"
        ),
    ),
}
_COL_RETURN = {
    "return_pct": ("Ret%", 7, lambda r: _fmt(r.get("return_pct"), 7)),
}
_COL_FUND = {
    "aum": ("AUM", 10, lambda r: _fmt_yen(r.get("aum"), 10)),
    "fee": ("Fee%", 6, lambda r: _fmt(r.get("fee"), 6)),
}
_COL_CONCENTRATION = {
    "top_name": (
        "TopStock",
        16,
        lambda r: pad(_truncate_name(str(r.get("top_name") or ""), 16), 16),
    ),
    "top1": ("Top1%", 7, lambda r: _fmt(r.get("top1"), 7)),
    "top3": ("Top3%", 7, lambda r: _fmt(r.get("top3"), 7)),
    "top10": ("Top10%", 7, lambda r: _fmt(r.get("top10"), 7)),
    "n_holdings": (
        "#Hold",
        5,
        lambda r: (
            f"{int(r['n_holdings']):>5}"
            if r.get("n_holdings") is not None
            else f"{'-':>5}"
        ),
    ),
}

# Which columns to show for each sort stat
_DISPLAY_PROFILES: dict[str, list[str]] = {
    "turnover": ["turnover", "turnover_ratio", "volume", "aum", "fee"],
    "turnover_ratio": ["turnover_ratio", "turnover", "volume", "aum", "fee"],
    "range_pct": [
        "range_pct",
        "atr",
        "range_ratio",
        "vol_ratio",
        "return_pct",
        "turnover",
    ],
    "atr": ["atr", "range_pct", "range_ratio", "vol_ratio", "return_pct"],
    "range_ratio": ["range_ratio", "range_pct", "atr", "vol_ratio", "turnover"],
    "vol_ratio": ["vol_ratio", "volume", "turnover", "turnover_ratio", "return_pct"],
    "return_pct": ["return_pct", "range_pct", "vol_ratio", "turnover"],
    "aum": ["aum", "fee", "turnover", "turnover_ratio"],
    "fee": ["fee", "aum", "turnover"],
    "top1": ["top1", "top3", "top10", "top_name", "n_holdings", "aum"],
    "top3": ["top3", "top1", "top10", "top_name", "n_holdings", "aum"],
    "top10": ["top10", "top1", "top3", "top_name", "n_holdings", "aum"],
}

# All column defs merged
_ALL_COLS = {
    **_COL_TURNOVER,
    **_COL_VOLATILITY,
    **_COL_VOLUME,
    **_COL_RETURN,
    **_COL_FUND,
    **_COL_CONCENTRATION,
}


def _display(df: pd.DataFrame, sort_by: str) -> None:
    if df.empty:
        print("\nNo results found.")
        return

    # Clamp name width
    name_w = min(
        max((display_width(str(n)) for n in df["name"]), default=4),
        NAME_MAX_WIDTH,
    )
    name_w = max(name_w, 4)

    # Pick columns to display
    col_keys = _DISPLAY_PROFILES.get(sort_by, list(_ALL_COLS.keys())[:6])
    cols = [(k, _ALL_COLS[k]) for k in col_keys if k in _ALL_COLS]

    # Header
    sort_label = sort_by.upper()
    title = "ETF Screener"
    print()
    print(f"  {title} — top {len(df)} by {sort_label}")
    print()

    # Build header line
    hdr = f"  {'#':>2}  {'Code':<5}  {pad('Name', name_w)}"
    sep = f"  {'─' * 2}  {'─' * 5}  {'─' * name_w}"
    if "close" in df.columns:
        hdr += f"  {'Close':>8}"
        sep += f"  {'─' * 8}"
    for _, (label, width, _) in cols:
        hdr += f"  {label:>{width}}"
        sep += f"  {'─' * width}"
    print(hdr)
    print(sep)

    for i, (_, r) in enumerate(df.iterrows(), 1):
        name = _truncate_name(r["name"], name_w)
        line = f"  {i:>2}  {r['code']:<5}  {pad(name, name_w)}"
        if "close" in df.columns:
            line += f"  {r['close']:>8,.0f}"
        for _, (_, _, formatter) in cols:
            line += f"  {formatter(r)}"
        print(line)

    # Footer
    print()
    print(f"  Sorted by: {sort_label}", end="")
    if sort_by == "return_pct":
        print(" (abs value, descending)")
    elif sort_by in ASCENDING_STATS:
        print(" (ascending)")
    else:
        print(" (descending)")
    if "date" in df.columns:
        data_date = str(df.iloc[-1]["date"])[:10]
        print(f"  Rolling window: {ROLLING_WINDOW} days | Data: {data_date}")
    print()


def _print_help() -> None:
    print("""\
Usage: etf screen [--by STAT] [--days N] [--top N] [--en] [--refresh] [--db PATH]

Screen all ETFs by trading activity, volatility, fund size, or fees.

Options:
  --by STAT    Stat to sort by (default: range_pct)
  --days N     OHLCV lookback period in days (default: 30)
  --top N      Number of results (default: 20)
  --en         English names
  --refresh    Force re-fetch (ignore today's cache)
  --db PATH    Path to pcf.db

Available stats:
  Stat            Meaning
  ──────────────────────────────────────────────────────
  turnover        Daily turnover in yen (close * volume)
  turnover_ratio  Today's turnover vs 20-day avg
  range_pct       (high-low)/close * 100
  atr             20-day average of range_pct
  range_ratio     range_pct / atr (>2 = unusual)
  vol_ratio       volume / 20-day avg (>2 = surge)
  return_pct      Daily return %
  aum             Total net asset value (from DB)
  fee             Annual expense ratio % (from DB)
  top1            Top holding weight (from DB)
  top3            Top-3 cumulative weight (from DB)
  top10           Top-10 cumulative weight (from DB)

Stats 'aum', 'fee', 'top1', 'top3', 'top10' use local DB only (no OHLCV fetch needed).
OHLCV data is cached for 1 day at ~/.cache/pyjpx-etf/ohlcv/.

Requires: pyjquants (+ JQUANTS_API_KEY), pykabutan, local pcf.db (etf sync)""")
