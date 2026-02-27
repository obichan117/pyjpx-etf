"""CLI entry point: etf <code>"""

from __future__ import annotations

import argparse
import sys
import unicodedata

from .config import config
from .etf import ETF
from .exceptions import PyJPXETFError


def _display_width(s: str) -> int:
    """Return the number of terminal columns a string occupies."""
    return sum(2 if unicodedata.east_asian_width(c) in ("F", "W") else 1 for c in s)


def _pad(s: str, width: int) -> str:
    """Left-align *s* padded to *width* terminal columns."""
    return s + " " * (width - _display_width(s))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="etf",
        description="Show JPX ETF portfolio composition data.",
    )
    parser.add_argument("code", help="ETF code (e.g. 1306)")
    parser.add_argument(
        "--en", action="store_true", help="show English names (default: Japanese)"
    )
    args = parser.parse_args()

    if args.en:
        config.lang = "en"

    try:
        e = ETF(args.code)
        info = e.info
        df = e.top()
    except PyJPXETFError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{info.code} — {info.name} ({info.date})\n")

    name_width = max(_display_width(n) for n in df["name"])
    header = f" {'Code':<5}  {_pad('Name', name_width)}  {'Weight':>6}"
    sep = f"{'─' * 5}  {'─' * name_width}  {'─' * 6}"

    print(header)
    print(sep)
    for _, row in df.iterrows():
        print(f" {row['code']:<5}  {_pad(row['name'], name_width)}  {row['weight']:>5.1f}%")
    print()
