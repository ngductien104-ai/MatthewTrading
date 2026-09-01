"""Statistical validation for backtest results.

Three independent tools:
  - Monte Carlo permutation test: is the strategy significantly better than random?
  - Block bootstrap Sharpe CI: how stable is the risk-adjusted return?
  - Equity consistency report: is the in-sample curve steady across time windows?

None of the three is an out-of-sample test. They all read one equity curve that
was produced by one fit over one period, so they can say a result is fragile
but they can never say it generalises. Walk-forward -- refit on a train window,
measure on an unseen test window -- lives in :mod:`backtest.walkforward`.

Usage: called automatically by BaseEngine.run_backtest when config[\"validation\"]
is present, or invoked directly on backtest outputs.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from backtest.models import TradeRecord


# ─── Monte Carlo Permutation Test ───


def monte_carlo_test(
    trades: List[TradeRecord],
    initial_capital: float,
    n_simulations: int = 1000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Shuffle trade PnL order to test path significance.

    Null hypothesis: the observed Sharpe / max-drawdown is no better than
    a random ordering of the same trades.

    Args:
        trades: Completed round-trip trades from backtest.
        initial_capital: Starting capital.
        n_simulations: Number of random permutations.
        seed: Random seed for reproducibility.

    Returns:
        Dict with actual_sharpe, p_value_sharpe, actual_max_dd,
        p_value_max_dd, simulated_sharpes (percentiles).
    """
    if len(trades) < 3:
        return {"error": "need at least 3 trades", "p_value_sharpe": 1.0}

    pnls = np.array([t.pnl for t in trades])
    actual = _path_metrics(pnls, initial_capital)

    rng = np.random.default_rng(seed)
    sharpe_count = 0
    dd_count = 0
    sim_sharpes = []

    for _ in range(n_simulations):
        shuffled = rng.permutation(pnls)
        sim = _path_metrics(shuffled, initial_capital)
        sim_sharpes.append(sim["sharpe"])
        if sim["sharpe"] >= actual["sharpe"]:
            sharpe_count += 1
        if sim["max_dd"] >= actual["max_dd"]:  # less negative = "better"
            dd_count += 1

    sim_arr = np.array(sim_sharpes)
    return {
        "actual_sharpe": round(actual["sharpe"], 4),
        "actual_max_dd": round(actual["max_dd"], 4),
        "p_value_sharpe": round(sharpe_count / n_simulations, 4),
        "p_value_max_dd": round(dd_count / n_simulations, 4),
        "simulated_sharpe_mean": round(float(sim_arr.mean()), 4),
        "simulated_sharpe_std": round(float(sim_arr.std()), 4),
        "simulated_sharpe_p5": round(float(np.percentile(sim_arr, 5)), 4),
        "simulated_sharpe_p95": round(float(np.percentile(sim_arr, 95)), 4),
        "n_simulations": n_simulations,
        "n_trades": len(trades),
    }


def _path_metrics(pnls: np.ndarray, initial_capital: float) -> Dict[str, float]:
    """Compute Sharpe and max drawdown from a PnL sequence."""
    equity = initial_capital + np.cumsum(pnls)
    returns = np.diff(equity) / equity[:-1] if len(equity) > 1 else np.array([0.0])
    std = returns.std()
    sharpe = float(returns.mean() / (std + 1e-10) * np.sqrt(252))
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak > 0, peak, 1.0)
    max_dd = float(dd.min())
    return {"sharpe": sharpe, "max_dd": max_dd}


# ─── Bootstrap Sharpe CI ───


def _auto_block_size(n: int) -> int:
    """Return a default block length for the moving-block bootstrap.

    The usual rule of thumb, ``n ** (1/3)``, rounded and clamped to at least
    two -- a block of one is the iid bootstrap, which is the thing being
    replaced.
    """
    return max(2, int(round(n ** (1.0 / 3.0))))


def _block_resample(returns: np.ndarray, block_size: int, rng: np.random.Generator) -> np.ndarray:
    """Resample *returns* in contiguous wrapped blocks of *block_size*.

    Blocks wrap around the end of the series (the circular block bootstrap), so
    every observation is equally likely to be drawn. Without wrapping, the first
    and last few bars are systematically under-sampled.
    """
    n = returns.size
    n_blocks = int(np.ceil(n / block_size))
    starts = rng.integers(0, n, size=n_blocks)
    offsets = np.arange(block_size)
    indices = (starts[:, None] + offsets[None, :]).ravel() % n
    return returns[indices[:n]]


def bootstrap_sharpe_ci(
    equity_curve: pd.Series,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    bars_per_year: int = 252,
    seed: int = 42,
    block_size: int | None = None,
) -> Dict[str, Any]:
    """Resample returns in blocks to estimate a Sharpe confidence interval.

    Resampling one return at a time assumes they are independent, and strategy
    returns are not: a trend rule holds a position for days, so its wins and
    losses arrive in runs. Shuffling those runs apart destroys the very
    dependence that makes the Sharpe uncertain, and the interval comes out too
    narrow -- confident for the wrong reason. Resampling contiguous blocks keeps
    the local dependence intact.

    Args:
        equity_curve: Equity time series.
        n_bootstrap: Number of bootstrap samples.
        confidence: Confidence level (e.g. 0.95 for 95% CI).
        bars_per_year: Annualisation factor.
        seed: Random seed.
        block_size: Length of the resampled blocks. ``None`` picks
            ``round(n ** (1/3))``, at least 2. Pass ``1`` for the old iid
            bootstrap, which is worth doing only to see how much narrower it is.

    Returns:
        Dict with observed_sharpe, ci_lower, ci_upper, median_sharpe,
        prob_positive (fraction of samples with Sharpe > 0), and the
        ``block_size`` actually used.

    Raises:
        ValueError: A block size below one, or longer than the sample.
    """
    returns = equity_curve.pct_change().dropna().values
    if len(returns) < 5:
        return {"error": "need at least 5 return observations"}

    block = _auto_block_size(len(returns)) if block_size is None else int(block_size)
    if block < 1:
        raise ValueError(f"block_size must be at least 1; got {block}")
    if block > len(returns):
        raise ValueError(
            f"block_size {block} exceeds the {len(returns)} available returns"
        )

    observed = _sharpe(returns, bars_per_year)

    rng = np.random.default_rng(seed)
    boot_sharpes = [
        _sharpe(_block_resample(returns, block, rng), bars_per_year)
        for _ in range(n_bootstrap)
    ]

    arr = np.array(boot_sharpes)
    alpha = (1 - confidence) / 2
    lower = float(np.percentile(arr, alpha * 100))
    upper = float(np.percentile(arr, (1 - alpha) * 100))
    prob_pos = float(np.mean(arr > 0))

    return {
        "observed_sharpe": round(observed, 4),
        "ci_lower": round(lower, 4),
        "ci_upper": round(upper, 4),
        "median_sharpe": round(float(np.median(arr)), 4),
        "prob_positive": round(prob_pos, 4),
        "confidence": confidence,
        "n_bootstrap": n_bootstrap,
        "block_size": block,
    }


def _sharpe(returns: np.ndarray, bars_per_year: int = 252) -> float:
    std = returns.std()
    return float(returns.mean() / (std + 1e-10) * np.sqrt(bars_per_year))


# ─── Equity Consistency Report ───


def equity_consistency_report(
    equity_curve: pd.Series,
    trades: List[TradeRecord],
    n_windows: int = 5,
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Split one in-sample equity curve into windows and report its steadiness.

    This was called ``walk_forward_analysis``, which it never was. It refits
    nothing and holds nothing out: it slices the single curve the backtest
    already produced and asks whether the profit came evenly or from one lucky
    stretch. That is a worthwhile question and a different one from whether the
    strategy works on data it was not fitted to, which is what
    :mod:`backtest.walkforward` answers.

    A high consistency rate here is therefore not evidence of generalisation.
    An overfitted strategy can be perfectly consistent in sample.

    Each window is evaluated independently (returns normalised to window start).

    Args:
        equity_curve: Equity time series.
        trades: Completed trades.
        n_windows: Number of non-overlapping windows.
        bars_per_year: Annualisation factor.

    Returns:
        Dict with per-window stats and consistency metrics, plus ``in_sample``,
        which is True because it is always True.
    """
    if len(equity_curve) < n_windows * 2:
        return {"error": f"need at least {n_windows * 2} bars for {n_windows} windows"}

    indices = equity_curve.index
    window_size = len(indices) // n_windows
    windows = []

    for i in range(n_windows):
        start_idx = i * window_size
        end_idx = (i + 1) * window_size if i < n_windows - 1 else len(indices)
        win_eq = equity_curve.iloc[start_idx:end_idx]
        win_start = indices[start_idx]
        win_end = indices[end_idx - 1]

        # Per-window trades
        win_trades = [
            t for t in trades
            if win_start <= t.entry_time <= win_end
        ]

        # Per-window metrics
        ret = float(win_eq.iloc[-1] / win_eq.iloc[0] - 1) if win_eq.iloc[0] > 0 else 0.0
        win_returns = win_eq.pct_change().dropna().values
        sharpe = _sharpe(win_returns, bars_per_year) if len(win_returns) > 1 else 0.0

        peak = win_eq.cummax()
        dd = (win_eq - peak) / peak.replace(0, 1)
        max_dd = float(dd.min())

        win_pnls = [t.pnl for t in win_trades]
        win_rate = (
            len([p for p in win_pnls if p > 0]) / len(win_pnls)
            if win_pnls else 0.0
        )

        windows.append({
            "window": i + 1,
            "start": str(win_start.date()) if hasattr(win_start, "date") else str(win_start),
            "end": str(win_end.date()) if hasattr(win_end, "date") else str(win_end),
            "return": round(ret, 6),
            "sharpe": round(sharpe, 4),
            "max_dd": round(max_dd, 6),
            "trades": len(win_trades),
            "win_rate": round(win_rate, 4),
        })

    # Consistency metrics
    returns_list = [w["return"] for w in windows]
    sharpes_list = [w["sharpe"] for w in windows]
    profitable_windows = sum(1 for r in returns_list if r > 0)

    return {
        "n_windows": n_windows,
        "in_sample": True,
        "windows": windows,
        "profitable_windows": profitable_windows,
        "consistency_rate": round(profitable_windows / n_windows, 4),
        "return_mean": round(float(np.mean(returns_list)), 6),
        "return_std": round(float(np.std(returns_list)), 6),
        "sharpe_mean": round(float(np.mean(sharpes_list)), 4),
        "sharpe_std": round(float(np.std(sharpes_list)), 4),
    }


# ─── Purging and embargo ───
#
# Cross-validating a time series by shuffling folds leaks, and it leaks in a way
# that flatters the strategy. Two separate leaks, and both have to be closed:
#
#   1. A training bar's outcome reaches into the test window. A signal taken at
#      bar ``i`` and held for ``h`` bars is scored on bars ``i..i+h``, so if
#      ``i + h`` reaches the test window, that training observation and the test
#      set are measuring some of the same days. Dropping those training bars is
#      the *purge*.
#   2. The test window's own outcome reaches into training bars that follow it.
#      The last test signal is still open for ``h`` bars past the end of the
#      window, and those days are serially correlated with the bars just after.
#      Dropping a run of training bars after the test window is the *embargo*.
#
# The two are not the same operation and neither implies the other: the purge
# removes bars *before* the test window, the embargo removes bars *after* it.
# Lopez de Prado, Advances in Financial Machine Learning, ch. 7.


def purged_train_positions(
    n_samples: int,
    test_positions: np.ndarray | List[int],
    *,
    holding_bars: int = 0,
    embargo_bars: int = 0,
) -> np.ndarray:
    """Return training positions that cannot see the test window.

    Args:
        n_samples: Total number of bars.
        test_positions: Integer positions belonging to the test set. They need
            not be contiguous -- CPCV tests several disjoint groups at once --
            and every contiguous run is purged and embargoed on its own.
        holding_bars: How many bars a signal stays open. This is what makes a
            training bar's outcome overlap the test window.
        embargo_bars: How many bars after each test run to withhold from
            training. Lopez de Prado suggests at least ``holding_bars``.

    Returns:
        Sorted array of training positions, with the test set, the purged bars
        and the embargoed bars removed.

    Raises:
        ValueError: A negative window, or a test position outside the sample.
    """
    if holding_bars < 0 or embargo_bars < 0:
        raise ValueError(
            f"holding_bars and embargo_bars cannot be negative; got "
            f"holding_bars={holding_bars}, embargo_bars={embargo_bars}"
        )
    test = np.unique(np.asarray(test_positions, dtype=int))
    if test.size and (test.min() < 0 or test.max() >= n_samples):
        raise ValueError(
            f"test positions must lie in [0, {n_samples - 1}]; got "
            f"[{int(test.min())}, {int(test.max())}]"
        )

    blocked = np.zeros(n_samples, dtype=bool)
    blocked[test] = True
    for run_start, run_end in _contiguous_runs(test):
        # Purge: a training bar at i is scored over i..i+holding_bars, so it
        # overlaps this run whenever i + holding_bars >= run_start.
        purge_from = max(0, run_start - holding_bars)
        blocked[purge_from:run_start] = True
        # Embargo: the run's own last signals stay open past run_end.
        embargo_to = min(n_samples, run_end + 1 + embargo_bars)
        blocked[run_end + 1:embargo_to] = True

    return np.flatnonzero(~blocked)


def _contiguous_runs(positions: np.ndarray) -> List[tuple[int, int]]:
    """Return inclusive ``(start, end)`` bounds of each run of consecutive ints."""
    if positions.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(positions) > 1)
    starts = np.concatenate(([positions[0]], positions[breaks + 1]))
    ends = np.concatenate((positions[breaks], [positions[-1]]))
    return [(int(a), int(b)) for a, b in zip(starts, ends)]


def purged_kfold_splits(
    n_samples: int,
    n_splits: int = 5,
    *,
    holding_bars: int = 0,
    embargo_bars: int = 0,
) -> List[tuple[np.ndarray, np.ndarray]]:
    """Split a series into contiguous test folds with purged, embargoed training.

    Folds stay in time order and are never shuffled; only the training side is
    thinned. Note that the training set is not always in the past: the fold at
    the start of the sample trains entirely on later bars. That is deliberate --
    it is what makes this cross-validation rather than a backtest -- and it is
    also why :mod:`backtest.walkforward` exists separately for the strictly
    causal version.

    Args:
        n_samples: Total number of bars.
        n_splits: Number of contiguous test folds.
        holding_bars: How many bars a signal stays open.
        embargo_bars: Bars withheld after each test fold.

    Returns:
        List of ``(train_positions, test_positions)`` pairs.

    Raises:
        ValueError: Fewer than two folds, or fewer bars than folds.
    """
    if n_splits < 2:
        raise ValueError(f"need at least 2 folds to cross-validate; got {n_splits}")
    if n_samples < n_splits:
        raise ValueError(f"need at least {n_splits} bars for {n_splits} folds; got {n_samples}")

    bounds = np.linspace(0, n_samples, n_splits + 1).astype(int)
    splits = []
    for i in range(n_splits):
        test = np.arange(bounds[i], bounds[i + 1])
        train = purged_train_positions(
            n_samples, test, holding_bars=holding_bars, embargo_bars=embargo_bars
        )
        splits.append((train, test))
    return splits


# ─── Combinatorial Purged Cross-Validation ───
#
# Walk-forward gives you exactly one out-of-sample path, so its Sharpe has no
# distribution and you cannot tell a good strategy from a lucky ordering of the
# same data. CPCV builds many. Split the sample into ``N`` groups, test on every
# combination of ``k`` of them, and the C(N, k) splits reassemble into
# C(N-1, k-1) complete out-of-sample paths over the whole period -- each one a
# different interleaving of the same folds. A distribution of paths is what
# makes PBO and a deflated Sharpe computable at all.
#
# Lopez de Prado, Advances in Financial Machine Learning, ch. 12.


def cpcv_splits(
    n_samples: int,
    n_groups: int = 6,
    n_test_groups: int = 2,
    *,
    holding_bars: int = 0,
    embargo_bars: int = 0,
) -> List[Dict[str, Any]]:
    """Enumerate the combinatorial purged splits of a sample.

    Args:
        n_samples: Total number of bars.
        n_groups: Contiguous groups the sample is cut into.
        n_test_groups: How many groups are held out per split.
        holding_bars: How many bars a signal stays open.
        embargo_bars: Bars withheld after each test run.

    Returns:
        One dict per split, in combination order, with ``test_groups`` (the
        group indices held out), ``train`` and ``test`` position arrays.

    Raises:
        ValueError: The group count is below two, the test count is not in
            ``[1, n_groups)``, or there are fewer bars than groups.
    """
    if n_groups < 2:
        raise ValueError(f"need at least 2 groups; got {n_groups}")
    if not 1 <= n_test_groups < n_groups:
        raise ValueError(
            f"n_test_groups must be in [1, {n_groups - 1}]; got {n_test_groups}"
        )
    if n_samples < n_groups:
        raise ValueError(f"need at least {n_groups} bars for {n_groups} groups; got {n_samples}")

    bounds = np.linspace(0, n_samples, n_groups + 1).astype(int)
    groups = [np.arange(bounds[i], bounds[i + 1]) for i in range(n_groups)]

    splits: List[Dict[str, Any]] = []
    for combo in itertools.combinations(range(n_groups), n_test_groups):
        test = np.concatenate([groups[g] for g in combo])
        train = purged_train_positions(
            n_samples, test, holding_bars=holding_bars, embargo_bars=embargo_bars
        )
        splits.append({"test_groups": combo, "train": train, "test": np.sort(test)})
    return splits


def cpcv_path_assignment(n_groups: int = 6, n_test_groups: int = 2) -> Dict[tuple, int]:
    """Map each ``(split index, group index)`` to the path it belongs to.

    Every group is tested in exactly ``C(n_groups - 1, n_test_groups - 1)``
    splits, and that count is also the number of complete out-of-sample paths.
    Handing each group's occurrences out to a different path is what makes each
    path cover the whole sample exactly once.

    Args:
        n_groups: Contiguous groups the sample is cut into.
        n_test_groups: How many groups are held out per split.

    Returns:
        ``{(split_index, group_index): path_index}``.
    """
    combos = list(itertools.combinations(range(n_groups), n_test_groups))
    seen: Dict[int, int] = {}
    assignment: Dict[tuple, int] = {}
    for split_index, combo in enumerate(combos):
        for group in combo:
            assignment[(split_index, group)] = seen.get(group, 0)
            seen[group] = seen.get(group, 0) + 1
    return assignment


def cpcv_n_paths(n_groups: int = 6, n_test_groups: int = 2) -> int:
    """Return how many complete out-of-sample paths the splits reassemble into."""
    return math.comb(n_groups - 1, n_test_groups - 1)


# ─── Probabilistic and Deflated Sharpe ───
#
# A Sharpe ratio is an estimate that gets reported as though it were a
# measurement. Two separate things inflate it:
#
#   1. **Short samples and non-normal returns.** The standard error of a Sharpe
#      estimate depends on skew and kurtosis, and trading returns have plenty of
#      both. The Probabilistic Sharpe Ratio gives the probability that the true
#      Sharpe exceeds a benchmark, given the sample's actual shape.
#   2. **Selection.** If a hundred variants were tried and the best kept, that
#      Sharpe is the maximum of a hundred draws, not a typical one. The expected
#      maximum of N independent worthless trials with dispersion sigma grows
#      like sigma * sqrt(2 log N) -- it is large, and it is free. The Deflated
#      Sharpe Ratio is the PSR measured against that expected maximum instead of
#      against zero.
#
# Bailey & Lopez de Prado, "The Deflated Sharpe Ratio" (2014).
#
# Everything here computes in per-observation Sharpe internally while taking and
# returning annualised numbers, because quietly mixing the two is the easiest
# way to get a confident wrong answer out of these formulas.

_EULER_MASCHERONI = 0.5772156649015329


def _per_observation_sharpe(returns: np.ndarray) -> float:
    std = float(returns.std(ddof=1))
    if std <= 0:
        return 0.0
    return float(returns.mean()) / std


def probabilistic_sharpe_ratio(
    returns: "np.ndarray | pd.Series",
    *,
    benchmark_sharpe: float = 0.0,
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Return the probability that the true Sharpe beats *benchmark_sharpe*.

    Args:
        returns: Per-bar returns, not an equity curve.
        benchmark_sharpe: Annualised Sharpe to beat. Zero asks only "is this
            better than nothing", which is the weakest question available.
        bars_per_year: Annualisation factor for the inputs and outputs.

    Returns:
        Dict with ``psr``, the annualised ``sharpe``, the sample ``skew`` and
        ``kurtosis`` that shaped it, and ``n_observations``.

    Raises:
        ValueError: Fewer than three returns, zero variance, or a sample so
            skewed the estimator's variance term goes non-positive. Each of
            those makes the correction undefined rather than merely imprecise.
    """
    values = np.asarray(returns, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 3:
        raise ValueError(
            f"need at least 3 returns to estimate skew and kurtosis; got {values.size}"
        )

    n = values.size
    sr = _per_observation_sharpe(values)
    sr_star = float(benchmark_sharpe) / math.sqrt(bars_per_year)

    centred = values - values.mean()
    sd = float(centred.std(ddof=1))
    if sd <= 0:
        raise ValueError("returns have zero variance, so a Sharpe ratio is undefined")
    skew = float((centred ** 3).mean() / sd ** 3)
    kurtosis = float((centred ** 4).mean() / sd ** 4)  # not excess

    variance = 1.0 - skew * sr + (kurtosis - 1.0) / 4.0 * sr ** 2
    if variance <= 0:
        raise ValueError(
            f"the Sharpe estimator variance term is non-positive ({variance:.4g}); "
            "this sample is too skewed or heavy-tailed for the approximation"
        )

    z = (sr - sr_star) * math.sqrt(n - 1) / math.sqrt(variance)
    return {
        "psr": round(NormalDist().cdf(z), 6),
        "sharpe": round(sr * math.sqrt(bars_per_year), 6),
        "benchmark_sharpe": round(float(benchmark_sharpe), 6),
        "skew": round(skew, 6),
        "kurtosis": round(kurtosis, 6),
        "n_observations": int(n),
    }


def expected_max_sharpe(
    trial_sharpes: "np.ndarray | List[float]",
    *,
    bars_per_year: int = 252,
) -> float:
    """Return the Sharpe a *worthless* strategy is expected to post as best of N.

    This is the deflation benchmark. Given ``n`` trials whose Sharpes have
    dispersion ``sigma`` and no skill whatever, the best of them lands here.
    A result at or below this number is fully explained by having looked many
    times, without any of it being skill.

    Args:
        trial_sharpes: Annualised Sharpe of every variant tried, the kept one
            included.
        bars_per_year: Annualisation factor.

    Returns:
        Annualised expected maximum Sharpe. Zero when every trial scored the
        same, since choosing between identical results selects nothing.

    Raises:
        ValueError: Fewer than two trials. One trial involves no selection, so
            there is no maximum to correct for.
    """
    trials = np.asarray(trial_sharpes, dtype=float)
    trials = trials[np.isfinite(trials)]
    n = trials.size
    if n < 2:
        raise ValueError(
            f"deflation needs at least 2 trials to have selected between; got {n}. "
            "With a single trial there is no selection bias -- use the PSR against zero."
        )

    # The condition is semantic, not numeric: every variant scored the same, so
    # choosing between them selected nothing. Testing the standard deviation
    # against zero would miss it, because the sd of identical floats is ~1e-16.
    if float(trials.min()) == float(trials.max()):
        return 0.0
    sigma = float(trials.std(ddof=1)) / math.sqrt(bars_per_year)
    if sigma <= 0:
        return 0.0

    normal = NormalDist()
    gamma = _EULER_MASCHERONI
    z_one = normal.inv_cdf(1.0 - 1.0 / n)
    z_two = normal.inv_cdf(1.0 - 1.0 / (n * math.e))
    sr0 = sigma * ((1.0 - gamma) * z_one + gamma * z_two)
    return float(sr0 * math.sqrt(bars_per_year))


def deflated_sharpe_ratio(
    returns: "np.ndarray | pd.Series",
    trial_sharpes: "np.ndarray | List[float]",
    *,
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Return the Sharpe's survival probability after charging for the search.

    Args:
        returns: Per-bar returns of the strategy that was kept.
        trial_sharpes: Annualised Sharpe of every variant tried, the kept one
            included. Passing only the survivors understates the search and
            inflates the answer, which is the specific error this function
            exists to prevent, so ``n_trials`` is reported back for the reader
            to check against what was actually run.
        bars_per_year: Annualisation factor.

    Returns:
        Dict with ``dsr``, the ``expected_max_sharpe`` it was deflated against,
        ``n_trials``, and the sample statistics behind the PSR.

    Raises:
        ValueError: Propagated from the two functions above.
    """
    sr0 = expected_max_sharpe(trial_sharpes, bars_per_year=bars_per_year)
    psr = probabilistic_sharpe_ratio(
        returns, benchmark_sharpe=sr0, bars_per_year=bars_per_year
    )
    n_trials = int(np.isfinite(np.asarray(trial_sharpes, dtype=float)).sum())
    return {
        "dsr": psr["psr"],
        "expected_max_sharpe": round(sr0, 6),
        "n_trials": n_trials,
        "sharpe": psr["sharpe"],
        "skew": psr["skew"],
        "kurtosis": psr["kurtosis"],
        "n_observations": psr["n_observations"],
    }


# ─── Probability of Backtest Overfitting ───
#
# The deflated Sharpe asks whether the winner's number survives the search. PBO
# asks a blunter question about the *selection procedure* itself: when you pick
# the best variant in sample, how often does it land in the bottom half out of
# sample? If that happens about half the time, your selection rule carries no
# information and the whole exercise is fitting noise -- however good the
# winner's backtest looks.
#
# CSCV: cut the sample into S blocks, take every way of splitting them into
# equal in-sample and out-of-sample halves, and for each split record the
# out-of-sample rank of whichever variant won in sample. PBO is the share of
# splits where that rank falls below the median. Because both halves are the
# same size and every block appears in each half equally often, the procedure
# has no in-sample/out-of-sample asymmetry to exploit -- hence "symmetric".
#
# Bailey, Borwein, Lopez de Prado & Zhu, "The Probability of Backtest
# Overfitting" (2015).


def _block_sharpes(
    block_sum: np.ndarray,
    block_sumsq: np.ndarray,
    block_len: np.ndarray,
    selection: np.ndarray,
) -> np.ndarray:
    """Return each variant's Sharpe over the selected blocks, pooled.

    Sharpe is recomputed from per-block sums rather than by slicing the matrix,
    which is what keeps C(16, 8) = 12,870 splits affordable.
    """
    n = float(block_len[selection].sum())
    total = block_sum[selection].sum(axis=0)
    total_sq = block_sumsq[selection].sum(axis=0)
    mean = total / n
    var = (total_sq - n * mean ** 2) / (n - 1.0)
    std = np.sqrt(np.maximum(var, 0.0))
    return np.where(std > 0, mean / np.where(std > 0, std, 1.0), 0.0)


def probability_of_backtest_overfitting(
    returns_matrix: np.ndarray | pd.DataFrame,
    n_blocks: int = 16,
) -> Dict[str, Any]:
    """Return how often the in-sample winner underperforms out of sample.

    Args:
        returns_matrix: ``(n_bars, n_variants)``. One column per variant that
            was considered -- every one, not only the ones that looked good,
            since the question is about the selection and a pre-filtered set
            has already had the selection applied to it.
        n_blocks: Contiguous blocks the sample is cut into. Must be even; the
            splits are the ``C(n_blocks, n_blocks/2)`` equal halves.

    Returns:
        Dict with ``pbo``, the number of ``splits`` examined, the median logit,
        and ``performance_degradation`` -- the mean drop in Sharpe from the
        winner's in-sample value to its out-of-sample value, which is the size
        of the disappointment PBO gives the frequency of.

    Raises:
        ValueError: Fewer than two variants (nothing to select between), an odd
            or too-small block count, or fewer bars than blocks.

    A single PBO number is noisy, and much noisier than its two decimal places
    suggest. Measured here on pure-noise variants with no edge at all, over 24
    independent samples of 1,500 bars and 20 variants: the mean lands near the
    theoretical 0.5, but the standard deviation is about 0.19 and individual
    draws ranged from 0.16 to 0.91. So a run reporting 0.37 is not evidence of
    a selection rule that works -- it is inside the null. Treat PBO as strong
    evidence only well away from 0.5, and read it beside
    ``performance_degradation`` rather than on its own.

    Cost grows as ``C(n_blocks, n_blocks/2)``: the default 16 blocks means
    12,870 splits and takes a few seconds.
    """
    matrix = np.asarray(
        returns_matrix.to_numpy() if hasattr(returns_matrix, "to_numpy") else returns_matrix,
        dtype=float,
    )
    if matrix.ndim != 2:
        raise ValueError(f"returns_matrix must be 2-D (bars x variants); got shape {matrix.shape}")
    n_bars, n_variants = matrix.shape
    if n_variants < 2:
        raise ValueError(
            f"PBO measures a choice between variants; got {n_variants} column(s). "
            "One variant was never selected, so it cannot have been overfitted by selection."
        )
    if n_blocks < 4 or n_blocks % 2:
        raise ValueError(f"n_blocks must be even and at least 4; got {n_blocks}")
    if n_bars < n_blocks * 2:
        raise ValueError(
            f"need at least {n_blocks * 2} bars to cut {n_blocks} usable blocks; got {n_bars}"
        )

    bounds = np.linspace(0, n_bars, n_blocks + 1).astype(int)
    block_sum = np.stack([matrix[bounds[i]:bounds[i + 1]].sum(axis=0) for i in range(n_blocks)])
    block_sumsq = np.stack([(matrix[bounds[i]:bounds[i + 1]] ** 2).sum(axis=0) for i in range(n_blocks)])
    block_len = np.diff(bounds).astype(float)

    all_blocks = np.arange(n_blocks)
    logits: List[float] = []
    degradations: List[float] = []
    for combo in itertools.combinations(range(n_blocks), n_blocks // 2):
        is_blocks = np.array(combo)
        oos_blocks = np.setdiff1d(all_blocks, is_blocks)

        is_sharpe = _block_sharpes(block_sum, block_sumsq, block_len, is_blocks)
        oos_sharpe = _block_sharpes(block_sum, block_sumsq, block_len, oos_blocks)

        winner = int(np.argmax(is_sharpe))
        # Rank of the winner among all variants out of sample, 1 = worst.
        rank = float(np.sum(oos_sharpe <= oos_sharpe[winner]))
        omega = rank / (n_variants + 1.0)
        omega = min(max(omega, 1e-12), 1.0 - 1e-12)
        logits.append(math.log(omega / (1.0 - omega)))
        degradations.append(float(is_sharpe[winner] - oos_sharpe[winner]))

    logit_array = np.array(logits)
    return {
        "pbo": round(float(np.mean(logit_array <= 0.0)), 6),
        "splits": len(logits),
        "n_variants": int(n_variants),
        "n_blocks": int(n_blocks),
        "median_logit": round(float(np.median(logit_array)), 6),
        "performance_degradation": round(float(np.mean(degradations)), 6),
    }


# ─── Runner integration ───


def run_validation(
    config: Dict[str, Any],
    equity_curve: pd.Series,
    trades: List[TradeRecord],
    initial_capital: float,
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Run configured validation checks.

    Reads from config["validation"]:
      - monte_carlo: {n_simulations, seed}
      - bootstrap: {n_bootstrap, confidence, seed}
      - equity_consistency: {n_windows}  (accepts the old name walk_forward)

    Args:
        config: Backtest config (must contain "validation" key).
        equity_curve: Equity time series.
        trades: Completed trades.
        initial_capital: Starting capital.
        bars_per_year: Annualisation factor.

    Returns:
        Dict keyed by validation type with results.
    """
    v_cfg = config.get("validation", {})
    results: Dict[str, Any] = {}

    if "monte_carlo" in v_cfg:
        mc_cfg = v_cfg["monte_carlo"] if isinstance(v_cfg["monte_carlo"], dict) else {}
        results["monte_carlo"] = monte_carlo_test(
            trades, initial_capital,
            n_simulations=mc_cfg.get("n_simulations", 1000),
            seed=mc_cfg.get("seed", 42),
        )

    if "bootstrap" in v_cfg:
        bs_cfg = v_cfg["bootstrap"] if isinstance(v_cfg["bootstrap"], dict) else {}
        results["bootstrap"] = bootstrap_sharpe_ci(
            equity_curve, bars_per_year=bars_per_year,
            n_bootstrap=bs_cfg.get("n_bootstrap", 1000),
            confidence=bs_cfg.get("confidence", 0.95),
            seed=bs_cfg.get("seed", 42),
        )

    # "walk_forward" is still read so an existing config keeps working, but the
    # result is reported under the name that describes it. Leaving it under the
    # old key would let the real walk-forward and this in-sample report collide.
    ec_key = "equity_consistency" if "equity_consistency" in v_cfg else "walk_forward"
    if ec_key in v_cfg:
        ec_cfg = v_cfg[ec_key] if isinstance(v_cfg[ec_key], dict) else {}
        results["equity_consistency"] = equity_consistency_report(
            equity_curve, trades,
            n_windows=ec_cfg.get("n_windows", 5),
            bars_per_year=bars_per_year,
        )

    return results


# ─── Standalone CLI ───


def _load_equity(run_dir: Path) -> pd.Series:
    """Load equity curve from artifacts/equity.csv."""
    path = run_dir / "artifacts" / "equity.csv"
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df["equity"]


def _load_trades(run_dir: Path) -> List[TradeRecord]:
    """Load trades from artifacts/trades.csv and convert to TradeRecord list."""
    path = run_dir / "artifacts" / "trades.csv"
    df = pd.read_csv(path)
    if df.empty:
        return []

    # trades.csv has entry+exit row pairs; extract exit rows (they have pnl != 0)
    trades = []
    exit_rows = df[df["pnl"] != 0].reset_index(drop=True)
    for _, row in exit_rows.iterrows():
        trades.append(TradeRecord(
            symbol=str(row.get("code", "")),
            direction=1 if row.get("side") == "sell" else -1,
            entry_price=0.0,
            exit_price=float(row.get("price", 0)),
            entry_time=pd.Timestamp(row.get("timestamp", "2000-01-01")),
            exit_time=pd.Timestamp(row.get("timestamp", "2000-01-01")),
            size=float(row.get("qty", 0)),
            leverage=1.0,
            pnl=float(row.get("pnl", 0)),
            pnl_pct=float(row.get("return_pct", 0)),
            exit_reason=str(row.get("reason", "signal")),
            holding_bars=int(row.get("holding_days", 0)),
            commission=0.0,
        ))
    return trades


def _parse_run_dir(argv: List[str]) -> Path:
    """Validate CLI input and return a usable run directory path."""
    if len(argv) < 2:
        raise SystemExit("Usage: python -m backtest.validation <run_dir>")

    raw_run_dir = argv[1]
    if not raw_run_dir.strip():
        raise SystemExit("run_dir must be a non-empty path")
    if "\0" in raw_run_dir:
        raise SystemExit("Invalid run_dir path: embedded NUL byte")

    try:
        run_dir = Path(raw_run_dir).expanduser()
        exists = run_dir.exists()
        is_dir = run_dir.is_dir() if exists else False
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Invalid run_dir path: {exc}") from exc

    if not exists:
        raise SystemExit(f"run_dir does not exist: {run_dir}")
    if not is_dir:
        raise SystemExit(f"run_dir is not a directory: {run_dir}")
    return run_dir


def main(run_dir: Path) -> Dict[str, Any]:
    """Run all three validations on existing backtest artifacts.

    Reads equity.csv, trades.csv, and config.json from run_dir.

    Args:
        run_dir: Directory with artifacts/ subdirectory.

    Returns:
        Validation results dict.
    """
    import json

    # Load config for initial_cash
    config_path = run_dir / "config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        config = {}
    initial_capital = config.get("initial_cash", 1_000_000)

    equity = _load_equity(run_dir)
    trades = _load_trades(run_dir)

    results = {
        "monte_carlo": monte_carlo_test(trades, initial_capital),
        "bootstrap": bootstrap_sharpe_ci(equity),
        "equity_consistency": equity_consistency_report(equity, trades),
    }

    # Write results
    out = run_dir / "artifacts" / "validation.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    import sys

    main(_parse_run_dir(sys.argv))
