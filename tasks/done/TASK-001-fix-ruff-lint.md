# TASK-001: Fix ruff import-sort error in test_cli_screen.py

**Status**: todo
**Priority**: high
**Delegation**: quick-fix
**PR**: 1 (fix/daily-pcf-keepalive)

## Description
CI lint fails on `tests/unit/test_cli_screen.py` — unsorted import block (I001).
This is one of the two causes of the failed v0.6.0 publish.

## Acceptance Criteria
- [ ] `uv run ruff check .` passes with 0 errors
- [ ] `uv run ruff format --check .` passes

## Notes
`uv run ruff check --fix .` resolves it. Verify no other files change.
