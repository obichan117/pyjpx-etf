# TASK-013: Pipeline silently no-ops when Rakuten blocks the runner

**Status**: in-progress
**Priority**: high
**Delegation**: implementer
**PR**: fix/pipeline-silent-noop

## Description
2026-07-02: the revived daily pipeline ran green but appended ZERO rows —
Rakuten returned no data to the GitHub Actions runner (fine from residential
IPs), `_fetch_all_etf_codes()` came back empty, and graceful degradation let
the run log "0 success, 0 failed", upload an unchanged DB, and exit 0.
Users synced a "fresh" DB still frozen at 2026-05-14.

## Fix (three parts)
1. Browser-like User-Agent (`_UA_HEADERS` in config.py) on all outbound
   data-provider requests (fetcher/rakuten/master/fees) — default
   `python-requests` UA is a likely WAF filter for datacenter IPs.
2. Universe fallback: Rakuten empty → `SELECT DISTINCT code FROM pcf_info`
   (the just-downloaded DB already knows ~435 codes).
3. Hard failure: no codes at all, or 0 successful PCF fetches → RuntimeError
   → non-zero exit → red workflow, upload step skipped. Graceful degradation
   is right for the library, wrong for the cron.

## Acceptance Criteria
- [ ] Unit tests: fallback path, both-empty raise, zero-success raise
- [ ] Live Rakuten fetch still works with the UA header (residential)
- [ ] PR merged; manual workflow_dispatch appends real rows (MAX(date) in
      pcf_info advances) OR goes red visibly — never a green no-op
