"""Integration tests for ranking (always live from Rakuten)."""

import pandas as pd
import pytest

from pyjpx_etf import ranking


@pytest.mark.integration
class TestRanking:
    def test_ranking_default(self):
        df = ranking()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "code" in df.columns
        assert "return" in df.columns
        assert "fee" in df.columns

    def test_ranking_1y_top20(self):
        df = ranking("1y", n=20)
        assert len(df) == 20

    def test_ranking_worst5(self):
        df = ranking("1m", n=-5)
        assert len(df) == 5
        # worst = ascending, so first return should be lowest
        assert df["return"].iloc[0] <= df["return"].iloc[-1]

    def test_ranking_all(self):
        df = ranking("1m", n=0)
        assert len(df) > 100  # there are hundreds of TSE ETFs

    def test_ranking_invalid_period(self):
        with pytest.raises(ValueError):
            ranking("99y")

    @pytest.mark.parametrize("period", ["1m", "3m", "6m", "1y", "3y", "5y", "10y", "ytd"])
    def test_all_periods(self, period):
        df = ranking(period, n=3)
        assert isinstance(df, pd.DataFrame)
        assert len(df) <= 3
