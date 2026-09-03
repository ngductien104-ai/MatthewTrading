"""A moving-average crossover whose lengths are *fitted*, not chosen.

Why this exists at all
----------------------
Stage 2.1 built purged cross-validation, CPCV, PSR, the deflated Sharpe and
PBO, and then ran them against buy-and-hold and a hard-coded SMA(20/50). Both
results were the same shape of nothing: CPCV returned five out-of-sample paths
that were *identical*, standard deviation exactly zero, and walk-forward
returned an out-of-sample Sharpe of -0,2785 against an in-sample -0,2832.

Neither was a bug. Every one of those tools measures the gap that opens between
what a fit looked like on the data it was fitted to and what it does next. A
rule with no fitted parameters has no such gap, so the tools correctly reported
that there was nothing to report -- and a number that looks like a result and
carries no information is worse than no number, because it reads as evidence of
validation on a checklist.

So this engine picks its lengths by search: it scores every ``(fast, slow)``
pair on the training window and keeps the best. That is a real selection over
real trials, which means it can be genuinely overfitted, which is the
precondition for the anti-overfit suite to say anything at all. The selection is
also what :func:`~backtest.validation.deflated_sharpe_ratio` needs declared --
:attr:`FittedSMA.trial_sharpes` reports every variant tried, not only the
winner, since passing the survivors alone is the specific error that function
exists to prevent.

The look-ahead boundary
-----------------------
``train_end`` comes from the fold config. Bars after it are excluded from the
*search* and from nothing else: the chosen pair is then applied across the whole
frame, because that is what running a fitted strategy forward means. Without a
``train_end`` the engine fits on everything it is given, which is honest for a
single in-sample backtest and is exactly the look-ahead the walk-forward is
there to remove -- so it says which mode it is in on the instance.
"""

from __future__ import annotations

from itertools import product
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

#: Candidate fast lengths.
DEFAULT_FAST = (5, 10, 15, 20, 30)

#: Candidate slow lengths. Pairs where slow <= fast are not a crossover and are
#: dropped rather than scored, so the trial count reflects real variants.
DEFAULT_SLOW = (30, 50, 80, 120, 200)


def _sharpe(returns: pd.Series, bars_per_year: int = 252) -> float:
    """Return an annualised Sharpe, or ``-inf`` when it is undefined.

    ``-inf`` rather than zero: a variant that never traded, or never varied,
    must lose the search outright instead of tying with a genuine loser.
    """
    values = np.asarray(returns.dropna(), dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return float("-inf")
    sd = float(values.std(ddof=1))
    if sd <= 0:
        return float("-inf")
    return float(values.mean() / sd * np.sqrt(bars_per_year))


class FittedSMA:
    """Long when the fast average leads the slow one, with lengths fitted.

    Attributes:
        fast: Fitted fast length, available after :meth:`generate`.
        slow: Fitted slow length.
        trial_sharpes: In-sample annualised Sharpe of every pair scored, in
            search order. Hand this to ``deflated_sharpe`` so the deflation
            charges for the whole search rather than the one that won it.
        fitted_in_sample_only: Whether a ``train_end`` bounded the search. False
            means the parameters saw every bar they are scored on.
    """

    def __init__(
        self,
        config: Dict[str, Any] | None = None,
        *,
        fast_grid: Sequence[int] = DEFAULT_FAST,
        slow_grid: Sequence[int] = DEFAULT_SLOW,
        bars_per_year: int = 252,
    ) -> None:
        config = config or {}
        self.train_end = config.get("train_end")
        self.fast_grid = tuple(int(value) for value in fast_grid)
        self.slow_grid = tuple(int(value) for value in slow_grid)
        self.bars_per_year = int(bars_per_year)
        self.fast: int | None = None
        self.slow: int | None = None
        self.trial_sharpes: List[float] = []
        self.trials: List[Tuple[int, int, float]] = []
        self.fitted_in_sample_only = self.train_end is not None

    @property
    def pairs(self) -> List[Tuple[int, int]]:
        """Return the candidate pairs, slow strictly longer than fast."""
        return [
            (fast, slow)
            for fast, slow in product(self.fast_grid, self.slow_grid)
            if slow > fast
        ]

    @staticmethod
    def _positions(close: pd.Series, fast: int, slow: int) -> pd.Series:
        """Return the 1/0 target weight for one pair."""
        return (close.rolling(fast).mean() > close.rolling(slow).mean()).astype(float)

    def _score(self, frames: Dict[str, pd.DataFrame], fast: int, slow: int) -> float:
        """Return the equal-weight in-sample Sharpe of one pair."""
        legs = []
        for frame in frames.values():
            close = frame["close"]
            # The position is shifted before it meets the return it earns.
            # Without the shift the fit is scored on same-bar knowledge and
            # every pair looks brilliant, which would make the search select
            # for look-ahead rather than for signal.
            held = self._positions(close, fast, slow).shift(1)
            legs.append(close.pct_change() * held)
        if not legs:
            return float("-inf")
        return _sharpe(pd.concat(legs, axis=1).mean(axis=1), self.bars_per_year)

    def fit(self, data_map: Dict[str, pd.DataFrame]) -> Tuple[int, int]:
        """Choose the pair with the best in-sample Sharpe.

        Args:
            data_map: Symbol to OHLCV frame, indexed by date.

        Returns:
            The chosen ``(fast, slow)``.

        Raises:
            ValueError: The training window scored no usable variant -- too
                few bars for the shortest pair, or no price variation at all.
                Falling back to an arbitrary default here would report a fitted
                strategy that was never fitted.
        """
        train = data_map
        if self.train_end is not None:
            cutoff = pd.Timestamp(self.train_end)
            train = {
                code: frame.loc[frame.index <= cutoff] for code, frame in data_map.items()
            }
            train = {code: frame for code, frame in train.items() if not frame.empty}

        self.trials = [(fast, slow, self._score(train, fast, slow)) for fast, slow in self.pairs]
        self.trial_sharpes = [score for _, _, score in self.trials if np.isfinite(score)]
        usable = [item for item in self.trials if np.isfinite(item[2])]
        if not usable:
            raise ValueError(
                f"no SMA pair scored on the training window ({len(self.pairs)} tried, "
                f"train_end={self.train_end}): too few bars for the shortest pair, or a "
                "flat series. A default pair here would report a fit that never happened."
            )
        self.fast, self.slow, _ = max(usable, key=lambda item: item[2])
        return self.fast, self.slow

    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        """Fit on the training window, then apply the fit across every bar."""
        self.fit(data_map)
        return {
            code: self._positions(frame["close"], self.fast, self.slow)
            for code, frame in data_map.items()
        }


def fitted_sma_factory(
    *, fast_grid: Sequence[int] = DEFAULT_FAST, slow_grid: Sequence[int] = DEFAULT_SLOW
):
    """Return a factory matching ``walk_forward``'s ``signal_engine_factory``.

    A factory, not an instance: each fold must fit from scratch, or fold two
    starts out already knowing what fold one learned.
    """

    def build(config: Dict[str, Any]) -> FittedSMA:
        return FittedSMA(config, fast_grid=fast_grid, slow_grid=slow_grid)

    return build
