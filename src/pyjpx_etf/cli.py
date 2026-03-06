"""CLI entry point: etf <code> | etf rank | etf sync | etf search | etf history"""

from __future__ import annotations

import sys


def _print_help() -> None:
    from . import __version__

    print(f"""\
pyjpx-etf {__version__}

Usage:
  etf <code|alias> [--en] [-a] [--live]  Show ETF portfolio composition
  etf rank [n] [period] [--en]           Rank ETFs by return
  etf sync [--force]                     Download/update PCF database
  etf find <stock_code> [n] [--en]       Find ETFs holding a stock
  etf history <etf_code> [stock] [--en]  Weight history
  etf --version                          Show version
  etf --help                             Show this help

Aliases:
  topix, 225, core30, div50, div70, pbr, sox, jpsox1, jpsox2

Periods:
  1m (default), 3m, 6m, 1y, 3y, 5y, 10y, ytd

Examples:
  etf 1306                Top 10 holdings of TOPIX ETF
  etf topix --en -a       All holdings in English
  etf 1306 --live         Force live fetch (skip local DB)
  etf rank                Top 10 by 1-month return
  etf rank -5 1y          Worst 5 by 1-year return
  etf sync                Download latest PCF database
  etf find 6857            ETFs holding Advantest
  etf find 7203 5          Top 5 ETFs holding Toyota
  etf history 1306 6857   Advantest weight in TOPIX ETF over time""")


def main() -> None:
    argv = sys.argv[1:]
    if not argv or (argv[0] in ("-h", "--help")):
        _print_help()
        return
    if argv[0] in ("-V", "--version"):
        from . import __version__

        print(f"pyjpx-etf {__version__}")
        return

    from ._internal.cli_db import main_history, main_search, main_sync
    from ._internal.cli_rank import main_rank
    from ._internal.cli_show import main_etf

    if argv[0] == "rank":
        main_rank(argv[1:])
    elif argv[0] == "sync":
        main_sync(argv[1:])
    elif argv[0] in ("find", "search"):
        main_search(argv[1:])
    elif argv[0] == "history":
        main_history(argv[1:])
    else:
        main_etf(argv)
