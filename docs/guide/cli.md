# CLI Reference

pyjpx-etf installs the `etf` command.

## ETF Lookup

```
etf <code|alias> [--en] [-a] [--live]
```

Show portfolio composition for an ETF.

| Flag | Description |
|------|-------------|
| `--en` | Show English names (default: Japanese) |
| `-a`, `--all` | Show all holdings (default: top 10) |
| `--live` | Skip local DB, always fetch from HTTP providers |

```
$ etf 1306
$ etf topix --en -a
$ etf 200A --live
```

### Aliases

Shortcuts for popular ETFs:

| Alias | Code | Name |
|-------|------|------|
| `topix` | 1306 | TOPIX ETF |
| `225` | 1321 | Nikkei 225 ETF |
| `core30` | 1311 | TOPIX Core30 ETF |
| `div50` | 1489 | 日経平均高配当株50 ETF |
| `div70` | 1577 | 野村日本株高配当70 ETF |
| `pbr` | 2080 | PBR1倍割れ解消推進 ETF |
| `sox` | 2243 | グローバルX 半導体関連-日本株式 ETF |
| `jpsox1` | 200A | 日経半導体株 ETF |
| `jpsox2` | 2644 | グローバルX 半導体 ETF |

```
$ etf topix          # same as: etf 1306
$ etf sox --en       # same as: etf 2243 --en
```

## ETF Ranking

```
etf rank [n] [period] [--en]
```

Rank all TSE ETFs by return.

| Argument | Description |
|----------|-------------|
| `n` | Number of results. Positive = top N, negative = worst N (default: 10) |
| `period` | Return period (default: `1m`) |
| `--en` | English names |

Available periods: `1m`, `3m`, `6m`, `1y`, `3y`, `5y`, `10y`, `ytd`.

```
$ etf rank                # top 10 by 1-month return
$ etf rank 20 1y          # top 20 by 1-year return
$ etf rank -5 ytd --en    # worst 5 by ytd, English
```

## Database Sync

```
etf sync [--force]
```

Download the latest PCF database from GitHub Releases.

| Flag | Description |
|------|-------------|
| `--force` | Re-download even if local DB is less than 1 day old |

```
$ etf sync
Database ready: /Users/you/.cache/pyjpx-etf/pcf.db
```

The database is required for `search` and `history` commands.

## Stock Search

```
etf find <stock_code> [n] [--en]
```

Find ETFs that hold a given stock, ranked by weight.

| Argument | Description |
|----------|-------------|
| `stock_code` | Stock code to search for (e.g. `6857`) |
| `n` | Number of results (default: 10) |
| `--en` | English names |

```
$ etf find 6857            # ETFs holding Advantest
$ etf find 7203 5          # top 5 ETFs holding Toyota
$ etf find 6857 --en       # English names
```

!!! tip
    `etf search` also works — it's an alias for `etf find`.

## Weight History

```
etf history <etf_code> [stock_code] [--en]
```

Show historical weight data from the local database.

| Argument | Description |
|----------|-------------|
| `etf_code` | ETF code (e.g. `1306`) |
| `stock_code` | Optional stock code for time-series view |
| `--en` | English names |

**With stock code** — time series of that stock's weight:

```
$ etf history 1306 6857
```

```
 Date          Weight      Shares         Price
────────────  ────────  ────────────  ──────────
 2026-03-01     0.85%   1,200,000.0     8,500.0
 2026-03-02     0.89%   1,200,000.0     8,870.0
```

**Without stock code** — top holdings with weight change:

```
$ etf history 1306
```

```
 Code   Name                Weight    Change
─────  ──────────────────  ────────  ────────
 7203   トヨタ自動車          3.80%   +0.12%
 8306   三菱UFJ...           2.50%   -0.05%
```

## Version and Help

```
$ etf --version
pyjpx-etf 0.4.0

$ etf --help
```
