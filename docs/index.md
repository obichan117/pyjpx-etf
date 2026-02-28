# pyjpx-etf

A clean, beginner-friendly Python library for fetching JPX ETF portfolio composition (PCF) data and ranking ETFs by returns.

## Features

- **Simple API** — yfinance-style `ETF("1306")` interface
- **ETF ranking** — rank all TSE ETFs by returns (1m, 1y, ytd, etc.)
- **Japanese names by default** — powered by the JPX master list
- **No authentication** — uses free, public endpoints
- **Lightweight** — just `requests`, `pandas`, `xlrd`, and `lxml`
- **Auto provider detection** — tries ICE Data Services, then Solactive

## Quick Example

```python
import pyjpx_etf as etf

e = etf.ETF("1306")
print(e.info.name)  # "TOPIX連動型上場投資信託"
print(e.fee)        # 0.0505
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

### CLI

```
$ etf 1306
$ etf rank              # top 10 by 1-month return
$ etf rank -5 1y --en   # worst 5 by 1-year, English
$ etf --help            # show all commands
```

## Installation

```bash
pip install pyjpx-etf
```

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/obichan117/pyjpx-etf/blob/main/examples/quickstart.ipynb)
