# TASK-007: Design the screen/ subpackage split

**Status**: done
**Priority**: medium
**Delegation**: main
**PR**: 2 (refactor/screen-subpackage)

## Description
Produce the exact function→module mapping for splitting
`_internal/cli_screen.py` (673 lines) into `_internal/screen/`, per the
2026-07-02 audit decision (Option 1). Output feeds TASK-008 as a complete spec.

## Target
```
_internal/screen/
├── __init__.py    # main_screen() + argparse loop + LAZY extras-guard
├── ohlcv.py       # _fetch_jquants, _fetch_kabutan, _fetch_all, cache fns, ~/.env loading
├── signals.py     # _compute_signals, _screen, _safe_round, STATS/OHLCV_STATS/DB_STATS constants
└── display.py     # _display, _truncate_name, _fmt, _fmt_yen, column defs/profiles, _print_help
```

## Design decisions to settle
- [ ] Extras-guard: move ImportError check from module import into `main_screen()`,
      fired only when `sort_by in OHLCV_STATS` → `--by aum|fee` works without extras;
      unit tests import signals/display with no extras.
- [ ] Where DB query helpers (_get_etf_codes/names/fees/aum) live (likely signals.py
      or a small db-facing section in __init__.py — decide by dependency direction).
- [ ] Whether _fmt/_fmt_yen graduate to cli_fmt.py or stay in display.py
      (audit lean: stay in display.py; cli_fmt's format_yen serves a different shape).
- [ ] `cli.py` dispatch: `from ._internal.screen import main_screen` — ImportError
      handling in cli.py:57-66 becomes unnecessary for missing extras (guard is lazy
      now) but keep a graceful message path.

## Acceptance Criteria
- [x] Written mapping (see Notes) covering every symbol in cli_screen.py
- [x] TASK-008 spec updated (adds screen/db.py — 5 modules, not 4)

## Notes — FINAL DESIGN (2026-07-02)

Five modules (adds `db.py` beyond the original four — the DB query helpers are
data access, not orchestration, and don't belong in `__init__.py`):

### screen/signals.py — pure computation (pandas only, importable without extras)
ROLLING_WINDOW, OHLCV_STATS, DB_STATS, STATS, DEFAULT_STAT, ASCENDING_STATS,
_compute_signals, _safe_round, _screen

### screen/display.py — rendering (pandas + cli_fmt + config, no extras)
NAME_MAX_WIDTH, _truncate_name, _fmt, _fmt_yen, _COL_TURNOVER, _COL_VOLATILITY,
_COL_VOLUME, _COL_RETURN, _COL_FUND, _DISPLAY_PROFILES, _ALL_COLS, _display,
_print_help. Imports ROLLING_WINDOW/ASCENDING_STATS from .signals (footer text).

### screen/db.py — pcf.db inputs (sqlite3 + config, no extras)
_get_etf_codes, _get_etf_names, _get_etf_fees, _get_etf_aum

### screen/ohlcv.py — I/O: fetch + cache (extras used here, imported inside fns)
CACHE_DIR, MAX_WORKERS_JQUANTS, MAX_WORKERS_KABUTAN, KABUTAN_DELAY,
_cache_path, _json_default, _save_cache, _load_cache,
_fetch_jquants, _fetch_kabutan, _fetch_all,
PLUS the ~/.env loading block (dotenv try/except) — moved from module top of
cli_screen.py to module top of ohlcv.py (only needed for J-Quants auth; ohlcv
is only imported lazily from main_screen).

### screen/__init__.py — entry point + orchestration (imports clean without extras)
DEFAULT_TOP, DEFAULT_DAYS, main_screen().
- LAZY extras-guard: DELETE the module-level ImportError check
  (cli_screen.py:23-30). Inside main_screen(), after arg parsing, when
  `sort_by in OHLCV_STATS`: check `importlib.util.find_spec` for pyjquants &
  pykabutan; if any missing, print
  "Error: stat '<X>' needs OHLCV data. Install: pip install 'pyjpx-etf[screen]'"
  to stderr and sys.exit(1). Only then `from .ohlcv import ...`.
- `--by aum|fee` therefore works with NO extras installed.
- Default db_path via `from ..db_core import db_path` (as today).

### cli.py dispatch
`from ._internal.screen import main_screen` — plain import; remove the
try/except ImportError fallback at cli.py:57-66 (module imports clean now);
keep dispatch shape identical otherwise.

### Import graph (no cycles)
signals ← display, __init__ · db ← __init__ · ohlcv ← __init__ (lazy, guarded)
· display ← __init__ · config/cli_fmt/db_core = leaf deps.

### Behavior deltas (intended, all improvements)
1. `etf screen --by fee|aum` works without extras installed.
2. Missing-extras error names the stat and fires only for OHLCV stats.
3. ~/.env is parsed only when an OHLCV fetch actually happens.
No other output/behavior changes.
