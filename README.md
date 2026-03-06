# pyjpx-etf

[![PyPI](https://img.shields.io/pypi/v/pyjpx-etf)](https://pypi.org/project/pyjpx-etf/)
[![Python](https://img.shields.io/pypi/pyversions/pyjpx-etf)](https://pypi.org/project/pyjpx-etf/)
[![License](https://img.shields.io/pypi/l/pyjpx-etf)](https://github.com/obichan117/pyjpx-etf/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://obichan117.github.io/pyjpx-etf)

A clean, beginner-friendly Python library for fetching JPX ETF portfolio composition (PCF) data, ranking ETFs by returns, and analyzing holdings.

## Installation

```bash
pip install pyjpx-etf
```

## Quick Start

```python
import pyjpx_etf as etf

# ETF lookup (auto-syncs local DB on first use)
e = etf.ETF("1306")
print(e.info.name)       # "TOPIX連動型上場投資信託"
print(e.nav)             # total fund NAV in yen
print(e.fee)             # trust fee (%) e.g. 0.06
print(e.holdings[:3])
# [Holding(code='7203', name='トヨタ自動車', ...),
#  Holding(code='8306', name='三菱UFJフィナンシャル・グループ', ...),
#  Holding(code='6758', name='ソニーグループ', ...)]
```

## Python API

### ETF Ranking

```python
etf.ranking()              # top 10 by 1-month return
etf.ranking("1y", n=20)    # top 20 by 1-year return
etf.ranking("ytd", n=-5)   # worst 5 by ytd return
```

### Reverse Stock Search

```python
etf.search("6857")         # which ETFs hold Advantest?
etf.search("7203", n=5)    # top 5 ETFs holding Toyota
```

### Weight History

```python
etf.history("1306", "6857")  # Advantest weight in TOPIX over time
etf.history("1306")          # top holdings with weight change
```

### Language & Config

```python
etf.config.lang = "en"          # "ja" (default) or "en"
etf.config.timeout = 60         # HTTP timeout in seconds
etf.config.request_delay = 0.5  # delay between retries
```

## CLI

### ETF Lookup

```
$ etf 1306

1306 — TOPIX連動型上場投資信託 (2026-02-27)
Nav: 5170億  信託報酬: 0.06%

 Code   Name                                Weight
─────  ──────────────────────────────────  ──────
 7203   トヨタ自動車                          3.7%
 8306   三菱ＵＦＪフィナンシャル・グループ    3.3%
 6501   日立製作所                            2.4%
 ...
```

```
$ etf topix --en -a     # English, all holdings
$ etf 1306 --live       # skip local DB, fetch live
```

### ETF Ranking

```
$ etf rank                # top 10 by 1-month return
$ etf rank 20 1y          # top 20 by 1-year return
$ etf rank -5 ytd --en    # worst 5 by ytd, English names
```

Available periods: `1m` (default), `3m`, `6m`, `1y`, `3y`, `5y`, `10y`, `ytd`

### Stock Search

```
$ etf find 6857            # ETFs holding Advantest
$ etf find 7203 5          # top 5 ETFs holding Toyota
$ etf find 6857 --en       # English names
```

### Weight History

```
$ etf history 1306 6857    # Advantest weight in TOPIX over time
$ etf history 1306         # top holdings with weight change
$ etf history 1306 --en    # English names
```

### Database Sync

The local database auto-syncs on first use each day. To force a refresh:

```
$ etf sync                 # download/update
$ etf sync --force         # force re-download
```

### Aliases

| Alias | Code | ETF |
|-------|------|-----|
| `etf topix` | 1306 | TOPIX連動型上場投資信託 |
| `etf 225` | 1321 | 日経225連動型上場投資信託 |
| `etf core30` | 1311 | TOPIX Core30連動型上場投資信託 |
| `etf div50` | 1489 | 日経平均高配当株50指数連動型ETF |
| `etf div70` | 1577 | 野村日本株高配当70連動型ETF |
| `etf pbr` | 2080 | PBR1倍割れ解消推進ETF |
| `etf sox` | 2243 | Global X 半導体 ETF |
| `etf jpsox1` | 200A | 日経半導体株 ETF |
| `etf jpsox2` | 2644 | Global X 半導体関連-日本株式 ETF |

### Options

```
$ etf --help               # show all commands
$ etf --version            # show version
```

## Documentation

[Full documentation](https://obichan117.github.io/pyjpx-etf)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/obichan117/pyjpx-etf/blob/main/examples/quickstart.ipynb)
