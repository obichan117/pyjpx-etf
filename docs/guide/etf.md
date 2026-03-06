# ETF Data

## The ETF Class

The `ETF` class is the main entry point. It lazily fetches data on first access.

```python
import pyjpx_etf as etf

e = etf.ETF("1306")
```

By default, data is read from the local SQLite database (if available via `etf sync`). This is fast, reliable, and works offline. If the DB doesn't exist or doesn't contain the ETF, it falls back to a live HTTP fetch.

```python
# DB-first (default) — reads from local DB, falls back to live
e = etf.ETF("1306")

# Force live — skip DB, always fetch from HTTP providers
e = etf.ETF("1306", live=True)
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

### Top Holdings

Get a quick summary of the top N holdings:

```python
df = e.top()       # top 10 by weight (default)
df = e.top(20)     # top 20
```

Returns a DataFrame with columns: `code`, `name`, `weight` (as percentage).

### NAV

Total fund net asset value (cash + holdings market value) in yen:

```python
e.nav  # 515997003139 (in yen)
```

### Fee

Trust fee (信託報酬), sourced from the local DB, JPX fee page, or Rakuten Securities (in order). Independent of PCF data:

```python
e.fee  # 0.06 (means 0.06%)
```

Returns `None` if the fee is unavailable from all sources.

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
    print("Network error or outside data hours")
```

!!! info "Error precedence"
    `ETFNotFoundError` is only raised when **all** providers return 404. If any provider returns a server error or network error, `FetchError` is raised instead — the code might be valid but temporarily unavailable.
