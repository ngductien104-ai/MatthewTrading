"""Unit tests for the ``vndata`` truth-source layer.

Every test here is offline. Since 13/11/2026 the layer has two truth sources:
DataPro (price, flow, symbol list) reachable from Python, and VNDIRECT MCP
(fundamentals, macro, company data) reachable only from an MCP client. These
tests pin both halves: DataPro's unit traps, and the loud failure for every
class that moved to VNDIRECT.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import vndata
from vndata import fundamental, macro, price, reference, ta
from vndata.errors import SourceUnavailable


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
        """Run a raw frame through the same schema gate DataPro frames pass."""
        df = frame.rename(columns={"time": "trade_date"}).set_index("trade_date").sort_index()
        return price._validate_and_audit(df, symbol=symbol, start="2024-01-02", end="2024-01-08")

    def test_datapro_down_raises_instead_of_switching_source(self, monkeypatch):
        monkeypatch.setattr(price, "datapro_available", lambda *a, **k: False)
        with pytest.raises(SourceUnavailable, match="no fallback"):
            price.ohlcv("HPG.VN", "2026-01-02", "2026-01-08")
        with pytest.raises(SourceUnavailable):
            price.ohlcv("HPG.VN", "2026-01-02", "2026-01-08", allow_fallback=True)

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
        for key in ("ohlcv", "foreign_flow", "proprietary_flow", "reference_price", "symbol_list"):
            assert vndata.SOURCE_MAP[key] == "datapro"

    def test_fundamental_classes_route_to_vndirect(self):
        for key in ("income_statement", "ratios", "macro", "shareholders", "capital_history"):
            assert vndata.SOURCE_MAP[key] == "vndirect_mcp"

    def test_no_class_routes_to_vnstock(self):
        assert not [k for k, v in vndata.SOURCE_MAP.items() if "vnstock" in v]


class TestMovedToVndirect:
    @pytest.mark.parametrize("call", [
        lambda: fundamental.statement("HPG"),
        lambda: fundamental.ratios("HPG.VN"),
        lambda: fundamental.is_bank("VCB"),
        lambda: macro.economy("cpi"),
        lambda: reference.company("FPT"),
        lambda: reference.events("FPT"),
        lambda: vndata.corporate.capital_history("HPG"),
        lambda: vndata.news.company_news("HPG"),
    ])
    def test_raises_and_names_vndirect(self, call):
        with pytest.raises(SourceUnavailable, match="VNDIRECT MCP"):
            call()

    def test_disclosure_lag_policy_survives_the_source_change(self):
        assert fundamental.DISCLOSURE_LAG_DAYS == {"year": 90, "quarter": 45}

    def test_no_vnstock_import_anywhere_in_the_layer(self):
        from pathlib import Path

        root = Path(vndata.__file__).parent
        offenders = []
        for path in root.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "import vnstock" in text or "from vnstock" in text:
                offenders.append(path.name)
        assert offenders == []


class TestReferenceSnapshots:
    @pytest.fixture(autouse=True)
    def _tmp_snapshots(self, tmp_path, monkeypatch):
        monkeypatch.setattr(reference, "SNAPSHOT_DIR", tmp_path)
        monkeypatch.setattr(reference, "CLASSIFICATION_FILE", tmp_path / "icb_classification.csv")
        monkeypatch.setattr(reference, "INDEX_MEMBERS_FILE", tmp_path / "index_members.json")

    def test_missing_snapshot_is_loud(self):
        with pytest.raises(SourceUnavailable, match="VNDIRECT MCP"):
            reference.classification()
        with pytest.raises(SourceUnavailable, match="VN30"):
            reference.symbols_by_group("VN30")

    def test_classification_round_trip_keeps_codes_four_digits(self):
        reference.save_classification(
            pd.DataFrame({"symbol": ["vcb", "HPG"], "icb_code_lv2": [8300, "1700"],
                          "icb_name_lv2": ["Banks", "Basic Resources"]}),
            source="vndirect:test", as_of="2026-11-13")
        out = reference.classification()
        assert out.set_index("symbol")["icb_code_lv2"].to_dict() == {"HPG": "1700", "VCB": "8300"}
        assert out.attrs["as_of"] == "2026-11-13"
        assert out.attrs["source"] == "vndirect:test"

    def test_duplicate_symbols_are_refused(self):
        with pytest.raises(ValueError, match="duplicate"):
            reference.save_classification(
                pd.DataFrame({"symbol": ["VCB", "VCB"], "icb_code_lv2": ["8300", "8300"],
                              "icb_name_lv2": ["Banks", "Banks"]}), source="t")

    def test_index_members_round_trip_returns_a_symbol_series(self):
        reference.save_index_members("vn30", ["FPT.VN", "hpg", "FPT"], source="vndirect:test",
                                     as_of="2026-11-13")
        out = reference.symbols_by_group("VN30")
        assert isinstance(out, pd.Series) and out.name == "symbol"
        assert out.tolist() == ["FPT", "HPG"]
        assert out.attrs["as_of"] == "2026-11-13"

    def test_symbols_reads_datapro_and_maps_hsx_to_hose(self, monkeypatch):
        csv = "\n".join([
            "SYMBOL,NAME,NAME_EN,EXCHANGE,TYPE,SHARES_OUT",
            "HPG,Hoa Phat,Hoa Phat,HSX,STOCK,100",
            "E1VFVN30,ETF,ETF,HSX,ETF,5",
            "VNINDEX,VN-Index,VN-Index,HSX,IDX,0",
        ])
        monkeypatch.setattr(reference, "_symbols_csv", lambda: csv)
        assert reference.equities()[["symbol", "exchange"]].values.tolist() == [["HPG", "HOSE"]]
        assert reference.etfs()["symbol"].tolist() == ["E1VFVN30"]


class TestLocalIndicators:
    def _bars(self, closes):
        n = len(closes)
        return pd.DataFrame({"open": closes, "high": [c + 1 for c in closes],
                             "low": [c - 1 for c in closes], "close": closes,
                             "volume": [100.0] * n},
                            index=pd.date_range("2026-01-01", periods=n))

    def test_rsi_is_100_when_price_only_rises(self):
        ind = ta.from_frame(self._bars([float(i) for i in range(1, 40)]))
        assert ind.momentum.rsi(14).iloc[-1] == pytest.approx(100.0)

    def test_rsi_matches_wilder_reference(self):
        # Wilder's 14-day worked example: the first RSI on these closes is 70.53.
        closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
                  46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
        rsi = ta.from_frame(self._bars(closes)).momentum.rsi(14).iloc[-1]
        assert rsi == pytest.approx(70.53, abs=0.1)

    def test_sma_and_bbands_share_a_midline(self):
        ind = ta.from_frame(self._bars([float(i % 7) for i in range(60)]))
        assert ind.trend.sma(20).iloc[-1] == pytest.approx(ind.volatility.bbands(20)["mid"].iloc[-1])

    def test_atr_of_a_flat_two_point_range_is_two(self):
        # high - low = 2 every bar and no gaps -> true range 2.
        ind = ta.from_frame(self._bars([10.0] * 40))
        assert ind.volatility.atr(14).iloc[-1] == pytest.approx(2.0)


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


def test_rss_published_keeps_colon_offset():
    """TinnhanhCK ghi '+07:00'; truoc 12/10/2026 bi doc thanh UTC, lech 7 gio."""
    import xml.etree.ElementTree as ET
    from datetime import timedelta

    from vndata.news import _published

    def when(raw):
        return _published(ET.fromstring(f"<item><pubDate>{raw}</pubDate></item>"))

    assert when("Mon, 12 Oct 2026 15:48:54 +07:00").utcoffset() == timedelta(hours=7)
    assert when("Mon, 12 Oct 2026 15:48:54 +0700").utcoffset() == timedelta(hours=7)
    assert when("Mon, 12 Oct 2026 08:27:49 GMT").utcoffset() == timedelta(0)
