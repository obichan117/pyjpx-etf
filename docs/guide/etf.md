# ETF Data

## The ETF Class

The `ETF` class is the main entry point. It lazily fetches data on first access.

```python
import pyjpx_etf as etf

e = etf.ETF("1306")
```

### ETF Info

Access metadata via the `info` property. Names are Japanese by default:

```python
e.info.code               # "1306"
e.info.name               # "TOPIX連動型上場投資信託"
e.info.cash_component     # Fund cash component
e.info.shares_outstanding # Shares outstanding
e.info.date               # Fund date as datetime.date

# Convert to dict
dict_info = e.info.to_dict()
```

### Holdings

Access constituent holdings:

```python
for h in e.holdings[:3]:
    print(f"{h.code} {h.name}: {h.weight:.2%}")
# 7203 トヨタ自動車: 3.80%
# 8306 三菱UFJフィナンシャル・グループ: 2.50%
# 6758 ソニーグループ: 2.30%
```

Each `Holding` has: `code`, `name`, `isin`, `exchange`, `currency`, `shares`, `price`, `weight`.

### NAV

Total fund net asset value (cash + holdings market value) in yen:

```python
e.nav  # 515997003139 (in yen)
```

### Fee (信託報酬)

Trust fee (信託報酬), sourced from JPX with Rakuten Securities as fallback. Independent of PCF data:

```python
e.fee  # 0.06 (means 0.06%)
```

Returns `None` if the fee is unavailable from both sources.

### DataFrame Output

```python
df = e.to_dataframe()
# Columns: code, name, isin, exchange, currency, shares, price, weight
```

### Language

Set `config.lang` before creating an `ETF` instance:

```python
import pyjpx_etf as etf

# Japanese (default)
e = etf.ETF("1306")
e.info.name  # "TOPIX連動型上場投資信託"

# English
etf.config.lang = "en"
e = etf.ETF("1306")
e.info.name  # "TOPIX ETF"
```

## Error Handling

```python
from pyjpx_etf import ETFNotFoundError, FetchError, ParseError

try:
    e = etf.ETF("9999")
    _ = e.info
except ETFNotFoundError:
    print("ETF not found")
except FetchError:
    print("Network error")
```
