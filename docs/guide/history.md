# Weight History

Track how a stock's weight in an ETF changes over time, or see which holdings have gained/lost the most weight.

!!! note "Requires local database"
    `history()` reads from the local SQLite database. Run `etf sync` first to download it. More days of data accumulate as the daily cron job runs.

## Tracking a Specific Stock

```python
import pyjpx_etf as etf

# How has Advantest's weight in TOPIX ETF changed over time?
df = etf.history("1306", "6857")
```

```
         date    weight      shares     price
0  2026-03-01  0.008523  1200000.0    8500.0
1  2026-03-02  0.008891  1200000.0    8870.0
2  2026-03-03  0.009102  1200000.0    9080.0
...
```

Returns a `pd.DataFrame` with columns:

| Column | Type | Description |
|--------|------|-------------|
| `date` | str | Date (YYYY-MM-DD) |
| `weight` | float | Portfolio weight (0.0–1.0) |
| `shares` | float | Number of shares held |
| `price` | float | Stock price on that date |

## Top Holdings Overview

Without a stock code, `history()` returns the top 20 holdings with their weight change from the earliest to the latest date in the database:

```python
df = etf.history("1306")
```

```
   code              name    weight  weight_change
0  7203        トヨタ自動車    0.0380         0.0012
1  8306  三菱UFJ...          0.0250        -0.0005
2  6758    ソニーグループ      0.0230         0.0008
...
```

Returns a `pd.DataFrame` with columns:

| Column | Type | Description |
|--------|------|-------------|
| `code` | str | Stock code |
| `name` | str | Stock name |
| `weight` | float | Latest portfolio weight (0.0–1.0) |
| `weight_change` | float | Weight change from earliest to latest date |

## CLI

```
$ etf history 1306 6857      # Advantest weight in TOPIX over time
$ etf history 1306           # top holdings with weight change
$ etf history 1306 --en      # English names
```

## Use Cases

- **Rebalancing insight**: see when an ETF increases/decreases a position
- **Trend analysis**: track a stock's growing or declining weight across index rebalances
- **Sector rotation**: compare weight changes across top holdings to spot sector trends
