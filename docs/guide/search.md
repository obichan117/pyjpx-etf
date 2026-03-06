# Reverse Stock Search

Find which ETFs hold a given stock, ranked by portfolio weight.

!!! note "Requires local database"
    `search()` reads from the local SQLite database. Run `etf sync` first to download it.

## Python

```python
import pyjpx_etf as etf

# Which ETFs hold Advantest (6857)?
df = etf.search("6857")
```

```
   code                    name    weight     shares
0  2644  半導体ETF                  0.1523   150000.0
1  1306  TOPIX連動型上場投資信託      0.0089  1200000.0
2  1321  日経225連動型上場投資信託    0.0078   800000.0
...
```

### Parameters

```python
etf.search("6857")              # top 10 (default)
etf.search("6857", n=20)        # top 20
etf.search("6857", date="2026-03-01")  # specific date
```

### Return Value

Returns a `pd.DataFrame` with columns:

| Column | Type | Description |
|--------|------|-------------|
| `code` | str | ETF code |
| `name` | str | ETF name (respects `config.lang`) |
| `weight` | float | Portfolio weight (0.0–1.0) |
| `shares` | float | Number of shares held |

## CLI

```
$ etf find 6857            # ETFs holding Advantest
$ etf find 7203 5          # top 5 ETFs holding Toyota
$ etf find 6857 --en       # English names
```

!!! tip "Use `find` or `search`"
    Both `etf find` and `etf search` work — they're aliases.

## Use Cases

- **Exposure analysis**: how much of your ETF portfolio is exposed to a single stock?
- **ETF selection**: find the most concentrated ETF for a stock you're bullish on
- **Diversification check**: see if multiple ETFs overlap on the same holdings
