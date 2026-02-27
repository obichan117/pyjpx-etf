"""CLI entry point: etf <code>"""

from __future__ import annotations

import argparse
import sys
import unicodedata

from .config import _ALIASES, config
from .etf import ETF
from .exceptions import PyJPXETFError


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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="etf",
        description="Show JPX ETF portfolio composition data.",
    )
    parser.add_argument(
        "code",
        help="ETF code or alias (e.g. 1306, topix, 225, sox, fang, jpsox1, jpsox2)",
    )
    parser.add_argument(
        "--en", action="store_true", help="show English names (default: Japanese)"
    )
    parser.add_argument(
        "-a", "--all", action="store_true", help="show all holdings (default: top 10)"
    )
    args = parser.parse_args()

    if args.en:
        config.lang = "en"

    code = _resolve_code(args.code)

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

    _print_holdings(e, show_all=args.all)
