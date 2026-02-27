# pyjpx-etf

A clean, beginner-friendly Python library for fetching JPX ETF portfolio composition (PCF) data.

## Features

- **Simple API** — yfinance-style `ETF("1306")` interface
- **No authentication** — uses free, public PCF CSV endpoints
- **Lightweight** — just `requests` and `pandas`
- **Auto provider detection** — tries ICE Data Services, then Solactive

## Quick Example

```python
import pyjpx_etf as etf

e = etf.ETF("1306")
print(e.info.name)       # "TOPIX ETF"
print(e.to_dataframe().head())
```

## Installation

```bash
pip install pyjpx-etf
```

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/obichan117/pyjpx-etf/blob/main/examples/quickstart.ipynb)
