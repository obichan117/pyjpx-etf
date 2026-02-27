"""CLI entry point: etf <code>"""

from __future__ import annotations

import argparse
import sys

from .etf import ETF
from .exceptions import PyJPXETFError


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="etf",
        description="Show JPX ETF portfolio composition data.",
    )
    parser.add_argument("code", help="ETF code (e.g. 1306)")
    args = parser.parse_args()

    try:
        e = ETF(args.code)
        info = e.info
        df = e.top()
    except PyJPXETFError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{info.code} — {info.name} ({info.date})\n")

    name_width = max(len(n) for n in df["name"])
    header = f" {'Code':<5}  {'Name':<{name_width}}  {'Weight':>6}"
    sep = f"{'─' * 5}  {'─' * name_width}  {'─' * 6}"

    print(header)
    print(sep)
    for _, row in df.iterrows():
        print(f" {row['code']:<5}  {row['name']:<{name_width}}  {row['weight']:>5.1f}%")
    print()
