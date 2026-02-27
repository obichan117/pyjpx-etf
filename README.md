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
print(e.info.name)       # "TOPIX ETF"
print(e.holdings[:5])    # First 5 holdings
print(e.to_dataframe())  # Full DataFrame with weights
```

## Configuration

```python
import pyjpx_etf as etf

etf.config.timeout = 60
etf.config.request_delay = 0.5
```

## Documentation

[Full documentation](https://obichan117.github.io/pyjpx-etf)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/obichan117/pyjpx-etf/blob/main/examples/quickstart.ipynb)
