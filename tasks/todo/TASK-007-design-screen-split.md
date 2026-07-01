# TASK-007: Design the screen/ subpackage split

**Status**: todo
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
- [ ] Written mapping (can live in this file's Notes) covering every symbol in cli_screen.py
- [ ] TASK-008 spec updated if mapping differs from the target above
