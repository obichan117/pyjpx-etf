# TASK-010: TieredCache evaluation + __all__ hygiene

**Status**: todo
**Priority**: low
**Delegation**: main (cache decision) + quick-fix (__all__ sweep)
**PR**: 2 (refactor/screen-subpackage)
**Blocked by**: TASK-008

## Description
Two hygiene items from the audit:

### A. OHLCV cache vs TieredCache [main] — DECIDED 2026-07-02: keep bespoke cache
Evaluated. TieredCache does NOT fit, for three reasons:
1. Calendar-day semantics ("today's candles", date-keyed file) vs TieredCache's
   elapsed-seconds TTL — a 23:00 fetch would still be "fresh" next morning and
   serve stale candles.
2. Values are dict[str, DataFrame] needing custom JSON encode/decode
   (Decimal/Timestamp via _json_default); TieredCache stores plain JSON.
3. TieredCache's zero-arg fetcher + memory tier are useless in a one-shot CLI
   with a parameterized fetch.
Generalizing TieredCache for one caller violates YAGNI.
ACTION (fold into ohlcv.py during this task): add a short docstring note to
screen/ohlcv.py explaining why it does not use _internal/_cache.TieredCache
(the three reasons above, compressed).

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
