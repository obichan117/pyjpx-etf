# ETF Data

## The ETF Class

The `ETF` class is the main entry point. It lazily fetches data on first access.

```python
import pyjpx_etf as etf

e = etf.ETF("1306")
```

### ETF Info

Access metadata via the `info` property:

```python
e.info.code               # "1306"
e.info.name               # "TOPIX ETF"
e.info.cash_component     # Fund cash component
e.info.shares_outstanding # Shares outstanding
e.info.date               # Fund date as datetime.date

# Convert to dict
dict_info = e.info.to_dict()
```

### Holdings

Access constituent holdings:

```python
for h in e.holdings:
    print(f"{h.code} {h.name}: {h.weight:.2%}")
```

Each `Holding` has: `code`, `name`, `isin`, `exchange`, `currency`, `shares`, `price`, `weight`.

### DataFrame Output

```python
df = e.to_dataframe()
# Columns: code, name, isin, exchange, currency, shares, price, weight
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
