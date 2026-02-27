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
├── etf.py             # ETF class (main entry, lazy-loaded) + _resolve_japanese_names()
├── models.py          # ETFInfo, Holding frozen dataclasses
├── config.py          # Provider URLs, timeout, delay, lang (mutable singleton, lang validated)
├── exceptions.py      # PyJPXETFError → ETFNotFoundError, FetchError, ParseError
├── cli.py             # CLI entry point: `etf <code|alias> [--en] [-a]`, aliases (topix, 225, sox, fang, jpsox1, jpsox2)
└── _internal/
    ├── fetcher.py     # I/O only: HTTP GET → raw CSV text (provider fallback)
    ├── parser.py      # Pure parse: CSV text → models (no I/O)
    ├── master.py      # JPX master list: fetch XLS (_fetch_master_xls) + parse (_parse_master_xls), 2-tier cache
    └── fees.py        # JPX ETF fees (信託報酬): fetch HTML (_fetch_fee_html) + parse (_parse_fee_html), 2-tier cache
```

### Key Design Patterns

- **Fetch/Parse split**: `_internal/fetcher.py` does HTTP only, `_internal/parser.py` does CSV parsing only. `_internal/master.py` and `_internal/fees.py` also follow this split.
- **Lazy loading**: ETF data fetched on first `.info` or `.holdings` access
- **Provider fallback**: Try ICE first, then Solactive. CSV content validated (rejects HTML 200s)
- **Error precedence**: ETFNotFoundError only if *all* providers return 404; any server/network error → FetchError
- **Name resolution**: Extracted to `_resolve_japanese_names()` in `etf.py` — keeps `_load()` focused on fetch+parse
- **Config validation**: `config.lang` only accepts `"ja"` or `"en"`, raises `ValueError` otherwise

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
| 2243 | Global X US Tech Top 20 ETF | Solactive |
| 200A | 日経半導体株 ETF | ICE |
| 316A | iShares 日経半導体株 ETF | ICE |

## API

```python
import pyjpx_etf as etf

e = etf.ETF("1306")
e.info                     # ETFInfo dataclass
e.info.name                # "TOPIX ETF"
e.info.to_dict()           # dict of all fields
e.nav                      # total fund NAV in yen (int)
e.fee                      # 0.06 (trust fee %, or None)
e.holdings                 # list[Holding]
e.to_dataframe()           # pd.DataFrame with weights

etf.config.timeout = 60
etf.config.request_delay = 0.5
```

## Dependencies

- `requests>=2.32` — HTTP
- `pandas>=2.0` — DataFrame output
- `xlrd>=2.0` — required by `pd.read_excel` for JPX master `.xls` files
- `lxml>=5.0` — required by `pd.read_html` for JPX ETF fee page
- No Pydantic, no async
