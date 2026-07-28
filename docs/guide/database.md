# Local Database

pyjpx-etf can store ETF data locally in a SQLite database, enabling offline access, reverse stock search, and historical weight tracking.

## How It Works

A GitHub Actions cron job runs daily at 07:55 JST (Mon–Fri), fetching PCF data for all ~400 TSE ETFs and saving it to a SQLite database. Two variants are published as GitHub Release assets:

- **Latest snapshot** (`pcf-latest.db.gz`, a few MB) — each ETF's most recent PCF only. This is what `etf sync` downloads daily, and it's all that `ETF`, `search()`, `concentration()` and `screen` need.
- **Full history** (`pcf-full.db.gz`, hundreds of MB and growing) — the complete append-only history, needed only by `history()`. Downloaded on demand with `etf sync --full` to a separate `pcf-full.db` file, so daily syncs never overwrite it.

```
GitHub Actions (daily) ──→ pcf-latest.db.gz ──→ etf sync ────────→ ~/.cache/pyjpx-etf/pcf.db
                       └─→ pcf-full.db.gz  ──→ etf sync --full ─→ ~/.cache/pyjpx-etf/pcf-full.db
```

## Syncing the Database

### Python

```python
import pyjpx_etf as etf

path = etf.sync()            # latest snapshot; downloads only if the remote is newer
path = etf.sync(force=True)  # always re-download
path = etf.sync(full=True)   # full history DB (large!) for history()
```

### CLI

```
$ etf sync            # download/update latest snapshot (small, fast)
$ etf sync --force    # force re-download
$ etf sync --full     # download full history DB for `etf history`
```

The database is saved to `~/.cache/pyjpx-etf/pcf.db` by default (the full-history variant goes to `pcf-full.db` alongside it). Override the base path with:

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

Both DB variants share this schema — the latest-snapshot DB simply contains only each ETF's most recent `(code, date)` rows (its `meta` table has `variant = latest`).
