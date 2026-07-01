# TASK-005: Document the screen feature (docs, README, mkdocs nav)

**Status**: todo
**Priority**: high
**Delegation**: implementer
**PR**: 1 (fix/daily-pcf-keepalive)

## Description
The `screen` feature (v0.6.0) shipped with zero documentation. It must be
documented before v0.6.0 publishes (user decision from 2026-07-02 audit).

## Exact Changes
1. **New page `docs/guide/screen.md`** (follow the style of docs/guide/cli.md /
   ranking.md): what it does (screens all ETFs in local pcf.db by trading
   activity/volatility/fund stats), install (`pip install 'pyjpx-etf[screen]'`),
   requirements (JQUANTS_API_KEY in env or ~/.env, `etf sync` first), all flags
   (--by --days --top --en --refresh --db), the 9 stats table (copy meanings
   from `_internal/cli_screen.py:573-584`), note that `aum`/`fee` are DB-only
   (no API key needed for fetch, but extras must be installed), 1-day OHLCV
   cache at ~/.cache/pyjpx-etf/ohlcv/, and the primary use case: spotting
   unusual volatility (`--by range_ratio`, `--by vol_ratio`).
2. **mkdocs.yml**: add `guide/screen.md` to the Guide nav after the CLI page.
3. **docs/guide/cli.md**: add an `etf screen` section consistent with the other
   commands.
4. **README.md**: add screen to the CLI overview + optional install note
   (`pip install 'pyjpx-etf[screen]'`).
5. **docs/getting-started.md**: brief mention of the optional screen extra.

## Acceptance Criteria
- [ ] `uv run mkdocs build --strict` passes
- [ ] screen appears in nav, guide/cli.md, README
- [ ] No claims contradicting actual behavior (verify flags/stats against code)
