"""Tests for _internal/db.py — SQLite read/write layer."""

import datetime

import pytest

from pyjpx_etf._internal import db
from pyjpx_etf.config import config
from pyjpx_etf.models import Holding


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary DB and point config at it."""
    db_file = tmp_path / "test.db"
    original = config.db_path
    config.db_path = db_file
    conn = db.get_connection(readonly=False)
    db.init_schema(conn)
    yield conn
    conn.close()
    config.db_path = original


@pytest.fixture()
def populated_db(tmp_db):
    """DB with sample data inserted."""
    conn = tmp_db
    db.upsert_etf(conn, "1306", name_ja="TOPIX連動型", name_en="TOPIX ETF", fee=0.06)
    db.upsert_etf(
        conn,
        "2644",
        name_ja="半導体ETF",
        name_en="Semiconductor ETF",
        fee=0.41,
    )
    db.insert_pcf_info(
        conn,
        "1306",
        "2026-03-01",
        name="TOPIX ETF",
        cash_component=1000.0,
        shares_outstanding=100000,
    )
    holdings = [
        Holding(
            code="7203",
            name="TOYOTA",
            isin="JP001",
            exchange="TSE",
            currency="JPY",
            shares=1000.0,
            price=2500.0,
            weight=0.6,
        ),
        Holding(
            code="6857",
            name="ADVANTEST",
            isin="JP002",
            exchange="TSE",
            currency="JPY",
            shares=500.0,
            price=5000.0,
            weight=0.4,
        ),
    ]
    db.insert_holdings(conn, "1306", "2026-03-01", holdings)

    # Second date for history
    db.insert_pcf_info(
        conn,
        "1306",
        "2026-02-28",
        name="TOPIX ETF",
        cash_component=900.0,
        shares_outstanding=100000,
    )
    holdings_old = [
        Holding(
            code="7203",
            name="TOYOTA",
            isin="JP001",
            exchange="TSE",
            currency="JPY",
            shares=1000.0,
            price=2400.0,
            weight=0.55,
        ),
        Holding(
            code="6857",
            name="ADVANTEST",
            isin="JP002",
            exchange="TSE",
            currency="JPY",
            shares=500.0,
            price=4800.0,
            weight=0.45,
        ),
    ]
    db.insert_holdings(conn, "1306", "2026-02-28", holdings_old)

    db.upsert_security(conn, "7203", name_ja="トヨタ自動車")
    db.upsert_security(conn, "6857", name_ja="アドバンテスト")
    db.update_meta(conn, "version", "1")
    conn.commit()
    return conn


class TestSchema:
    def test_init_schema_creates_tables(self, tmp_db):
        conn = tmp_db
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert {"meta", "etfs", "pcf_info", "pcf_holdings", "securities"} <= names

    def test_init_schema_idempotent(self, tmp_db):
        db.init_schema(tmp_db)  # second call should not fail


class TestWriteQueries:
    def test_upsert_etf(self, tmp_db):
        conn = tmp_db
        db.upsert_etf(conn, "1306", name_ja="TOPIX", fee=0.06)
        row = conn.execute("SELECT * FROM etfs WHERE code='1306'").fetchone()
        assert row["name_ja"] == "TOPIX"
        assert row["fee"] == 0.06

    def test_upsert_etf_preserves_existing(self, tmp_db):
        conn = tmp_db
        db.upsert_etf(conn, "1306", name_ja="TOPIX", fee=0.06)
        db.upsert_etf(conn, "1306", name_en="TOPIX ETF")
        row = conn.execute("SELECT * FROM etfs WHERE code='1306'").fetchone()
        assert row["name_ja"] == "TOPIX"
        assert row["name_en"] == "TOPIX ETF"
        assert row["fee"] == 0.06

    def test_insert_pcf_info(self, tmp_db):
        conn = tmp_db
        db.insert_pcf_info(
            conn,
            "1306",
            "2026-03-01",
            name="TOPIX",
            cash_component=1000.0,
            shares_outstanding=100,
        )
        row = conn.execute("SELECT * FROM pcf_info WHERE code='1306'").fetchone()
        assert row["name"] == "TOPIX"

    def test_insert_holdings(self, tmp_db):
        conn = tmp_db
        h = [
            Holding(
                code="7203",
                name="TOYOTA",
                isin="JP001",
                exchange="TSE",
                currency="JPY",
                shares=100.0,
                price=2500.0,
                weight=1.0,
            )
        ]
        db.insert_holdings(conn, "1306", "2026-03-01", h)
        row = conn.execute("SELECT * FROM pcf_holdings WHERE code='1306'").fetchone()
        assert row["holding_code"] == "7203"

    def test_update_meta(self, tmp_db):
        conn = tmp_db
        db.update_meta(conn, "version", "1")
        row = conn.execute("SELECT value FROM meta WHERE key='version'").fetchone()
        assert row["value"] == "1"


class TestReadQueries:
    def test_read_etf_info_latest(self, populated_db):
        info = db.read_etf_info("1306")
        assert info is not None
        assert info.code == "1306"
        assert info.date == datetime.date(2026, 3, 1)

    def test_read_etf_info_specific_date(self, populated_db):
        info = db.read_etf_info("1306", "2026-02-28")
        assert info is not None
        assert info.date == datetime.date(2026, 2, 28)

    def test_read_etf_info_missing(self, populated_db):
        assert db.read_etf_info("9999") is None

    def test_read_holdings_latest(self, populated_db):
        holdings = db.read_holdings("1306")
        assert holdings is not None
        assert len(holdings) == 2
        assert holdings[0].code == "7203"  # higher weight

    def test_read_holdings_missing(self, populated_db):
        assert db.read_holdings("9999") is None

    def test_read_etf_fee(self, populated_db):
        assert db.read_etf_fee("1306") == 0.06

    def test_read_etf_fee_missing(self, populated_db):
        assert db.read_etf_fee("9999") is None

    def test_read_etf_dates(self, populated_db):
        dates = db.read_etf_dates("1306")
        assert len(dates) == 2
        assert dates[0] == datetime.date(2026, 3, 1)  # newest first

    def test_read_etf_list(self, populated_db):
        etfs = db.read_etf_list()
        assert "1306" in etfs
        assert etfs["1306"]["fee"] == 0.06

    def test_search_by_holding(self, populated_db):
        config.lang = "en"
        df = db.search_by_holding("7203")
        assert len(df) == 1
        assert df.iloc[0]["code"] == "1306"

    def test_read_history_with_holding(self, populated_db):
        df = db.read_history("1306", "7203")
        assert len(df) == 2
        assert "date" in df.columns
        assert "weight" in df.columns

    def test_read_history_overview(self, populated_db):
        df = db.read_history("1306")
        assert len(df) == 2
        assert "weight_change" in df.columns


class TestDbMissing:
    def test_read_etf_info_no_db(self, tmp_path):
        config.db_path = tmp_path / "nonexistent.db"
        assert db.read_etf_info("1306") is None
        config.db_path = None

    def test_db_exists_false(self, tmp_path):
        config.db_path = tmp_path / "nonexistent.db"
        assert not db.db_exists()
        config.db_path = None
