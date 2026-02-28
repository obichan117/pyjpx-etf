# ETF Ranking

## The ranking() Function

Rank all TSE-listed ETFs by return over various periods.

```python
import pyjpx_etf as etf

# Top 10 by 1-month return (default)
df = etf.ranking()
```

```
   code                     name  return   fee  dividend_yield
0  1623  NEXT FUNDS 鉄鋼・非鉄...   49.10  0.32            1.39
1  2646  グローバルX メタルビジネス...   47.62  0.59            1.13
2  213A  上場インデックスファンド...   42.46  0.15            0.77
...
```

## Periods

| Period | Description |
|--------|-------------|
| `1m` | 1 month (default) |
| `3m` | 3 months |
| `6m` | 6 months |
| `1y` | 1 year |
| `3y` | 3 years |
| `5y` | 5 years |
| `10y` | 10 years |
| `ytd` | Year to date |

```python
etf.ranking("1y")       # top 10 by 1-year return
etf.ranking("ytd")      # top 10 by ytd return
```

## Controlling Results

```python
etf.ranking("1m", n=20)    # top 20
etf.ranking("1m", n=-10)   # worst 10
etf.ranking("1m", n=0)     # all ETFs, sorted descending
```

- Positive `n`: top N (sorted descending by return)
- Negative `n`: worst N (sorted ascending by return)
- `n=0`: all ETFs sorted descending

## Language

Respects `config.lang`:

```python
etf.config.lang = "en"
etf.ranking()  # English names
```

## CLI

```
$ etf rank                # top 10, 1m
$ etf rank 20             # top 20, 1m
$ etf rank -10            # worst 10, 1m
$ etf rank 20 1y          # top 20, 1y
$ etf rank -5 ytd --en    # worst 5, ytd, English
```

## Data Source

Ranking data comes from Rakuten Securities, updated daily. Fees are merged from the JPX ETF list page and Rakuten. ETFs with no return data for the requested period are excluded.
