# Concentration Screening

Find ETFs that are heavily concentrated in one or a few stocks, and estimate how much a stock's price move could shift each ETF's fair value.

!!! note "Requires local database"
    `concentration()` reads from the local SQLite database. Run `etf sync` first to download it.

## The Arbitrage Use Case

When a stock gaps at the open (e.g. on an earnings surprise), any ETF that holds a large weight in that stock should reprice roughly in proportion:

```
estimated NAV impact ≈ stock weight × stock gap %
```

An ETF where a single stock is 30–50% of the portfolio (common with sector or thematic ETFs tracking a handful of names) moves almost like the stock itself. A broad index ETF like TOPIX, where the top holding is a few percent, barely moves. `concentration()` and `search(gap=...)` surface exactly this: which ETFs are concentrated enough in a given stock for a gap to matter.

## Python API

### Ranking ETFs by Concentration

```python
import pyjpx_etf as etf

# Top 20 ETFs by single-stock concentration (top1)
df = etf.concentration()

# Top 10 by top-3 holdings concentration
df = etf.concentration(n=10, by="top3")

# Top 10 by top-10 holdings concentration
df = etf.concentration(n=10, by="top10")
```

```
   code                                  name top_code              top_name      top1      top3     top10  n_holdings           aum
0  2858  グローバルＸ　日経２２５　カバード・コール　ＥＴＦ（プレミアム再投資型）     1320              DAIWA AM  0.501160  0.995834  0.995834           2  3.034092e+08
1  2837              グローバルＸ　中小型リーダーズ－日本株式　ＥＴＦ     285A  KIOXIA HLDG CORP ORD  0.491927  0.599787  0.747026          50  7.561505e+10
2  1622      ＮＥＸＴ　ＦＵＮＤＳ　自動車・輸送機（ＴＯＰＩＸ－１７）上場投信     7203     TOYOTA MOTOR CORP  0.482734  0.637878  0.868587          50  4.031514e+09
...
```

### Parameters

```python
etf.concentration()                # top 20 by top1 (default)
etf.concentration(n=10, by="top3")  # top 10 by cumulative top-3 weight
```

| Parameter | Type | Description |
|-----------|------|--------------|
| `n` | int | Number of results (default: `20`) |
| `by` | str | Stat to sort by: `"top1"`, `"top3"`, or `"top10"` (default: `"top1"`) |

Raises `ValueError` if `by` is anything other than `"top1"`, `"top3"`, or `"top10"`.

### Return Value

Returns a `pd.DataFrame` with columns:

| Column | Type | Description |
|--------|------|--------------|
| `code` | str | ETF code |
| `name` | str | ETF name (respects `config.lang`) |
| `top_code` | str | Code of the ETF's largest holding |
| `top_name` | str | Name of the ETF's largest holding |
| `top1` | float | Weight of the single largest holding (fraction, e.g. `0.49` for 49%) |
| `top3` | float | Cumulative weight of the top 3 holdings (fraction) |
| `top10` | float | Cumulative weight of the top 10 holdings (fraction) |
| `n_holdings` | int | Number of equity holdings counted |
| `aum` | float | Total net asset value in yen |

`top1`, `top3`, and `top10` are always all present regardless of `by` — `by` only controls sort order.

!!! note "Only JP-listed equities count"
    Concentration is computed over holdings whose code is a 4-character JP-style ticker starting with a digit (e.g. `6857`, `285A`). CASH rows, FX forwards/bonds, and foreign feeder tickers (e.g. an ETF-of-ETF holding a single foreign fund like `IEMG`) are excluded, so `n_holdings` may be smaller than the ETF's total row count in the PCF.

## CLI

`etf screen --by top1|top3|top10` runs the same concentration ranking, DB-only (no OHLCV fetch, no `screen` extra required):

```
$ etf screen --by top1 --top 8
```

```
  ETF Screener — top 8 by TOP1

   #  Code   Name                            Top1%    Top3%   Top10%          TopStock  #Hold         AUM
  ──  ─────  ────────────────────────────  ───────  ───────  ───────  ────────────────  ─────  ──────────
   1  2858   グローバルＸ　日経２２５　…     50.12    99.58    99.58  DAIWA AM              2          3億
   2  2837   グローバルＸ　中小型リーダ…     49.19    59.98    74.70  KIOXIA HLDG COR…     50        756億
   3  1622   ＮＥＸＴ　ＦＵＮＤＳ　自動…     48.27    63.79    86.86  TOYOTA MOTOR CO…     50         40億
   4  1618   ＮＥＸＴ　ＦＵＮＤＳ　エネ…     40.88    88.28    99.84  ENEOS HOLDINGS …     11         24億
   5  200A   ＮＥＸＴ　ＦＵＮＤＳ　日経…     33.38    56.12    85.39  KIOXIA HLDGS CO…     30       1305億
   6  221A   ＭＡＸＩＳ日経半導体株上場…     33.38    56.12    85.39  KIOXIA HLDGS CO…     30         93億
   7  1615   ＮＥＸＴ　ＦＵＮＤＳ　東証…     31.06    68.92    85.79  MITSUBISHI UFJ …     69       3865億
   8  1631   ＮＥＸＴ　ＦＵＮＤＳ　銀行…     31.06    68.92    85.79  MITSUBISHI UFJ …     69        245億

  Sorted by: TOP1 (descending)
```

See the [ETF Screener guide](screen.md) and [CLI Reference](cli.md) for the other `--by` stats, which include OHLCV-based ones requiring the `screen` extra.

## Estimating Gap Impact with `search(gap=...)`

`etf find <stock> --gap PCT` (or `search(stock, gap=...)` in Python) finds every ETF holding a stock and estimates each one's fair-value impact for a given move in that stock:

```
$ etf find 285A --gap +8
```

```
  285A キオクシアホールディングス

 Code   Name                                                                            Weight        Shares         AUM    Impact
─────  ──────────────────────────────────────────────────────────────────────────────  ────────  ────────────  ──────────  ────────
 2837   グローバルＸ　中小型リーダーズ－日本株式　ＥＴＦ                                49.19%       487,600        756億  +  3.94%
 200A   ＮＥＸＴ　ＦＵＮＤＳ　日経半導体株指数連動型上場投信                            33.38%       570,800       1305億  +  2.67%
 221A   ＭＡＸＩＳ日経半導体株上場投信                                                  33.38%        40,457      92.82億  +  2.67%
 282A   グローバルＸ　半導体・トップ１０－日本株式　ＥＴＦ                              21.70%        49,100        173億  +  1.74%
 1625   ＮＥＸＴ　ＦＵＮＤＳ　電機・精密（ＴＯＰＩＸ－１７）上場投信                     3.43%         7,300        162億  +  0.27%
 ...
```

285A here is Kioxia Holdings — an ETF like `2837` (Global X MSCI SuperDividend, small/mid leaders) holds ~49% of its portfolio in Kioxia, so an 8% gap in Kioxia implies roughly a +3.9% fair-value move in that ETF. The `AUM` column matters as much as `Impact`: `2858` in the ranking above is 50% concentrated but has an AUM of only ~¥3億 (near-illiquid), while `200A` and `1329` are large enough to actually trade.

In Python:

```python
df = etf.search("285A", gap=8.0)
```

```
   code                                    name    weight         shares           aum    impact
0  2837                グローバルＸ　中小型リーダーズ－日本株式　ＥＴＦ  0.491927  487600.000000  7.561505e+10  3.935412
1  200A              ＮＥＸＴ　ＦＵＮＤＳ　日経半導体株指数連動型上場投信  0.333830  570800.000000  1.305334e+11  2.670643
2  221A                         ＭＡＸＩＳ日経半導体株上場投信  0.333829   40456.804424  9.282172e+09  2.670629
...
```

`impact` is `weight` (fraction) × `gap` (percent), expressed in percent — e.g. a 20% weight with a `gap=8.0` gives `impact=1.6`.

## Caveats

- **Fair-value approximation, not price prediction.** `impact` assumes the ETF reprices in exact proportion to the stock's weight. It ignores everything else moving in the basket that day, and it ignores any existing premium/discount between the ETF's market price and its NAV.
- **Weights are a snapshot.** Both `concentration()` and `search(gap=...)` use the morning PCF (portfolio composition file) — the basket as published before the market open. Intraday rebalances, corporate actions, or creation/redemption activity during the day are not reflected.
- **Check `aum` before acting.** A high `top1`/`top3`/`top10` weight on a tiny or illiquid ETF is not tradable — always look at `aum` alongside concentration or impact.

## Use Cases

- **Earnings gap trades**: a stock gaps on earnings — find which concentrated ETFs should reprice, and by how much
- **Concentration risk check**: see how exposed an ETF is to a single name before buying it
- **Basket screening**: rank all ETFs by concentration to find thematic/sector funds hiding behind a diversified-sounding name
