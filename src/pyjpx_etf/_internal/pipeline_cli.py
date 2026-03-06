"""CLI entry point for pipeline. Used by GitHub Actions."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .pipeline import run_pipeline


def main() -> None:
    """Entry point: python -m pyjpx_etf._internal.pipeline_cli [--db path]"""
    parser = argparse.ArgumentParser(description="Build PCF database snapshot")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("/tmp/pcf.db"),
        help="Path to output SQLite database (default: /tmp/pcf.db)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Delay between requests in seconds (default: 0.3)",
    )
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=None,
        help="Save unparseable CSV files to this directory for debugging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    from ..config import config

    config.request_delay = args.delay

    run_pipeline(args.db, debug_dir=args.debug_dir)


if __name__ == "__main__":
    main()
