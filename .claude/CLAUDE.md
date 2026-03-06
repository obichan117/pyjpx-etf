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
├── __init__.py        # Public API: ETF, config, ranking, search, history, sync
├── etf.py             # ETF class (DB-first, live fallback) + _resolve_japanese_names()
├── ranking.py         # ranking() — ETF returns ranking via Rakuten data (always live)
├── search.py          # search() — reverse stock lookup from local DB
├── history.py         # history() — weight tracking over time from local DB
├── sync.py            # sync() — download pcf.db from GitHub Releases
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
    └── cli_db.py      # CLI handlers: etf sync, search, history
```

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
- Downloaded by users via `etf sync`

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
etf.sync()                 # download pcf.db from GitHub Releases

# Search: find ETFs holding a stock
etf.search("6857")         # ETFs holding Advantest

# History: weight tracking over time
etf.history("1306", "6857")  # Advantest weight in TOPIX over time
etf.history("1306")          # top holdings with weight change

etf.config.timeout = 60
etf.config.request_delay = 0.5
etf.config.db_path = Path("/custom/pcf.db")
```

## CLI

```
etf <code|alias> [--en] [-a] [--live]  Show ETF portfolio
etf rank [n] [period] [--en]           Rank ETFs by return
etf sync [--force]                     Download/update PCF database
etf find <stock_code> [n] [--en]       Find ETFs holding a stock
etf history <etf_code> [stock] [--en]  Weight history
```

## Dependencies

- `requests>=2.32` — HTTP
- `pandas>=2.0` — DataFrame output
- `xlrd>=2.0` — required by `pd.read_excel` for JPX master `.xls` files
- `lxml>=5.0` — required by `pd.read_html` for JPX ETF fee page
- `sqlite3` — stdlib, no extra dependency
- No Pydantic, no async

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
