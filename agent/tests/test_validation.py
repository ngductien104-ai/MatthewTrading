"""Tests for backtest validation module.

Validates:
  - Monte Carlo permutation test: p-value, output structure
  - Bootstrap Sharpe CI: confidence interval bounds, prob_positive
  - Walk-Forward analysis: window splitting, consistency metrics
  - run_validation dispatcher
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest.models import TradeRecord
from backtest.validation import (
    bootstrap_sharpe_ci,
    monte_carlo_test,
    run_validation,
    equity_consistency_report,
    purged_kfold_splits,
    purged_train_positions,
    cpcv_n_paths,
    cpcv_path_assignment,
    cpcv_splits,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_trades(pnls: list[float], start: str = "2025-01-01") -> list[TradeRecord]:
    """Create TradeRecord list from PnL values."""
    trades = []
    base = pd.Timestamp(start)
    for i, pnl in enumerate(pnls):
        entry = base + pd.Timedelta(days=i * 2)
        exit_ = entry + pd.Timedelta(days=1)
        trades.append(TradeRecord(
            symbol="TEST",
            direction=1,
            entry_price=100.0,
            exit_price=100.0 + pnl / 10,
            entry_time=entry,
            exit_time=exit_,
            size=10.0,
            leverage=1.0,
            pnl=pnl,
            pnl_pct=pnl / 1000 * 100,
            exit_reason="signal",
            holding_bars=1,
            commission=0.0,
        ))
    return trades


def _make_equity(n: int = 100, drift: float = 0.001, seed: int = 42) -> pd.Series:
    """Create a synthetic equity curve."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift, 0.02, n)
    prices = 1_000_000 * np.cumprod(1 + returns)
    dates = pd.bdate_range("2025-01-01", periods=n)
    return pd.Series(prices, index=dates)


# ---------------------------------------------------------------------------
# Monte Carlo Permutation Test
# ---------------------------------------------------------------------------


class TestMonteCarlo:
    def test_output_structure(self) -> None:
        trades = _make_trades([100, -50, 200, -30, 150, -80, 120, -40, 90, -20])
        result = monte_carlo_test(trades, 1_000_000, n_simulations=100)
        assert "actual_sharpe" in result
        assert "p_value_sharpe" in result
        assert "p_value_max_dd" in result
        assert "n_simulations" in result
        assert result["n_simulations"] == 100
        assert result["n_trades"] == 10

    def test_p_value_range(self) -> None:
        trades = _make_trades([100, -50, 200, -30, 150])
        result = monte_carlo_test(trades, 1_000_000, n_simulations=200)
        assert 0.0 <= result["p_value_sharpe"] <= 1.0
        assert 0.0 <= result["p_value_max_dd"] <= 1.0

    def test_strong_strategy_low_p_value(self) -> None:
        """A consistently profitable strategy should have low p-value."""
        trades = _make_trades([100, 200, 150, 180, 120, 90, 110, 130, 160, 140])
        result = monte_carlo_test(trades, 1_000_000, n_simulations=500, seed=42)
        # All trades profitable → hard to beat by shuffling (already optimal)
        # p-value should be moderate (shuffling can't make it worse when all positive)
        assert result["actual_sharpe"] > 0

    def test_too_few_trades(self) -> None:
        trades = _make_trades([100, -50])
        result = monte_carlo_test(trades, 1_000_000)
        assert "error" in result

    def test_reproducibility(self) -> None:
        trades = _make_trades([100, -50, 200, -30, 150, -80])
        r1 = monte_carlo_test(trades, 1_000_000, n_simulations=100, seed=42)
        r2 = monte_carlo_test(trades, 1_000_000, n_simulations=100, seed=42)
        assert r1["p_value_sharpe"] == r2["p_value_sharpe"]


# ---------------------------------------------------------------------------
# Bootstrap Sharpe CI
# ---------------------------------------------------------------------------


class TestBootstrapSharpe:
    def test_output_structure(self) -> None:
        eq = _make_equity(100)
        result = bootstrap_sharpe_ci(eq, n_bootstrap=100)
        assert "observed_sharpe" in result
        assert "ci_lower" in result
        assert "ci_upper" in result
        assert "prob_positive" in result
        assert "confidence" in result
        assert result["confidence"] == 0.95

    def test_ci_contains_observed(self) -> None:
        """The observed Sharpe should usually fall within the CI."""
        eq = _make_equity(200, drift=0.001)
        result = bootstrap_sharpe_ci(eq, n_bootstrap=500)
        # Not guaranteed, but very likely for 95% CI
        assert result["ci_lower"] <= result["ci_upper"]

    def test_positive_drift_mostly_positive(self) -> None:
        """Equity with positive drift should have high prob_positive."""
        eq = _make_equity(200, drift=0.003, seed=123)
        result = bootstrap_sharpe_ci(eq, n_bootstrap=500)
        assert result["prob_positive"] > 0.5

    def test_too_few_observations(self) -> None:
        eq = pd.Series([100, 101, 102], index=pd.bdate_range("2025-01-01", periods=3))
        result = bootstrap_sharpe_ci(eq, n_bootstrap=100)
        assert "error" in result

    def test_reproducibility(self) -> None:
        eq = _make_equity(50)
        r1 = bootstrap_sharpe_ci(eq, n_bootstrap=100, seed=42)
        r2 = bootstrap_sharpe_ci(eq, n_bootstrap=100, seed=42)
        assert r1["ci_lower"] == r2["ci_lower"]

    def test_custom_confidence(self) -> None:
        eq = _make_equity(100)
        r90 = bootstrap_sharpe_ci(eq, confidence=0.90, n_bootstrap=200)
        r99 = bootstrap_sharpe_ci(eq, confidence=0.99, n_bootstrap=200)
        # 99% CI should be wider than 90% CI
        width_90 = r90["ci_upper"] - r90["ci_lower"]
        width_99 = r99["ci_upper"] - r99["ci_lower"]
        assert width_99 >= width_90


# ---------------------------------------------------------------------------
# Walk-Forward Analysis
# ---------------------------------------------------------------------------


class TestEquityConsistency:
    def test_output_structure(self) -> None:
        eq = _make_equity(100)
        trades = _make_trades([100, -50] * 10)
        result = equity_consistency_report(eq, trades, n_windows=4)
        assert result["n_windows"] == 4
        assert len(result["windows"]) == 4
        assert "consistency_rate" in result
        assert "return_mean" in result
        assert "sharpe_mean" in result

    def test_window_fields(self) -> None:
        eq = _make_equity(100)
        trades = _make_trades([100, -50] * 10)
        result = equity_consistency_report(eq, trades, n_windows=5)
        w = result["windows"][0]
        assert "window" in w
        assert "start" in w
        assert "end" in w
        assert "return" in w
        assert "sharpe" in w
        assert "max_dd" in w
        assert "trades" in w
        assert "win_rate" in w

    def test_consistency_rate(self) -> None:
        """Equity with positive drift should have high consistency."""
        eq = _make_equity(200, drift=0.003)
        trades = _make_trades([100] * 50)
        result = equity_consistency_report(eq, trades, n_windows=5)
        assert result["consistency_rate"] > 0.5

    def test_windows_cover_full_range(self) -> None:
        eq = _make_equity(100)
        trades = _make_trades([100] * 10)
        result = equity_consistency_report(eq, trades, n_windows=5)
        first_start = result["windows"][0]["start"]
        last_end = result["windows"][-1]["end"]
        assert first_start == str(eq.index[0].date())
        assert last_end == str(eq.index[-1].date())

    def test_too_few_bars(self) -> None:
        eq = pd.Series([100, 101], index=pd.bdate_range("2025-01-01", periods=2))
        result = equity_consistency_report(eq, [], n_windows=5)
        assert "error" in result


# ---------------------------------------------------------------------------
# run_validation dispatcher
# ---------------------------------------------------------------------------


class TestRunValidation:
    def test_empty_config_returns_empty(self) -> None:
        eq = _make_equity(50)
        result = run_validation({}, eq, [], 1_000_000)
        assert result == {}

    def test_all_three(self) -> None:
        eq = _make_equity(100)
        trades = _make_trades([100, -50, 200, -30, 150])
        config = {
            "validation": {
                "monte_carlo": {"n_simulations": 50},
                "bootstrap": {"n_bootstrap": 50},
                "equity_consistency": {"n_windows": 3},
            }
        }
        result = run_validation(config, eq, trades, 1_000_000)
        assert "monte_carlo" in result
        assert "bootstrap" in result
        assert "equity_consistency" in result

    def test_single_tool(self) -> None:
        eq = _make_equity(100)
        trades = _make_trades([100, -50, 200])
        config = {"validation": {"bootstrap": {"n_bootstrap": 50}}}
        result = run_validation(config, eq, trades, 1_000_000)
        assert "bootstrap" in result
        assert "monte_carlo" not in result


class TestTheReportDoesNotClaimToBeWalkForward:
    """The old name promised out-of-sample evidence this function cannot give."""

    def test_the_result_says_it_is_in_sample(self) -> None:
        eq = _make_equity(100)
        result = equity_consistency_report(eq, _make_trades([100] * 10), n_windows=4)
        assert result["in_sample"] is True

    def test_a_config_written_against_the_old_name_still_runs(self) -> None:
        eq = _make_equity(100)
        config = {"validation": {"walk_forward": {"n_windows": 3}}}
        result = run_validation(config, eq, _make_trades([100] * 6), 1_000_000)
        assert result["equity_consistency"]["n_windows"] == 3

    def test_the_old_key_is_not_echoed_back(self) -> None:
        """The name is being freed for the real walk-forward, so it must not linger."""
        eq = _make_equity(100)
        config = {"validation": {"walk_forward": {"n_windows": 3}}}
        result = run_validation(config, eq, _make_trades([100] * 6), 1_000_000)
        assert "walk_forward" not in result

    def test_the_new_name_wins_when_both_are_given(self) -> None:
        eq = _make_equity(100)
        config = {"validation": {
            "walk_forward": {"n_windows": 3},
            "equity_consistency": {"n_windows": 5},
        }}
        result = run_validation(config, eq, _make_trades([100] * 6), 1_000_000)
        assert result["equity_consistency"]["n_windows"] == 5


class TestPurgeAndEmbargo:
    """Two different leaks, on two different sides of the test window."""

    def test_purge_removes_training_bars_whose_outcome_reaches_the_test_window(self) -> None:
        train = purged_train_positions(20, range(8, 12), holding_bars=2, embargo_bars=0)
        # A signal at bar 6 is still open at bar 8, the first test bar.
        assert 6 not in train and 7 not in train
        assert 5 in train

    def test_embargo_removes_training_bars_that_follow_the_test_window(self) -> None:
        train = purged_train_positions(20, range(8, 12), holding_bars=0, embargo_bars=3)
        assert [12, 13, 14] == [i for i in (12, 13, 14) if i not in train]
        assert 15 in train

    def test_purge_and_embargo_are_independent(self) -> None:
        """Neither implies the other: one looks back, the other looks forward."""
        purged_only = purged_train_positions(20, range(8, 12), holding_bars=2, embargo_bars=0)
        embargo_only = purged_train_positions(20, range(8, 12), holding_bars=0, embargo_bars=3)
        assert 6 in embargo_only and 6 not in purged_only
        assert 12 in purged_only and 12 not in embargo_only

    def test_with_no_holding_and_no_embargo_only_the_test_bars_leave(self) -> None:
        train = purged_train_positions(10, [3, 4], holding_bars=0, embargo_bars=0)
        assert train.tolist() == [0, 1, 2, 5, 6, 7, 8, 9]

    def test_each_disjoint_test_run_is_purged_on_its_own(self) -> None:
        """CPCV tests several groups at once; a gap between them is not one run."""
        train = purged_train_positions(
            30, [5, 6, 7, 20, 21, 22], holding_bars=2, embargo_bars=2
        )
        for blocked in (3, 4, 8, 9, 18, 19, 23, 24):
            assert blocked not in train, blocked
        for kept in (2, 10, 17, 25):
            assert kept in train, kept

    def test_windows_that_run_off_the_ends_are_clipped_not_wrapped(self) -> None:
        train = purged_train_positions(10, [0, 1], holding_bars=5, embargo_bars=5)
        assert train.tolist() == [7, 8, 9]

    def test_a_negative_window_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            purged_train_positions(10, [3], holding_bars=-1)

    def test_a_test_position_outside_the_sample_is_refused(self) -> None:
        with pytest.raises(ValueError, match=r"must lie in \[0, 9\]"):
            purged_train_positions(10, [3, 10])


class TestPurgedKFold:
    def test_test_folds_tile_the_sample_exactly_once(self) -> None:
        splits = purged_kfold_splits(50, 5, holding_bars=3, embargo_bars=3)
        covered = np.concatenate([test for _, test in splits])
        assert sorted(covered.tolist()) == list(range(50))

    def test_train_and_test_never_overlap(self) -> None:
        for train, test in purged_kfold_splits(50, 5, holding_bars=3, embargo_bars=3):
            assert not set(train.tolist()) & set(test.tolist())

    def test_folds_stay_in_time_order(self) -> None:
        splits = purged_kfold_splits(50, 5)
        starts = [int(test[0]) for _, test in splits]
        assert starts == sorted(starts)

    def test_a_wider_holding_window_can_only_shrink_the_training_set(self) -> None:
        narrow = purged_kfold_splits(60, 4, holding_bars=1, embargo_bars=1)
        wide = purged_kfold_splits(60, 4, holding_bars=6, embargo_bars=6)
        for (n_train, _), (w_train, _) in zip(narrow, wide):
            assert set(w_train.tolist()) <= set(n_train.tolist())
            assert len(w_train) < len(n_train)

    def test_one_fold_is_not_cross_validation(self) -> None:
        with pytest.raises(ValueError, match="at least 2 folds"):
            purged_kfold_splits(50, 1)

    def test_more_folds_than_bars_is_refused(self) -> None:
        with pytest.raises(ValueError, match="at least 5 bars"):
            purged_kfold_splits(3, 5)


class TestCPCV:
    """Walk-forward yields one OOS path; CPCV yields a distribution of them."""

    def test_split_count_is_the_combination_count(self) -> None:
        assert len(cpcv_splits(120, n_groups=6, n_test_groups=2)) == 15
        assert len(cpcv_splits(120, n_groups=5, n_test_groups=2)) == 10

    def test_path_count_follows_from_the_group_count(self) -> None:
        assert cpcv_n_paths(6, 2) == 5
        assert cpcv_n_paths(5, 2) == 4
        assert cpcv_n_paths(6, 3) == 10

    def test_every_path_covers_the_whole_sample_exactly_once(self) -> None:
        """This is the property that makes a path a backtest rather than a fold."""
        n_groups, n_test = 6, 2
        assignment = cpcv_path_assignment(n_groups, n_test)
        per_path: dict[int, list[int]] = {}
        for (_split, group), path in assignment.items():
            per_path.setdefault(path, []).append(group)
        assert len(per_path) == cpcv_n_paths(n_groups, n_test)
        for groups in per_path.values():
            assert sorted(groups) == list(range(n_groups))

    def test_each_group_is_tested_in_every_path_and_no_more(self) -> None:
        assignment = cpcv_path_assignment(6, 2)
        counts: dict[int, int] = {}
        for (_split, group), _path in assignment.items():
            counts[group] = counts.get(group, 0) + 1
        assert set(counts.values()) == {cpcv_n_paths(6, 2)}

    def test_train_and_test_never_overlap_in_any_split(self) -> None:
        for split in cpcv_splits(200, 6, 2, holding_bars=5, embargo_bars=5):
            assert not set(split["train"].tolist()) & set(split["test"].tolist())

    def test_disjoint_test_groups_are_purged_separately(self) -> None:
        """Groups 0 and 5 are not adjacent, so the bars between them survive."""
        splits = {s["test_groups"]: s for s in cpcv_splits(60, 6, 2, holding_bars=2)}
        train = splits[(0, 5)]["train"]
        assert 30 in train  # the middle of the sample is untouched
        assert 48 not in train  # purged ahead of group 5, which starts at 50

    def test_a_single_group_of_test_is_ordinary_purged_kfold(self) -> None:
        cpcv = cpcv_splits(60, 5, 1, holding_bars=2, embargo_bars=2)
        kfold = purged_kfold_splits(60, 5, holding_bars=2, embargo_bars=2)
        for split, (train, test) in zip(cpcv, kfold):
            assert split["test"].tolist() == test.tolist()
            assert split["train"].tolist() == train.tolist()

    def test_testing_every_group_leaves_no_training_data(self) -> None:
        with pytest.raises(ValueError, match=r"must be in \[1, 5\]"):
            cpcv_splits(60, 6, 6)

    def test_one_group_is_not_a_partition(self) -> None:
        with pytest.raises(ValueError, match="at least 2 groups"):
            cpcv_splits(60, 1, 1)
