# TASK-012: sync() freshness check must compare against the remote

**Status**: in-progress
**Priority**: high
**Delegation**: implementer
**PR**: fix/sync-remote-freshness → v0.6.1

## Description
`sync()` skipped downloading when the local file's mtime was < 24h old — a
proxy that lies when the release asset is rebuilt after the user's download
(2026-07-02: users kept the stale 2026-05-14 DB even after the pipeline
revival, and needed `--force`).

## Design (Option A, decided 2026-07-02)
- HEAD the release asset → `Last-Modified` → compare to local mtime;
  download only if remote is newer.
- After download, `os.utime` the local file to the remote timestamp so the
  comparison stays truthful.
- Offline / header missing → keep local copy (graceful degradation).
- Rejected: local data-date heuristic (re-downloads 330 MB daily during
  upstream outages); GitHub API query (rate limits, same info as HEAD).

## Acceptance Criteria
- [ ] Unit tests cover: remote-not-newer skip, remote-newer download,
      offline fallback, mtime stamping
- [ ] Docs/help text no longer claim the 24h heuristic
- [ ] Version bumped to 0.6.1 (publishes on merge)
- [ ] Full checklist green; PR merged; PyPI shows 0.6.1
