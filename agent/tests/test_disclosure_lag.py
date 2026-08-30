"""One point-in-time disclosure policy shared by vndata and VN loaders."""

from __future__ import annotations

import pandas as pd
import pytest

from backtest.loaders import vnstock_data_fundamentals, vnstock_fundamentals
from vndata import fundamental


def test_vn_loaders_share_vndata_disclosure_lag_policy() -> None:
    assert fundamental.DISCLOSURE_LAG_DAYS == {"year": 90, "quarter": 45}
    assert vnstock_fundamentals.vndata_fundamental is fundamental
    assert vnstock_data_fundamentals.vndata_fundamental is fundamental
    with pytest.raises(TypeError):
        fundamental.DISCLOSURE_LAG_DAYS["year"] = 0


def test_both_loaders_preserve_synthesised_disclosure_dates() -> None:
    free = object.__new__(vnstock_fundamentals.VNStockFundamentalProvider)
    free._fetch_statement = lambda symbol, table, method: pd.DataFrame(
        {"item_id": ["net_profit"], "2024": [123.0]}
    )
    annual = free.query_fundamentals(
        "income", ["VCB.VN"], as_of="2025-12-31", fields=["net_profit"]
    )

    sponsor = object.__new__(vnstock_data_fundamentals.VNStockDataFundamentalProvider)

    assert annual.loc[0, "ann_date"] == pd.Timestamp("2025-03-31")
    assert sponsor._ann_date("2024") == pd.Timestamp("2025-03-31")
    assert sponsor._ann_date("2024-Q1") == pd.Timestamp("2024-05-15")
