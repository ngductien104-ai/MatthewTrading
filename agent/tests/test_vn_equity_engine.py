"""Regression tests for Vietnam-equity market rules."""

from __future__ import annotations

import pandas as pd

from backtest.engines.vn_equity import VNEquityEngine


def _run_engine(session_dates: list[str], entry_idx: int) -> VNEquityEngine:
    dates = pd.DatetimeIndex(session_dates)
    bars = pd.DataFrame(
        {
            "open": range(100, 100 + len(dates)),
            "close": range(100, 100 + len(dates)),
            "pre_close": range(100, 100 + len(dates)),
        },
        index=dates,
    )
    symbol = "VNINDEX.VN"
    weights = [0.0] * len(dates)
    weights[entry_idx] = 1.0
    target = pd.DataFrame({symbol: weights}, index=dates)
    engine = VNEquityEngine({"initial_cash": 100_000_000, "slippage": 0.0})
    engine._execute_bars(
        dates,
        {symbol: bars},
        pd.DataFrame({symbol: bars["close"]}, index=dates),
        target,
        [symbol],
    )
    return engine


def test_tet_2024_counts_observed_bars_not_weekdays() -> None:
    """T+2 follows real Tet sessions: weekdays say 6, observed bars say 1.

    The VNINDEX DataPro calendar jumps from 07/02/2024 to 15/02/2024.
    Weekday counting would sell immediately on 15/02; the engine must reject
    that signal and wait for the second observed session on 16/02.
    """
    engine = _run_engine([
        "2024-02-05",
        "2024-02-06",
        "2024-02-07",
        "2024-02-15",
        "2024-02-16",
        "2024-02-19",
    ], entry_idx=2)

    assert len(engine.trades) == 1
    trade = engine.trades[0]
    assert trade.entry_time == pd.Timestamp("2024-02-07")
    assert trade.exit_time == pd.Timestamp("2024-02-16")
    assert trade.holding_bars == 2
    assert trade.exit_reason == "signal"


def test_normal_week_t_plus_two_is_unchanged() -> None:
    """Without a closure, two observed bars equal the former weekday count."""
    engine = _run_engine([
        "2024-02-19",
        "2024-02-20",
        "2024-02-21",
        "2024-02-22",
    ], entry_idx=0)

    assert len(engine.trades) == 1
    trade = engine.trades[0]
    assert trade.entry_time == pd.Timestamp("2024-02-19")
    assert trade.exit_time == pd.Timestamp("2024-02-21")
    assert trade.holding_bars == 2
    assert trade.exit_reason == "signal"
