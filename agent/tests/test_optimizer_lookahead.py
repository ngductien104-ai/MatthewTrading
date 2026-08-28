"""Regression: the optimizer overlay must not see the bar it is sizing.

``BaseOptimizer.optimize`` used ``ret.loc[:dt]``, which is inclusive of ``dt``,
so the realised return of the very bar being sized fed the covariance matrix
used to size it. ``BaseEngine._align`` shifts signals correctly; this overlay
re-introduced a one-bar look-ahead on top of that shift.

The shock test below is the falsifiable form of that claim: perturb only the
return on date ``dt`` and every weight on ``dt`` must be byte-identical.
"""

import numpy as np
import pandas as pd

from backtest.optimizers.risk_parity import optimize as risk_parity_optimize


def _panel(n_dates: int = 120, seed: int = 7):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n_dates)
    codes = ["AAA.VN", "BBB.VN", "CCC.VN"]
    ret = pd.DataFrame(
        rng.normal(0, 0.015, size=(n_dates, len(codes))), index=dates, columns=codes
    )
    pos = pd.DataFrame(1.0, index=dates, columns=codes)
    return ret, pos, dates


def test_weights_ignore_the_return_of_the_bar_being_sized():
    ret, pos, dates = _panel()
    shocked_at = dates[100]

    base = risk_parity_optimize(ret, pos, dates, lookback=60)

    ret_shocked = ret.copy()
    ret_shocked.loc[shocked_at] = [0.90, -0.85, 0.75]  # violent, one bar only
    shocked = risk_parity_optimize(ret_shocked, pos, dates, lookback=60)

    pd.testing.assert_series_equal(
        base.loc[shocked_at], shocked.loc[shocked_at], check_names=False
    )


def test_the_shock_still_moves_later_weights():
    """Guard against a vacuous pass: the shock must matter *somewhere*.

    If it changed nothing anywhere, the test above would pass for the wrong
    reason (e.g. the optimizer silently skipping every date).
    """
    ret, pos, dates = _panel()
    shocked_at = dates[100]

    base = risk_parity_optimize(ret, pos, dates, lookback=60)
    ret_shocked = ret.copy()
    ret_shocked.loc[shocked_at] = [0.90, -0.85, 0.75]
    shocked = risk_parity_optimize(ret_shocked, pos, dates, lookback=60)

    assert not base.loc[dates[101]].equals(shocked.loc[dates[101]])
