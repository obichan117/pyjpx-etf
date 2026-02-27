import datetime

import pytest

from pyjpx_etf._internal.parser import parse_pcf
from pyjpx_etf.exceptions import ParseError

VALID_CSV = """\
ETF Code,ETF Name,Fund Cash Component,Shares Outstanding,Fund Date
1306,TOPIX ETF,496973797639.0,8133974978,20260227

Code,Name,ISIN,Exchange,Currency,Shares Amount,Stock Price
1332,NISSUI CORPORATION,JP3718800000,TSE,JPY,7647000.0,1506.5
7203,TOYOTA MOTOR,JP3633400001,TSE,JPY,3000000.0,2500.0
"""


class TestParseValidCSV:
    def test_info_fields(self):
        info, _ = parse_pcf(VALID_CSV)
        assert info.code == "1306"
        assert info.name == "TOPIX ETF"
        assert info.cash_component == 496973797639.0
        assert info.shares_outstanding == 8133974978
        assert info.date == datetime.date(2026, 2, 27)

    def test_holdings_count(self):
        _, holdings = parse_pcf(VALID_CSV)
        assert len(holdings) == 2

    def test_holding_fields(self):
        _, holdings = parse_pcf(VALID_CSV)
        h = holdings[0]
        assert h.code == "1332"
        assert h.name == "NISSUI CORPORATION"
        assert h.isin == "JP3718800000"
        assert h.exchange == "TSE"
        assert h.currency == "JPY"
        assert h.shares == 7647000.0
        assert h.price == 1506.5

    def test_weights_sum_to_one(self):
        _, holdings = parse_pcf(VALID_CSV)
        total = sum(h.weight for h in holdings)
        assert abs(total - 1.0) < 1e-9

    def test_weight_proportional_to_market_value(self):
        _, holdings = parse_pcf(VALID_CSV)
        mv0 = holdings[0].shares * holdings[0].price
        mv1 = holdings[1].shares * holdings[1].price
        total = mv0 + mv1
        assert abs(holdings[0].weight - mv0 / total) < 1e-9
        assert abs(holdings[1].weight - mv1 / total) < 1e-9


class TestParseMalformedCSV:
    def test_missing_sections(self):
        with pytest.raises(ParseError, match="two sections"):
            parse_pcf("just one line")

    def test_empty_info_section(self):
        csv = "\n\nCode,Name,ISIN,Exchange,Currency,Shares,Price\n1332,X,Y,TSE,JPY,100,200"
        with pytest.raises(ParseError):
            parse_pcf(csv)

    def test_no_valid_holdings(self):
        csv = """\
ETF Code,ETF Name,Fund Cash Component,Shares Outstanding,Fund Date
1306,TOPIX ETF,100.0,1000,20260101

Code,Name,ISIN,Exchange,Currency,Shares Amount,Stock Price
"""
        with pytest.raises(ParseError, match="No valid holdings"):
            parse_pcf(csv)
