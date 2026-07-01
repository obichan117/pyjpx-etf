# TASK-008: Execute the screen/ subpackage split

**Status**: todo
**Priority**: medium
**Delegation**: implementer
**PR**: 2 (refactor/screen-subpackage)
**Blocked by**: TASK-007

## Description
Mechanically execute the split designed in TASK-007: create
`src/pyjpx_etf/_internal/screen/{__init__,ohlcv,signals,display}.py`, move code
per the mapping, delete `cli_screen.py`, update `cli.py` import.

## Acceptance Criteria
- [ ] `cli_screen.py` deleted; no references remain (`grep -r cli_screen src/ tests/`)
- [ ] `etf screen --help` works; `etf screen --by fee` works WITHOUT pyjquants/pykabutan installed
- [ ] `etf screen` (OHLCV stat) without extras prints the install hint and exits cleanly
- [ ] `uv run pytest tests/unit/ -v` passes
- [ ] `uv run ruff check . && uv run ruff format --check .` passes
- [ ] Behavior unchanged otherwise (same output for same inputs)
