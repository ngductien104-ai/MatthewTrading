"""Unit tests for the ``vndata`` truth-source layer.

Every test here is offline. The unit traps are pinned with the exact values
measured against live HPG and TCB FY2025 data on 2026-08-27, so a silent
upstream change that reintroduces a trap fails the suite instead of quietly
corrupting a valuation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from vndata import normalize, price, ta


def _ratio_frame(rows: list[tuple[str, str, str, float]]) -> pd.DataFrame:
    """Build a raw ratio frame with the Categorical dtypes the API really returns."""
    df = pd.DataFrame(rows, columns=["period", "id", "unit", "value"])
    df["period"] = pd.Categorical(df["period"])  # unordered, like upstream
    df["unit"] = pd.Categorical(df["unit"])
    df["id"] = pd.Categorical(df["id"])
    df["name"] = df["id"].astype(str)
    return df


class TestNormalizeRatio:
    def test_fraction_declared_as_percent_is_scaled(self):
        """HPG FY2025 ROE arrives as 0.1269 under a '%' label; it means 12.69%."""
        out = normalize.normalize_ratio(_ratio_frame([("2025", "RT_PRT_ROE", "%", 0.1269059)]))
        assert out.loc[0, "value"] == pytest.approx(12.69059)
        assert out.loc[0, "unit"] == "%"
        assert "fraction" in out.loc[0, "note"]

    def test_dividend_yield_is_already_percent(self):
        """RT_VALUE_DIVIDEND_YIELD is the one '%' field that must NOT be scaled."""
        out = normalize.normalize_ratio(
            _ratio_frame([("2025", "RT_VALUE_DIVIDEND_YIELD", "%", 2.267574)])
        )
        assert out.loc[0, "value"] == pytest.approx(2.267574)

    def test_cost_ratios_lose_their_flipped_sign(self):
        """TCB NPL coverage arrives as -1.2805; the truth is 128.05%."""
        out = normalize.normalize_ratio(
            _ratio_frame([("2025", "RT_BANK_NPL_COVERAGE", "%", -1.280544)])
        )
        assert out.loc[0, "value"] == pytest.approx(128.0544)

    def test_money_field_mislabelled_as_billions(self):
        """RT_VALUE_MARKET_CAP says 'tỷ VNĐ' but stores plain VND."""
        out = normalize.normalize_ratio(
            _ratio_frame([("2025", "RT_VALUE_MARKET_CAP", "tỷ VNĐ", 2.152968e14)])
        )
        assert out.loc[0, "value"] == pytest.approx(2.152968e14)
        assert out.loc[0, "unit"] == "VND"

    def test_broken_fields_become_nan_and_name_the_replacement(self):
        """RT_VALUE_EQUITY returns 0.209 for HPG — unusable, not merely small."""
        out = normalize.normalize_ratio(
            _ratio_frame([("2025", "RT_VALUE_EQUITY", "tỷ VNĐ", 0.2094131)])
        )
        assert np.isnan(out.loc[0, "value"])
        assert "BS_EQUITY" in out.loc[0, "note"]

    def test_zero_means_not_applicable(self):
        """An industrial reports 0.0 for NIM: that is 'n/a', never a measured zero."""
        out = normalize.normalize_ratio(_ratio_frame([("2025", "RT_BANK_NIM", "%", 0.0)]))
        assert np.isnan(out.loc[0, "value"])
        assert "not-applicable" in out.loc[0, "note"]

    def test_nan_is_never_filled(self):
        out = normalize.normalize_ratio(_ratio_frame([("2025", "RT_VALUE_EPS", "VNĐ", float("nan"))]))
        assert np.isnan(out.loc[0, "value"])

    def test_category_header_rows_are_dropped(self):
        out = normalize.normalize_ratio(
            _ratio_frame([
                ("2025", "RT_CAT_PROFITABILITY", "", float("nan")),
                ("2025", "RT_PRT_ROA", "%", 0.064069),
            ])
        )
        assert list(out["id"]) == ["RT_PRT_ROA"]

    def test_period_becomes_sortable(self):
        """Upstream ships an unordered Categorical, so .max() raises on the raw frame."""
        raw = _ratio_frame([("2024", "RT_PRT_ROE", "%", 0.1), ("2025", "RT_PRT_ROE", "%", 0.2)])
        with pytest.raises(TypeError):
            raw["period"].max()
        out = normalize.normalize_ratio(raw)
        assert out["period"].max() == "2025"

    def test_raw_values_are_preserved_for_audit(self):
        out = normalize.normalize_ratio(_ratio_frame([("2025", "RT_PRT_ROE", "%", 0.1269059)]))
        assert out.loc[0, "value_raw"] == pytest.approx(0.1269059)
        assert out.loc[0, "unit_raw"] == "%"

    def test_rejects_a_frame_that_is_not_a_ratio_table(self):
        with pytest.raises(ValueError, match="missing columns"):
            normalize.normalize_ratio(pd.DataFrame({"foo": [1]}))


class TestNormalizeStatement:
    def test_diluted_eps_zero_is_a_not_reported_sentinel(self):
        df = pd.DataFrame({
            "period": pd.Categorical(["2025"]),
            "id": ["IS_DILUTED_EARNINGS_PER_SHARE"],
            "value": [0.0],
        })
        out = normalize.normalize_statement(df)
        assert np.isnan(out.loc[0, "value"])

    def test_ordinary_statement_values_pass_through(self):
        df = pd.DataFrame({
            "period": pd.Categorical(["2025"]),
            "id": ["IS_NET_REVENUE"],
            "value": [1.561161e14],
        })
        out = normalize.normalize_statement(df)
        assert out.loc[0, "value"] == pytest.approx(1.561161e14)
        assert out.loc[0, "period"] == "2025"

    def test_negative_line_items_keep_their_sign(self):
        """Costs are booked negative in the source and must stay negative."""
        df = pd.DataFrame({
            "period": pd.Categorical(["2025"]),
            "id": ["IS_COST_OF_GOODS_SOLD"],
            "value": [-1.316183e14],
        })
        assert normalize.normalize_statement(df).loc[0, "value"] < 0


class TestPivot:
    def test_pivot_sorts_periods_ascending(self):
        long = normalize.normalize_ratio(
            _ratio_frame([
                ("2025", "RT_PRT_ROE", "%", 0.2),
                ("2024", "RT_PRT_ROE", "%", 0.1),
            ])
        )
        wide = normalize.pivot(long)
        assert list(wide.index) == ["2024", "2025"]
        assert wide.loc["2025", "RT_PRT_ROE"] == pytest.approx(20.0)


class TestPriceUnits:
    def _bars(self) -> pd.DataFrame:
        df = pd.DataFrame(
            # VCB, 2026-08-01, straight from the DataPro daily CSV.
            {"close": [59.373], "value": [285499090.0], "volume": [4751600.0]},
            index=pd.to_datetime(["2026-08-01"]),
        )
        df.attrs["price_unit"] = "thousand VND"
        df.attrs["value_unit"] = "thousand VND"
        return df

    def test_to_vnd_scales_price_and_turnover(self):
        out = price.to_vnd(self._bars())
        assert out.loc[out.index[0], "close"] == pytest.approx(59373.0)
        assert out.loc[out.index[0], "value"] == pytest.approx(285499090000.0)
        assert out.attrs["price_unit"] == "VND"

    def test_to_vnd_leaves_volume_alone(self):
        out = price.to_vnd(self._bars())
        assert out.loc[out.index[0], "volume"] == pytest.approx(4751600.0)

    def test_to_vnd_is_idempotent(self):
        once = price.to_vnd(self._bars())
        twice = price.to_vnd(once)
        assert twice.loc[twice.index[0], "close"] == pytest.approx(59373.0)

    def test_turnover_reconciles_against_volume_times_price(self):
        """The 1,000x convention is what makes VAL agree with volume x price."""
        vnd = price.to_vnd(self._bars()).iloc[0]
        implied = vnd["volume"] * vnd["close"]
        assert implied / vnd["value"] == pytest.approx(1.0, rel=0.02)


class TestSymbolHandling:
    @pytest.mark.parametrize(
        "code,expected",
        [("VCB.VN", "VCB"), ("vcb.vn", "VCB"), ("VCB", "VCB"), (" fpt ", "FPT")],
    )
    def test_vn_suffix_is_stripped(self, code, expected):
        assert price._ticker(code) == expected


class TestTaFrame:
    def test_reshape_produces_the_columns_indicator_expects(self):
        bars = pd.DataFrame(
            {"open": [1.0], "high": [2.0], "low": [0.5], "close": [1.5], "volume": [100.0]},
            index=pd.to_datetime(["2026-08-01"]),
        )
        bars.index.name = "trade_date"
        out = ta.to_ta_frame(bars)
        assert list(out.columns) == ["time", "open", "high", "low", "close", "volume"]

    def test_missing_ohlcv_column_is_refused(self):
        bars = pd.DataFrame({"close": [1.5]}, index=pd.to_datetime(["2026-08-01"]))
        bars.index.name = "trade_date"
        with pytest.raises(ValueError, match="missing columns required for TA"):
            ta.to_ta_frame(bars)


class TestSourceMap:
    def test_price_classes_route_to_datapro(self):
        import vndata

        for key in ("ohlcv", "foreign_flow", "proprietary_flow", "reference_price"):
            assert vndata.SOURCE_MAP[key] == "datapro"

    def test_fundamental_classes_route_to_vnstock_data(self):
        import vndata

        for key in ("income_statement", "ratios", "macro", "industry_classification"):
            assert vndata.SOURCE_MAP[key] == "vnstock_data"

    def test_free_tier_is_confined_to_the_documented_carve_out(self):
        import vndata

        free = {k for k, v in vndata.SOURCE_MAP.items() if v == "vnstock (free)"}
        assert free == {"capital_history", "insider_trading", "ownership"}
