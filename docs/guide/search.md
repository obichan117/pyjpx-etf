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
   code                    name    weight     shares           aum
0  2644  半導体ETF                  0.1523   150000.0  1.234500e+11
1  1306  TOPIX連動型上場投資信託      0.0089  1200000.0  5.170000e+12
2  1321  日経225連動型上場投資信託    0.0078   800000.0  3.200000e+12
...
```

### Parameters

```python
etf.search("6857")              # top 10 (default)
etf.search("6857", n=20)        # top 20
etf.search("6857", date="2026-03-01")  # specific date
etf.search("285A", gap=8.0)     # add an `impact` column for a +8% stock gap
```

| Parameter | Type | Description |
|-----------|------|--------------|
| `n` | int | Number of results (default: `10`) |
| `date` | str \| None | Specific date (`YYYY-MM-DD`); uses the latest available date if `None` |
| `gap` | float \| None | If given, adds an `impact` column: estimated NAV impact (%) = `weight` (fraction) × `gap` (%) |

### Return Value

Returns a `pd.DataFrame` with columns:

| Column | Type | Description |
|--------|------|-------------|
| `code` | str | ETF code |
| `name` | str | ETF name (respects `config.lang`) |
| `weight` | float | Portfolio weight (0.0–1.0) |
| `shares` | float | Number of shares held |
| `aum` | float | ETF's total net asset value in yen |
| `impact` | float | Only present when `gap` is given: estimated NAV impact in percent |

!!! tip "Use `aum` to judge tradability"
    A high weight in a tiny or illiquid ETF isn't very actionable — check `aum` alongside `weight`/`impact` before acting on a result. See the [Concentration Screening guide](concentration.md) for more on the `gap=`/`impact` workflow.

## CLI

```
$ etf find 6857            # ETFs holding Advantest
$ etf find 7203 5          # top 5 ETFs holding Toyota
$ etf find 6857 --en       # English names
$ etf find 285A --gap +8   # add an Impact column for a +8% Kioxia gap
```

!!! tip "Use `find` or `search`"
    Both `etf find` and `etf search` work — they're aliases.

## Use Cases

- **Exposure analysis**: how much of your ETF portfolio is exposed to a single stock?
- **ETF selection**: find the most concentrated ETF for a stock you're bullish on
- **Diversification check**: see if multiple ETFs overlap on the same holdings
