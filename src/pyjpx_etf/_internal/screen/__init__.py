"""CLI handler: etf screen — ETF screener.

Screens all ETFs in local pcf.db using OHLCV data from J-Quants
(with Kabutan fallback). Supports sorting by volatility, turnover,
returns, AUM, and fees.

OHLCV data is cached locally (~/.cache/pyjpx-etf/ohlcv/) with 1-day TTL
so only the first run of each day is slow.

Requires (only when sorting by an OHLCV stat):
    - JQUANTS_API_KEY in env or ~/.env
    - pyjquants installed
    - pykabutan installed (fallback for J-Quants gaps)

Always requires:
    - Local pcf.db synced: etf sync

Install: pip install 'pyjpx-etf[screen]'
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from ..db_core import db_path as _get_default_db_path
from .db import (
    _get_concentration,
    _get_etf_aum,
    _get_etf_codes,
    _get_etf_fees,
    _get_etf_names,
)
from .display import _display, _print_help
from .signals import CONCENTRATION_STATS, DEFAULT_STAT, OHLCV_STATS, STATS, _screen

DEFAULT_TOP = 20
DEFAULT_DAYS = 30


def main_screen(argv: list[str]) -> None:
    if "--help" in argv or "-h" in argv:
        _print_help()
        return

    sort_by = DEFAULT_STAT
    days = DEFAULT_DAYS
    top = DEFAULT_TOP
    refresh = False
    db_path = _get_default_db_path()

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--by" and i + 1 < len(argv):
            i += 1
            sort_by = argv[i]
            if sort_by not in STATS:
                print(
                    f"Error: unknown stat {sort_by!r}. Choose from: {', '.join(STATS)}",
                    file=sys.stderr,
                )
                sys.exit(1)
        elif arg == "--days" and i + 1 < len(argv):
            i += 1
            days = int(argv[i])
        elif arg == "--top" and i + 1 < len(argv):
            i += 1
            top = int(argv[i])
        elif arg == "--en":
            from ...config import config

            config.lang = "en"
        elif arg == "--refresh":
            refresh = True
        elif arg == "--db" and i + 1 < len(argv):
            i += 1
            db_path = Path(argv[i])
        else:
            print(f"Error: unknown argument {arg!r}", file=sys.stderr)
            _print_help()
            sys.exit(1)
        i += 1

    if not db_path.exists():
        print(f"Error: DB not found at {db_path}")
        print("Run 'etf sync' to download the database first.")
        sys.exit(1)

    # Lazy extras guard: only needed for OHLCV stats
    needs_ohlcv = sort_by in OHLCV_STATS
    if needs_ohlcv:
        _missing = [
            pkg
            for pkg in ("pyjquants", "pykabutan")
            if importlib.util.find_spec(pkg) is None
        ]
        if _missing:
            print(
                f"Error: stat {sort_by!r} needs OHLCV data. "
                "Install: pip install 'pyjpx-etf[screen]'",
                file=sys.stderr,
            )
            sys.exit(1)

    print("Loading ETF data from DB...")
    codes = _get_etf_codes(db_path)
    names = _get_etf_names(db_path)
    fees = _get_etf_fees(db_path)
    aum_data = _get_etf_aum(db_path)
    print(f"  Found {len(codes)} ETFs")

    concentration_data: dict = {}
    if sort_by in CONCENTRATION_STATS:
        concentration_data = _get_concentration(db_path)

    ohlcv: dict = {}

    if needs_ohlcv:
        from .ohlcv import _cache_path, _fetch_all

        period = f"{days}d"

        # Clear cache if --refresh
        if refresh:
            path = _cache_path(period)
            if path.exists():
                path.unlink()
                print("  Cache cleared.")

        print(f"\nFetching {period} OHLCV data...")
        ohlcv = _fetch_all(codes, period)
        print(f"  Total: {len(ohlcv)} ETFs with data")

    print(f"\nScreening top {top} by {sort_by}...")
    results = _screen(
        ohlcv,
        names,
        fees,
        aum_data,
        sort_by=sort_by,
        top=top,
        concentration=concentration_data,
    )
    _display(results, sort_by)
