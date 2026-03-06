# pyjpx-etf

A clean, beginner-friendly Python library for fetching JPX ETF portfolio composition (PCF) data, ranking ETFs by returns, and analyzing holdings.

## Features

- **Simple API** — yfinance-style `ETF("1306")` interface
- **Local database** — daily snapshots via GitHub Actions, offline access with `etf sync`
- **ETF ranking** — rank all TSE ETFs by returns (1m, 1y, ytd, etc.)
- **Reverse stock search** — find which ETFs hold a given stock
- **Weight history** — track holding weight changes over time
- **Japanese names by default** — powered by the JPX master list
- **No authentication** — uses free, public endpoints
- **Lightweight** — just `requests`, `pandas`, `xlrd`, and `lxml`

## Quick Example

```python
import pyjpx_etf as etf

# Sync database (first time only)
etf.sync()

# ETF lookup (reads from local DB)
e = etf.ETF("1306")
print(e.info.name)  # "TOPIX連動型上場投資信託"
print(e.fee)        # 0.06
print(e.top())
```

```
   code          name    weight
0  7203      トヨタ自動車     3.8
1  8306  三菱UFJフィナンシャル・グループ  2.5
2  6758    ソニーグループ     2.3
...
```

### ETF Ranking

```python
etf.ranking()              # top 10 by 1-month return
etf.ranking("1y", n=20)    # top 20 by 1-year return
etf.ranking("ytd", n=-5)   # worst 5 by ytd return
```

### Reverse Stock Search

```python
etf.search("6857")         # which ETFs hold Advantest?
```

### Weight History

```python
etf.history("1306", "6857")  # Advantest weight in TOPIX over time
etf.history("1306")          # top holdings with weight change
```

### CLI

```
$ etf sync                 # download PCF database
$ etf 1306                 # ETF portfolio composition
$ etf rank                 # top 10 by 1-month return
$ etf rank -5 1y --en      # worst 5 by 1-year, English
$ etf find 6857            # ETFs holding Advantest
$ etf history 1306 6857    # weight history
$ etf --help               # all commands
```

## Installation

```bash
pip install pyjpx-etf
```

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/obichan117/pyjpx-etf/blob/main/examples/quickstart.ipynb)
