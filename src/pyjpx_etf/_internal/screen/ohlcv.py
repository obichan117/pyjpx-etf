"""I/O: OHLCV fetch (J-Quants + Kabutan fallback) and local disk cache.

Requires the `screen` extras (pyjquants, pykabutan) — imported lazily inside
functions. This module itself is only imported lazily from
`screen.main_screen()` once the extras guard has passed.

Does NOT use _internal/_cache.TieredCache because: (1) needs calendar-day
freshness via date-keyed files, not elapsed-second TTL; (2) values are pandas
DataFrames requiring custom JSON encode/decode; (3) one-shot CLI load pattern
where memory tier and zero-arg fetcher signatures don't fit.
"""

from __future__ import annotations

import io
import json
import os
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stderr
from datetime import date
from pathlib import Path

import pandas as pd

# Load ~/.env if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv(Path.home() / ".env")
except ModuleNotFoundError:
    _env_file = Path.home() / ".env"
    if _env_file.exists():
        for _line in _env_file.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))

CACHE_DIR = Path.home() / ".cache" / "pyjpx-etf" / "ohlcv"
MAX_WORKERS_JQUANTS = 10
MAX_WORKERS_KABUTAN = 3
KABUTAN_DELAY = 0.5


# ---------------------------------------------------------------------------
# OHLCV cache
# ---------------------------------------------------------------------------


def _cache_path(period: str) -> Path:
    return CACHE_DIR / f"ohlcv_{period}_{date.today().isoformat()}.json"


def _json_default(obj: object) -> object:
    """Handle Decimal, Timestamp, date, etc. for JSON serialization."""
    if hasattr(obj, "__float__"):
        return float(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def _save_cache(ohlcv: dict[str, pd.DataFrame], period: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Clean old cache files for this period
    for f in CACHE_DIR.glob(f"ohlcv_{period}_*.json"):
        if f != _cache_path(period):
            f.unlink()
    data = {}
    for code, df in ohlcv.items():
        data[code] = df.to_dict(orient="records")
    _cache_path(period).write_text(
        json.dumps(data, default=_json_default), encoding="utf-8"
    )


def _load_cache(period: str) -> dict[str, pd.DataFrame] | None:
    path = _cache_path(period)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {code: pd.DataFrame(records) for code, records in raw.items()}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


def _fetch_jquants(code: str, period: str) -> tuple[str, pd.DataFrame]:
    import pyjquants as pjq

    try:
        with warnings.catch_warnings(), redirect_stderr(io.StringIO()):
            warnings.simplefilter("ignore")
            df = pjq.Ticker(code).history(period)
        return code, df
    except Exception:
        return code, pd.DataFrame()


def _fetch_kabutan(code: str, period: str) -> tuple[str, pd.DataFrame]:
    import pykabutan as pk

    try:
        df = pk.Ticker(code).history(period)
        return code, df
    except Exception:
        return code, pd.DataFrame()


def _fetch_all(codes: list[str], period: str) -> dict[str, pd.DataFrame]:
    # Try cache first
    cached = _load_cache(period)
    if cached:
        print(f"  Using cached data ({len(cached)} ETFs from today)")
        return cached

    results: dict[str, pd.DataFrame] = {}
    total = len(codes)

    # Phase 1: J-Quants
    print("  Phase 1: J-Quants (threaded)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_JQUANTS) as executor:
        futures = {
            executor.submit(_fetch_jquants, code, period): code for code in codes
        }
        done = 0
        for future in as_completed(futures):
            code, df = future.result()
            done += 1
            if not df.empty:
                results[code] = df
            if done % 50 == 0 or done == total:
                print(f"    {done}/{total}...", flush=True)

    jquants_count = len(results)
    missing = [c for c in codes if c not in results]

    if missing:
        # Phase 2: Kabutan fallback
        try:
            import pykabutan as pk
        except ModuleNotFoundError:
            print(
                f"  Skipping Kabutan fallback (pykabutan not installed). "
                f"{len(missing)} ETFs missing."
            )
        else:
            print(f"  Phase 2: Kabutan fallback for {len(missing)} missing ETFs...")
            pk.config.request_delay = KABUTAN_DELAY

            with ThreadPoolExecutor(max_workers=MAX_WORKERS_KABUTAN) as executor:
                futures = {
                    executor.submit(_fetch_kabutan, code, period): code
                    for code in missing
                }
                done = 0
                for future in as_completed(futures):
                    code, df = future.result()
                    done += 1
                    if not df.empty:
                        results[code] = df
                    if done % 50 == 0 or done == len(missing):
                        print(f"    {done}/{len(missing)}...", flush=True)

            kabutan_count = len(results) - jquants_count
            still_missing = len(codes) - len(results)
            print(
                f"  J-Quants: {jquants_count}, Kabutan: +{kabutan_count}, "
                f"still missing: {still_missing}"
            )

    # Save to cache
    if results:
        try:
            _save_cache(results, period)
            print("  Cached for today.")
        except Exception as exc:
            print(f"  Warning: failed to cache ({exc})")

    return results
