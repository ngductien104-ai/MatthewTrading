from __future__ import annotations

import pandas as pd
import pytest

from backtest.loaders.datapro_loader import DataLoader
from vndata import price
from vndata.errors import SourceUnavailable


def _frame(*, instrument: str = "equity", degraded: bool = False) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "open": [30.421], "high": [31.339], "low": [30.325], "close": [30.566],
            "ref_price": [30.325], "volume": [9_299_700], "value": [296_432_615],
            "put_through_volume": [20_080], "prop_buy_volume": [0],
            "active_buy_volume": [4_075_000], "foreign_buy_volume": [1_685_700],
            "listed_shares": [2_272_318_464 if instrument == "equity" else 0],
            "open_interest": [0],
        },
        index=pd.to_datetime(["2021-01-04"]),
    )
    frame.index.name = "trade_date"
    frame.attrs.update(
        source="vnstock_data" if degraded else "datapro",
        degraded=degraded,
        instrument=instrument,
        price_unit="thousand VND" if instrument == "equity" else "index level",
        value_unit="thousand VND" if instrument == "equity" else "million VND",
    )
    if degraded:
        frame.attrs["degraded_reason"] = "DataPro desktop unreachable"
    return frame


def test_default_columns_and_equity_scale_are_unchanged(monkeypatch):
    monkeypatch.setattr("backtest.loaders.datapro_loader.price.ohlcv", lambda *a, **k: _frame())
    out = DataLoader().fetch(["VRE.VN"], "2021-01-04", "2021-01-04")["VRE.VN"]
    assert list(out.columns) == ["open", "high", "low", "close", "volume", "pre_close"]
    assert out.iloc[0]["close"] == pytest.approx(30.566)
    assert out.attrs["instrument"] == "equity"
    assert out.attrs["price_unit"] == "thousand VND"


def test_index_level_is_not_scaled(monkeypatch):
    frame = _frame(instrument="index")
    frame.loc[:, "close"] = 1120.47
    monkeypatch.setattr("backtest.loaders.datapro_loader.price.ohlcv", lambda *a, **k: frame)
    out = DataLoader().fetch(["VNINDEX.VN"], "2021-01-04", "2021-01-04")["VNINDEX.VN"]
    assert out.iloc[0]["close"] == pytest.approx(1120.47)
    assert out.attrs["price_unit"] == "index level"
    assert out.attrs["value_unit"] == "million VND"


def test_fields_unlock_full_datapro_columns_without_changing_default(monkeypatch):
    monkeypatch.setattr("backtest.loaders.datapro_loader.price.ohlcv", lambda *a, **k: _frame())
    fields = ["value", "put_through_volume", "prop_buy_volume", "active_buy_volume", "foreign_buy_volume"]
    out = DataLoader().fetch(["VRE.VN"], "2021-01-04", "2021-01-04", fields=fields)["VRE.VN"]
    assert list(out.columns) == [
        "open", "high", "low", "close", "volume", "pre_close", *fields,
    ]


def test_every_canonical_datapro_field_is_requestable(monkeypatch):
    frame = _frame()
    for column in price.COLUMN_MAP.values():
        if column not in frame:
            frame[column] = 1.0
    monkeypatch.setattr("backtest.loaders.datapro_loader.price.ohlcv", lambda *a, **k: frame)
    fields = [name for name in price.COLUMN_MAP.values() if name not in {
        "open", "high", "low", "close", "volume", "ref_price",
    }]
    out = DataLoader().fetch(["VRE.VN"], "2021-01-04", "2021-01-04", fields=fields)["VRE.VN"]
    assert set(fields).issubset(out.columns)


def test_legacy_foreign_field_alias_still_works(monkeypatch):
    monkeypatch.setattr("backtest.loaders.datapro_loader.price.ohlcv", lambda *a, **k: _frame())
    out = DataLoader().fetch(
        ["VRE.VN"], "2021-01-04", "2021-01-04", fields=["foreign_buy"]
    )["VRE.VN"]
    assert out.iloc[0]["foreign_buy"] == 1_685_700
    assert "foreign_buy_volume" not in out.columns


def test_degraded_fallback_is_loud_at_loader_boundary(monkeypatch):
    monkeypatch.setattr(
        "backtest.loaders.datapro_loader.price.ohlcv", lambda *a, **k: _frame(degraded=True)
    )
    with pytest.raises(SourceUnavailable, match="degraded.*DataPro desktop unreachable"):
        DataLoader().fetch(["VRE.VN"], "2021-01-04", "2021-01-04")


def test_client_failure_is_not_downgraded_to_an_empty_result(monkeypatch):
    def fail(*args, **kwargs):
        raise ConnectionError("DataPro request died after ping")

    monkeypatch.setattr("backtest.loaders.datapro_loader.price.ohlcv", fail)
    with pytest.raises(ConnectionError, match="died after ping"):
        DataLoader().fetch(["VRE.VN"], "2021-01-04", "2021-01-04")


def _schema_gate(broken: set[str]):
    """Serve real frames, but let vndata's own schema gate reject *broken* codes."""
    def ohlcv(code, start, end, **kwargs):
        frame = _frame()
        if code in broken:
            frame = frame.copy()
            frame.loc[frame.index[0], "close"] = float("nan")
            frame.attrs.update(_frame().attrs)
            return price._validate_and_audit(frame, symbol=code, start=start, end=end)
        return frame
    return ohlcv


def test_one_broken_symbol_no_longer_takes_the_whole_universe_down(monkeypatch):
    monkeypatch.setattr(
        "backtest.loaders.datapro_loader.price.ohlcv", _schema_gate({"BAD.VN"})
    )
    loader = DataLoader()
    out = loader.fetch(["VRE.VN", "BAD.VN", "HPG.VN"], "2021-01-04", "2021-01-04")
    assert sorted(out) == ["HPG.VN", "VRE.VN"]


def test_the_dropped_symbol_is_named_with_its_reason(monkeypatch):
    monkeypatch.setattr(
        "backtest.loaders.datapro_loader.price.ohlcv", _schema_gate({"BAD.VN"})
    )
    loader = DataLoader()
    loader.fetch(["VRE.VN", "BAD.VN"], "2021-01-04", "2021-01-04")
    assert [entry["code"] for entry in loader.skipped_symbols] == ["BAD.VN"]
    assert "non-finite" in loader.skipped_symbols[0]["reason"]
    assert "2021-01-04" in loader.skipped_symbols[0]["reason"]


def test_a_clean_run_records_no_skips(monkeypatch):
    monkeypatch.setattr("backtest.loaders.datapro_loader.price.ohlcv", _schema_gate(set()))
    loader = DataLoader()
    loader.fetch(["VRE.VN", "HPG.VN"], "2021-01-04", "2021-01-04")
    assert loader.skipped_symbols == []


def test_the_skip_list_does_not_survive_into_the_next_fetch(monkeypatch):
    """base.py fetches after runner.py already did; a stale skip would double-count."""
    monkeypatch.setattr(
        "backtest.loaders.datapro_loader.price.ohlcv", _schema_gate({"BAD.VN"})
    )
    loader = DataLoader()
    loader.fetch(["BAD.VN"], "2021-01-04", "2021-01-04")
    loader.fetch(["VRE.VN"], "2021-01-04", "2021-01-04")
    assert loader.skipped_symbols == []


def test_a_provenance_failure_still_stops_the_run(monkeypatch):
    """Skipping is for bad numbers, not for a frame that is not from DataPro."""
    monkeypatch.setattr(
        "backtest.loaders.datapro_loader.price.ohlcv", lambda *a, **k: _frame(degraded=True)
    )
    loader = DataLoader()
    with pytest.raises(SourceUnavailable):
        loader.fetch(["VRE.VN", "HPG.VN"], "2021-01-04", "2021-01-04")


def test_engine_turns_a_skip_into_a_run_card_warning():
    from backtest.engines.base import _record_skipped_symbols

    config: dict = {}
    loader = DataLoader()
    loader.skipped_symbols = [{"code": "BAD.VN", "reason": "close: 3 rows non-finite"}]
    _record_skipped_symbols(config, loader)
    warning = config["_run_card_warnings"][0]
    assert warning.startswith("SYMBOL DROPPED: BAD.VN")
    assert "close: 3 rows non-finite" in warning


def test_the_same_skip_is_not_written_twice():
    """runner.py and base.py both fetch; the card should still say it once."""
    from backtest.engines.base import _record_skipped_symbols

    config: dict = {}
    loader = DataLoader()
    loader.skipped_symbols = [{"code": "BAD.VN", "reason": "close: 3 rows non-finite"}]
    _record_skipped_symbols(config, loader)
    _record_skipped_symbols(config, loader)
    assert len(config["_run_card_warnings"]) == 1


def test_a_loader_without_the_attribute_is_left_alone():
    from backtest.engines.base import _record_skipped_symbols

    config: dict = {}
    _record_skipped_symbols(config, object())
    assert "_run_card_warnings" not in config
