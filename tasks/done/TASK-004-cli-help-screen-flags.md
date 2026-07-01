# TASK-004: Complete screen flags in top-level CLI help

**Status**: todo
**Priority**: medium
**Delegation**: quick-fix
**PR**: 1 (fix/daily-pcf-keepalive)

## Description
`src/pyjpx_etf/cli.py:20` lists `etf screen [--by STAT] [--top N] [--en]` but
the command also supports `--days N`, `--refresh`, `--db PATH`
(see `_internal/cli_screen.py:561`).

## Exact Change
Update the help line to:
```
etf screen [--by STAT] [--days N] [--top N] [--en] [--refresh] [--db PATH]  ETF screener (requires extras)
```
(match surrounding alignment/format of the help block).

## Acceptance Criteria
- [ ] `uv run python -m pyjpx_etf.cli --help` (or `etf --help`) shows all six flags
- [ ] `uv run pytest tests/unit/test_cli.py -v` passes
