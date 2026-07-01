# TASK-002: Make CI install screen extras + guard test collection

**Status**: todo
**Priority**: high
**Delegation**: implementer
**PR**: 1 (fix/daily-pcf-keepalive)

## Description
CI runs plain `uv sync`, so `pyjquants`/`pykabutan` are absent and
`tests/unit/test_cli_screen.py` fails at collection: `_internal/cli_screen.py`
raises ImportError at module import when the extras are missing
(cli_screen.py:23-30). This broke CI on all Python versions and blocked the
v0.6.0 PyPI publish.

## Exact Changes
1. `.github/workflows/ci.yml`: change all four `- run: uv sync` steps to
   `- run: uv sync --all-extras`.
2. `tests/unit/test_cli_screen.py`: add at top, before the
   `from pyjpx_etf._internal.cli_screen import ...` block:
   ```python
   import pytest

   pytest.importorskip("pyjquants")
   pytest.importorskip("pykabutan")
   ```
3. `src/pyjpx_etf/_internal/cli_screen.py:21`: change `import importlib` to
   `import importlib.util` (`importlib.util.find_spec` is used; the submodule
   is only available by import-order accident today).

## Acceptance Criteria
- [ ] `uv run pytest tests/unit/ -v` passes (243+ tests)
- [ ] With extras uninstalled (`uv run --no-project --with pytest,pandas,requests pytest tests/unit/test_cli_screen.py` or equivalent venv without extras), the file is SKIPPED, not errored
- [ ] `uv run ruff check .` passes
