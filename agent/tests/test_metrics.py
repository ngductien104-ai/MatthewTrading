"""Tests for backtest metrics calculation.

Validates:
  - bars_per_year annualization
  - win_rate_and_stats
  - by_symbol_stats / by_exit_reason_stats
  - calc_metrics (Sharpe, drawdown, Sortino, Calmar, etc.)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest.metrics import (
    by_exit_reason_stats,
    by_symbol_stats,
    calc_bars_per_year,
    calc_metrics,
    win_rate_and_stats,
)
from backtest.models import TradeRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trade(
    symbol: str = "X",
    pnl: float = 100.0,
    direction: int = 1,
    exit_reason: str = "signal",
    holding_bars: int = 5,
) -> TradeRecord:
    return TradeRecord(
        symbol=symbol,
        direction=direction,
        entry_price=100.0,
        exit_price=100.0 + pnl / 100,
        entry_time=pd.Timestamp("2025-01-01"),
        exit_time=pd.Timestamp("2025-01-06"),
        size=100.0,
        leverage=1.0,
        pnl=pnl,
        pnl_pct=pnl / 100,
        exit_reason=exit_reason,
        holding_bars=holding_bars,
        commission=1.0,
    )


# ---------------------------------------------------------------------------
# calc_bars_per_year
# ---------------------------------------------------------------------------


class TestBarsPerYear:
    def test_daily_tushare(self) -> None:
        assert calc_bars_per_year("1D", "tushare") == 252

    def test_daily_okx(self) -> None:
        assert calc_bars_per_year("1D", "okx") == 365

    def test_minute_tushare(self) -> None:
        # 252 trading days × 240 minutes/day = 60480
        assert calc_bars_per_year("1m", "tushare") == 252 * 240

    def test_hourly_okx(self) -> None:
        # 365 days × 24 hours/day = 8760
        assert calc_bars_per_year("1H", "okx") == 365 * 24

    def test_minute_mootdx(self) -> None:
        # mootdx is A-share: 252 trading days × 240 minutes/day (regression —
        # previously fell back to bars_per_day=1, mis-annualising intraday vol)
        assert calc_bars_per_year("1m", "mootdx") == 252 * 240

    def test_minute_futu(self) -> None:
        # futu is equity (HK + A-share): same equity annualisation as akshare
        assert calc_bars_per_year("1m", "futu") == 252 * 240

    def test_unknown_source(self) -> None:
        # Falls back to 252 trading days
        assert calc_bars_per_year("1D", "unknown") == 252

    def test_unknown_interval(self) -> None:
        # Falls back to 1 bar/day
        assert calc_bars_per_year("2H", "tushare") == 252


# ---------------------------------------------------------------------------
# win_rate_and_stats
# ---------------------------------------------------------------------------


class TestWinRateAndStats:
    def test_all_winners(self) -> None:
        trades = [_trade(pnl=100), _trade(pnl=200), _trade(pnl=50)]
        stats = win_rate_and_stats(trades)
        assert stats["win_rate"] == 1.0
        assert stats["max_consecutive_loss"] == 0

    def test_all_losers(self) -> None:
        trades = [_trade(pnl=-100), _trade(pnl=-200)]
        stats = win_rate_and_stats(trades)
        assert stats["win_rate"] == 0.0
        assert stats["max_consecutive_loss"] == 2

    def test_mixed(self) -> None:
        trades = [_trade(pnl=100), _trade(pnl=-50), _trade(pnl=200)]
        stats = win_rate_and_stats(trades)
        assert stats["win_rate"] == pytest.approx(2 / 3)
        assert stats["max_consecutive_loss"] == 1

    def test_profit_factor(self) -> None:
        trades = [_trade(pnl=300), _trade(pnl=-100)]
        stats = win_rate_and_stats(trades)
        assert stats["profit_factor"] == pytest.approx(3.0)

    def test_profit_loss_ratio(self) -> None:
        trades = [_trade(pnl=200), _trade(pnl=-100)]
        stats = win_rate_and_stats(trades)
        assert stats["profit_loss_ratio"] == pytest.approx(2.0)

    def test_empty_trades(self) -> None:
        stats = win_rate_and_stats([])
        assert stats["win_rate"] == 0.0
        assert stats["profit_factor"] == 0.0

    def test_consecutive_losses(self) -> None:
        trades = [
            _trade(pnl=100),
            _trade(pnl=-10),
            _trade(pnl=-20),
            _trade(pnl=-30),
            _trade(pnl=50),
            _trade(pnl=-5),
        ]
        stats = win_rate_and_stats(trades)
        assert stats["max_consecutive_loss"] == 3

    def test_avg_holding_bars(self) -> None:
        trades = [_trade(holding_bars=5), _trade(holding_bars=10), _trade(holding_bars=15)]
        stats = win_rate_and_stats(trades)
        assert stats["avg_holding_bars"] == 10.0


# ---------------------------------------------------------------------------
# by_symbol_stats
# ---------------------------------------------------------------------------


class TestBySymbolStats:
    def test_single_symbol(self) -> None:
        trades = [_trade("AAPL", 100), _trade("AAPL", -50)]
        stats = by_symbol_stats(trades)
        assert "AAPL" in stats
        assert stats["AAPL"]["count"] == 2
        assert stats["AAPL"]["total_pnl"] == 50.0
        assert stats["AAPL"]["win_rate"] == 0.5

    def test_multiple_symbols(self) -> None:
        trades = [_trade("A", 100), _trade("B", -50), _trade("A", 200)]
        stats = by_symbol_stats(trades)
        assert stats["A"]["count"] == 2
        assert stats["B"]["count"] == 1

    def test_empty(self) -> None:
        assert by_symbol_stats([]) == {}


# ---------------------------------------------------------------------------
# by_exit_reason_stats
# ---------------------------------------------------------------------------


class TestByExitReasonStats:
    def test_single_reason(self) -> None:
        trades = [_trade(exit_reason="signal", pnl=100), _trade(exit_reason="signal", pnl=-50)]
        stats = by_exit_reason_stats(trades)
        assert stats["signal"]["count"] == 2
        assert stats["signal"]["total_pnl"] == 50.0

    def test_multiple_reasons(self) -> None:
        trades = [
            _trade(exit_reason="signal", pnl=100),
            _trade(exit_reason="liquidation", pnl=-500),
            _trade(exit_reason="end_of_backtest", pnl=50),
        ]
        stats = by_exit_reason_stats(trades)
        assert len(stats) == 3
        assert stats["liquidation"]["total_pnl"] == -500.0

    def test_empty(self) -> None:
        assert by_exit_reason_stats([]) == {}


# ---------------------------------------------------------------------------
# calc_metrics
# ---------------------------------------------------------------------------


class TestCalcMetrics:
    def _flat_equity(self) -> pd.Series:
        """Equity that stays flat at 1M (zero return)."""
        dates = pd.bdate_range("2025-01-01", periods=252)
        return pd.Series(1_000_000.0, index=dates)

    def _growing_equity(self) -> pd.Series:
        """Equity that grows linearly from 1M to 1.2M (20% return)."""
        dates = pd.bdate_range("2025-01-01", periods=252)
        return pd.Series(np.linspace(1_000_000, 1_200_000, 252), index=dates)

    def _declining_equity(self) -> pd.Series:
        """Equity that declines from 1M to 800K (-20%)."""
        dates = pd.bdate_range("2025-01-01", periods=252)
        return pd.Series(np.linspace(1_000_000, 800_000, 252), index=dates)

    def test_total_return(self) -> None:
        eq = self._growing_equity()
        m = calc_metrics(eq, [], 1_000_000, 252)
        assert m["total_return"] == pytest.approx(0.2, rel=0.01)

    def test_negative_return(self) -> None:
        eq = self._declining_equity()
        m = calc_metrics(eq, [], 1_000_000, 252)
        assert m["total_return"] < 0

    def test_max_drawdown_negative(self) -> None:
        eq = self._declining_equity()
        m = calc_metrics(eq, [], 1_000_000, 252)
        assert m["max_drawdown"] < 0

    def test_flat_equity_zero_return(self) -> None:
        eq = self._flat_equity()
        m = calc_metrics(eq, [], 1_000_000, 252)
        assert m["total_return"] == pytest.approx(0.0)

    def test_sharpe_positive_for_growth(self) -> None:
        eq = self._growing_equity()
        m = calc_metrics(eq, [], 1_000_000, 252)
        assert m["sharpe"] > 0

    def test_trade_count(self) -> None:
        eq = self._growing_equity()
        trades = [_trade(pnl=100), _trade(pnl=-50)]
        m = calc_metrics(eq, trades, 1_000_000, 252)
        assert m["trade_count"] == 2
        assert m["win_rate"] == 0.5

    def test_benchmark_comparison(self) -> None:
        eq = self._growing_equity()
        dates = eq.index
        bench_ret = pd.Series(0.0004, index=dates)  # ~10% annual
        m = calc_metrics(eq, [], 1_000_000, 252, bench_ret=bench_ret)
        assert m["benchmark_return"] > 0
        assert "excess_return" in m
        assert "information_ratio" in m

    def test_empty_equity(self) -> None:
        m = calc_metrics(pd.Series(dtype=float), [], 1_000_000, 252)
        assert m["final_value"] == 1_000_000
        assert m["total_return"] == 0

    def test_final_value(self) -> None:
        eq = self._growing_equity()
        m = calc_metrics(eq, [], 1_000_000, 252)
        assert m["final_value"] == pytest.approx(1_200_000, rel=0.01)

    def test_sortino_positive_for_growth(self) -> None:
        eq = self._growing_equity()
        m = calc_metrics(eq, [], 1_000_000, 252)
        assert m["sortino"] > 0

    def test_calmar_positive_for_drawdown(self) -> None:
        """Growing equity with a dip should have positive Calmar."""
        dates = pd.bdate_range("2025-01-01", periods=100)
        values = np.concatenate([
            np.linspace(1_000_000, 900_000, 30),  # dip
            np.linspace(900_000, 1_200_000, 70),   # recovery
        ])
        eq = pd.Series(values, index=dates)
        m = calc_metrics(eq, [], 1_000_000, 252)
        assert m["max_drawdown"] < 0
        # Calmar = annual_return / |max_drawdown|
        if m["annual_return"] > 0:
            assert m["calmar"] > 0


class TestRiskFreeRate:
    """Sharpe measures reward over the alternative of not trading.

    In Vietnam that alternative is a deposit paying 4-5%, so leaving the rate at
    zero credits the strategy with return it never had to work for. Measured on
    a real VNINDEX SMA curve, assuming zero inflates the Sharpe by 37.6%
    against a 5% deposit rate.
    """

    def _noisy_equity(self, seed: int = 3) -> pd.Series:
        dates = pd.bdate_range("2020-01-01", periods=1000)
        rng = np.random.default_rng(seed)
        return pd.Series(
            np.cumprod(1 + rng.normal(0.0006, 0.01, 1000)) * 1_000_000, index=dates
        )

    def test_the_default_leaves_every_existing_result_unchanged(self) -> None:
        eq = self._noisy_equity()
        assert calc_metrics(eq, [], 1_000_000, 252) == calc_metrics(
            eq, [], 1_000_000, 252, risk_free=0.0
        )

    def test_a_hurdle_lowers_the_sharpe(self) -> None:
        eq = self._noisy_equity()
        assert (
            calc_metrics(eq, [], 1_000_000, 252, risk_free=0.05)["sharpe"]
            < calc_metrics(eq, [], 1_000_000, 252)["sharpe"]
        )

    def test_a_higher_hurdle_lowers_it_further(self) -> None:
        eq = self._noisy_equity()
        sharpes = [
            calc_metrics(eq, [], 1_000_000, 252, risk_free=rf)["sharpe"]
            for rf in (0.0, 0.03, 0.05, 0.09)
        ]
        assert sharpes == sorted(sharpes, reverse=True)

    def test_sortino_clears_the_same_hurdle_as_sharpe(self) -> None:
        """One measured against zero while the other clears 5% is incomparable."""
        eq = self._noisy_equity()
        plain = calc_metrics(eq, [], 1_000_000, 252)
        hurdled = calc_metrics(eq, [], 1_000_000, 252, risk_free=0.05)
        assert hurdled["sortino"] < plain["sortino"]

    def test_the_return_itself_is_untouched(self) -> None:
        """A hurdle changes the risk-adjusted ratio, not what the account made."""
        eq = self._noisy_equity()
        plain = calc_metrics(eq, [], 1_000_000, 252)
        hurdled = calc_metrics(eq, [], 1_000_000, 252, risk_free=0.05)
        assert hurdled["total_return"] == plain["total_return"]
        assert hurdled["annual_return"] == plain["annual_return"]
        assert hurdled["max_drawdown"] == plain["max_drawdown"]

    def test_the_rate_is_compounded_down_not_divided(self) -> None:
        """Dividing by bars_per_year is a bias, not noise, and it is avoidable."""
        eq = self._noisy_equity()
        m = calc_metrics(eq, [], 1_000_000, 252, risk_free=0.05)
        rf_bar = (1.05) ** (1 / 252) - 1
        ret = eq.pct_change().fillna(0.0)
        expected = float((ret - rf_bar).mean() / (ret.std() + 1e-10) * np.sqrt(252))
        assert m["sharpe"] == pytest.approx(expected, rel=1e-9)
        assert rf_bar < 0.05 / 252  # compounding gives a smaller per-bar hurdle

    def test_the_applied_rate_is_reported_back(self) -> None:
        eq = self._noisy_equity()
        assert calc_metrics(eq, [], 1_000_000, 252, risk_free=0.045)["risk_free"] == 0.045

    def test_an_empty_run_still_carries_the_key(self) -> None:
        assert "risk_free" in calc_metrics(pd.Series(dtype=float), [], 1_000_000, 252)
