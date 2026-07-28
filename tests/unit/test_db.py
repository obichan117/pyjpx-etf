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
        # cash_component=1000 + (1000*2500 + 500*5000) on latest date
        assert df.iloc[0]["aum"] == 5_001_000.0
        assert df.iloc[0]["date"] == "2026-03-01"

    def test_search_by_holding_excludes_dropped_stock(self, populated_db):
        # 8035 was held on 2026-02-28 but is absent from 1306's latest
        # snapshot (2026-03-01) — search must not resurrect the old weight.
        db.insert_holdings(
            populated_db,
            "1306",
            "2026-02-28",
            [
                Holding(
                    code="8035",
                    name="TOKYO ELECTRON",
                    isin="JP003",
                    exchange="TSE",
                    currency="JPY",
                    shares=100.0,
                    price=30000.0,
                    weight=0.3,
                )
            ],
        )
        populated_db.commit()
        df = db.search_by_holding("8035")
        assert df.empty

    def test_read_history_with_holding(self, populated_db):
        df = db.read_history("1306", "7203")
        assert len(df) == 2
        assert "date" in df.columns
        assert "weight" in df.columns

    def test_read_history_overview(self, populated_db):
        df = db.read_history("1306")
        assert len(df) == 2
        assert "weight_change" in df.columns


@pytest.fixture()
def concentration_db(tmp_db):
    """DB with a concentrated ETF, a diversified ETF, and a derivative row."""
    conn = tmp_db
    db.upsert_etf(conn, "9001", name_ja="集中ETF", name_en="Concentrated ETF", fee=0.10)
    db.upsert_etf(conn, "9002", name_ja="分散ETF", name_en="Diversified ETF", fee=0.20)

    db.insert_pcf_info(
        conn,
        "9001",
        "2026-06-01",
        name="Concentrated ETF",
        cash_component=1000.0,
        shares_outstanding=1000,
    )
    db.insert_pcf_info(
        conn,
        "9002",
        "2026-06-01",
        name="Diversified ETF",
        cash_component=1000.0,
        shares_outstanding=1000,
    )

    concentrated_holdings = [
        Holding(
            code="1111",
            name="BigCo",
            isin="JP101",
            exchange="TSE",
            currency="JPY",
            shares=100.0,
            price=1000.0,
            weight=0.22,
        ),
        Holding(
            code="2222",
            name="SmallCo",
            isin="JP102",
            exchange="TSE",
            currency="JPY",
            shares=100.0,
            price=100.0,
            weight=0.03,
        ),
        Holding(
            code="",
            name="FX Forward",
            isin="",
            exchange="",
            currency="USD",
            shares=0.0,
            price=0.0,
            weight=0.75,
        ),
    ]
    db.insert_holdings(conn, "9001", "2026-06-01", concentrated_holdings)

    diversified_holdings = [
        Holding(
            code=f"{3000 + i}",
            name=f"Stock{i}",
            isin=f"JP20{i}",
            exchange="TSE",
            currency="JPY",
            shares=10.0,
            price=100.0,
            weight=0.02,
        )
        for i in range(20)
    ]
    db.insert_holdings(conn, "9002", "2026-06-01", diversified_holdings)

    # Feeder fund-of-funds ETF: holds one foreign ETF + cash. Both holding
    # codes are 4 chars but must NOT count as JP-equity concentration.
    db.upsert_etf(conn, "9003", name_ja="フィーダーETF", name_en="Feeder ETF", fee=0.1)
    db.insert_pcf_info(
        conn,
        "9003",
        "2026-06-01",
        name="Feeder ETF",
        cash_component=1000.0,
        shares_outstanding=1000,
    )
    feeder_holdings = [
        Holding(
            code="IEMG",
            name="ISHARES CORE MSCI EM",
            isin="US001",
            exchange="NYSE",
            currency="USD",
            shares=100.0,
            price=50.0,
            weight=0.95,
        ),
        Holding(
            code="CASH",
            name="CASH",
            isin="",
            exchange="",
            currency="JPY",
            shares=0.0,
            price=0.0,
            weight=0.05,
        ),
    ]
    db.insert_holdings(conn, "9003", "2026-06-01", feeder_holdings)
    conn.commit()
    return conn


class TestConcentrationStats:
    def test_columns(self, concentration_db):
        config.lang = "en"
        df = db.concentration_stats()
        assert list(df.columns) == [
            "code",
            "name",
            "top_code",
            "top_name",
            "top1",
            "top3",
            "top10",
            "n_holdings",
            "aum",
        ]

    def test_ordering_by_top1(self, concentration_db):
        config.lang = "en"
        df = db.concentration_stats()
        assert df.iloc[0]["code"] == "9001"  # concentrated ETF ranks first
        assert df.iloc[0]["name"] == "Concentrated ETF"
        assert df.iloc[0]["top_code"] == "1111"

    def test_weights_are_fractions(self, concentration_db):
        df = db.concentration_stats()
        row = df[df["code"] == "9001"].iloc[0]
        assert abs(row["top1"] - 0.22) < 1e-9
        assert abs(row["top3"] - 0.25) < 1e-9  # only 2 equity holdings

    def test_derivative_row_present_but_excluded(self, concentration_db):
        # Derivative (FX forward) row is present in raw pcf_holdings...
        row = concentration_db.execute(
            "SELECT * FROM pcf_holdings WHERE code = '9001' AND holding_code = ''"
        ).fetchone()
        assert row is not None
        assert row["weight"] == 0.75

        # ...but excluded from concentration stats (only 4-char equity codes)
        df = db.concentration_stats()
        top_row = df[df["code"] == "9001"].iloc[0]
        assert abs(top_row["top1"] - 0.22) < 1e-9
        assert top_row["n_holdings"] == 2

    def test_feeder_and_cash_codes_excluded(self, concentration_db):
        # 9003 holds only IEMG (foreign ticker) + CASH — 4-char codes that
        # don't match the JP-equity pattern, so the ETF has no qualifying
        # holdings and must not appear in the ranking at all.
        df = db.concentration_stats()
        assert "9003" not in df["code"].tolist()
        assert df.iloc[0]["code"] == "9001"  # still the real concentrated ETF

    def test_diversified_etf_has_low_concentration(self, concentration_db):
        df = db.concentration_stats()
        row = df[df["code"] == "9002"].iloc[0]
        assert abs(row["top1"] - 0.02) < 1e-9
        assert row["n_holdings"] == 20

    def test_sort_by_top3(self, concentration_db):
        df = db.concentration_stats(by="top3")
        vals = df["top3"].tolist()
        assert vals == sorted(vals, reverse=True)

    def test_n_limits_results(self, concentration_db):
        df = db.concentration_stats(n=1)
        assert len(df) == 1

    def test_includes_aum(self, concentration_db):
        df = db.concentration_stats()
        row = df[df["code"] == "9001"].iloc[0]
        # cash_component=1000 + (100*1000 + 100*100 + 0*0)
        assert row["aum"] == 111_000.0

    def test_empty_without_db(self, tmp_path):
        config.db_path = tmp_path / "nonexistent.db"
        df = db.concentration_stats()
        assert df.empty
        config.db_path = None


class TestDbMissing:
    def test_read_etf_info_no_db(self, tmp_path):
        config.db_path = tmp_path / "nonexistent.db"
        assert db.read_etf_info("1306") is None
        config.db_path = None

    def test_db_exists_false(self, tmp_path):
        config.db_path = tmp_path / "nonexistent.db"
        assert not db.db_exists()
        config.db_path = None


class TestExportLatest:
    def test_keeps_only_latest_snapshot(self, populated_db, tmp_path):
        import sqlite3

        dest = tmp_path / "latest.db"
        db.export_latest(db.db_path(), dest)

        out = sqlite3.connect(str(dest))
        out.row_factory = sqlite3.Row
        try:
            dates = [
                r["date"] for r in out.execute("SELECT DISTINCT date FROM pcf_holdings")
            ]
            assert dates == ["2026-03-01"]
            assert out.execute("SELECT COUNT(*) FROM pcf_holdings").fetchone()[0] == 2
            assert out.execute("SELECT COUNT(*) FROM etfs").fetchone()[0] == 2
            assert out.execute("SELECT COUNT(*) FROM securities").fetchone()[0] == 2
            variant = out.execute(
                "SELECT value FROM meta WHERE key = 'variant'"
            ).fetchone()
            assert variant["value"] == "latest"
        finally:
            out.close()


class TestFullDbPreference:
    def test_read_history_prefers_full_db(self, populated_db):
        import shutil

        # Snapshot today's two-date DB as the full-history DB, then strip
        # the older date from the main DB (simulating a latest-only sync).
        shutil.copy(db.db_path(), db.full_db_path())
        populated_db.execute("DELETE FROM pcf_holdings WHERE date = '2026-02-28'")
        populated_db.commit()

        df = db.read_history("1306", "7203")
        assert len(df) == 2  # both dates, served from the full DB
