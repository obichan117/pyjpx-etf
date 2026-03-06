# Getting Started

## Installation

```bash
pip install pyjpx-etf
```

## Setup: Sync the Database

pyjpx-etf works best with a local database. Download it once:

```python
import pyjpx_etf as etf
etf.sync()
```

Or from the CLI:

```
$ etf sync
```

This downloads a pre-built SQLite database (~5 MB) from GitHub Releases to `~/.cache/pyjpx-etf/pcf.db`. The database is updated daily by a GitHub Actions cron job.

!!! tip "Without the database"
    You can skip `sync` — ETF lookups will fall back to live HTTP. But `search()` and `history()` require the local DB.

## Basic Usage

```python
import pyjpx_etf as etf

e = etf.ETF("1306")

# ETF metadata (Japanese names by default)
print(e.info.name)              # "TOPIX連動型上場投資信託"
print(e.info.cash_component)    # 496973797639.0
print(e.info.shares_outstanding)  # 8133974978
print(e.info.date)              # datetime.date(2026, 2, 27)

# Holdings
for h in e.holdings[:3]:
    print(f"{h.name}: {h.weight:.2%}")
# トヨタ自動車: 3.80%
# 三菱UFJフィナンシャル・グループ: 2.50%
# ソニーグループ: 2.30%

# Full DataFrame
df = e.to_dataframe()
```

### DB-First vs Live

```python
# Default: reads from local DB, falls back to live HTTP
e = etf.ETF("1306")

# Force live fetch (skip DB, always hit HTTP providers)
e = etf.ETF("1306", live=True)
```

### Language

Names default to Japanese (`config.lang = "ja"`). Switch to English:

```python
etf.config.lang = "en"
e = etf.ETF("1306")
print(e.info.name)  # "TOPIX ETF"
```

The CLI uses `--en` for English:

```
$ etf 1306 --en
```

### Configuration

```python
import pyjpx_etf as etf

etf.config.timeout = 60         # HTTP timeout in seconds
etf.config.request_delay = 0.5  # Delay between provider retries
etf.config.lang = "en"          # "ja" (default) or "en"
```

## ETF Ranking

Rank all TSE ETFs by return over various periods:

```python
import pyjpx_etf as etf

# Top 10 by 1-month return (default)
df = etf.ranking()

# Top 20 by 1-year return
df = etf.ranking("1y", n=20)

# Worst 5 by ytd return
df = etf.ranking("ytd", n=-5)

# All ETFs sorted by return
df = etf.ranking("1m", n=0)
```

Returns a DataFrame with columns: `code`, `name`, `return`, `fee`, `dividend_yield`.

Available periods: `1m`, `3m`, `6m`, `1y`, `3y`, `5y`, `10y`, `ytd`.

## Reverse Stock Search

Find which ETFs hold a given stock:

```python
df = etf.search("6857")         # ETFs holding Advantest
df = etf.search("7203", n=5)    # top 5 ETFs holding Toyota
```

## Weight History

Track holdings over time:

```python
df = etf.history("1306", "6857")  # Advantest weight in TOPIX over time
df = etf.history("1306")          # top holdings with weight change
```

## CLI

```
$ etf 1306                 # ETF portfolio composition
$ etf topix --en -a        # all holdings, English, using alias
$ etf rank                 # top 10 by 1-month return
$ etf rank 20 1y --en      # top 20 by 1-year return, English
$ etf sync                 # download/update database
$ etf find 6857            # ETFs holding Advantest
$ etf history 1306 6857    # weight tracking
$ etf --help               # all commands
```

## Data Sources

pyjpx-etf fetches data from multiple providers:

| Provider | Data |
|---|---|
| ICE Data Services | PCF (portfolio composition) for most TSE ETFs |
| Solactive AG | PCF for Global X Japan ETFs |
| S&P Global | PCF for additional ETFs |
| JPX | Trust fees (信託報酬), Japanese security names |
| Rakuten Securities | Period returns, dividend yields, supplementary fees |

PCF data is updated daily on business days, available 7:50–23:55 JST.
Ranking data (Rakuten) is available anytime.
