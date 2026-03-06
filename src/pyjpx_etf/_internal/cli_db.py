"""CLI handlers for DB-dependent commands: sync, search, history."""

from __future__ import annotations

import sys

from ..config import config
from ..exceptions import PyJPXETFError
from .cli_fmt import display_width, pad


def main_sync(argv: list[str]) -> None:
    """Handle ``etf sync [--force]``."""
    force = "--force" in argv

    from ..sync import sync

    try:
        path = sync(force=force)
        print(f"Database ready: {path}")
    except PyJPXETFError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def main_search(argv: list[str]) -> None:
    """Handle ``etf search <stock_code> [n] [--en]``."""
    stock_code = None
    n = 10
    en = False

    for arg in argv:
        if arg == "--en":
            en = True
        elif stock_code is None:
            stock_code = arg
        else:
            try:
                n = int(arg)
            except ValueError:
                print(f"Error: invalid argument {arg!r}", file=sys.stderr)
                sys.exit(1)

    if stock_code is None:
        print("Usage: etf search <stock_code> [n] [--en]", file=sys.stderr)
        sys.exit(1)

    if en:
        config.lang = "en"

    from ..search import search

    try:
        df = search(stock_code, n=n)
    except PyJPXETFError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if df.empty:
        print(f"No ETFs found holding stock {stock_code}.")
        return

    name_width = max(display_width(str(n)) for n in df["name"])
    name_width = max(name_width, 4)

    print()
    print(f" {'Code':<5}  {pad('Name', name_width)}  {'Weight':>8}  {'Shares':>12}")
    print(f"{'─' * 5}  {'─' * name_width}  {'─' * 8}  {'─' * 12}")
    for _, row in df.iterrows():
        print(
            f" {row['code']:<5}  {pad(str(row['name']), name_width)}"
            f"  {row['weight'] * 100:>7.2f}%  {row['shares']:>12,.0f}"
        )
    print()


def main_history(argv: list[str]) -> None:
    """Handle ``etf history <etf_code> [stock_code] [--en]``."""
    etf_code = None
    stock_code = None
    en = False

    for arg in argv:
        if arg == "--en":
            en = True
        elif etf_code is None:
            etf_code = arg
        elif stock_code is None:
            stock_code = arg

    if etf_code is None:
        print("Usage: etf history <etf_code> [stock_code] [--en]", file=sys.stderr)
        sys.exit(1)

    if en:
        config.lang = "en"

    from ..history import history

    try:
        df = history(etf_code, stock_code)
    except PyJPXETFError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if df.empty:
        print("No history data available.")
        return

    if stock_code is not None:
        # Time series view
        print()
        print(f" {'Date':<12}  {'Weight':>8}  {'Shares':>12}  {'Price':>10}")
        print(f"{'─' * 12}  {'─' * 8}  {'─' * 12}  {'─' * 10}")
        for _, row in df.iterrows():
            print(
                f" {row['date']:<12}  {row['weight'] * 100:>7.2f}%"
                f"  {row['shares']:>12,.0f}  {row['price']:>10,.1f}"
            )
        print()
    else:
        # Top holdings with weight change
        name_width = max(display_width(str(n)) for n in df["name"])
        name_width = max(name_width, 4)

        print()
        print(f" {'Code':<5}  {pad('Name', name_width)}  {'Weight':>8}  {'Change':>8}")
        print(f"{'─' * 5}  {'─' * name_width}  {'─' * 8}  {'─' * 8}")
        for _, row in df.iterrows():
            change = row["weight_change"] * 100
            sign = "+" if change >= 0 else ""
            print(
                f" {row['code']:<5}  {pad(str(row['name']), name_width)}"
                f"  {row['weight'] * 100:>7.2f}%  {sign}{change:>6.2f}%"
            )
        print()
