# pyjpx-etf

A clean, beginner-friendly Python library for fetching JPX ETF portfolio composition (PCF) data.

## Installation

```bash
pip install pyjpx-etf
```

## Quick Start

```python
import pyjpx_etf as etf

e = etf.ETF("1306")
print(e.info.name)       # "TOPIX連動型上場投資信託"
print(e.nav)             # total fund NAV in yen
print(e.fee)             # trust fee (%) e.g. 0.06
print(e.holdings[:3])
# [Holding(code='7203', name='トヨタ自動車', ...),
#  Holding(code='8306', name='三菱UFJフィナンシャル・グループ', ...),
#  Holding(code='6758', name='ソニーグループ', ...)]
```

## CLI

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

### Aliases

Use shorthand aliases instead of codes:

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
$ etf sox --en         # English names
$ etf topix -a         # all holdings (not just top 10)
$ etf 1306 -a --en     # combine options
```

## Language Setting

Names default to Japanese. Switch to English via config or CLI flag:

```python
import pyjpx_etf as etf

# English names
etf.config.lang = "en"
e = etf.ETF("1306")
print(e.info.name)  # "TOPIX ETF"
```

## Configuration

```python
import pyjpx_etf as etf

etf.config.timeout = 60
etf.config.request_delay = 0.5
etf.config.lang = "en"  # "ja" (default) or "en"
```

## Documentation

[Full documentation](https://obichan117.github.io/pyjpx-etf)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/obichan117/pyjpx-etf/blob/main/examples/quickstart.ipynb)
