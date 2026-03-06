"""CLI handler: etf rank [n] [period] [--en]"""

from __future__ import annotations

import sys

import pandas as pd

from ..config import config
from ..ranking import ranking
from .cli_fmt import display_width, pad
from .rakuten import PERIOD_COLUMNS


def _print_ranking(df: pd.DataFrame, period: str) -> None:
    """Format and print the ranking table."""
    if df.empty:
        print("No data available.")
        return

    period_label = f"Return ({period})"
    name_width = max(display_width(str(n)) for n in df["name"])
    name_width = max(name_width, 4)  # at least "Name"

    header = (
        f" {'Code':<5}  {pad('Name', name_width)}"
        f"  {period_label:>12}  {'Fee':>6}  {'Yield':>6}"
    )
    sep = f"{'─' * 5}  {'─' * name_width}  {'─' * 12}  {'─' * 6}  {'─' * 6}"

    print()
    print(header)
    print(sep)
    for _, row in df.iterrows():
        fee_str = f"{row['fee']:.2f}%" if pd.notna(row["fee"]) else "   -"
        yld_str = (
            f"{row['dividend_yield']:.2f}%"
            if pd.notna(row["dividend_yield"])
            else "   -"
        )
        print(
            f" {row['code']:<5}  {pad(str(row['name']), name_width)}"
            f"  {row['return']:>11.2f}%  {fee_str:>6}  {yld_str:>6}"
        )
    print()


def main_rank(argv: list[str]) -> None:
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
