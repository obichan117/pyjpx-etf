# pyjpx-etf

A clean, beginner-friendly Python library for fetching JPX ETF portfolio composition (PCF) data.

## Quick Start Commands

```bash
# Setup
uv sync

# Run unit tests
uv run pytest tests/unit/ -v

# Run integration tests (hits live endpoints, requires JST business hours)
uv run pytest tests/integration/ --integration -v

# Format & lint
uv run ruff format .
uv run ruff check .

# Serve docs
uv run mkdocs serve

# Build docs (strict)
uv run mkdocs build --strict

# Run PCF pipeline (builds/updates SQLite DB)
uv run python -m pyjpx_etf._internal.pipeline_cli --db /tmp/pcf.db
```

## Architecture

```
src/pyjpx_etf/
├── __init__.py        # Public API: ETF, config, ranking, search, history, concentration, sync
├── etf.py             # ETF class (DB-first, live fallback) + _resolve_japanese_names()
├── ranking.py         # ranking() — ETF returns ranking via Rakuten data (always live)
├── search.py          # search() — reverse stock lookup from local DB, gap= for NAV-impact estimate
├── history.py         # history() — weight tracking over time from local DB
├── concentration.py   # concentration() — rank ETFs by top-holding weight (top1/top3/top10), local DB
├── sync.py            # sync() — download latest-snapshot DB (full=True: full history)
├── models.py          # ETFInfo, Holding frozen dataclasses
├── config.py          # Provider URLs, timeout, delay, lang, db_path
├── exceptions.py      # PyJPXETFError → ETFNotFoundError, FetchError, ParseError, DatabaseError
├── cli.py             # CLI router: dispatches to _internal/cli_* handlers
└── _internal/
    ├── _cache.py      # Generic 2-tier cache (memory → disk JSON with TTL)
    ├── db.py          # Re-export facade for db_core + db_read + db_write
    ├── db_core.py     # Schema, db_path, db_exists, get_connection
    ├── db_read.py     # Read queries (used by public API)
    ├── db_write.py    # Write queries (used by pipeline only)
    ├── fetcher.py     # I/O only: HTTP GET → raw CSV text (provider fallback)
    ├── parser.py      # Pure parse: CSV text → models (no I/O)
    ├── master.py      # JPX master list: fetch XLS + parse, TieredCache (7-day TTL)
    ├── fees.py        # JPX ETF fees (信託報酬): fetch HTML + parse, TieredCache (7-day TTL)
    ├── rakuten.py     # Rakuten Securities CSV: fee + returns + yield, TieredCache (1-day TTL)
    ├── pipeline.py    # Daily cron orchestrator: fetch all ETFs → SQLite (internal only)
    ├── pipeline_cli.py # CLI for pipeline: python -m pyjpx_etf._internal.pipeline_cli
    ├── cli_fmt.py     # Shared terminal formatting (display_width, pad, format_yen)
    ├── cli_show.py    # CLI handler: etf <code>
    ├── cli_rank.py    # CLI handler: etf rank
    ├── cli_db.py      # CLI handlers: etf sync, search, history
    └── screen/        # CLI handler: etf screen — ETF screener ([screen] extras for OHLCV stats)
        ├── __init__.py # main_screen() entry + LAZY extras-guard (fires only for OHLCV stats)
        ├── ohlcv.py    # I/O: J-Quants + Kabutan threaded fetch + 1-day date-keyed disk cache
        ├── signals.py  # Pure: stat constants, _compute_signals, _screen — pandas only, no I/O
        ├── display.py  # Table rendering, column profiles, _fmt/_fmt_yen, help text
        └── db.py       # pcf.db inputs: codes, names, fees, AUM
```

### Screen subsystem (refactored 2026-07-02 from a 673-line cli_screen.py)

- **Purpose**: filtering ETFs with unusual volatility (tracking errors) for potential
  arbitrage (`--by range_ratio`, `--by vol_ratio`).
- **Lazy extras-guard**: `screen/` imports cleanly without pyjquants/pykabutan; the
  guard fires inside `main_screen()` only for OHLCV stats. `--by aum|fee` works with
  no extras. (The old module-level ImportError broke CI test collection.)
- **OHLCV cache is intentionally NOT TieredCache**: needs calendar-day freshness
  (date-keyed files) not elapsed-TTL, stores DataFrames needing custom JSON
  encode/decode, and runs one-shot (no memory tier).
- **Future signal**: iNAV premium/discount from PCF data (true mispricing detector for
  arbitrage) — would live in `screen/premium.py`. Not yet implemented.

### Key Design Patterns

- **DB-first, live-fallback**: `ETF("1306")` reads from local SQLite DB when available, falls back to live HTTP. `ETF("1306", live=True)` always fetches live.
- **Fetch/Parse split**: `_internal/fetcher.py` does HTTP only, `_internal/parser.py` does CSV parsing only. Other internal modules follow this split.
- **TieredCache**: `_internal/_cache.py` provides memory → disk (JSON with TTL) → fetch. Used by master.py, fees.py, rakuten.py.
- **DB split**: `db_core.py` (schema/connection), `db_read.py` (public API queries), `db_write.py` (pipeline-only writes). `db.py` re-exports all for backwards compatibility.
- **CLI split**: `cli.py` is a thin router. Subcommand handlers live in `_internal/cli_*.py`.
- **Lazy loading**: ETF data fetched on first `.info` or `.holdings` access
- **Provider fallback**: Try ICE first, then Solactive, then S&P Global. CSV content validated (rejects HTML 200s)
- **Fee fallback**: DB → JPX fee page → Rakuten CSV
- **Error precedence**: ETFNotFoundError only if *all* providers return 404; any server/network error → FetchError
- **Config validation**: `config.lang` only accepts `"ja"` or `"en"`, raises `ValueError` otherwise
- **Ranking stays live**: Rakuten CSV provides returns data not stored in DB. Rakuten works 24/7.
- **Append-only PCF history**: Each day's PCF is keyed on `(code, date)`. No updates, no deletes.

### SQLite Database

- Path: `~/.cache/pyjpx-etf/pcf.db` (override with `config.db_path`)
- Tables: `meta`, `etfs`, `pcf_info`, `pcf_holdings`, `securities`
- Built by GitHub Actions daily cron (07:55 JST, Mon-Fri)
- Two release assets: `pcf-latest.db.gz` (latest snapshot per ETF, a few MB — default
  `etf sync`) and `pcf-full.db.gz` (full append-only history, 100s of MB — `etf sync --full`,
  saved to `pcf-full.db` so daily syncs never overwrite it). Uncompressed `pcf.db` (full)
  kept for clients <= 0.7.0. `history()` prefers `pcf-full.db` when present.

## Data Sources

| Provider | URL Pattern | Covers |
|---|---|---|
| ICE Data Services | `https://inav.ice.com/pcf-download/{code}.csv` | Majority of TSE ETFs |
| Solactive AG | `https://www.solactive.com/downloads/etfservices/tse-pcf/single/{code}.csv` | Global X Japan ETFs |
| S&P Global | `https://api.ebs.ihsmarkit.com/inav/getfile?filename={code}.csv` | Additional ETFs |
| Rakuten Securities | `https://www.rakuten-sec.co.jp/web/market/search/etf_search/ETFD.csv` | Fees, returns, yields for all TSE ETFs |

- Available 7:50–23:55 JST on business days
- ICE returns HTML (not 404) outside hours and for unknown codes — fetcher handles this
- Solactive CSVs use `\r\n` line endings — parser normalizes this

### Verified ETF Codes

| Code | Name | Provider |
|---|---|---|
| 1306 | TOPIX ETF | ICE |
| 1321 | Nikkei 225 ETF | ICE |
| 1348 | MAXIS TOPIX ETF | ICE |
| 2564 | Global X MSCI SuperDividend Japan ETF | Solactive |
| 2627 | Global X E-Commerce Japan ETF | Solactive |
| 2644 | Global X Japan Semiconductor ETF | Solactive |
| 200A | 日経半導体株 ETF | ICE |

## API

```python
import pyjpx_etf as etf

# ETF lookup (DB-first, live fallback)
e = etf.ETF("1306")
e.info                     # ETFInfo dataclass
e.info.name                # "TOPIX ETF"
e.nav                      # total fund NAV in yen (int)
e.fee                      # 0.06 (trust fee %)
e.holdings                 # list[Holding]
e.to_dataframe()           # pd.DataFrame with weights

# Force live fetch (skip DB)
e = etf.ETF("1306", live=True)

# ETF ranking by period returns (always live from Rakuten)
etf.ranking()              # top 10 by 1m return
etf.ranking("1y", n=20)    # top 20 by 1y return

# Sync local database
etf.sync()                 # download latest-snapshot DB (a few MB)
etf.sync(full=True)        # download full-history DB for history()

# Search: find ETFs holding a stock
etf.search("6857")         # ETFs holding Advantest
etf.search("285A", gap=8.0)  # + impact column: weight (fraction) × gap (%)

# History: weight tracking over time
etf.history("1306", "6857")  # Advantest weight in TOPIX over time
etf.history("1306")          # top holdings with weight change

# Concentration: rank ETFs by top-holding weight (local DB only)
etf.concentration()          # top 20 by top1
etf.concentration(n=10, by="top3")

etf.config.timeout = 60
etf.config.request_delay = 0.5
etf.config.db_path = Path("/custom/pcf.db")
```

## CLI

```
etf <code|alias> [--en] [-a] [--live]  Show ETF portfolio
etf rank [n] [period] [--en]           Rank ETFs by return
etf sync [--force] [--full]            Download/update PCF database (--full: history)
etf find <stock_code> [n] [--en] [--gap PCT]  Find ETFs holding a stock (+ NAV-impact estimate)
etf history <etf_code> [stock] [--en]  Weight history
etf screen [--by STAT] [--days N] [--top N] [--en] [--refresh] [--db PATH]
                                       ETF screener (requires [screen] extras + JQUANTS_API_KEY
                                       only for OHLCV stats; top1/top3/top10/aum/fee are DB-only)
```

`etf screen` stats: `turnover`, `turnover_ratio`, `range_pct` (default), `atr`,
`range_ratio` (>2 = unusual volatility), `vol_ratio` (>2 = volume surge), `return_pct`
(all need OHLCV fetch); `aum`, `fee`, `top1`, `top3`, `top10` (local DB only, no extras).
OHLCV cached 1 day at `~/.cache/pyjpx-etf/ohlcv/`.

## Dependencies

- `requests>=2.32` — HTTP
- `pandas>=2.0` — DataFrame output
- `xlrd>=2.0` — required by `pd.read_excel` for JPX master `.xls` files
- `lxml>=5.0` — required by `pd.read_html` for JPX ETF fee page
- `sqlite3` — stdlib, no extra dependency
- No Pydantic, no async

### Optional extras (`pip install 'pyjpx-etf[screen]'`)

- `pyjquants>=0.3.0` — J-Quants OHLCV data (needs `JQUANTS_API_KEY` in env or `~/.env`)
- `pykabutan>=0.1.1` — Kabutan scraping fallback for J-Quants gaps
- CI must run `uv sync --all-extras` so `tests/unit/test_cli_screen.py` can import

## Git Branching & CI/CD

### Branching Strategy

```
main (protected — requires PR + CI pass)
  └── feature/xxx, fix/xxx, docs/xxx (short-lived branches)
```

### Workflow

```
1. git checkout -b feature/xxx
2. make changes, commit
3. git push → create PR → CI runs automatically
4. merge to main after CI passes
5. if version in pyproject.toml is new → auto-publishes to PyPI + creates GitHub Release
```

To publish a new version: bump version in `pyproject.toml` + `src/pyjpx_etf/__init__.py`, then merge to main.

### CI Pipeline (`.github/workflows/ci.yml`)

Triggers: push to `main`, PRs to `main`, called by publish workflow.

| Job | What |
|-----|------|
| `lint` | `ruff check` + `ruff format --check` |
| `test` | Unit tests on Python 3.10, 3.11, 3.12, 3.13 |
| `integration` | Integration tests (needs: test) — hits live endpoints |
| `docs` | `mkdocs build --strict` |

### Publish Pipeline (`.github/workflows/publish.yml`)

Triggers: push to `main`. Runs CI first, checks if version in `pyproject.toml` is new on PyPI. If new version detected → builds, publishes to PyPI (trusted publishing), and auto-creates a GitHub Release.

### Daily PCF Pipeline (`.github/workflows/daily-pcf.yml`)

Triggers: cron 07:55 JST Mon-Fri + manual `workflow_dispatch`. Downloads previous DB, runs pipeline to fetch ~400 ETFs, uploads updated `pcf.db` to `db-latest` release.

⚠ **GitHub auto-disables scheduled workflows after 60 days without repo activity**
(`disabled_inactivity`). This killed the cron 2026-05-13 → 2026-07-02, leaving a
permanent ~7-week gap in the append-only PCF history (no backfill source exists).
The fix is the "Keep workflow alive" step (`gh api -X PUT .../workflows/daily-pcf.yml/enable`
+ `actions: write` permission) — it must stay in the workflow. Do NOT use
`gautamkrishnar/keepalive-workflow`: that action's repo is ToS-blocked by GitHub
and fails with "Repository access blocked".

### Incident log (2026-07-02 audit)

- **v0.6.0 publish failed (2026-03-14)**: `test_cli_screen.py` imports `cli_screen`,
  which raises ImportError without the `[screen]` extras — CI runs plain `uv sync`,
  so collection failed on all Python versions; plus one ruff import-sort error.
  PyPI stayed at 0.5.0 while main was 0.6.0. Screen has therefore **never shipped**.
  Lesson: any test importing an extras-gated module needs CI extras install and/or
  `pytest.importorskip`.

### Running Tests Locally

```bash
# Unit tests only (fast, no network)
uv run pytest tests/unit/ -v

# Integration tests (hits live endpoints)
uv run pytest tests/integration/ --integration -v

# All tests
uv run pytest tests/ --integration -v

# Full pre-push check
uv run ruff check && uv run ruff format --check && uv run pytest tests/ --integration -v && uv run mkdocs build --strict
```
