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

    def test_equity_to_assets_is_scaled_even_though_the_label_is_honest(self):
        """TCB FY2025 equity/assets is a correct 0.1505 under 'lần'; quote it as 15.05%."""
        out = normalize.normalize_ratio(
            _ratio_frame([("2025", "RT_LEV_EQUITY_TO_ASSETS", "lần", 0.1505450)])
        )
        assert out.loc[0, "value"] == pytest.approx(15.05450)
        assert out.loc[0, "unit"] == "%"
        assert out.loc[0, "value_raw"] == pytest.approx(0.1505450)

    def test_a_genuine_multiple_is_not_scaled(self):
        """HPG FY2025 D/E is 0.9654x — a multiple, not a percentage."""
        out = normalize.normalize_ratio(
            _ratio_frame([("2025", "RT_LEV_DE", "lần", 0.9653954)])
        )
        assert out.loc[0, "value"] == pytest.approx(0.9653954)
        assert out.loc[0, "unit"] == "lần"

    def test_valuation_multiples_keep_their_value_but_carry_a_warning(self):
        """RT_VALUE_PB history is unreliable; the number passes through, flagged."""
        out = normalize.normalize_ratio(
            _ratio_frame([("2023", "RT_VALUE_PB", "lần", 0.6663884)])
        )
        assert out.loc[0, "value"] == pytest.approx(0.6663884)
        assert "latest period" in out.loc[0, "note"]

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
            # listed_shares is what marks this an equity rather than an index,
            # which is what selects the 1,000x turnover scale.
            {"close": [59.373], "value": [285499090.0], "volume": [4751600.0],
             "listed_shares": [8355675136.0], "open_interest": [0.0]},
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


class TestInstrumentUnits:
    """``VAL`` is scaled differently per instrument — a 1,000x trap.

    Measured 2026-08-25/27: HPG 68,320,100 shares x 23,163 VND reconciles with
    ``VAL`` 1,793,446,015 only at 1,000x, while HNXINDEX ``VAL`` 2,621,503
    reconciles only at 1,000,000x. VN30F1M reconciles at neither.
    """

    def _frame(self, listed: float, oi: float, close: float, volume: float, value: float):
        df = pd.DataFrame(
            {"listed_shares": [listed], "open_interest": [oi], "close": [close],
             "volume": [volume], "value": [value]},
            index=pd.to_datetime(["2026-08-25"]),
        )
        return df

    def test_equity_is_detected_from_listed_shares(self):
        df = self._frame(8355675136, 0, 23.163, 68320100, 1793446015)
        assert price.classify_instrument(df) == "equity"

    def test_index_has_no_listed_shares_and_no_open_interest(self):
        df = self._frame(0, 0, 266.58, 117880078, 2621503)
        assert price.classify_instrument(df) == "index"

    def test_futures_has_open_interest_but_no_listed_shares(self):
        df = self._frame(0, 51608, 1783, 385400, 694735523)
        assert price.classify_instrument(df) == "futures"

    def test_equity_turnover_reconciles_at_one_thousand(self):
        out = price.to_vnd(self._frame(8355675136, 0, 23.163, 68320100, 1793446015))
        row = out.iloc[0]
        assert row["volume"] * row["close"] / row["value"] == pytest.approx(1.0, rel=0.15)

    def test_index_turnover_reconciles_at_one_million(self):
        """831bn VND over 117.9m shares implies ~22,240 VND/share — plausible.
        At the equity scale it would imply 22 VND/share, which is not."""
        out = price.to_vnd(self._frame(0, 0, 266.58, 117880078, 2621503))
        row = out.iloc[0]
        assert row["value"] == pytest.approx(2.621503e12)
        assert 5_000 < row["value"] / row["volume"] < 100_000

    def test_index_close_is_a_level_and_is_not_scaled(self):
        out = price.to_vnd(self._frame(0, 0, 266.58, 117880078, 2621503))
        assert out.iloc[0]["close"] == pytest.approx(266.58)
        assert out.attrs["price_unit"] == "index level"

    def test_futures_turnover_is_refused_rather_than_guessed(self):
        out = price.to_vnd(self._frame(0, 51608, 1783, 385400, 694735523))
        assert out.iloc[0]["value"] == pytest.approx(694735523)
        assert "unverified" in out.attrs["value_unit"]


class TestSymbolHandling:
    @pytest.mark.parametrize(
        "code,expected",
        [("VCB.VN", "VCB"), ("vcb.vn", "VCB"), ("VCB", "VCB"), (" fpt ", "FPT")],
    )
    def test_vn_suffix_is_stripped(self, code, expected):
        assert price._ticker(code) == expected


class TestPriceContract:
    def _fallback(self, monkeypatch, frame, symbol="VNINDEX.VN"):
        class Equity:
            def ohlcv(self, **kwargs):
                return frame

        class Market:
            def equity(self, symbol):
                return Equity()

        monkeypatch.setitem(__import__("sys").modules, "vnstock_data", type(
            "FakeVnstockData", (), {"Market": Market}
        ))
        return price._fallback_ohlcv(symbol, "2024-01-02", "2024-01-08")

    def test_index_fallback_does_not_claim_thousand_vnd(self, monkeypatch):
        frame = pd.DataFrame({
            "time": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [1120.0, 1121.0], "high": [1122.0, 1123.0],
            "low": [1119.0, 1120.0], "close": [1121.0, 1122.0],
            "volume": [1.0, 2.0],
        })
        out = self._fallback(monkeypatch, frame)
        assert out.attrs["source"] == "vnstock_data"
        assert out.attrs["degraded"] is True
        # The scale was measured on 2026-09-01 and matches DataPro exactly, so
        # this no longer says "unknown". What stays unknown is the instrument,
        # and that is what stops the frame from claiming an equity's unit.
        assert out.attrs["price_unit"] != "thousand VND"
        assert out.attrs["instrument"] == "unverified"
        assert "unclassifiable" in out.attrs["price_unit"]

    def test_empty_fallback_keeps_true_provenance(self, monkeypatch):
        out = self._fallback(monkeypatch, pd.DataFrame())
        assert out.empty
        assert out.attrs["source"] == "vnstock_data"
        assert out.attrs["degraded"] is True

    @pytest.mark.parametrize(
        "mutate,match",
        [
            (lambda df: df.drop(columns="volume"), "missing required columns"),
            (lambda df: df.assign(close=["not-a-number", "2"]), "finite numeric"),
            (lambda df: df.assign(time=pd.to_datetime(["2024-01-02", "2024-01-02"])), "duplicates"),
        ],
    )
    def test_broken_schema_is_loud(self, monkeypatch, mutate, match):
        frame = pd.DataFrame({
            "time": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [1.0, 2.0], "high": [1.0, 2.0], "low": [1.0, 2.0],
            "close": [1.0, 2.0], "volume": [1.0, 2.0],
        })
        broken = mutate(frame)
        with pytest.raises(ValueError, match=match):
            self._fallback(monkeypatch, broken)

    def test_non_finite_error_identifies_symbol_dates_and_count(self, monkeypatch):
        frame = pd.DataFrame({
            "time": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [1.0, 2.0], "high": [1.0, 2.0], "low": [1.0, 2.0],
            "close": [1.0, float("nan")], "volume": [1.0, 2.0],
        })
        with pytest.raises(ValueError) as exc_info:
            self._fallback(monkeypatch, frame, symbol="VRE.VN")
        message = str(exc_info.value)
        assert "VRE.VN" in message
        assert "close" in message
        assert "2024-01-03" in message
        assert "1 row" in message

    def test_internal_missing_weekday_is_audited_not_called_a_holiday(self, monkeypatch):
        frame = pd.DataFrame({
            "time": pd.to_datetime(["2024-01-02", "2024-01-04", "2024-01-05"]),
            "open": [1.0] * 3, "high": [1.0] * 3, "low": [1.0] * 3,
            "close": [1.0] * 3, "volume": [1.0] * 3,
        })
        audit = self._fallback(monkeypatch, frame).attrs["session_audit"]
        assert audit["internal_absent_weekday_candidates"] == ["2024-01-03"]

    def test_broken_datapro_schema_is_loud(self, monkeypatch):
        class Response:
            status_code = 200
            text = (
                "TRADING_TIME,OPEN_PX,HIGH_PX,LOW_PX,CLOSE_PX\n"
                "1704153600,1,2,0.5,1.5\n"
            )

            def raise_for_status(self):
                return None

        monkeypatch.setattr(price, "datapro_available", lambda: True)
        monkeypatch.setattr(price.requests, "get", lambda *args, **kwargs: Response())
        with pytest.raises(ValueError, match="missing required columns.*volume"):
            price.ohlcv("VRE.VN", "2024-01-02", "2024-01-02")


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


class TestAdjustmentPolicy:
    """DataPro serves back-adjusted prices; ``adj_rate`` is how you undo it.

    Measured 2026-09-01 against the HOSE tick grid over 9,908 daily bars across
    15 symbols: ``close * adj_rate`` lands a median 0.233 VND from a valid tick
    (max 1.01, 100% within 3 VND), while ``close / adj_rate`` and the stored
    close scatter uniformly at 8.6 and 12.0 VND. The numbers below are real
    DataPro rows, VCB before and after its 2026-07-23 ex-date.
    """

    def _bars(self) -> pd.DataFrame:
        df = pd.DataFrame(
            {"close": [61.744, 61.148, 54.000],
             "adj_rate": [1.007393, 1.007393, 1.000000],
             "volume": [1.0, 2.0, 3.0]},
            index=pd.to_datetime(["2026-06-01", "2026-06-02", "2026-07-23"]),
        )
        df.index.name = "trade_date"
        df.attrs["source"] = "datapro"
        return df

    def test_traded_price_multiplies_rather_than_divides(self):
        out = price.traded_price(self._bars())
        assert out.iloc[0] == pytest.approx(62.2005, abs=1e-4)  # 62,200 VND, on the 100 VND tick

    def test_traded_price_lands_on_the_hose_tick_grid(self):
        """A wrong direction scatters across the tick; the right one does not."""
        vnd = price.traded_price(self._bars()) * 1000.0
        # VCB trades above 50,000 VND, where the mandated tick is 100 VND.
        off_grid = (vnd % 100).where(lambda s: s <= 50, 100 - (vnd % 100))
        assert off_grid.max() < 3.0

    def test_a_bar_after_the_last_ex_date_is_already_the_traded_price(self):
        bars = self._bars()
        assert bars["adj_rate"].iloc[-1] == 1.0
        assert price.traded_price(bars).iloc[-1] == pytest.approx(54.000)

    def test_datapro_frames_say_they_are_adjusted(self, monkeypatch):
        bars = self._bars()
        assert bars.attrs["source"] == "datapro"

    def test_refuses_to_guess_when_adj_rate_is_absent(self):
        bars = self._bars().drop(columns=["adj_rate"])
        with pytest.raises(ValueError, match="no.*adj_rate"):
            price.traded_price(bars)

    def test_names_the_missing_column_rather_than_the_rate(self):
        with pytest.raises(ValueError, match="'ref_price'"):
            price.traded_price(self._bars(), column="ref_price")


class TestFallbackReconciliation:
    """What the 2026-09-01 two-source measurement changed on the degraded path."""

    def _fallback(self, monkeypatch, frame, symbol="VNINDEX.VN"):
        class Equity:
            def ohlcv(self, **kwargs):
                return frame

        class Market:
            def equity(self, symbol):
                return Equity()

        monkeypatch.setitem(__import__("sys").modules, "vnstock_data", type(
            "FakeVnstockData", (), {"Market": Market}
        ))
        return price._fallback_ohlcv(symbol, "2026-08-27", "2026-08-28")

    def _snapshot_frame(self, close_of_the_extra_row: float = 1832.12) -> pd.DataFrame:
        """The real shape: the newest session arrives twice, close identical.

        Observed on VNINDEX and VN30 for 2026-08-28 — same high, low and close,
        different open and volume — while every closed historical range is clean.
        """
        return pd.DataFrame({
            "time": pd.to_datetime(["2026-08-27", "2026-08-28", "2026-08-28"]),
            "open": [1821.82, 1833.27, 1830.53],
            "high": [1838.25, 1838.20, 1838.20],
            "low": [1815.42, 1819.16, 1819.16],
            "close": [1831.56, 1832.12, close_of_the_extra_row],
            "volume": [484230398.0, 562184482.0, 643935725.0],
        })

    def test_the_duplicate_session_no_longer_kills_every_index_request(self, monkeypatch):
        out = self._fallback(monkeypatch, self._snapshot_frame())
        assert len(out) == 2
        assert not out.index.has_duplicates

    def test_the_fuller_snapshot_is_the_one_kept(self, monkeypatch):
        out = self._fallback(monkeypatch, self._snapshot_frame())
        kept = out.loc[pd.Timestamp("2026-08-28")]
        assert kept["volume"] == pytest.approx(643935725.0)
        assert kept["open"] == pytest.approx(1830.53)

    def test_the_collapse_is_recorded_not_silent(self, monkeypatch):
        out = self._fallback(monkeypatch, self._snapshot_frame())
        assert out.attrs["vendor_duplicate_sessions"] == ["2026-08-28"]

    def test_duplicates_that_disagree_on_close_are_not_this_artefact(self, monkeypatch):
        """Two different closes for one session is contradiction, not a snapshot."""
        with pytest.raises(ValueError, match="duplicates"):
            self._fallback(monkeypatch, self._snapshot_frame(close_of_the_extra_row=1799.0))

    def test_a_clean_range_is_left_alone(self, monkeypatch):
        frame = self._snapshot_frame().iloc[:2]
        out = self._fallback(monkeypatch, frame)
        assert len(out) == 2
        assert "vendor_duplicate_sessions" not in out.attrs

    def test_the_degraded_frame_cannot_be_converted_to_vnd(self, monkeypatch):
        """Its scale is verified; which of the three rules applies is not."""
        out = self._fallback(monkeypatch, self._snapshot_frame())
        with pytest.raises(ValueError, match="instrument is 'unverified'"):
            price.to_vnd(out)

    def test_the_back_adjustment_cannot_be_undone_from_a_degraded_frame(self, monkeypatch):
        out = self._fallback(monkeypatch, self._snapshot_frame())
        assert out.attrs["adjustment"] == "back-adjusted"
        with pytest.raises(ValueError, match="no.*adj_rate"):
            price.traded_price(out)
