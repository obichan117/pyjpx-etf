# ETF Screener

## Overview

`etf screen` scans all ~400 ETFs in your local `pcf.db` and ranks them by trading activity, volatility, fund size, or fees. It's useful for quickly spotting ETFs worth a closer look — e.g. ones with unusually wide daily ranges or a volume surge — instead of checking each ETF one by one.

This is an optional feature and is not installed by default.

## Install

```bash
pip install 'pyjpx-etf[screen]'
```

This pulls in `pyjquants` (J-Quants API client) and `pykabutan` (Kabutan fallback scraper), which provide the OHLCV (open/high/low/close/volume) data used for volatility and volume stats.

## Requirements

- **J-Quants API key** — set `JQUANTS_API_KEY` in your environment or in a `~/.env` file.
- **Local database** — run `etf sync` first so `screen` has ETFs to scan.

`aum` and `fee` stats only need the local DB (no OHLCV fetch, no API key required).

## Usage

```
etf screen [--by STAT] [--days N] [--top N] [--en] [--refresh] [--db PATH]
```

| Flag | Description |
|------|-------------|
| `--by STAT` | Stat to sort by (default: `range_pct`) |
| `--days N` | OHLCV lookback period in days (default: `30`) |
| `--top N` | Number of results (default: `20`) |
| `--en` | English names |
| `--refresh` | Force re-fetch, ignoring today's cache |
| `--db PATH` | Path to `pcf.db` (default: `~/.cache/pyjpx-etf/pcf.db`) |

```
$ etf screen                       # top 20 by range_pct
$ etf screen --by vol_ratio        # top 20 by volume surge
$ etf screen --by aum --top 10     # top 10 by fund size, no OHLCV fetch
$ etf screen --by range_ratio --en # unusual volatility, English names
```

## Available Stats

| Stat | Meaning |
|------|---------|
| `turnover` | Daily turnover in yen (`close * volume`) |
| `turnover_ratio` | Today's turnover vs 20-day avg |
| `range_pct` | `(high - low) / close * 100` |
| `atr` | 20-day average of `range_pct` |
| `range_ratio` | `range_pct / atr` (>2 = unusual) |
| `vol_ratio` | `volume / 20-day avg volume` (>2 = surge) |
| `return_pct` | Daily return % |
| `aum` | Total net asset value (DB only) |
| `fee` | Annual expense ratio % (DB only) |

`aum` and `fee` come straight from the local database — no OHLCV fetch is needed for those two stats, so they run instantly even without a J-Quants key.

All other stats require OHLCV data and a 20-day rolling window, so `--days` should generally stay at 30 or higher to leave room for the rolling average.

## Primary Use Case: Spotting Unusual Activity

The most common use is finding ETFs behaving abnormally today relative to their own recent history:

```
$ etf screen --by range_ratio   # unusually wide/narrow daily range vs 20-day ATR
$ etf screen --by vol_ratio     # volume surge vs 20-day average volume
```

A `range_ratio` or `vol_ratio` above 2 flags an ETF trading well outside its normal recent behavior.

## OHLCV Caching

OHLCV data is fetched from J-Quants (with Kabutan as a fallback for gaps) and cached locally at `~/.cache/pyjpx-etf/ohlcv/`, keyed by lookback period and date. The cache has a 1-day TTL:

- The **first run of the day** fetches OHLCV for all ~400 ETFs and is slow.
- **Subsequent runs the same day** read from cache and return instantly.

Use `--refresh` to force a re-fetch and ignore today's cache.
