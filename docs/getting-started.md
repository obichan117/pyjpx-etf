# Getting Started

## Installation

```bash
pip install pyjpx-etf
```

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

etf.config.timeout = 60        # HTTP timeout in seconds
etf.config.request_delay = 0.5  # Delay between provider retries
etf.config.lang = "en"          # "ja" (default) or "en"
```

## Data Sources

pyjpx-etf fetches PCF (Portfolio Composition File) CSVs from:

| Provider | Covers |
|---|---|
| ICE Data Services | Majority of TSE ETFs |
| Solactive AG | Global X Japan ETFs |

Data is updated daily on business days, available 7:50–23:55 JST.
