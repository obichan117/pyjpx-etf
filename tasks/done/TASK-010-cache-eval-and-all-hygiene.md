# TASK-010: TieredCache evaluation + __all__ hygiene

**Status**: todo
**Priority**: low
**Delegation**: main (cache decision) + quick-fix (__all__ sweep)
**PR**: 2 (refactor/screen-subpackage)
**Blocked by**: TASK-008

## Description
Two hygiene items from the audit:

### A. OHLCV cache vs TieredCache [main]
`screen/ohlcv.py` rolls its own daily-file JSON cache while `_internal/_cache.py`
(TieredCache) exists. Evaluate whether TieredCache fits (per-period key, 1-day TTL,
DataFrame serialization). If it doesn't fit cleanly, KEEP the bespoke cache and
document why in the module docstring — do not force it (YAGNI).

### B. __all__ in public modules [quick-fix]
Public modules leak internals into their namespaces (etf.py exposes fetch_pcf,
parse_pcf, get_fees...; search.py exposes search_by_holding; ranking.py exposes
PERIOD_COLUMNS). Add `__all__` to etf.py, ranking.py, search.py, history.py,
sync.py, models.py, config.py, exceptions.py listing only the public names
already exported via `__init__.py`.

## Acceptance Criteria
- [ ] Cache decision recorded (either refactor done or docstring rationale)
- [ ] `__all__` added; `uv run pytest tests/unit/ -v` passes
- [ ] Public API unchanged: all 13 `__init__.py` exports still importable
