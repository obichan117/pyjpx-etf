# pyjpx-etf

A clean, beginner-friendly Python library for fetching JPX ETF portfolio composition (PCF) data.

## Features

- **Simple API** — yfinance-style `ETF("1306")` interface
- **Japanese names by default** — powered by the JPX master list
- **No authentication** — uses free, public PCF CSV endpoints
- **Lightweight** — just `requests`, `pandas`, and `xlrd`
- **Auto provider detection** — tries ICE Data Services, then Solactive

## Quick Example

```python
import pyjpx_etf as etf

e = etf.ETF("1306")
print(e.info.name)  # "TOPIX連動型上場投資信託"
print(e.top())
```

```
   code          name    weight
0  7203      トヨタ自動車     3.8
1  8306  三菱UFJフィナンシャル・グループ  2.5
2  6758    ソニーグループ     2.3
...
```

### CLI

```
$ etf 1306

1306 — ＮＥＸＴ　ＦＵＮＤＳ　ＴＯＰＩＸ連動型上場投信 (2026-02-27)

 Code   Name                                Weight
─────  ──────────────────────────────────  ──────
 7203   トヨタ自動車                          3.7%
 8306   三菱ＵＦＪフィナンシャル・グループ    3.3%
 6501   日立製作所                            2.4%
 8316   三井住友フィナンシャルグループ        2.3%
 6758   ソニーグループ                        2.1%
 8058   三菱商事                              2.0%
 8411   みずほフィナンシャルグループ          1.8%
 8035   東京エレクトロン                      1.7%
 7011   三菱重工業                            1.7%
 6857   アドバンテスト                        1.6%
```

Use `--en` for English names: `etf 1306 --en`

## Installation

```bash
pip install pyjpx-etf
```

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/obichan117/pyjpx-etf/blob/main/examples/quickstart.ipynb)
