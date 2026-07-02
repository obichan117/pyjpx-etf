# TASK-009: Re-point and extend screen tests

**Status**: todo
**Priority**: medium
**Delegation**: implementer
**PR**: 2 (refactor/screen-subpackage)
**Blocked by**: TASK-008

## Description
Update tests for the new subpackage and close the coverage gaps found in the
2026-07-02 audit.

## Exact Changes
1. `tests/unit/test_cli_screen.py`: import from `pyjpx_etf._internal.screen.signals`
   / `.display` instead of `cli_screen`. Remove the `pytest.importorskip` guards for
   pure modules (signals/display need only pandas — they must be importable without
   extras by construction).
2. New test: invoking the screen command with an OHLCV stat while extras are missing
   prints the `pip install 'pyjpx-etf[screen]'` hint and exits non-zero (mock
   `importlib.util.find_spec` or patch the guard).
3. New test: `--by fee` path works without extras (mock sqlite DB via existing
   test fixtures in tests/conftest.py / test_db.py patterns).
4. `tests/unit/test_cli.py` `test_help_includes_new_commands` (line ~379): assert
   "screen" appears in help output.

## Acceptance Criteria
- [ ] `uv run pytest tests/unit/ -v` passes
- [ ] `uv run ruff check .` passes
