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
print(e.holdings[:3])
# [Holding(code='7203', name='トヨタ自動車', ...),
#  Holding(code='8306', name='三菱UFJフィナンシャル・グループ', ...),
#  Holding(code='6758', name='ソニーグループ', ...)]
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

English names with `--en`:

```
$ etf 1306 --en

1306 — TOPIX ETF (2026-02-27)

 Code   Name                Weight
─────  ──────────────────  ──────
 7203   TOYOTA MOTOR CORP     3.7%
 8306   MITSUBISHI UFJ FIN    3.3%
 6501   HITACHI               2.4%
 ...
```

### Language Setting

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
