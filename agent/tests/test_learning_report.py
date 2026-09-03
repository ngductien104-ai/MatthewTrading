"""Tests for the scorecard.

The statistics are checked against values worked out by hand rather than
against whatever the code happens to return, because a scorecard that agrees
with itself is exactly the failure mode it exists to prevent.
"""

from __future__ import annotations

import pytest

from src.learning.records import CallRecord, Evidence, Outcome
from src.learning.report import (
    GRADED,
    Row,
    brier_score,
    build_scorecard,
    wilson_interval,
)
from src.learning.store import LearningStore, append_call_with_evidence


class TestWilson:
    def test_a_coin_flip_at_n_eight_barely_narrows_anything(self):
        low, high = wilson_interval(4, 8)
        assert low == pytest.approx(0.2152, abs=1e-3)
        assert high == pytest.approx(0.7848, abs=1e-3)

    def test_the_interval_stays_inside_the_unit_interval_at_the_edges(self):
        for hits, total in ((0, 3), (3, 3), (1, 1)):
            low, high = wilson_interval(hits, total)
            assert 0.0 <= low <= high <= 1.0

    def test_more_of_the_same_evidence_narrows_the_interval(self):
        narrow = wilson_interval(40, 80)
        wide = wilson_interval(4, 8)
        assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])

    def test_nothing_observed_claims_nothing(self):
        assert wilson_interval(0, 0) == (0.0, 1.0)


class TestBrier:
    def test_a_perfect_forecaster_scores_zero(self):
        assert brier_score([(1.0, 1), (0.0, 0)]) == pytest.approx(0.0)

    def test_the_ledgers_own_numbers_reproduce(self):
        """The seven graded calls that stated a confidence, worked by hand."""
        pairs = [(0.75, 1), (0.78, 1), (0.80, 0), (0.70, 0), (0.62, 1), (0.62, 1), (0.61, 0)]
        assert brier_score(pairs) == pytest.approx(0.2717, abs=1e-4)

    def test_no_forecasts_scores_nothing_rather_than_zero(self):
        assert brier_score([]) is None


def _call(store, ticker, action, **overrides):
    fields = {
        "ticker": ticker,
        "as_of": "2026-06-15",
        "action": action,
        "known_at": "2026-06-15T09:00:00Z",
        "ref_price": 100.0,
        "target": 130.0,
        "confidence": 0.6,
        "source_session_id": "sess",
        "source_event_sha256": ticker,
    }
    fields.update(overrides)
    record = CallRecord(**fields)
    thesis = Evidence(
        kind="research_report",
        observed_at=record.known_at,
        source_path=f"{ticker}.md",
        excerpt=f"{ticker} memo",
    )
    record.evidence_ids = [thesis.evidence_id]
    append_call_with_evidence(store, record, [thesis])
    return record


def _outcome(store, record, verdict, *, alpha=0.05, extras="", **overrides):
    price = Evidence(
        kind="price_series",
        observed_at="2026-07-14T08:00:00Z",
        source_path=f"datapro://daily/{record.ticker}",
        locator="2026-06-15..2026-07-14",
        excerpt=f"{record.ticker} 2026-06-15..2026-07-14 entry_close=100 exit_close=110 {extras}",
    )
    store.append_evidence(price)
    fields = {
        "call_id": record.call_id,
        "episode_id": record.episode_id,
        "resolved_at": "2026-07-14",
        "checkpoint_sessions": 21,
        "verdict": verdict,
        "resolved_price": 110.0,
        "realized_ret": 0.10,
        "vni_ret": 0.10 - alpha,
        "alpha": alpha,
        "evidence_ids": [price.evidence_id],
    }
    fields.update(overrides)
    store.append_outcome(Outcome(**fields))


class TestScorecard:
    def test_only_hit_and_miss_enter_the_hit_rate(self, tmp_path):
        with LearningStore(tmp_path / "l.db") as store:
            for ticker, verdict in (
                ("AAA", "hit"),
                ("BBB", "miss"),
                ("CCC", "invalidated"),
                ("DDD", "no_claim"),
            ):
                action = "hold" if verdict == "no_claim" else "accumulate"
                _outcome(store, _call(store, ticker, action), verdict)
            stats = build_scorecard(store).to_dict()
        assert stats["scored"] == 4
        assert stats["graded"] == 2
        assert stats["hit_rate"] == pytest.approx(0.5)

    def test_a_stopped_out_call_is_not_counted_as_wrong_about_direction(self, tmp_path):
        with LearningStore(tmp_path / "l.db") as store:
            _outcome(store, _call(store, "AAA", "accumulate"), "invalidated")
            stats = build_scorecard(store).to_dict()
        assert stats["graded"] == 0
        assert stats["hit_rate"] is None
        assert GRADED == ("hit", "miss")

    def test_the_calibration_subset_uses_its_own_denominator(self, tmp_path):
        """Not every graded call states a confidence.

        Comparing a mean confidence over the calls that did against a hit rate
        over the calls that did not is the mismatched denominator this report is
        supposed to catch, not commit.
        """
        with LearningStore(tmp_path / "l.db") as store:
            _outcome(store, _call(store, "AAA", "accumulate", confidence=0.8), "hit")
            _outcome(store, _call(store, "BBB", "accumulate", confidence=0.8), "hit")
            _outcome(store, _call(store, "CCC", "accumulate", confidence=None), "miss")
            stats = build_scorecard(store).to_dict()
        assert stats["graded"] == 3
        assert stats["hit_rate"] == pytest.approx(2 / 3)
        assert stats["confidence_n"] == 2
        assert stats["confidence_hit_rate"] == pytest.approx(1.0)

    def test_a_checkpoint_with_no_outcomes_reports_empty_not_wrong(self, tmp_path):
        with LearningStore(tmp_path / "l.db") as store:
            _outcome(store, _call(store, "AAA", "accumulate"), "hit")
            card = build_scorecard(store, checkpoint=63)
        assert card.rows == []
        assert card.to_dict()["hit_rate"] is None
        assert "nothing graded yet" in card.to_text()

    def test_the_text_states_the_interval_rather_than_the_rate_alone(self, tmp_path):
        with LearningStore(tmp_path / "l.db") as store:
            _outcome(store, _call(store, "AAA", "accumulate"), "hit")
            _outcome(store, _call(store, "BBB", "accumulate"), "miss")
            text = build_scorecard(store).to_text()
        assert "95% CI" in text
        assert "NOT ATTRIBUTED" in text
        assert "one regime" in text


class TestEntryPrinted:
    def _row(self, action, target, ref, adj_low, rate=1.0):
        call = CallRecord(
            ticker="AAA",
            as_of="2026-06-15",
            action=action,
            known_at="2026-06-15T09:00:00Z",
            ref_price=ref,
            target=target,
            source_session_id="s",
            source_event_sha256="x",
        )
        outcome = Outcome(call_id=call.call_id, resolved_at="2026-07-14", checkpoint_sessions=21)
        return Row(call=call, outcome=outcome, prices={"adj_low": adj_low, "entry_adj_rate": rate})

    def test_an_entry_that_traded_is_reported_as_reached(self):
        """BSR waited at 26.350 for 24.000 and 23.350 traded."""
        assert self._row("wait", 24000, 26350, 23350).entry_printed is True

    def test_an_entry_that_never_traded_is_reported_as_missed(self):
        assert self._row("wait", 19500, 21300, 20650).entry_printed is False

    def test_a_corporate_action_does_not_fake_an_entry(self):
        """PET named 44.000 and its raw traded low was 35.400 -- which looks
        reached until the 1,45x action is undone, putting the low at 48.900."""
        row = self._row("wait", 44000, 54800, 33735, rate=1.4496)
        assert row.entry_printed is False

    def test_a_target_above_the_price_is_not_an_entry_to_wait_for(self):
        """VRE: ``avoid`` at 24.300 with a target of 26.200, which is a
        fair-value note and not a price anyone was waiting to buy at."""
        assert self._row("avoid", 26200, 24300, 20000).entry_printed is None

    def test_a_long_call_is_not_asked_the_question_at_all(self):
        assert self._row("accumulate", 130, 100, 50).entry_printed is None

    def test_a_call_with_no_price_evidence_declines_to_answer(self):
        row = self._row("wait", 19500, 21300, 20650)
        row.prices = {}
        assert row.entry_printed is None


def test_the_scorecard_reads_the_live_ledger_without_a_network(tmp_path, monkeypatch):
    """Build a scorecard end to end through the store, with sockets refused.

    The report claims to need nothing but the ledger. This is that claim made
    falsifiable rather than asserted in a docstring.
    """
    import socket

    with LearningStore(tmp_path / "l.db") as store:
        _outcome(
            store,
            _call(store, "AAA", "wait", target=90.0, confidence=0.75),
            "hit",
            alpha=-0.04,
            extras="adj_low=85 entry_adj_rate=1.0",
        )

        def refuse(*args, **kwargs):
            raise AssertionError("the scorecard must not open a socket")

        monkeypatch.setattr(socket, "socket", refuse)
        text = build_scorecard(store).to_text()

    assert "DID THE ENTRY EVER PRINT?" in text
    assert "YES" in text
