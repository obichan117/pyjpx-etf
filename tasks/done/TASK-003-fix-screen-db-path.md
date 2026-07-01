# TASK-003: cli_screen must respect config.db_path

**Status**: todo
**Priority**: high
**Delegation**: quick-fix
**PR**: 1 (fix/daily-pcf-keepalive)

## Description
`src/pyjpx_etf/_internal/cli_screen.py:606` hardcodes
`Path.home() / ".cache" / "pyjpx-etf" / "pcf.db"` as the default DB path.
Every other command resolves the default via `db.db_path()`, which respects
the `config.db_path` override. Behavioral inconsistency.

## Exact Change
In `main_screen()` replace the hardcoded default with:
```python
from .db import db_path as _default_db_path
db_path = _default_db_path()
```
(keep the `--db PATH` CLI override behavior unchanged).

## Acceptance Criteria
- [ ] Default path comes from `db.db_path()` (verify `db_core.py` exposes it; it does)
- [ ] `--db /some/path` still overrides
- [ ] `uv run pytest tests/unit/ -v` passes
