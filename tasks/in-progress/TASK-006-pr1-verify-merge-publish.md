# TASK-006: PR 1 — verify, merge, confirm v0.6.0 publish + cron revival

**Status**: todo
**Priority**: high
**Delegation**: main
**PR**: 1 (fix/daily-pcf-keepalive)

## Description
Gate task for PR 1. The branch already contains the keepalive commit (3a73cb5).
After TASK-001..005 land on it, run the full checklist, open the PR, merge,
and verify the two broken pipelines recover.

## Acceptance Criteria
- [ ] Post-Implementation Checklist: `uv run pytest tests/ --integration -v`,
      `uv run ruff check && uv run ruff format --check`,
      `uv run mkdocs build --strict`
- [ ] Commit `uv.lock` (0.6.0 version sync, currently uncommitted)
- [ ] PR opened against main; CI green (this proves the CI fix — CI was red on main)
- [ ] After merge: publish workflow succeeds, PyPI shows 0.6.0, GitHub Release v0.6.0 created
- [ ] Daily PCF workflow enabled; next scheduled run (07:55 JST) succeeds and
      `db-latest` asset timestamp updates (was frozen at 2026-05-13)

## Notes
- Merging is itself a push that resets GitHub's 60-day inactivity timer; the
  keepalive step prevents recurrence.
- The May-14→July PCF history gap is permanent (no backfill source). Accepted.
