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
```

## Architecture

```
src/pyjpx_etf/
├── __init__.py        # Public API: ETF class, config, exceptions, models
├── etf.py             # ETF class (main entry, lazy-loaded)
├── models.py          # ETFInfo, Holding frozen dataclasses
├── config.py          # Provider URLs, timeout, delay (mutable singleton)
├── exceptions.py      # PyJPXETFError → ETFNotFoundError, FetchError, ParseError
└── _internal/
    ├── fetcher.py     # I/O only: HTTP GET → raw CSV text (provider fallback)
    └── parser.py      # Pure parse: CSV text → models (no I/O)
```

### Key Design Patterns

- **Fetch/Parse split**: `_internal/fetcher.py` does HTTP only, `_internal/parser.py` does CSV parsing only
- **Lazy loading**: ETF data fetched on first `.info` or `.holdings` access
- **Provider fallback**: Try ICE first, then Solactive. CSV content validated (rejects HTML 200s)
- **Error precedence**: ETFNotFoundError only if *all* providers return 404; any server/network error → FetchError

## Data Sources

| Provider | URL Pattern | Covers |
|---|---|---|
| ICE Data Services | `https://inav.ice.com/pcf-download/{code}.csv` | Majority of TSE ETFs |
| Solactive AG | `https://www.solactive.com/downloads/etfservices/tse-pcf/single/{code}.csv` | Global X Japan ETFs |

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

## API

```python
import pyjpx_etf as etf

e = etf.ETF("1306")
e.info                     # ETFInfo dataclass
e.info.name                # "TOPIX ETF"
e.info.to_dict()           # dict of all fields
e.holdings                 # list[Holding]
e.to_dataframe()           # pd.DataFrame with weights

etf.config.timeout = 60
etf.config.request_delay = 0.5
```

## Dependencies

- `requests>=2.32` — HTTP
- `pandas>=2.0` — DataFrame output
- No Pydantic, no async, no cache
