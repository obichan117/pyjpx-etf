"""Integration tests for DB-dependent features: search, history, ETF DB-first.

Builds a small test DB from live data (3 ETFs) rather than downloading
from GitHub Releases, so these tests don't depend on the release existing.
"""

import pandas as pd
import pytest

from pyjpx_etf import ETF, history, search
from pyjpx_etf._internal import db
from pyjpx_etf._internal.fetcher import fetch_pcf
from pyjpx_etf._internal.parser import parse_pcf
from pyjpx_etf.config import config

_TEST_CODES = ["1306", "1321", "2644"]


@pytest.fixture(scope="module")
def _test_db(tmp_path_factory):
    """Build a small real DB from live PCF data for a few ETFs."""
    db_file = tmp_path_factory.mktemp("db") / "test_pcf.db"
    original = config.db_path
    config.db_path = db_file

    conn = db.get_connection(readonly=False)
    db.init_schema(conn)

    for code in _TEST_CODES:
        csv_text = fetch_pcf(code)
        info, holdings = parse_pcf(csv_text)
        date_str = info.date.isoformat()
        db.upsert_etf(conn, code, name_en=info.name)
        db.insert_pcf_info(
            conn,
            code,
            date_str,
            name=info.name,
            cash_component=info.cash_component,
            shares_outstanding=info.shares_outstanding,
        )
        db.insert_holdings(conn, code, date_str, holdings)

    # Store fees from JPX
    try:
        from pyjpx_etf._internal.fees import get_fees

        fees = get_fees(refresh=True)
        for code in _TEST_CODES:
            fee = fees.get(code)
            if fee is not None:
                db.upsert_etf(conn, code, fee=fee)
    except Exception:
        pass  # fee fetch is optional

    # Store Japanese names from master
    try:
        from pyjpx_etf._internal.master import get_japanese_names

        names = get_japanese_names(refresh=True)
        for code in _TEST_CODES:
            name_ja = names.get(code)
            if name_ja:
                db.upsert_etf(conn, code, name_ja=name_ja)
    except Exception:
        pass

    conn.commit()
    conn.close()

    yield db_file

    config.db_path = original


@pytest.mark.integration
class TestETFFromDB:
    def test_loads_from_db(self, _test_db):
        e = ETF("1306")
        assert e.info.code == "1306"
        assert e.info.name != ""
        assert len(e.holdings) > 100

    def test_fee_from_db(self, _test_db):
        e = ETF("1306")
        fee = e.fee
        assert isinstance(fee, float)
        assert 0 < fee < 10

    def test_nav_from_db(self, _test_db):
        e = ETF("1306")
        nav = e.nav
        assert isinstance(nav, int)
        assert nav > 0

    def test_to_dataframe_from_db(self, _test_db):
        df = ETF("1306").to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "weight" in df.columns

    def test_solactive_from_db(self, _test_db):
        e = ETF("2644")
        assert e.info.code == "2644"
        assert len(e.holdings) > 0


@pytest.mark.integration
class TestSearch:
    def test_search_returns_results(self, _test_db):
        # Toyota is in both 1306 and 1321
        df = search("7203")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "code" in df.columns
        assert "weight" in df.columns

    def test_search_n_limits_results(self, _test_db):
        df = search("7203", n=1)
        assert len(df) <= 1

    def test_search_unknown_stock(self, _test_db):
        df = search("0000")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


@pytest.mark.integration
class TestHistory:
    def test_history_single_stock(self, _test_db):
        # With only 1 day of data, we get at least 1 row
        df = history("1306", "7203")
        assert isinstance(df, pd.DataFrame)
        assert "weight" in df.columns

    def test_history_top_holdings(self, _test_db):
        df = history("1306")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "code" in df.columns
