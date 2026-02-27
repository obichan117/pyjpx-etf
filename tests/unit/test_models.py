import datetime

from pyjpx_etf.models import ETFInfo, Holding


class TestETFInfo:
    def test_construction(self):
        info = ETFInfo(
            code="1306",
            name="TOPIX ETF",
            cash_component=496973797639.0,
            shares_outstanding=8133974978,
            date=datetime.date(2026, 2, 27),
        )
        assert info.code == "1306"
        assert info.name == "TOPIX ETF"
        assert info.cash_component == 496973797639.0
        assert info.shares_outstanding == 8133974978
        assert info.date == datetime.date(2026, 2, 27)

    def test_to_dict(self):
        info = ETFInfo(
            code="1306",
            name="TOPIX ETF",
            cash_component=100.0,
            shares_outstanding=1000,
            date=datetime.date(2026, 1, 1),
        )
        d = info.to_dict()
        assert d == {
            "code": "1306",
            "name": "TOPIX ETF",
            "cash_component": 100.0,
            "shares_outstanding": 1000,
            "date": datetime.date(2026, 1, 1),
        }


class TestHolding:
    def test_construction(self):
        h = Holding(
            code="7203",
            name="TOYOTA",
            isin="JP1234567890",
            exchange="TSE",
            currency="JPY",
            shares=1000.0,
            price=2500.0,
            weight=0.05,
        )
        assert h.code == "7203"
        assert h.shares == 1000.0
        assert h.weight == 0.05

    def test_to_dict(self):
        h = Holding(
            code="7203",
            name="TOYOTA",
            isin="JP1234567890",
            exchange="TSE",
            currency="JPY",
            shares=1000.0,
            price=2500.0,
            weight=0.05,
        )
        d = h.to_dict()
        assert d["code"] == "7203"
        assert d["weight"] == 0.05
        assert len(d) == 8
