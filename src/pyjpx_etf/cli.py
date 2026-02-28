"""CLI entry point: etf <code> | etf rank [n] [period]"""

from __future__ import annotations

import sys
import unicodedata

import pandas as pd

from ._internal.rakuten import PERIOD_COLUMNS
from .config import _ALIASES, config
from .etf import ETF
from .exceptions import PyJPXETFError
from .ranking import ranking


def _display_width(s: str) -> int:
    """Return the number of terminal columns a string occupies."""
    return sum(2 if unicodedata.east_asian_width(c) in ("F", "W") else 1 for c in s)


def _pad(s: str, width: int) -> str:
    """Left-align *s* padded to *width* terminal columns."""
    return s + " " * (width - _display_width(s))


def _format_yen(value: int) -> str:
    """Format yen amount with Japanese unit suffixes (億/兆)."""
    oku = value / 1_0000_0000  # 億
    if oku >= 10000:  # >= 1兆
        cho = value / 1_0000_0000_0000
        s = f"{cho:.1f}".rstrip("0").rstrip(".")
        return f"{s}兆"
    if oku >= 100:
        return f"{oku:.0f}億"
    s = f"{oku:.2f}".rstrip("0").rstrip(".")
    return f"{s}億"


def _resolve_code(code: str) -> str:
    """Resolve an alias or raw ETF code to a numeric/alphanumeric code."""
    return _ALIASES.get(code.lower(), code)


def _print_holdings(e: ETF, *, show_all: bool) -> None:
    """Print the holdings table (top 10 or all)."""
    if show_all:
        df = e.to_dataframe()
        df = (
            df[["code", "name", "weight"]]
            .assign(weight=lambda d: d["weight"] * 100)
            .reset_index(drop=True)
        )
    else:
        df = e.top()

    name_width = max(_display_width(n) for n in df["name"])
    header = f" {'Code':<5}  {_pad('Name', name_width)}  {'Weight':>6}"
    sep = f"{'─' * 5}  {'─' * name_width}  {'─' * 6}"

    print(header)
    print(sep)
    for _, row in df.iterrows():
        print(
            f" {row['code']:<5}  {_pad(row['name'], name_width)}  {row['weight']:>5.1f}%"
        )
    print()


def _print_ranking(df: pd.DataFrame, period: str) -> None:
    """Format and print the ranking table."""
    if df.empty:
        print("No data available.")
        return

    period_label = f"Return ({period})"
    name_width = max(_display_width(str(n)) for n in df["name"])
    name_width = max(name_width, 4)  # at least "Name"

    header = (
        f" {'Code':<5}  {_pad('Name', name_width)}"
        f"  {period_label:>12}  {'Fee':>5}  {'Yield':>6}"
    )
    sep = (
        f"{'─' * 5}  {'─' * name_width}"
        f"  {'─' * 12}  {'─' * 5}  {'─' * 6}"
    )

    print()
    print(header)
    print(sep)
    for _, row in df.iterrows():
        fee_str = f"{row['fee']:.2f}" if pd.notna(row["fee"]) else "  -"
        yld_str = f"{row['dividend_yield']:.2f}%" if pd.notna(row["dividend_yield"]) else "   -"
        print(
            f" {row['code']:<5}  {_pad(str(row['name']), name_width)}"
            f"  {row['return']:>11.2f}%  {fee_str:>5}  {yld_str:>6}"
        )
    print()


def _main_rank(argv: list[str]) -> None:
    """Handle ``etf rank [n] [period] [--en]``."""
    n = 10
    period = "1m"
    en = False

    positional: list[str] = []
    for arg in argv:
        if arg == "--en":
            en = True
        else:
            positional.append(arg)

    valid_periods = set(PERIOD_COLUMNS.keys())

    for arg in positional:
        if arg in valid_periods:
            period = arg
        else:
            try:
                n = int(arg)
            except ValueError:
                print(f"Error: invalid argument {arg!r}", file=sys.stderr)
                sys.exit(1)

    if en:
        config.lang = "en"

    try:
        df = ranking(period=period, n=n)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    _print_ranking(df, period)


def _main_etf(argv: list[str]) -> None:
    """Handle ``etf <code> [--en] [-a]``."""
    code = None
    en = False
    show_all = False

    i = 0
    while i < len(argv):
        if argv[i] == "--en":
            en = True
        elif argv[i] in ("-a", "--all"):
            show_all = True
        elif code is None:
            code = argv[i]
        i += 1

    if code is None:
        print("Usage: etf <code|alias> [--en] [-a]", file=sys.stderr)
        sys.exit(1)

    if en:
        config.lang = "en"

    code = _resolve_code(code)

    try:
        e = ETF(code)
        info = e.info
    except PyJPXETFError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{info.code} — {info.name} ({info.date})")

    meta_parts: list[str] = []
    meta_parts.append(f"Nav: {_format_yen(e.nav)}")
    fee = e.fee
    if fee is not None:
        fee_label = "信託報酬" if config.lang == "ja" else "Fee"
        meta_parts.append(f"{fee_label}: {fee}%")
    print("  ".join(meta_parts))
    print()

    _print_holdings(e, show_all=show_all)


def _print_help() -> None:
    from . import __version__

    print(f"""\
pyjpx-etf {__version__}

Usage:
  etf <code|alias> [--en] [-a]    Show ETF portfolio composition
  etf rank [n] [period] [--en]    Rank ETFs by return
  etf --version                   Show version
  etf --help                      Show this help

Aliases:
  topix, 225, core30, div50, div70, pbr, sox, jpsox1, jpsox2

Periods:
  1m (default), 3m, 6m, 1y, 3y, 5y, 10y, ytd

Examples:
  etf 1306                Top 10 holdings of TOPIX ETF
  etf topix --en -a       All holdings in English
  etf rank                Top 10 by 1-month return
  etf rank -5 1y          Worst 5 by 1-year return""")


def main() -> None:
    argv = sys.argv[1:]
    if not argv or (argv[0] in ("-h", "--help")):
        _print_help()
        return
    if argv[0] in ("-V", "--version"):
        from . import __version__

        print(f"pyjpx-etf {__version__}")
        return
    if argv[0] == "rank":
        _main_rank(argv[1:])
    else:
        _main_etf(argv)
