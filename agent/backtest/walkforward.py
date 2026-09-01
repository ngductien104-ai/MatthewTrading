"""Walk-forward evaluation: fit on a train window, measure on an unseen one.

This is the module :func:`backtest.validation.equity_consistency_report` was
misnamed after. That function slices one curve produced by one fit. This one
re-runs the engine once per fold and keeps only the bars the fold had never
been shown, then stitches those pieces into a single out-of-sample path.

What this module guarantees, and what it cannot
-----------------------------------------------
It guarantees out-of-sample **evaluation**: no bar reaches the stitched path
unless it fell after that fold's ``train_end``, and an embargo drops the bars
immediately after the training window so a position still open at the boundary
is not scored on both sides of it.

It cannot guarantee out-of-sample **fitting**. The engine has no separate fit
step -- ``SignalEngine.generate(data_map)`` receives the frames and returns
signals -- so each fold config carries ``train_end`` and ``oos_start`` and it is
the signal engine's job to honour them. A signal engine that consults data past
``train_end`` when choosing its parameters is not being cross-validated here,
and no amount of fold arithmetic in this module would detect that. Saying so is
the point: the function this replaces promised out-of-sample evidence in its
name and delivered none, and a second module making a quieter version of the
same promise would be no improvement.

Each fold is warmed with its whole training window rather than starting cold at
``test_start``, because an indicator with a 200-bar lookback produces nothing
useful over its first 200 bars, and a fold that began at the test boundary
would be measuring the warm-up instead of the strategy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

import pandas as pd


class WalkForwardError(RuntimeError):
    """A fold could not be built, or could not be run."""


@dataclass(frozen=True)
class Fold:
    """One train/test window pair, in dates.

    Attributes:
        index: Zero-based fold number, in time order.
        train_start: First bar the signal engine may look at.
        train_end: Last in-sample bar. Nothing after this may inform the fit.
        test_start: First out-of-sample bar, separated from ``train_end`` by the
            embargo rather than adjacent to it.
        test_end: Last out-of-sample bar.
    """

    index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp

    def as_dict(self) -> Dict[str, Any]:
        """Return the fold as JSON-safe ISO dates for a run card."""
        return {
            "index": self.index,
            "train_start": self.train_start.date().isoformat(),
            "train_end": self.train_end.date().isoformat(),
            "test_start": self.test_start.date().isoformat(),
            "test_end": self.test_end.date().isoformat(),
        }


def make_folds(
    dates: Sequence[pd.Timestamp] | pd.DatetimeIndex,
    *,
    n_folds: int = 5,
    train_bars: int | None = None,
    embargo_bars: int = 0,
    anchored: bool = False,
) -> List[Fold]:
    """Cut a date index into consecutive train/test folds.

    Test windows tile the tail of the sample and never overlap, so the stitched
    path visits each out-of-sample bar exactly once.

    Args:
        dates: Trading dates, ascending.
        n_folds: Number of out-of-sample windows.
        train_bars: Length of the training window. ``None`` gives every fold
            the same training length the first fold can afford once all the
            test windows and the embargo are reserved.
        embargo_bars: Bars dropped between ``train_end`` and ``test_start``. A
            position open across the boundary is otherwise scored twice.
        anchored: Grow the training window from a fixed start instead of
            rolling it forward. Anchored uses more history; rolling adapts to
            regime change. Neither is right in general, so neither is default
            behaviour disguised as a fact.

    Returns:
        Folds in time order.

    Raises:
        WalkForwardError: Fewer than two folds, a negative embargo, an
            unsorted index, or too few bars to give every fold both windows.
    """
    index = pd.DatetimeIndex(dates)
    if n_folds < 2:
        raise WalkForwardError(f"walk-forward needs at least 2 folds; got {n_folds}")
    if embargo_bars < 0:
        raise WalkForwardError(f"embargo_bars cannot be negative; got {embargo_bars}")
    if not index.is_monotonic_increasing:
        raise WalkForwardError("dates must be sorted ascending before folding")

    n = len(index)
    test_size = n // (n_folds + 1)
    if test_size < 1:
        raise WalkForwardError(
            f"{n} bars cannot make {n_folds} test windows; need at least {n_folds + 1}"
        )

    first_test_start = n - n_folds * test_size
    train_span = first_test_start - embargo_bars
    if train_span < 1:
        raise WalkForwardError(
            f"{n} bars leave no training window before the first test fold: the test "
            f"windows take {n_folds * test_size} bars and the embargo takes {embargo_bars}"
        )

    folds: List[Fold] = []
    for i in range(n_folds):
        test_lo = first_test_start + i * test_size
        test_hi = n - 1 if i == n_folds - 1 else test_lo + test_size - 1
        train_hi = test_lo - embargo_bars - 1
        if train_hi < 0:
            raise WalkForwardError(f"fold {i} has no training bars left after the embargo")
        if anchored:
            train_lo = 0
        else:
            span = train_span if train_bars is None else int(train_bars)
            train_lo = max(0, train_hi + 1 - span)
        if train_lo > train_hi:
            raise WalkForwardError(f"fold {i} has an empty training window")
        folds.append(
            Fold(
                index=i,
                train_start=index[train_lo],
                train_end=index[train_hi],
                test_start=index[test_lo],
                test_end=index[test_hi],
            )
        )
    return folds


def _oos_returns(fold_dir: Path, fold: Fold) -> pd.Series:
    """Read one fold's equity and return only its out-of-sample per-bar returns."""
    path = fold_dir / "artifacts" / "equity.csv"
    if not path.exists():
        raise WalkForwardError(
            f"fold {fold.index} ({fold.test_start.date()}..{fold.test_end.date()}) "
            f"produced no equity curve at {path}"
        )
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    if "equity" not in frame.columns:
        raise WalkForwardError(f"fold {fold.index} equity.csv has no 'equity' column")

    # Returns are differenced across the whole fold and only then sliced, so the
    # first out-of-sample bar keeps the move that carried into it rather than
    # silently starting flat.
    returns = frame["equity"].pct_change()
    mask = (returns.index >= fold.test_start) & (returns.index <= fold.test_end)
    oos = returns.loc[mask].fillna(0.0)
    if oos.empty:
        raise WalkForwardError(
            f"fold {fold.index} produced no bars inside its test window "
            f"{fold.test_start.date()}..{fold.test_end.date()}"
        )
    return oos


def walk_forward(
    config: Dict[str, Any],
    loader: Any,
    signal_engine_factory: Callable[[], Any],
    run_dir: Path,
    *,
    dates: Sequence[pd.Timestamp] | pd.DatetimeIndex,
    n_folds: int = 5,
    train_bars: int | None = None,
    embargo_bars: int = 0,
    anchored: bool = False,
    bars_per_year: int = 252,
    engine_factory: Callable[[Dict[str, Any]], Any] | None = None,
) -> Dict[str, Any]:
    """Run one backtest per fold and stitch the out-of-sample pieces together.

    Args:
        config: Base backtest config. Each fold gets a copy carrying its own
            dates plus ``train_end`` and ``oos_start``.
        loader: Data loader, passed through to the engine unchanged.
        signal_engine_factory: Called once per fold. A factory rather than an
            instance, so a stateful signal engine cannot carry what it learned
            in one fold into the next.
        run_dir: Parent directory. Each fold writes into ``fold_00``,
            ``fold_01`` and so on, keeping its own artifacts and run card, so
            any single fold can be reproduced on its own.
        dates: The full trading date index the folds are cut from.
        n_folds: Number of out-of-sample windows.
        train_bars: Training window length, or None for the longest available.
        embargo_bars: Bars dropped between training and test.
        anchored: Expanding training window instead of rolling.
        bars_per_year: Annualisation factor.
        engine_factory: Builds the engine for each fold, given that fold's
            config. Defaults to the VN equity engine. It takes the config
            because the engines do: capital, commission and the exchange map
            all come from it, and an engine built once and reused would carry
            one fold's spent capital and open trades into the next.

    Returns:
        Dict with ``folds`` and their per-fold numbers, the stitched
        ``oos_metrics``, and ``oos_equity`` as a Series.

    Raises:
        WalkForwardError: A fold could not be built, stopped the engine, or
            produced no test bars. A walk-forward with a hole in it is not a
            walk-forward, so this stops rather than quietly reporting a shorter
            path than it claims to have measured.
    """
    from backtest.metrics import calc_metrics

    if engine_factory is None:
        from backtest.engines.vn_equity import VNEquityEngine

        engine_factory = VNEquityEngine

    folds = make_folds(
        dates,
        n_folds=n_folds,
        train_bars=train_bars,
        embargo_bars=embargo_bars,
        anchored=anchored,
    )

    run_dir = Path(run_dir)
    pieces: List[pd.Series] = []
    per_fold: List[Dict[str, Any]] = []

    for fold in folds:
        fold_dir = run_dir / f"fold_{fold.index:02d}"
        fold_dir.mkdir(parents=True, exist_ok=True)

        fold_config = dict(config)
        fold_config["start_date"] = fold.train_start.date().isoformat()
        fold_config["end_date"] = fold.test_end.date().isoformat()
        # The boundary the signal engine is expected to respect. This module
        # hands it over and cannot enforce it; see the module docstring.
        fold_config["train_end"] = fold.train_end.date().isoformat()
        fold_config["oos_start"] = fold.test_start.date().isoformat()
        fold_config["_run_card_warnings"] = list(config.get("_run_card_warnings") or []) + [
            f"WALK-FORWARD FOLD {fold.index}: in sample through {fold.train_end.date()}, "
            f"scored on {fold.test_start.date()}..{fold.test_end.date()}. Only the scored "
            "window enters the stitched out-of-sample path, and the metrics in this "
            "fold's own run card cover the whole window including training."
        ]

        try:
            metrics = engine_factory(fold_config).run_backtest(
                fold_config,
                loader,
                signal_engine_factory(),
                fold_dir,
                bars_per_year=bars_per_year,
            )
        except SystemExit as exc:  # the engine exits the process on bad input
            raise WalkForwardError(
                f"fold {fold.index} ({fold.train_start.date()}..{fold.test_end.date()}) "
                f"stopped the engine (exit code {exc.code}); the remaining folds were "
                "not run"
            ) from exc

        oos = _oos_returns(fold_dir, fold)
        pieces.append(oos)
        per_fold.append({
            **fold.as_dict(),
            "oos_bars": int(len(oos)),
            "oos_return": round(float((1 + oos).prod() - 1), 6),
            "whole_window_sharpe": round(float(metrics.get("sharpe", 0.0) or 0.0), 4),
        })

    stitched = pd.concat(pieces).sort_index()
    if stitched.index.has_duplicates:
        raise WalkForwardError(
            "test windows overlap, so the stitched path would score some bars twice"
        )

    initial_cash = float(config.get("initial_cash", 1_000_000))
    oos_equity = (1 + stitched).cumprod() * initial_cash
    oos_metrics = calc_metrics(
        oos_equity,
        [],
        initial_cash,
        bars_per_year,
        risk_free=float(config.get("risk_free", 0.0) or 0.0),
    )

    summary: Dict[str, Any] = {
        "n_folds": len(folds),
        "anchored": bool(anchored),
        "embargo_bars": int(embargo_bars),
        "oos_bars": int(len(stitched)),
        "folds": per_fold,
        "oos_metrics": {k: v for k, v in oos_metrics.items() if not isinstance(v, dict)},
    }

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "walk_forward.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    oos_equity.rename("equity").to_csv(run_dir / "oos_equity.csv", index_label="timestamp")

    summary["oos_equity"] = oos_equity
    return summary
