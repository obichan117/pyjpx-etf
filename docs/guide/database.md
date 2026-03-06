# Local Database

pyjpx-etf can store ETF data locally in a SQLite database, enabling offline access, reverse stock search, and historical weight tracking.

## How It Works

A GitHub Actions cron job runs daily at 07:55 JST (Mon–Fri), fetching PCF data for all ~400 TSE ETFs and saving it to a SQLite database. The database is published as a GitHub Release artifact.

Users download it with `etf sync` (or `etf.sync()` in Python). Once downloaded, all ETF lookups read from the local DB first, falling back to live HTTP only when needed.

```
GitHub Actions (daily) → pcf.db → GitHub Releases
                                         ↓
                                    etf sync
                                         ↓
                                ~/.cache/pyjpx-etf/pcf.db
                                         ↓
                               ETF("1306") reads DB first
```

## Syncing the Database

### Python

```python
import pyjpx_etf as etf

path = etf.sync()         # download if missing or older than 1 day
path = etf.sync(force=True)  # always re-download
```

### CLI

```
$ etf sync            # download/update
$ etf sync --force    # force re-download
```

The database is saved to `~/.cache/pyjpx-etf/pcf.db` by default. Override with:

```python
from pathlib import Path
etf.config.db_path = Path("/custom/path/pcf.db")
```

## DB-First, Live Fallback

By default, `ETF("1306")` reads from the local database. This is fast (no HTTP), reliable (works offline and outside data hours), and always up-to-date if you run `etf sync` regularly. If the DB doesn't exist or doesn't contain the ETF, it falls back to a live HTTP fetch.

```python
# DB-first (default) — fast, works offline
e = etf.ETF("1306")

# Force live — skip DB, fetch from HTTP providers
e = etf.ETF("1306", live=True)
```

## Database Schema

The database has 5 tables:

| Table | Purpose |
|-------|---------|
| `meta` | Key-value metadata (version, last updated) |
| `etfs` | ETF master list (code, names, fee) |
| `pcf_info` | PCF header data per ETF per date |
| `pcf_holdings` | Individual holdings per ETF per date |
| `securities` | Security names (Japanese/English) |

Data is append-only: each day's snapshot is keyed on `(code, date)`. No updates, no deletes. This enables historical analysis.
