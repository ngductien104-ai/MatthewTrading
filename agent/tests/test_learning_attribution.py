"""Tests for regime description and the cross-sectional base rate."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.learning.attribution import (
    MIN_PEERS,
    REGIME_LOOKBACK,
    cross_sectional_percentile,
    load_universe,
    market_state,
    peer_returns,
)


def series(closes, start="2024-01-01"):
    """Build an index frame indexed by trade date."""
    days = pd.bdate_range(start=start, periods=len(closes))
    frame = pd.DataFrame({"close": [float(value) for value in closes]}, index=days)
    frame.index.name = "trade_date"
    return frame


class TestMarketState:
    def test_short_history_says_nothing_rather_than_something_smaller(self):
        """A drawdown against 40 sessions is not a drawdown against a year.

        Relabelling it would make one column mean two things in one table.
        """
        frame = series([100.0] * 40)
        assert market_state(frame, str(frame.index[-1].date())) == ""

    def test_a_flat_year_reports_a_flat_state(self):
        frame = series([100.0] * (REGIME_LOOKBACK + 1))
        state = market_state(frame, str(frame.index[-1].date()))
        assert "dd252=+0.0%" in state
        assert "mom63=+0.0%" in state
        assert "mom21=+0.0%" in state

    def test_a_drawdown_from_the_years_high_is_measured_against_that_high(self):
        closes = [100.0] * 200 + list(np.linspace(100.0, 80.0, 53))
        frame = series(closes)
        state = market_state(frame, str(frame.index[-1].date()))
        assert "dd252=-20.0%" in state

    def test_momentum_uses_two_windows_that_can_disagree(self):
        """The state that matters: falling over three months, rising over one."""
        closes = [100.0] * 190 + list(np.linspace(100.0, 80.0, 42)) + list(
            np.linspace(80.0, 90.0, 21)
        )
        frame = series(closes)
        state = market_state(frame, str(frame.index[-1].date()))
        mom63 = state.split("mom63=")[1].split()[0]
        mom21 = state.split("mom21=")[1].split()[0]
        assert mom63.startswith("-")
        assert mom21.startswith("+")

    def test_a_day_outside_the_calendar_is_not_described(self):
        frame = series([100.0] * (REGIME_LOOKBACK + 1))
        assert market_state(frame, "2019-01-01") == ""

    def test_a_quiet_tape_ranks_low_on_realised_volatility(self):
        rng = np.random.default_rng(7)
        noisy = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.02, REGIME_LOOKBACK - 20)))
        calm = noisy[-1] * np.exp(np.cumsum(rng.normal(0, 0.001, 25)))
        frame = series(list(noisy) + list(calm))
        state = market_state(frame, str(frame.index[-1].date()))
        assert float(state.split("rv_pct=")[1]) < 0.2


class TestPeerReturns:
    def _peers(self, table):
        return {
            symbol: series(closes, start="2026-06-15") for symbol, closes in table.items()
        }

    def test_each_peer_is_measured_over_the_identical_window(self):
        peers = self._peers({"AAA": [100.0, 110.0], "BBB": [50.0, 45.0]})
        window = peer_returns(peers, "2026-06-15", "2026-06-16")
        assert window["AAA"] == pytest.approx(0.10)
        assert window["BBB"] == pytest.approx(-0.10)

    def test_the_call_itself_is_not_ranked_against_itself(self):
        peers = self._peers({"AAA": [100.0, 110.0], "BBB": [50.0, 45.0]})
        window = peer_returns(peers, "2026-06-15", "2026-06-16", exclude="AAA")
        assert set(window) == {"BBB"}

    def test_a_peer_that_did_not_trade_is_dropped_not_filled(self):
        """A suspended stock has no return over the window.

        Filling one would move the percentile the measurement exists to make.
        """
        peers = self._peers({"AAA": [100.0, 110.0]})
        peers["BBB"] = series([50.0], start="2026-06-15")
        window = peer_returns(peers, "2026-06-15", "2026-06-16")
        assert set(window) == {"AAA"}


class TestPercentile:
    def test_too_few_peers_buys_no_percentile(self):
        assert cross_sectional_percentile(0.1, {"A": 0.0, "B": 0.2}) is None

    def test_the_worst_of_the_field_ranks_at_the_bottom(self):
        peers = {str(index): index / 100 for index in range(MIN_PEERS)}
        assert cross_sectional_percentile(-1.0, peers) == pytest.approx(0.0)

    def test_the_best_of_the_field_ranks_at_the_top(self):
        peers = {str(index): index / 100 for index in range(MIN_PEERS)}
        assert cross_sectional_percentile(1.0, peers) == pytest.approx(1.0)

    def test_the_middle_of_the_field_ranks_in_the_middle(self):
        peers = {str(index): index / 100 for index in range(20)}
        assert cross_sectional_percentile(0.095, peers) == pytest.approx(0.5)

    def test_a_stock_that_fell_can_still_rank_well(self):
        """TPB fell 14,1% against an index down 9,4%.

        Whether that was bad for TPB or bad for everything is the question the
        index cannot answer and the cross-section can.
        """
        peers = {str(index): -0.20 + index / 500 for index in range(20)}
        assert cross_sectional_percentile(-0.141, peers) > 0.5


class TestLoadUniverse:
    def test_a_dead_peer_is_reported_and_the_rest_load(self):
        def fetch(symbol, start, end):
            if symbol == "DED":
                raise RuntimeError("no such symbol")
            return series([100.0, 110.0], start="2026-06-15")

        frames, problems = load_universe(fetch, ["AAA", "DED", "BBB"], "2026-06-15", "2026-06-16")
        assert set(frames) == {"AAA", "BBB"}
        assert len(problems) == 1 and "DED" in problems[0]

    def test_symbols_are_normalised_and_deduplicated(self):
        seen = []

        def fetch(symbol, start, end):
            seen.append(symbol)
            return series([100.0, 110.0], start="2026-06-15")

        load_universe(fetch, ["aaa.VN", "AAA", " bbb "], "2026-06-15", "2026-06-16")
        assert seen == ["AAA", "BBB"]

    def test_an_empty_frame_is_not_counted_as_a_peer(self):
        frames, _ = load_universe(
            lambda *_: pd.DataFrame(), ["AAA"], "2026-06-15", "2026-06-16"
        )
        assert frames == {}


def test_the_live_vn30_membership_has_the_shape_the_universe_loader_expects():
    """Ask the real reference source, rather than trusting a stub of it."""
    pytest.importorskip("vnstock_data")
    from src.learning.attribution import vn30_symbols

    try:
        symbols = vn30_symbols()
    except Exception as exc:  # noqa: BLE001 - the sponsored source may be down
        pytest.skip(f"VN30 membership unavailable: {exc}")
    assert len(symbols) == 30
    assert all(symbol.isalnum() and symbol.isupper() for symbol in symbols)
