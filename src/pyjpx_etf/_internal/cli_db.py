"""CLI handlers for DB-dependent commands: sync, search, history."""

from __future__ import annotations

import sys

import pandas as pd

from ..config import config
from ..exceptions import PyJPXETFError
from .cli_fmt import display_width, format_yen, pad
from .db_core import get_connection


def _lookup_name(table: str, code: str, en: bool) -> str:
    """Look up a name from etfs or securities table."""
    lang_col = "name_en" if en else "name_ja"
    try:
        conn = get_connection()
        row = conn.execute(
            f"SELECT {lang_col} FROM {table} WHERE code = ?", (code,)
        ).fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    return ""


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
    """Handle ``etf find <stock_code> [n] [--en] [--gap PCT]``."""
    stock_code = None
    n = 10
    en = False
    gap = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--en":
            en = True
        elif arg == "--gap" and i + 1 < len(argv):
            i += 1
            try:
                gap = float(argv[i])
            except ValueError:
                print(f"Error: invalid --gap value {argv[i]!r}", file=sys.stderr)
                sys.exit(1)
        elif stock_code is None:
            stock_code = arg
        else:
            try:
                n = int(arg)
            except ValueError:
                print(f"Error: invalid argument {arg!r}", file=sys.stderr)
                sys.exit(1)
        i += 1

    if stock_code is None:
        print("Usage: etf find <stock_code> [n] [--en] [--gap PCT]", file=sys.stderr)
        sys.exit(1)

    if en:
        config.lang = "en"

    from ..search import search

    try:
        df = search(stock_code, n=n, gap=gap)
    except PyJPXETFError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if df.empty:
        print(f"No ETFs found holding stock {stock_code}.")
        return

    stock_name = _lookup_name("securities", stock_code, en)

    name_width = max(display_width(str(n)) for n in df["name"])
    name_width = max(name_width, 4)

    print()
    header = stock_code
    if stock_name:
        header += f" {stock_name}"
    print(f"  {header}")
    print()
    header_line = (
        f" {'Code':<5}  {pad('Name', name_width)}"
        f"  {'Weight':>8}  {'Shares':>12}  {'AUM':>10}"
    )
    sep_line = f"{'─' * 5}  {'─' * name_width}  {'─' * 8}  {'─' * 12}  {'─' * 10}"
    if gap is not None:
        header_line += f"  {'Impact':>8}"
        sep_line += f"  {'─' * 8}"
    print(header_line)
    print(sep_line)
    for _, row in df.iterrows():
        aum = row.get("aum")
        aum_str = format_yen(aum) if pd.notna(aum) else "-"
        line = (
            f" {row['code']:<5}  {pad(str(row['name']), name_width)}"
            f"  {row['weight'] * 100:>7.2f}%  {row['shares']:>12,.0f}"
            f"  {aum_str:>10}"
        )
        if gap is not None:
            impact = row["impact"]  # already in percent: weight (fraction) × gap (%)
            sign = "+" if impact >= 0 else ""
            line += f"  {sign}{impact:>6.2f}%"
        print(line)
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

    etf_name = _lookup_name("etfs", etf_code, en)
    header = etf_code
    if etf_name:
        header += f" {etf_name}"
    if stock_code is not None:
        stock_name = _lookup_name("securities", stock_code, en)
        header += f" — {stock_code}"
        if stock_name:
            header += f" {stock_name}"

    if stock_code is not None:
        # Time series view
        print()
        print(f"  {header}")
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
        print(f"  {header}")
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
