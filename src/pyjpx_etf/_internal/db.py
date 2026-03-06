"""SQLite layer — re-exports from db_core, db_read, db_write."""

from .db_core import db_exists, db_path, get_connection
from .db_read import (
    read_etf_dates,
    read_etf_fee,
    read_etf_info,
    read_etf_list,
    read_history,
    read_holdings,
    search_by_holding,
)
from .db_write import (
    init_schema,
    insert_holdings,
    insert_pcf_info,
    update_meta,
    upsert_etf,
    upsert_security,
)

__all__ = [
    "db_exists",
    "db_path",
    "get_connection",
    "init_schema",
    "insert_holdings",
    "insert_pcf_info",
    "read_etf_dates",
    "read_etf_fee",
    "read_etf_info",
    "read_etf_list",
    "read_history",
    "read_holdings",
    "search_by_holding",
    "update_meta",
    "upsert_etf",
    "upsert_security",
]
