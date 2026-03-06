"""CLI handler: etf <code> [--en] [-a] [--live]"""

from __future__ import annotations

import sys

from ..config import _ALIASES, config
from ..etf import ETF
from ..exceptions import PyJPXETFError
from .cli_fmt import display_width, format_yen, pad


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

    name_width = max(display_width(n) for n in df["name"])
    header = f" {'Code':<5}  {pad('Name', name_width)}  {'Weight':>6}"
    sep = f"{'─' * 5}  {'─' * name_width}  {'─' * 6}"

    print(header)
    print(sep)
    for _, row in df.iterrows():
        print(
            f" {row['code']:<5}  {pad(row['name'], name_width)}  {row['weight']:>5.1f}%"
        )
    print()


def main_etf(argv: list[str]) -> None:
    """Handle ``etf <code> [--en] [-a] [--live]``."""
    code = None
    en = False
    show_all = False
    live = False

    i = 0
    while i < len(argv):
        if argv[i] == "--en":
            en = True
        elif argv[i] in ("-a", "--all"):
            show_all = True
        elif argv[i] == "--live":
            live = True
        elif code is None:
            code = argv[i]
        i += 1

    if code is None:
        print("Usage: etf <code|alias> [--en] [-a] [--live]", file=sys.stderr)
        sys.exit(1)

    if en:
        config.lang = "en"

    code = _resolve_code(code)

    try:
        e = ETF(code, live=live)
        info = e.info
    except PyJPXETFError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{info.code} — {info.name} ({info.date})")

    meta_parts: list[str] = []
    meta_parts.append(f"Nav: {format_yen(e.nav)}")
    fee = e.fee
    if fee is not None:
        fee_label = "信託報酬" if config.lang == "ja" else "Fee"
        meta_parts.append(f"{fee_label}: {fee}%")
    print("  ".join(meta_parts))
    print()

    _print_holdings(e, show_all=show_all)
