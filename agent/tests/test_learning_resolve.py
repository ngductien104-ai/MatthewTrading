"""Tests for the outcome resolver.

The synthetic frames here carry ``adj_rate`` and are shaped exactly like the
output of ``vndata.price.to_vnd``, because that is the contract the resolver
actually meets. The last test in the file goes through the real DataPro path
and is the one that would catch the frame drifting out from under these -- a
stub is always an easier contract than the real source, which is the lesson the
walk-forward module paid for.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.learning.records import CallRecord, Evidence, Outcome
from src.learning.resolve import (
    ACTION_DIRECTION,
    BENCHMARK_SYMBOL,
    NO_CLAIM,
    VN30_SYMBOL,
    resolve_ledger,
    score_call,
)
from src.learning.store import LearningStore, append_call_with_evidence

KNOWN_AT = "2026-06-15T09:00:00Z"


def frame(closes, *, adj_rate=1.0, low_scale=1.0, high_scale=1.0, start="2026-06-15"):
    """Build a frame shaped like ``vndata.price.to_vnd`` output.

    ``adj_rate`` is the cumulative back-adjustment factor, so a value above 1.0
    reproduces the case that matters: a series whose historical closes have been
    marked down by a dividend paid since.
    """
    days = pd.bdate_range(start=start, periods=len(closes))
    rates = adj_rate if isinstance(adj_rate, (list, tuple)) else [adj_rate] * len(closes)
    data = pd.DataFrame(
        {
            "close": [float(value) for value in closes],
            "low": [float(value) * low_scale for value in closes],
            "high": [float(value) * high_scale for value in closes],
            "adj_rate": [float(value) for value in rates],
        },
        index=days,
    )
    data.index.name = "trade_date"
    return data


def call(**overrides):
    """Build a call anchored on the first session of the synthetic calendar."""
    fields = {
        "ticker": "TST",
        "as_of": "2026-06-15",
        "action": "accumulate",
        "known_at": KNOWN_AT,
        "ref_price": 100.0,
        "target": 130.0,
        "confidence": 0.6,
        "source_session_id": "sess",
        "source_event_sha256": "abc123",
    }
    fields.update(overrides)
    return CallRecord(**fields)


def score(prices, benchmark, *, record=None, checkpoints=(21,), **kwargs):
    """Score one call at the 21-session checkpoint."""
    return score_call(
        record or call(),
        prices=prices,
        benchmark=benchmark,
        checkpoints=checkpoints,
        **kwargs,
    )


FLAT_BENCHMARK = frame([1000.0] * 30)


class TestDirection:
    def test_every_action_is_assigned_a_direction(self):
        from src.learning.records import ACTIONS

        assert set(ACTION_DIRECTION) == set(ACTIONS)

    def test_a_long_call_that_beats_the_index_is_a_hit(self):
        report = score(frame([100.0] * 21 + [120.0] * 9), FLAT_BENCHMARK)
        assert [item.verdict for item in report.outcomes] == ["hit"]
        assert report.outcomes[0].alpha == pytest.approx(0.20)

    def test_a_long_call_that_lags_the_index_is_a_miss(self):
        rising = frame([1000.0] * 21 + [1300.0] * 9)
        report = score(frame([100.0] * 21 + [120.0] * 9), rising)
        assert [item.verdict for item in report.outcomes] == ["miss"]

    def test_a_stay_away_call_is_right_when_the_ticker_underperforms(self):
        record = call(action="avoid", target=None, confidence=None)
        report = score(frame([100.0] * 21 + [80.0] * 9), FLAT_BENCHMARK, record=record)
        assert [item.verdict for item in report.outcomes] == ["hit"]

    def test_a_stay_away_call_is_wrong_when_the_ticker_runs_without_it(self):
        record = call(action="avoid", target=None, confidence=None)
        report = score(frame([100.0] * 21 + [130.0] * 9), FLAT_BENCHMARK, record=record)
        assert [item.verdict for item in report.outcomes] == ["miss"]

    @pytest.mark.parametrize("action", ["hold", "neutral"])
    def test_an_action_with_no_direction_is_measured_but_not_graded(self, action):
        record = call(action=action, target=None, confidence=None)
        report = score(frame([100.0] * 21 + [130.0] * 9), FLAT_BENCHMARK, record=record)
        outcome = report.outcomes[0]
        assert outcome.verdict == NO_CLAIM
        assert outcome.realized_ret == pytest.approx(0.30)
        assert outcome.alpha == pytest.approx(0.30)
        assert "no direction" in outcome.notes


class TestStop:
    def test_a_long_call_stopped_out_mid_window_is_invalidated_not_a_hit(self):
        """The MWG shape: through the stop on the way to finishing well up.

        Scoring this on the closing price alone would credit a position nobody
        was still holding.
        """
        prices = frame([100.0] * 5 + [88.0] * 3 + [130.0] * 22, low_scale=0.99)
        report = score(prices, FLAT_BENCHMARK, record=call(stop=90.0))
        outcome = report.outcomes[0]
        assert outcome.verdict == "invalidated"
        assert outcome.trigger_fired is True
        assert outcome.realized_ret == pytest.approx(0.30)
        assert "traded through" in outcome.notes

    def test_a_stop_the_price_never_reached_leaves_the_verdict_alone(self):
        prices = frame([100.0] * 21 + [130.0] * 9, low_scale=0.99)
        report = score(prices, FLAT_BENCHMARK, record=call(stop=50.0))
        assert report.outcomes[0].verdict == "hit"
        assert report.outcomes[0].trigger_fired is False

    def test_a_flat_back_adjustment_does_not_fabricate_a_breach(self):
        """Adjusted lows sit at 90.0 but the stop was quoted on the same grid
        shift, so at 90/1.1 it was never reached."""
        prices = frame([100.0] * 30, adj_rate=1.1, low_scale=0.9)
        report = score(prices, FLAT_BENCHMARK, record=call(stop=90.0))
        assert report.outcomes[0].trigger_fired is False

    def test_a_corporate_action_inside_the_window_does_not_fake_a_breach(self):
        """The PET shape: a 1,45x action mid-window drops the traded price 32%
        while the stock is flat. Testing a quoted stop against the later traded
        grid would report a stop-out that never happened."""
        rates = [1.45] * 5 + [1.0] * 25
        prices = frame([100.0] * 30, adj_rate=rates, low_scale=0.99)
        outcome = score(prices, FLAT_BENCHMARK, record=call(stop=130.0)).outcomes[0]
        assert outcome.realized_ret == pytest.approx(0.0)
        assert outcome.trigger_fired is False

    def test_a_stop_on_a_stay_away_call_is_not_checked(self):
        """BSR waits at 26.350 for 24.000 with a "stop" at 24.900, between the
        two. Which side that level guards is not machine-decidable."""
        record = call(action="wait", stop=95.0, target=80.0)
        prices = frame([100.0] * 21 + [80.0] * 9, low_scale=0.9)
        outcome = score(prices, FLAT_BENCHMARK, record=record).outcomes[0]
        assert outcome.trigger_fired is False
        assert outcome.verdict == "hit"


class TestBasis:
    def test_the_return_comes_from_the_close_not_the_stated_ref_price(self):
        """PHR states 62.000 against a 63.000 close -- an entry level.

        Measuring from it would fold a 1,6% entry gap into the return.
        """
        prices = frame([100.0] * 21 + [110.0] * 9)
        report = score(prices, FLAT_BENCHMARK, record=call(ref_price=98.0))
        assert report.outcomes[0].realized_ret == pytest.approx(0.10)
        assert any("entry level, not a close" in text for text in report.warnings)

    def test_a_ref_price_matching_the_traded_close_raises_no_warning(self):
        prices = frame([100.0] * 30, adj_rate=1.1)
        report = score(prices, FLAT_BENCHMARK, record=call(ref_price=110.0))
        assert report.warnings == []

    def test_the_return_is_dividend_consistent_where_the_quoted_price_is_not(self):
        """BSR's 17/06 close reads 26.056 today but traded at 26.350.

        The adjusted series is flat across the dividend; the traded grid is not,
        and a return taken off the traded grid would invent a 9% loss.
        """
        rates = [1.1] * 10 + [1.0] * 20
        prices = frame([100.0] * 30, adj_rate=rates)
        outcome = score(prices, FLAT_BENCHMARK).outcomes[0]
        assert outcome.realized_ret == pytest.approx(0.0)
        assert outcome.resolved_price == pytest.approx(100.0)

    def test_the_target_is_moved_onto_the_grid_the_outcome_is_measured_on(self):
        prices = frame([100.0] * 30, adj_rate=1.1)
        outcome = score(prices, FLAT_BENCHMARK, record=call(target=110.0)).outcomes[0]
        assert outcome.target_error == pytest.approx(0.0)

    def test_a_corporate_action_does_not_flip_the_sign_of_the_target_error(self):
        """PET as shipped: 44.000 target, 1,45x action, a 1,07% loss.

        Against the raw traded close the target error reads -15%, as if the
        price had undershot; on a single grid it is +23%, an overshoot. The
        sign of every target error through a corporate action depends on this.
        """
        rates = [1.45] * 5 + [1.0] * 25
        prices = frame([100.0] * 21 + [98.93] * 9, adj_rate=rates)
        outcome = score(prices, FLAT_BENCHMARK, record=call(target=80.0)).outcomes[0]
        assert outcome.realized_ret == pytest.approx(-0.0107, abs=1e-4)
        assert outcome.target_error == pytest.approx(0.7934, abs=1e-3)
        assert outcome.target_error > 0

    def test_a_call_with_no_target_carries_no_target_error(self):
        record = call(target=None, confidence=None)
        outcome = score(frame([100.0] * 30), FLAT_BENCHMARK, record=record).outcomes[0]
        assert outcome.target_error is None


class TestCalendar:
    def test_a_checkpoint_the_calendar_has_not_reached_is_pending_not_open(self):
        report = score(frame([100.0] * 30), FLAT_BENCHMARK, checkpoints=(21, 63, 126))
        assert len(report.outcomes) == 1
        assert [item.checkpoint_sessions for item in report.pending] == [63, 126]
        assert all("not elapsed" in item.reason for item in report.pending)

    def test_a_call_written_off_session_is_scored_from_the_next_session(self):
        record = call(as_of="2026-06-14", known_at="2026-06-14T09:00:00Z")
        report = score(frame([100.0] * 21 + [120.0] * 9), FLAT_BENCHMARK, record=record)
        assert report.outcomes[0].verdict == "hit"
        assert any("not a trading session" in text for text in report.warnings)

    def test_the_benchmark_supplies_the_calendar_so_holidays_need_no_list(self):
        """Two sessions of the benchmark are missing, as a holiday would leave
        them. The 21st checkpoint therefore lands two calendar days later."""
        full = FLAT_BENCHMARK
        gapped = full.drop(full.index[[5, 6]])
        prices = frame([100.0] * 21 + [120.0] * 9)
        outcome = score(prices, gapped).outcomes[0]
        assert outcome.resolved_at == str(gapped.index[21].date())


class TestSupersession:
    def test_a_revision_replaced_before_the_checkpoint_is_invalidated(self):
        first = call()
        later = CallRecord(
            ticker="TST",
            as_of="2026-06-22",
            action="sell",
            known_at="2026-06-22T09:00:00Z",
            episode_id=first.episode_id,
            revision=2,
            source_event_sha256="def456",
        )
        report = score(
            frame([100.0] * 21 + [120.0] * 9),
            FLAT_BENCHMARK,
            siblings=[first, later],
        )
        outcome = report.outcomes[0]
        assert outcome.verdict == "invalidated"
        assert "superseded by revision 2" in outcome.notes

    def test_a_revision_made_after_the_checkpoint_does_not_reach_back(self):
        first = call()
        later = CallRecord(
            ticker="TST",
            as_of="2026-08-03",
            action="sell",
            known_at="2026-08-03T09:00:00Z",
            episode_id=first.episode_id,
            revision=2,
            source_event_sha256="def456",
        )
        report = score(
            frame([100.0] * 21 + [120.0] * 9),
            FLAT_BENCHMARK,
            siblings=[first, later],
        )
        assert report.outcomes[0].verdict == "hit"


class TestHonesty:
    def test_unchecked_free_text_triggers_are_declared_rather_than_denied(self):
        record = call(invalidation_triggers=["Q2 EPS misses", "chairman resigns"])
        outcome = score(frame([100.0] * 30), FLAT_BENCHMARK, record=record).outcomes[0]
        assert outcome.trigger_fired is False
        assert "2 free-text trigger(s) not machine-checked" in outcome.notes

    def test_the_unattributed_regime_is_stated_not_left_to_look_measured(self):
        outcome = score(frame([100.0] * 30), FLAT_BENCHMARK).outcomes[0]
        assert outcome.regime == ""
        assert outcome.base_rate_pctile is None
        assert "base rate not attributed" in outcome.notes

    def test_the_window_extremes_survive_on_the_evidence(self):
        """The verdict is close-to-close, so the extremes are the only record of
        whether an entry a ``wait`` promised ever actually printed."""
        prices = frame([100.0] * 30, adj_rate=1.1, low_scale=0.8, high_scale=1.3)
        report = score(prices, FLAT_BENCHMARK)
        excerpt = report.evidence[0].excerpt
        assert "adj_low=80" in excerpt
        assert "adj_high=130" in excerpt
        assert "traded_low=88" in excerpt
        assert "traded_high=143" in excerpt
        assert "entry_adj_rate=1.1" in excerpt

    def test_evidence_is_observed_at_the_checkpoint_not_at_run_time(self):
        report = score(frame([100.0] * 30), FLAT_BENCHMARK)
        outcome = report.outcomes[0]
        for evidence in report.evidence:
            assert evidence.observed_at.startswith(outcome.resolved_at)

    def test_the_benchmark_series_is_cited_alongside_the_ticker(self):
        report = score(frame([100.0] * 30), FLAT_BENCHMARK)
        assert len(report.outcomes[0].evidence_ids) == 2
        assert any(BENCHMARK_SYMBOL in item.excerpt for item in report.evidence)


class TestLedgerPass:
    def _seed(self, store, record):
        evidence = Evidence(
            kind="research_report",
            observed_at=record.known_at,
            source_path="memo.md",
            excerpt="the memo",
        )
        record.evidence_ids = [evidence.evidence_id]
        append_call_with_evidence(store, record, [evidence])

    def _fetch(self, prices):
        def fetch(symbol, start, end):
            if symbol in (BENCHMARK_SYMBOL, VN30_SYMBOL):
                return FLAT_BENCHMARK
            return prices
        return fetch

    def test_a_pass_writes_outcomes_that_survive_the_evidence_wall(self, tmp_path):
        with LearningStore(tmp_path / "learning.db") as store:
            self._seed(store, call())
            report = resolve_ledger(
                store,
                fetch=self._fetch(frame([100.0] * 21 + [120.0] * 9)),
                today="2026-07-31",
                checkpoints=(21,),
            )
            assert store.counts()["outcomes"] == 1
            stored = store.outcomes_for(report.outcomes[0].call_id)
            assert [item.verdict for item in stored] == ["hit"]
            assert stored[0].vn30_ret is not None

    def test_a_dry_run_scores_without_writing(self, tmp_path):
        with LearningStore(tmp_path / "learning.db") as store:
            self._seed(store, call())
            report = resolve_ledger(
                store,
                fetch=self._fetch(frame([100.0] * 30)),
                today="2026-07-31",
                checkpoints=(21,),
                write=False,
            )
            assert len(report.outcomes) == 1
            assert store.counts()["outcomes"] == 0

    def test_a_second_pass_is_idempotent(self, tmp_path):
        fetch = self._fetch(frame([100.0] * 21 + [120.0] * 9))
        with LearningStore(tmp_path / "learning.db") as store:
            self._seed(store, call())
            for _ in range(2):
                resolve_ledger(store, fetch=fetch, today="2026-07-31", checkpoints=(21,))
            assert store.counts()["outcomes"] == 1

    def test_a_dead_symbol_is_reported_and_the_rest_still_score(self, tmp_path):
        good = frame([100.0] * 21 + [120.0] * 9)

        def fetch(symbol, start, end):
            if symbol in (BENCHMARK_SYMBOL, VN30_SYMBOL):
                return FLAT_BENCHMARK
            if symbol == "DED":
                raise RuntimeError("DataPro has no such symbol")
            return good

        with LearningStore(tmp_path / "learning.db") as store:
            self._seed(store, call())
            self._seed(store, call(ticker="DED", source_event_sha256="dead01"))
            report = resolve_ledger(store, fetch=fetch, today="2026-07-31", checkpoints=(21,))
            assert len(report.outcomes) == 1
            assert any("DED" in text for text in report.warnings)

    def test_a_missing_vn30_costs_a_field_not_the_run(self, tmp_path):
        good = frame([100.0] * 21 + [120.0] * 9)

        def fetch(symbol, start, end):
            if symbol == VN30_SYMBOL:
                raise RuntimeError("empty frame")
            if symbol == BENCHMARK_SYMBOL:
                return FLAT_BENCHMARK
            return good

        with LearningStore(tmp_path / "learning.db") as store:
            self._seed(store, call())
            report = resolve_ledger(store, fetch=fetch, today="2026-07-31", checkpoints=(21,))
            assert report.outcomes[0].verdict == "hit"
            assert report.outcomes[0].vn30_ret is None
            assert any(VN30_SYMBOL in text for text in report.warnings)

    def test_an_empty_ledger_produces_no_outcomes_and_no_fetches(self, tmp_path):
        def fetch(symbol, start, end):
            raise AssertionError("nothing to score should mean nothing to fetch")

        with LearningStore(tmp_path / "learning.db") as store:
            report = resolve_ledger(store, fetch=fetch)
            assert report.outcomes == []


def test_the_real_datapro_frame_still_satisfies_the_resolver():
    """Run the resolver against the live source, not a frame we wrote ourselves.

    Every other test here scores a frame built to the shape the resolver wants,
    which is a contract we set for ourselves. This one asks DataPro, and fails
    if ``to_vnd`` or ``traded_price`` stops handing back what the scorer reads.
    """
    price = pytest.importorskip("vndata.price")
    if not price.datapro_available():
        pytest.skip("DataPro desktop is not answering")

    from src.learning.resolve import datapro_prices

    prices = datapro_prices("PHR", "2026-06-30", "2026-08-29")
    benchmark = datapro_prices(BENCHMARK_SYMBOL, "2026-06-30", "2026-08-29")
    record = call(
        ticker="PHR",
        as_of="2026-06-30",
        known_at="2026-06-30T09:00:00Z",
        ref_price=62000.0,
        target=72000.0,
    )
    report = score_call(record, prices=prices, benchmark=benchmark, checkpoints=(21,))

    outcome = report.outcomes[0]
    assert outcome.verdict in {"hit", "miss", "invalidated"}
    assert outcome.resolved_price > 0
    assert outcome.realized_ret is not None and outcome.vni_ret is not None
    assert Outcome.from_dict(outcome.to_dict()) == outcome
    assert any("entry level, not a close" in text for text in report.warnings)
