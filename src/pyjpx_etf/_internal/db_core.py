"""SQLite schema and connection management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DEFAULT_DB_PATH = Path.home() / ".cache" / "pyjpx-etf" / "pcf.db"

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS etfs (
    code    TEXT PRIMARY KEY,
    name_ja TEXT,
    name_en TEXT,
    fee     REAL
);

CREATE TABLE IF NOT EXISTS pcf_info (
    code               TEXT NOT NULL,
    date               TEXT NOT NULL,
    name               TEXT,
    cash_component     REAL,
    shares_outstanding INTEGER,
    PRIMARY KEY (code, date)
);

CREATE TABLE IF NOT EXISTS pcf_holdings (
    code         TEXT NOT NULL,
    date         TEXT NOT NULL,
    holding_code TEXT NOT NULL,
    name         TEXT,
    isin         TEXT,
    exchange     TEXT,
    currency     TEXT,
    shares       REAL,
    price        REAL,
    weight       REAL,
    PRIMARY KEY (code, date, holding_code)
);

CREATE INDEX IF NOT EXISTS idx_holdings_stock ON pcf_holdings(holding_code);

CREATE TABLE IF NOT EXISTS securities (
    code    TEXT PRIMARY KEY,
    name_ja TEXT,
    name_en TEXT
);
"""


def db_path() -> Path:
    """Return the configured or default database path."""
    from ..config import config

    if config.db_path is not None:
        return config.db_path
    return _DEFAULT_DB_PATH


def db_exists() -> bool:
    """Return True if the database file exists."""
    return db_path().is_file()


def get_connection(*, readonly: bool = True) -> sqlite3.Connection:
    """Return a SQLite connection. Read-only by default."""
    path = db_path()
    if readonly:
        uri = f"file:{path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn
