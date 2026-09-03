"""Tests for the fitted moving-average crossover.

The point of this engine is that it can be overfitted. These tests check that
it actually selects, that the selection respects ``train_end``, and that it
reports the whole search rather than the winner -- because a deflated Sharpe
handed only the survivors is the error that function exists to prevent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest.strategies.fitted_sma import FittedSMA, fitted_sma_factory


def frame(closes, start="2022-01-03"):
    """Build an OHLCV frame indexed by business day."""
    index = pd.bdate_range(start=start, periods=len(closes))
    return pd.DataFrame({"close": [float(value) for value in closes]}, index=index)


def trending(n=600, seed=0, drift=0.0006, noise=0.012):
    """A series with a drift a crossover can actually find."""
    rng = np.random.default_rng(seed)
    return frame(100.0 * np.exp(np.cumsum(rng.normal(drift, noise, n))))


class TestSearch:
    def test_only_real_crossovers_are_scored(self):
        engine = FittedSMA(fast_grid=(5, 10, 30), slow_grid=(10, 30))
        assert (5, 10) in engine.pairs
        assert (10, 10) not in engine.pairs
        assert (30, 10) not in engine.pairs

    def test_it_chooses_a_pair_from_the_grid(self):
        engine = FittedSMA(fast_grid=(5, 20), slow_grid=(50, 120))
        fast, slow = engine.fit({"AAA": trending()})
        assert (fast, slow) in engine.pairs

    def test_every_variant_tried_is_reported_not_only_the_winner(self):
        """Passing only the survivors understates the search and inflates DSR."""
        engine = FittedSMA(fast_grid=(5, 10, 20), slow_grid=(50, 120, 200))
        engine.fit({"AAA": trending()})
        assert len(engine.trial_sharpes) == len(engine.pairs) == 9
        assert max(engine.trial_sharpes) == pytest.approx(
            max(score for _, _, score in engine.trials)
        )

    def test_the_winner_is_the_best_in_sample_score(self):
        engine = FittedSMA(fast_grid=(5, 10, 20), slow_grid=(50, 120))
        engine.fit({"AAA": trending()})
        best = max(engine.trials, key=lambda item: item[2])
        assert (engine.fast, engine.slow) == (best[0], best[1])

    def test_a_window_too_short_to_score_refuses_rather_than_defaulting(self):
        engine = FittedSMA(fast_grid=(5,), slow_grid=(200,))
        with pytest.raises(ValueError, match="no SMA pair scored"):
            engine.fit({"AAA": trending(n=30)})

    def test_a_flat_series_is_not_silently_fitted(self):
        engine = FittedSMA(fast_grid=(5,), slow_grid=(50,))
        with pytest.raises(ValueError, match="no SMA pair scored"):
            engine.fit({"AAA": frame([100.0] * 300)})

    def test_the_fit_is_scored_on_a_shifted_position(self):
        """Same-bar knowledge makes every pair look brilliant.

        A search scored without the shift selects for look-ahead, not signal,
        so the in-sample Sharpes must stay in a believable range.
        """
        engine = FittedSMA(fast_grid=(5, 20), slow_grid=(50, 120))
        engine.fit({"AAA": trending(seed=4)})
        assert max(engine.trial_sharpes) < 6.0


class TestTrainEnd:
    def test_the_search_stops_at_train_end(self):
        """Two engines differing only in the boundary must be able to disagree.

        If they never did, ``train_end`` would not be reaching the search.
        """
        data = {"AAA": trending(n=800, seed=11)}
        early = FittedSMA({"train_end": "2023-01-01"}, fast_grid=(5, 10, 20), slow_grid=(50, 120))
        whole = FittedSMA(fast_grid=(5, 10, 20), slow_grid=(50, 120))
        early.fit(data)
        whole.fit(data)
        assert early.trial_sharpes != whole.trial_sharpes

    def test_the_chosen_pair_is_applied_past_the_boundary(self):
        """Fitting in sample is the point; predicting only in sample is not."""
        data = {"AAA": trending(n=800, seed=2)}
        engine = FittedSMA({"train_end": "2023-01-01"}, fast_grid=(5, 20), slow_grid=(50, 120))
        signals = engine.generate(data)
        assert len(signals["AAA"]) == len(data["AAA"])
        assert signals["AAA"].loc["2024-01-02":].notna().all()

    def test_an_engine_with_no_boundary_says_it_saw_everything(self):
        assert FittedSMA().fitted_in_sample_only is False
        assert FittedSMA({"train_end": "2023-01-01"}).fitted_in_sample_only is True

    def test_bars_after_the_boundary_cannot_change_the_fit(self):
        """The decisive check: rewrite the future and the fit must not move."""
        base = trending(n=700, seed=5)
        tampered = base.copy()
        tampered.loc[tampered.index > pd.Timestamp("2023-06-01"), "close"] *= 3.0

        kwargs = {"fast_grid": (5, 10, 20), "slow_grid": (50, 120)}
        honest = FittedSMA({"train_end": "2023-06-01"}, **kwargs)
        honest.fit({"AAA": base})
        forged = FittedSMA({"train_end": "2023-06-01"}, **kwargs)
        forged.fit({"AAA": tampered})

        assert (honest.fast, honest.slow) == (forged.fast, forged.slow)
        assert honest.trial_sharpes == pytest.approx(forged.trial_sharpes)


class TestFactory:
    def test_each_fold_gets_an_engine_that_has_learned_nothing_yet(self):
        build = fitted_sma_factory(fast_grid=(5, 20), slow_grid=(50, 120))
        first = build({"train_end": "2023-01-01"})
        first.fit({"AAA": trending(n=700)})
        second = build({"train_end": "2024-01-01"})
        assert second.fast is None and second.trial_sharpes == []
        assert second.train_end != first.train_end

    def test_the_factory_signature_matches_what_walk_forward_calls(self):
        from backtest.walkforward import walk_forward
        import inspect

        annotation = inspect.signature(walk_forward).parameters["signal_engine_factory"]
        assert "Dict[str, Any]" in str(annotation.annotation)
        assert isinstance(fitted_sma_factory()({"train_end": "2023-01-01"}), FittedSMA)


def test_a_fitted_strategy_makes_the_deflated_sharpe_say_something():
    """The reason this engine exists.

    Against a rule with no fitted parameters the search is of size one, and a
    deflation against one trial is arithmetic with no content. With a real
    search the trial dispersion moves the hurdle, and the suite has something
    to charge for.
    """
    from backtest.validation import deflated_sharpe_ratio, expected_max_sharpe

    data = {"AAA": trending(n=900, seed=8)}
    engine = FittedSMA(fast_grid=(5, 10, 15, 20, 30), slow_grid=(50, 80, 120, 200))
    engine.fit(data)

    assert len(engine.trial_sharpes) >= 15
    hurdle = expected_max_sharpe(engine.trial_sharpes)
    assert hurdle > 0, "a real search must raise the bar above zero"

    close = data["AAA"]["close"]
    held = (
        close.rolling(engine.fast).mean() > close.rolling(engine.slow).mean()
    ).astype(float).shift(1)
    returns = (close.pct_change() * held).dropna()

    result = deflated_sharpe_ratio(returns, engine.trial_sharpes)
    assert result["n_trials"] == len(engine.trial_sharpes)
    assert result["expected_max_sharpe"] == pytest.approx(hurdle)
    assert 0.0 <= result["dsr"] <= 1.0
