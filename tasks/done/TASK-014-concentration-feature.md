# TASK-014: ETF concentration feature (v0.7.0)

**Status**: in-progress
**Priority**: high
**Delegation**: implementer (code), implementer (docs)
**PR**: feat/concentration

## Description
User's arbitrage workflow: when a stock gaps at the open, long/short ETFs
concentrated in it. Two moments served:
- Watchlist: `etf screen --by top1|top3|top10` — which ETFs are concentrated
  bets, and on what stock (TopStock column).
- Morning tool: `etf find <stock> --gap +8` — ETFs holding the gapper, with
  Est.Impact = weight × gap and AUM for tradability.

## Design decisions (2026-07-05)
- **API-first**: public `etf.concentration(n=, by=)` and `etf.search(gap=)`
  return DataFrames; CLI wraps them. Rationale: the future PRIVATE strategy
  library (`jpx-open-arb`) joins these with estimated-open quotes from a
  to-be-built quote library. pyjpx-etf stays composition-only (no live
  prices, no trade logic).
- Weights remain FRACTIONS in the API (consistent with search/holdings);
  CLI multiplies by 100.
- Concentration counts only equity-like holdings (LENGTH(holding_code)=4)
  — excludes FX forwards (280% weights in leveraged funds) and bond rows.
- Single SQL source of truth in db_read (`_CONCENTRATION_SQL`); screen/db
  reuses the constant against its explicit --db path.
- Future layering (recorded for jpx-open-arb): fair open = Σ wᵢ×est_openᵢ
  over the FULL basket (from ETF(code).holdings) vs the ETF's own estimated
  open — better than single-stock weight×gap.

## Acceptance Criteria
- [ ] `etf.concentration(n=5)` → 282A near top, top1 ≈ 0.21–0.22, top_code 285A
- [ ] `etf find 285A --gap +8` → Impact ≈ +1.7% for 282A, AUM column
- [ ] `etf screen --by top1` renders TopStock column, DB-only (no extras)
- [ ] Unit tests for query, API validation, gap math, CLI output
- [ ] Docs + v0.7.0 bump; full checklist; PR merged; PyPI 0.7.0
