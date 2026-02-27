import pandas as pd
import pytest

from pyjpx_etf import ETF, PyJPXETFError
from pyjpx_etf.config import _ALIASES


@pytest.mark.integration
class TestAliases:
    """Every alias must resolve and load successfully."""

    @pytest.mark.parametrize("alias,code", sorted(_ALIASES.items()))
    def test_alias(self, alias, code):
        e = ETF(code)
        assert e.info.code == code
        assert e.info.name != ""
        assert len(e.holdings) > 0


@pytest.mark.integration
class TestICEProvider:
    """ETFs served by ICE Data Services."""

    def test_topix_etf_1306(self):
        e = ETF("1306")
        assert e.info.code == "1306"
        assert e.info.name != ""
        assert len(e.holdings) > 100

    def test_nikkei225_etf_1321(self):
        e = ETF("1321")
        assert e.info.code == "1321"
        assert len(e.holdings) > 0

    def test_maxis_topix_1348(self):
        e = ETF("1348")
        assert e.info.code == "1348"
        assert len(e.holdings) > 100


@pytest.mark.integration
class TestSolactiveProvider:
    """ETFs served by Solactive AG (Global X Japan)."""

    def test_superdividend_2564(self):
        e = ETF("2564")
        assert e.info.code == "2564"
        assert len(e.holdings) > 0

    def test_ecommerce_2627(self):
        e = ETF("2627")
        assert e.info.code == "2627"
        assert len(e.holdings) > 0

    def test_semiconductor_2644(self):
        e = ETF("2644")
        assert e.info.code == "2644"
        assert len(e.holdings) > 0


@pytest.mark.integration
class TestCommonBehavior:
    def test_to_dataframe(self):
        df = ETF("1306").to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "weight" in df.columns

    def test_weights_sum_to_one(self):
        e = ETF("2644")
        total = sum(h.weight for h in e.holdings)
        assert abs(total - 1.0) < 1e-9

    def test_not_found(self):
        with pytest.raises(PyJPXETFError):
            ETF("0000").info

    def test_fee_returns_float(self):
        e = ETF("1306")
        fee = e.fee
        assert isinstance(fee, float)
        assert 0 < fee < 10  # sanity: fee is a reasonable percentage

    def test_nav_returns_positive_int(self):
        e = ETF("1306")
        nav = e.nav
        assert isinstance(nav, int)
        assert nav > 0
