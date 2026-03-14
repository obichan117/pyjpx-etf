"""CLI handler: etf screen — ETF screener.

Screens all ETFs in local pcf.db using OHLCV data from J-Quants
(with Kabutan fallback). Supports sorting by volatility, turnover,
returns, AUM, and fees.

OHLCV data is cached locally (~/.cache/pyjpx-etf/ohlcv/) with 1-day TTL
so only the first run of each day is slow.

Requires:
    - JQUANTS_API_KEY in env or ~/.env
    - pyjquants installed
    - pykabutan installed (fallback for J-Quants gaps)
    - Local pcf.db synced: etf sync

Install: pip install 'pyjpx-etf[screen]'
"""

from __future__ import annotations

import importlib

_missing = [
    pkg for pkg in ("pyjquants", "pykabutan") if importlib.util.find_spec(pkg) is None
]
if _missing:
    raise ImportError(
        f"Missing screen dependencies: {', '.join(_missing)}. "
        "Install with: pip install 'pyjpx-etf[screen]'"
    )

import io  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import sqlite3  # noqa: E402
import sys  # noqa: E402
import warnings  # noqa: E402
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402
from contextlib import redirect_stderr  # noqa: E402
from datetime import date  # noqa: E402
from pathlib import Path  # noqa: E402

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

import pandas as pd  # noqa: E402

from .cli_fmt import display_width, pad  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROLLING_WINDOW = 20
DEFAULT_TOP = 20
DEFAULT_DAYS = 30
MAX_WORKERS_JQUANTS = 10
MAX_WORKERS_KABUTAN = 3
KABUTAN_DELAY = 0.5
CACHE_DIR = Path.home() / ".cache" / "pyjpx-etf" / "ohlcv"
NAME_MAX_WIDTH = 28  # Max display width for ETF name column

# Stats that require OHLCV data
OHLCV_STATS = {
    "turnover": "Daily turnover (yen)",
    "turnover_ratio": "Today's turnover vs 20-day avg",
    "range_pct": "Daily range as % of close",
    "atr": "20-day average of range_pct",
    "range_ratio": "Today's range vs avg",
    "vol_ratio": "Today's volume vs 20-day avg",
    "return_pct": "Daily return %",
}

# Stats from DB only (no OHLCV needed)
DB_STATS = {
    "aum": "Total net asset value (yen)",
    "fee": "Annual expense ratio %",
}

STATS = {**OHLCV_STATS, **DB_STATS}

DEFAULT_STAT = "range_pct"

# Stats where lower is better (sort ascending)
ASCENDING_STATS = {"fee"}


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


def _get_etf_codes(db_path: Path) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT code FROM pcf_info ORDER BY code"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def _get_etf_names(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT code, name_ja FROM etfs").fetchall()
        return {r[0]: r[1] or "" for r in rows}
    finally:
        conn.close()


def _get_etf_fees(db_path: Path) -> dict[str, float]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT code, fee FROM etfs WHERE fee IS NOT NULL"
        ).fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        conn.close()


def _get_etf_aum(db_path: Path) -> dict[str, float]:
    """Compute AUM for each ETF from the latest date in pcf_info + pcf_holdings."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("""
            SELECT pi.code,
                   pi.cash_component + COALESCE(h.total_mv, 0) AS aum
            FROM pcf_info pi
            INNER JOIN (
                SELECT code, MAX(date) AS max_date
                FROM pcf_info
                GROUP BY code
            ) latest ON pi.code = latest.code AND pi.date = latest.max_date
            LEFT JOIN (
                SELECT code, date, SUM(shares * price) AS total_mv
                FROM pcf_holdings
                GROUP BY code, date
            ) h ON pi.code = h.code AND pi.date = h.date
        """).fetchall()
        return {r[0]: r[1] for r in rows if r[1] is not None}
    finally:
        conn.close()


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


# ---------------------------------------------------------------------------
# Screening
# ---------------------------------------------------------------------------


def _compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["range_pct"] = (df["high"] - df["low"]) / df["close"] * 100
    df["atr"] = df["range_pct"].rolling(ROLLING_WINDOW).mean()
    df["range_ratio"] = df["range_pct"] / df["atr"]
    df["vol_ratio"] = df["volume"] / df["volume"].rolling(ROLLING_WINDOW).mean()
    df["return_pct"] = df["close"].pct_change() * 100
    df["turnover"] = df["close"] * df["volume"]
    df["turnover_ratio"] = (
        df["turnover"] / df["turnover"].rolling(ROLLING_WINDOW).mean()
    )
    return df


def _safe_round(val: object, decimals: int = 2) -> float | None:
    if pd.isna(val):
        return None
    return round(float(val), decimals)


def _screen(
    ohlcv: dict[str, pd.DataFrame],
    names: dict[str, str],
    fees: dict[str, float],
    aum: dict[str, float],
    sort_by: str,
    top: int,
) -> pd.DataFrame:
    rows = []

    # DB-only stats: build rows from DB data, no OHLCV needed
    if sort_by in DB_STATS:
        for code in set(list(aum.keys()) + list(fees.keys())):
            rows.append(
                {
                    "code": code,
                    "name": names.get(code, ""),
                    "aum": aum.get(code),
                    "fee": fees.get(code),
                }
            )
    else:
        # OHLCV-based stats
        for code, df in ohlcv.items():
            if len(df) < ROLLING_WINDOW + 1:
                continue
            signals = _compute_signals(df)
            latest = signals.iloc[-1]
            if pd.isna(latest.get(sort_by)):
                continue
            rows.append(
                {
                    "code": code,
                    "name": names.get(code, ""),
                    "date": latest["date"],
                    "close": latest["close"],
                    "turnover": _safe_round(latest["turnover"], 0),
                    "turnover_ratio": _safe_round(latest["turnover_ratio"], 2),
                    "range_pct": _safe_round(latest["range_pct"], 2),
                    "atr": _safe_round(latest["atr"], 2),
                    "range_ratio": _safe_round(latest["range_ratio"], 2),
                    "vol_ratio": _safe_round(latest["vol_ratio"], 2),
                    "return_pct": _safe_round(latest["return_pct"], 2),
                    "volume": int(latest["volume"]),
                    "aum": aum.get(code),
                    "fee": fees.get(code),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    # Filter rows where sort column is missing
    if sort_by in result.columns:
        result = result.dropna(subset=[sort_by])

    # Sort
    ascending = sort_by in ASCENDING_STATS
    if sort_by == "return_pct":
        result["_sort"] = result[sort_by].abs()
        result = result.sort_values("_sort", ascending=False).drop(columns=["_sort"])
    else:
        result = result.sort_values(sort_by, ascending=ascending)

    return result.head(top).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def _truncate_name(name: str, max_width: int) -> str:
    """Truncate name to fit within max_width terminal columns."""
    if display_width(name) <= max_width:
        return name
    while display_width(name) > max_width - 1:
        name = name[:-1]
    return name + "…"


def _fmt(val: float | None, width: int, decimals: int = 2, suffix: str = "") -> str:
    if val is None:
        return f"{'-':>{width}}"
    inner_w = width - len(suffix)
    return f"{val:>{inner_w}.{decimals}f}{suffix}"


def _fmt_yen(val: float | None, width: int) -> str:
    if val is None:
        return f"{'-':>{width}}"
    if val >= 1e12:
        return f"{val / 1e12:>{width - 1}.1f}T"
    if val >= 1e8:
        return f"{val / 1e8:>{width - 1}.0f}億"
    if val >= 1e4:
        return f"{val / 1e4:>{width - 1}.0f}万"
    return f"{val:>{width},.0f}"


# Column definitions: (header, width, formatter)
# Grouped by category for selecting display columns
_COL_TURNOVER = {
    "turnover": ("Turnover", 10, lambda r: _fmt_yen(r.get("turnover"), 10)),
    "turnover_ratio": ("TnR", 5, lambda r: _fmt(r.get("turnover_ratio"), 4, 1, "x")),
}
_COL_VOLATILITY = {
    "range_pct": ("Range%", 7, lambda r: _fmt(r.get("range_pct"), 7)),
    "atr": ("ATR%", 6, lambda r: _fmt(r.get("atr"), 6)),
    "range_ratio": ("Ratio", 6, lambda r: _fmt(r.get("range_ratio"), 5, 1, "x")),
}
_COL_VOLUME = {
    "vol_ratio": ("VolR", 5, lambda r: _fmt(r.get("vol_ratio"), 5, 1)),
    "volume": (
        "Volume",
        12,
        lambda r: (
            f"{int(r.get('volume', 0)):>12,}"
            if r.get("volume") is not None
            else f"{'-':>12}"
        ),
    ),
}
_COL_RETURN = {
    "return_pct": ("Ret%", 7, lambda r: _fmt(r.get("return_pct"), 7)),
}
_COL_FUND = {
    "aum": ("AUM", 10, lambda r: _fmt_yen(r.get("aum"), 10)),
    "fee": ("Fee%", 6, lambda r: _fmt(r.get("fee"), 6)),
}

# Which columns to show for each sort stat
_DISPLAY_PROFILES: dict[str, list[str]] = {
    "turnover": ["turnover", "turnover_ratio", "volume", "aum", "fee"],
    "turnover_ratio": ["turnover_ratio", "turnover", "volume", "aum", "fee"],
    "range_pct": [
        "range_pct",
        "atr",
        "range_ratio",
        "vol_ratio",
        "return_pct",
        "turnover",
    ],
    "atr": ["atr", "range_pct", "range_ratio", "vol_ratio", "return_pct"],
    "range_ratio": ["range_ratio", "range_pct", "atr", "vol_ratio", "turnover"],
    "vol_ratio": ["vol_ratio", "volume", "turnover", "turnover_ratio", "return_pct"],
    "return_pct": ["return_pct", "range_pct", "vol_ratio", "turnover"],
    "aum": ["aum", "fee", "turnover", "turnover_ratio"],
    "fee": ["fee", "aum", "turnover"],
}

# All column defs merged
_ALL_COLS = {
    **_COL_TURNOVER,
    **_COL_VOLATILITY,
    **_COL_VOLUME,
    **_COL_RETURN,
    **_COL_FUND,
}


def _display(df: pd.DataFrame, sort_by: str) -> None:
    if df.empty:
        print("\nNo results found.")
        return

    # Clamp name width
    name_w = min(
        max((display_width(str(n)) for n in df["name"]), default=4),
        NAME_MAX_WIDTH,
    )
    name_w = max(name_w, 4)

    # Pick columns to display
    col_keys = _DISPLAY_PROFILES.get(sort_by, list(_ALL_COLS.keys())[:6])
    cols = [(k, _ALL_COLS[k]) for k in col_keys if k in _ALL_COLS]

    # Header
    sort_label = sort_by.upper()
    title = "ETF Screener"
    print()
    print(f"  {title} — top {len(df)} by {sort_label}")
    print()

    # Build header line
    hdr = f"  {'#':>2}  {'Code':<5}  {pad('Name', name_w)}"
    sep = f"  {'─' * 2}  {'─' * 5}  {'─' * name_w}"
    if "close" in df.columns:
        hdr += f"  {'Close':>8}"
        sep += f"  {'─' * 8}"
    for _, (label, width, _) in cols:
        hdr += f"  {label:>{width}}"
        sep += f"  {'─' * width}"
    print(hdr)
    print(sep)

    for i, (_, r) in enumerate(df.iterrows(), 1):
        name = _truncate_name(r["name"], name_w)
        line = f"  {i:>2}  {r['code']:<5}  {pad(name, name_w)}"
        if "close" in df.columns:
            line += f"  {r['close']:>8,.0f}"
        for _, (_, _, formatter) in cols:
            line += f"  {formatter(r)}"
        print(line)

    # Footer
    print()
    print(f"  Sorted by: {sort_label}", end="")
    if sort_by == "return_pct":
        print(" (abs value, descending)")
    elif sort_by in ASCENDING_STATS:
        print(" (ascending)")
    else:
        print(" (descending)")
    if "date" in df.columns:
        data_date = str(df.iloc[-1]["date"])[:10]
        print(f"  Rolling window: {ROLLING_WINDOW} days | Data: {data_date}")
    print()


def _print_help() -> None:
    print("""\
Usage: etf screen [--by STAT] [--days N] [--top N] [--refresh] [--db PATH]

Screen all ETFs by trading activity, volatility, fund size, or fees.

Options:
  --by STAT    Stat to sort by (default: range_pct)
  --days N     OHLCV lookback period in days (default: 30)
  --top N      Number of results (default: 20)
  --refresh    Force re-fetch (ignore today's cache)
  --db PATH    Path to pcf.db

Available stats:
  Stat            Meaning
  ──────────────────────────────────────────────────────
  turnover        Daily turnover in yen (close * volume)
  turnover_ratio  Today's turnover vs 20-day avg
  range_pct       (high-low)/close * 100
  atr             20-day average of range_pct
  range_ratio     range_pct / atr (>2 = unusual)
  vol_ratio       volume / 20-day avg (>2 = surge)
  return_pct      Daily return %
  aum             Total net asset value (from DB)
  fee             Annual expense ratio % (from DB)

Stats 'aum' and 'fee' use local DB only (no OHLCV fetch needed).
OHLCV data is cached for 1 day at ~/.cache/pyjpx-etf/ohlcv/.

Requires: pyjquants (+ JQUANTS_API_KEY), pykabutan, local pcf.db (etf sync)""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main_screen(argv: list[str]) -> None:
    if "--help" in argv or "-h" in argv:
        _print_help()
        return

    sort_by = DEFAULT_STAT
    days = DEFAULT_DAYS
    top = DEFAULT_TOP
    refresh = False
    db_path = Path.home() / ".cache" / "pyjpx-etf" / "pcf.db"

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

    print("Loading ETF data from DB...")
    codes = _get_etf_codes(db_path)
    names = _get_etf_names(db_path)
    fees = _get_etf_fees(db_path)
    aum_data = _get_etf_aum(db_path)
    print(f"  Found {len(codes)} ETFs")

    # Skip OHLCV fetch for DB-only stats
    needs_ohlcv = sort_by in OHLCV_STATS
    ohlcv: dict[str, pd.DataFrame] = {}

    if needs_ohlcv:
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
    results = _screen(ohlcv, names, fees, aum_data, sort_by=sort_by, top=top)
    _display(results, sort_by)
