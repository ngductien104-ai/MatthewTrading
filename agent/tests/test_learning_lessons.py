"""Tests for deriving playbook lessons from the ledger.

Every rule is a predicate over measured records. These tests check that a rule
fires only when the measurement says so, that a thin sample buys nothing, and
that re-deriving updates a lesson instead of duplicating it.
"""

from __future__ import annotations

import pytest

from src.learning.lessons import (
    CONFIRM_OBSERVATIONS,
    DOMAINS,
    MIN_OBSERVATIONS,
    Candidate,
    action_rules,
    calibration_rules,
    curate,
    derive,
    process_rules,
    render_playbook,
    write_playbook,
)
from src.learning.records import CallRecord, Evidence, Outcome
from src.learning.store import LearningStore, append_call_with_evidence


def call(ticker, action="accumulate", confidence=0.7):
    return {
        "call_id": f"call_{ticker}",
        "ticker": ticker,
        "action": action,
        "confidence": confidence,
    }


def outcome(ticker, verdict="hit", *, alpha=0.02, pctile=None, trigger=False):
    return {
        "call_id": f"call_{ticker}",
        "verdict": verdict,
        "alpha": alpha,
        "base_rate_pctile": pctile,
        "trigger_fired": trigger,
        "evidence_ids": [f"ev_{ticker}"],
    }


class TestCalibrationRules:
    def _pair(self, rows):
        calls = {f"call_{t}": call(t, confidence=c) for t, _, c in rows}
        outcomes = [outcome(t, v) for t, v, _ in rows]
        return outcomes, calls

    def test_confidence_well_above_the_hit_rate_becomes_a_lesson(self):
        rows = [("A", "hit", 0.8), ("B", "miss", 0.8), ("C", "miss", 0.8), ("D", "miss", 0.8)]
        found = calibration_rules(*self._pair(rows))
        assert any(item.rule == "calibration.overconfidence" for item in found)

    def test_a_well_calibrated_book_produces_no_lesson(self):
        rows = [("A", "hit", 0.5), ("B", "miss", 0.5), ("C", "hit", 0.5), ("D", "miss", 0.5)]
        found = calibration_rules(*self._pair(rows))
        assert not any(item.rule == "calibration.overconfidence" for item in found)

    def test_too_few_graded_calls_buys_no_lesson(self):
        """Below the floor a finding is an anecdote with a decimal point."""
        rows = [("A", "miss", 0.9), ("B", "miss", 0.9)]
        assert len(rows) < MIN_OBSERVATIONS
        found = calibration_rules(*self._pair(rows))
        assert not any(item.rule == "calibration.overconfidence" for item in found)

    def test_a_call_without_a_stated_confidence_is_not_counted(self):
        calls = {f"call_{t}": call(t, confidence=None) for t in "ABCD"}
        outcomes = [outcome(t, "miss") for t in "ABCD"]
        found = calibration_rules(outcomes, calls)
        assert not any(item.rule == "calibration.overconfidence" for item in found)

    def test_benchmarks_disagreeing_on_two_calls_becomes_a_lesson(self):
        calls = {f"call_{t}": call(t, action="wait") for t in "ABCD"}
        outcomes = [
            outcome("A", "hit", pctile=0.7),
            outcome("B", "hit", pctile=0.7),
            outcome("C", "miss", pctile=0.7),
            outcome("D", "miss", pctile=0.7),
        ]
        found = calibration_rules(outcomes, calls)
        rule = next(i for i in found if i.rule == "calibration.benchmark_disagreement")
        assert "A, B" in rule.statement

    def test_benchmarks_that_agree_produce_nothing(self):
        calls = {f"call_{t}": call(t) for t in "ABCD"}
        outcomes = [outcome(t, "hit", pctile=0.8) for t in "ABCD"]
        found = calibration_rules(outcomes, calls)
        assert not any(i.rule == "calibration.benchmark_disagreement" for i in found)

    def test_two_stop_outs_become_a_lesson_about_the_entry(self):
        calls = {f"call_{t}": call(t) for t in "AB"}
        outcomes = [outcome(t, "invalidated", trigger=True) for t in "AB"]
        rule = next(
            i for i in calibration_rules(outcomes, calls) if i.rule == "calibration.stopped_out"
        )
        assert "the entry is wrong, not the thesis" in rule.statement

    def test_one_stop_out_is_not_a_pattern(self):
        calls = {"call_A": call("A")}
        outcomes = [outcome("A", "invalidated", trigger=True)]
        found = calibration_rules(outcomes, calls)
        assert not any(i.rule == "calibration.stopped_out" for i in found)


class TestActionRules:
    def test_an_action_class_with_no_edge_becomes_a_lesson(self):
        calls = {f"call_{t}": call(t, action="wait") for t in "ABCD"}
        outcomes = [
            outcome("A", "hit", alpha=0.01),
            outcome("B", "miss", alpha=-0.01),
            outcome("C", "miss", alpha=0.0),
            outcome("D", "hit", alpha=0.0),
        ]
        rule = next(i for i in action_rules(outcomes, calls) if i.rule == "action.no_edge.wait")
        assert "2/4" in rule.statement
        assert "cannot distinguish this from chance" in rule.statement

    def test_a_winning_action_class_produces_no_warning(self):
        calls = {f"call_{t}": call(t, action="accumulate") for t in "ABCD"}
        outcomes = [outcome(t, "hit") for t in "ABCD"]
        assert action_rules(outcomes, calls) == []

    def test_a_thin_action_class_is_left_alone(self):
        calls = {f"call_{t}": call(t, action="avoid") for t in "AB"}
        outcomes = [outcome(t, "miss") for t in "AB"]
        assert action_rules(outcomes, calls) == []


class TestProcessRules:
    def test_a_low_completion_rate_becomes_a_budgeting_lesson(self):
        records = [{"completed": False, "tokens": 10} for _ in range(9)]
        records += [{"completed": True, "tokens": 10}]
        rule = next(i for i in process_rules(records) if i.rule == "process.completion_rate")
        assert "1 of 10" in rule.statement
        # It must name its population. ProcessRecord describes editor sessions,
        # and a lesson that says "runs" gets read as a verdict on swarm runs --
        # a different population with a different failure mode.
        assert "Claude Code sessions" in rule.statement

    def test_it_says_nothing_about_swarm_runs_without_being_given_any(self):
        """Reading the disk here made an empty test ledger derive a real lesson."""
        records = [{"completed": False, "tokens": 10} for _ in range(9)]
        assert not [
            i for i in process_rules(records) if i.rule == "process.swarm_completion_cause"
        ]

    def test_a_supplied_summary_produces_a_lesson_that_names_the_repair(self):
        from src.scheduler.reliability import RunReliability

        records = [{"completed": False, "tokens": 10} for _ in range(9)]
        summary = RunReliability(18, 3, {"provider_no_balance": 15}, {}, 15)
        rule = next(
            i
            for i in process_rules(records, summary)
            if i.rule == "process.swarm_completion_cause"
        )
        assert "3 of 18 swarm runs" in rule.statement
        assert "billing problem" in rule.statement

    def test_a_healthy_completion_rate_produces_nothing(self):
        records = [{"completed": True, "tokens": 10} for _ in range(10)]
        assert not any(i.rule == "process.completion_rate" for i in process_rules(records))

    def test_an_error_seen_in_two_runs_becomes_a_lesson(self):
        records = [
            {"process_id": "p1", "errors_caught": [{"code": "unit_error"}]},
            {"process_id": "p2", "errors_caught": [{"code": "unit_error"}]},
        ]
        rule = next(
            i for i in process_rules(records) if i.rule == "process.recurrence.unit_error"
        )
        assert "has not learned" in rule.statement

    def test_an_error_seen_once_is_a_process_that_worked(self):
        records = [{"process_id": "p1", "errors_caught": [{"code": "unit_error"}]}]
        assert not any(i.rule.startswith("process.recurrence") for i in process_rules(records))


class TestStatusFromEvidence:
    def test_a_well_evidenced_finding_is_confirmed(self):
        candidate = Candidate("calibration", "x", ["ev_1"], CONFIRM_OBSERVATIONS, "r")
        assert candidate.to_lesson().status == "confirmed"

    def test_a_thinly_observed_finding_stays_provisional_and_expires(self):
        candidate = Candidate("calibration", "x", ["ev_1"], 2, "r")
        lesson = candidate.to_lesson()
        assert lesson.status == "provisional"
        assert lesson.expires_at

    def test_a_finding_with_no_evidence_cannot_be_confirmed(self):
        """Process lessons cite no evidence records, so they stay provisional."""
        candidate = Candidate("process", "x", [], 100, "r")
        assert candidate.to_lesson().status == "provisional"


class TestCurate:
    @pytest.fixture()
    def store(self, tmp_path):
        with LearningStore(tmp_path / "l.db") as ledger:
            yield ledger

    def test_re_deriving_the_same_finding_updates_rather_than_duplicates(self, store):
        """The delta update: a rewritten playbook erodes, an incremented one does not."""
        candidate = Candidate("calibration", "Confidence runs high.", [], 5, "r")
        curate(store, [candidate])
        curate(store, [Candidate("calibration", "Confidence runs high.", [], 9, "r")])
        live = store.live_lessons(domain="calibration")
        assert len(live) == 1
        assert live[0].support_count == 9

    def test_rewording_one_rule_replaces_its_line_rather_than_adding_one(self, store):
        """This test used to assert the opposite, and the opposite was the bug.

        Keying a lesson on its wording meant a counting rule -- which writes
        its own numbers into its statement -- produced a fresh lesson on every
        derivation. Two live lines making the same claim with different numbers
        is not a richer playbook, it is one the reader has to disambiguate.
        """
        curate(store, [Candidate("calibration", "One thing.", [], 5, "r")])
        curate(store, [Candidate("calibration", "Another thing.", [], 5, "r")])
        live = store.live_lessons(domain="calibration")
        assert len(live) == 1
        assert live[0].statement == "Another thing."

    def test_two_different_rules_still_get_two_lessons(self, store):
        curate(store, [Candidate("calibration", "One thing.", [], 5, "r1")])
        curate(store, [Candidate("calibration", "Another thing.", [], 5, "r2")])
        assert len(store.live_lessons(domain="calibration")) == 2

    def test_the_first_write_date_survives_a_re_derivation(self, store):
        first = curate(store, [Candidate("calibration", "Stable.", [], 5, "r")])[0]
        again = curate(store, [Candidate("calibration", "Stable.", [], 6, "r")])[0]
        assert again.created_at == first.created_at


class TestPlaybook:
    @pytest.fixture()
    def store(self, tmp_path):
        with LearningStore(tmp_path / "l.db") as ledger:
            yield ledger

    def test_every_domain_gets_a_file_including_the_empty_ones(self, store, tmp_path):
        written = write_playbook(store, tmp_path / "playbook")
        assert set(written) == set(DOMAINS)
        for path in written.values():
            assert (tmp_path / "playbook").joinpath(path.split("\\")[-1]).exists()

    def test_an_empty_domain_says_why_it_is_empty(self, store, tmp_path):
        write_playbook(store, tmp_path / "playbook")
        text = (tmp_path / "playbook" / "nganhang.md").read_text(encoding="utf-8")
        assert "empty on purpose" in text

    def test_the_frontmatter_is_queryable(self, store):
        """295 vault notes carry none, which is why none can be queried."""
        text = render_playbook([], "vimo")
        assert text.startswith("---\n")
        assert "domain: vimo" in text
        assert "type: playbook" in text

    def test_a_stored_lesson_reaches_its_file_with_its_counts(self, store, tmp_path):
        curate(store, [Candidate("process", "Runs do not finish.", [], 24, "r")])
        write_playbook(store, tmp_path / "playbook")
        text = (tmp_path / "playbook" / "process.md").read_text(encoding="utf-8")
        assert "Runs do not finish." in text
        assert "support: 24" in text
        assert "status: **provisional**" in text


class TestDeriveOnAStore:
    def test_an_empty_ledger_derives_nothing_and_says_so_quietly(self, tmp_path):
        with LearningStore(tmp_path / "l.db") as store:
            assert derive(store) == []

    def test_derive_reads_only_the_requested_checkpoint(self, tmp_path):
        with LearningStore(tmp_path / "l.db") as store:
            for ticker in "ABCD":
                record = CallRecord(
                    ticker=ticker,
                    as_of="2026-06-15",
                    action="accumulate",
                    known_at="2026-06-15T09:00:00Z",
                    confidence=0.9,
                    target=130.0,
                    source_session_id="s",
                    source_event_sha256=ticker,
                )
                thesis = Evidence(
                    kind="research_report",
                    observed_at=record.known_at,
                    source_path=f"{ticker}.md",
                    excerpt=f"{ticker} memo",
                )
                record.evidence_ids = [thesis.evidence_id]
                append_call_with_evidence(store, record, [thesis])
                price = Evidence(
                    kind="price_series",
                    observed_at="2026-07-14T08:00:00Z",
                    source_path=f"datapro://daily/{ticker}",
                    locator="w",
                    excerpt=f"{ticker} window",
                )
                store.append_evidence(price)
                store.append_outcome(
                    Outcome(
                        call_id=record.call_id,
                        resolved_at="2026-07-14",
                        checkpoint_sessions=21,
                        verdict="miss",
                        resolved_price=90.0,
                        realized_ret=-0.1,
                        alpha=-0.05,
                        evidence_ids=[price.evidence_id],
                    )
                )
            assert any(c.rule == "calibration.overconfidence" for c in derive(store))
            assert derive(store, checkpoint=63) == []


class TestLessonIdentityIsTheRuleNotTheWording:
    """The delta update was defeating itself.

    A counting rule writes its own numbers into its statement, so hashing the
    statement gave "4 of 25" and "3 of 24" different ids and every derivation
    appended a near-duplicate instead of moving the counts on the one already
    there. The ledger reached three live process lessons saying overlapping
    things before anyone noticed.
    """

    def test_the_same_rule_keeps_its_id_when_its_numbers_move(self):
        from src.learning.records import Lesson

        first = Lesson(
            domain="process", statement="3 of 24 runs", rule="process.completion_rate"
        )
        later = Lesson(
            domain="process", statement="4 of 25 runs", rule="process.completion_rate"
        )
        assert first.lesson_id == later.lesson_id

    def test_different_rules_stay_apart(self):
        from src.learning.records import Lesson

        one = Lesson(domain="process", statement="x", rule="process.completion_rate")
        two = Lesson(domain="process", statement="x", rule="process.swarm_completion_cause")
        assert one.lesson_id != two.lesson_id

    def test_a_lesson_with_no_rule_is_still_identified_by_its_wording(self):
        """For a hand-written line the wording really is the identity."""
        from src.learning.records import Lesson

        one = Lesson(domain="process", statement="written by hand", support_count=1)
        two = Lesson(domain="process", statement="written by hand", support_count=9)
        three = Lesson(domain="process", statement="something else", support_count=1)
        assert one.lesson_id == two.lesson_id
        assert one.lesson_id != three.lesson_id

    def test_re_deriving_updates_in_place_instead_of_accumulating(self, tmp_path):
        from src.learning.lessons import Candidate, curate
        from src.learning.store import LearningStore

        with LearningStore(tmp_path / "l.db") as store:
            curate(store, [Candidate("process", "3 of 24 runs", [], 24, "process.completion_rate")])
            curate(store, [Candidate("process", "4 of 25 runs", [], 25, "process.completion_rate")])
            live = store.live_lessons()
        assert len(live) == 1
        assert "4 of 25" in live[0].statement

    def test_a_rule_reworded_under_a_new_id_retires_the_old_line(self, tmp_path):
        """Two lines making the same claim with different numbers is worse than one."""
        from src.learning.lessons import Candidate, curate
        from src.learning.records import Lesson
        from src.learning.store import LearningStore

        with LearningStore(tmp_path / "l.db") as store:
            stale = Lesson(domain="process", statement="3 of 24 runs", support_count=24)
            stale.rule = "process.completion_rate"
            stale.lesson_id = "les_legacyid0001"
            store.append_lesson(stale)
            assert len(store.live_lessons()) == 1

            curate(
                store,
                [Candidate("process", "4 of 25 runs", [], 25, "process.completion_rate")],
            )
            live = store.live_lessons()
        assert len(live) == 1
        assert "4 of 25" in live[0].statement

    def test_a_hand_written_lesson_is_never_retired_by_a_deriver(self, tmp_path):
        from src.learning.lessons import Candidate, curate
        from src.learning.records import Lesson
        from src.learning.store import LearningStore

        with LearningStore(tmp_path / "l.db") as store:
            store.append_lesson(
                Lesson(domain="process", statement="a human wrote this", support_count=1)
            )
            curate(store, [Candidate("process", "derived", [], 5, "process.completion_rate")])
            statements = {lesson.statement for lesson in store.live_lessons()}
        assert "a human wrote this" in statements

    def test_retire_lesson_reports_whether_it_found_anything(self, tmp_path):
        from src.learning.lessons import retire_lesson
        from src.learning.records import Lesson
        from src.learning.store import LearningStore

        with LearningStore(tmp_path / "l.db") as store:
            lesson = Lesson(domain="process", statement="stale", support_count=1)
            store.append_lesson(lesson)
            assert retire_lesson(store, lesson.lesson_id, "les_new") is True
            assert retire_lesson(store, "les_nothere") is False
            assert store.live_lessons() == []
