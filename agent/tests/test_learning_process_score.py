"""Tests for the process rubric.

The rubric's whole claim is that a model cannot earn a point by asserting one.
Most of these tests are attempts to earn points dishonestly.
"""

from __future__ import annotations

import json

import pytest

from src.learning.extract import SourceDocument
from src.learning.process_score import (
    MAX_SCORE,
    RUBRIC,
    build_error_prompt,
    build_prompt,
    classify_errors,
    completion_rate,
    disagreement,
    parse_reply,
    recurrence,
    score_document,
    stalls,
)

MEMO = """# PHR — accumulate

Data retrieved 2026-06-30 from DataPro; financials cover Q1 2026.
The rubber price assumption of 42,000,000 VND/tonne produces an EBITDA of
1,850 billion VND, which is the whole of the target.
The land compensation decision from GVR is expected in Q3 2026.
The view is wrong if compensation slips past 2027 or the stop at 56,000 trades.
Size this at 1.5% of NAV, capped at 3%.
"""


def document(text=MEMO, path="memo.md"):
    """Build a SourceDocument the way load_document would."""
    return SourceDocument(
        doc_id="doc_1",
        kind="research_report",
        path=path,
        text=text,
        sha256="abc",
        observed_at="2026-06-30T09:00:00Z",
        episode_key="_phr_committee",
        session_id="sess",
        source_uuid="",
    )


def replies(**quotes):
    """Return a propose() that answers with the given quotes."""
    payload = {item.code: quotes.get(item.code) for item in RUBRIC}
    return lambda _prompt: json.dumps(payload)


PERFECT = {
    "source_timestamp": "Data retrieved 2026-06-30 from DataPro",
    "data_cutoff": "financials cover Q1 2026",
    "valuation_bridge": (
        "The rubber price assumption of 42,000,000 VND/tonne produces an EBITDA of"
    ),
    "catalyst": "The land compensation decision from GVR is expected in Q3 2026.",
    "falsification": "The view is wrong if compensation slips past 2027",
    "position_size": "Size this at 1.5% of NAV, capped at 3%.",
}


class TestScoring:
    def test_a_document_that_satisfies_everything_scores_full_marks(self):
        result = score_document(document(), replies(**PERFECT))
        assert result.score == MAX_SCORE
        assert result.missing_codes == []

    def test_every_earned_item_carries_locatable_evidence(self):
        result = score_document(document(), replies(**PERFECT))
        assert len(result.evidence()) == MAX_SCORE
        for evidence in result.evidence():
            assert evidence.locator.startswith("L")
            assert evidence.excerpt in MEMO

    def test_an_unclaimed_item_costs_nothing_but_earns_nothing(self):
        result = score_document(document(), replies(**{**PERFECT, "catalyst": None}))
        assert result.score == MAX_SCORE - 1
        assert "catalyst" in result.missing_codes
        assert result.items[3].rejected == "not claimed"

    def test_the_rubric_is_unweighted(self):
        """A weighting is a claim about importance nothing here has measured."""
        one = score_document(document(), replies(**{**PERFECT, "catalyst": None}))
        two = score_document(document(), replies(**{**PERFECT, "position_size": None}))
        assert one.score == two.score


class TestAPointCannotBeAsserted:
    def test_a_quote_that_is_not_in_the_document_earns_nothing(self):
        """The specific failure: a model paraphrasing what it wishes were there."""
        forged = {**PERFECT, "catalyst": "A catalyst is clearly present in this memo."}
        result = score_document(document(), replies(**forged))
        assert result.score == MAX_SCORE - 1
        assert result.items[3].rejected == "quote is not in the document"

    def test_a_real_quote_without_the_required_shape_earns_nothing(self):
        """Offering a dateless line for data_cutoff is confident and empty."""
        weak = {**PERFECT, "data_cutoff": "which is the whole of the target."}
        result = score_document(document(), replies(**weak))
        assert result.score == MAX_SCORE - 1
        assert "must contain a date" in result.items[1].rejected
        assert result.items[1].quote  # located, but refused

    def test_a_size_with_no_percentage_is_not_a_constraint(self):
        loose = {**PERFECT, "position_size": "Size this at"}
        result = score_document(document(), replies(**loose))
        assert "position_size" in result.missing_codes

    def test_a_bridge_with_no_number_crosses_nothing(self):
        loose = {**PERFECT, "valuation_bridge": "which is the whole of the target."}
        result = score_document(document(), replies(**loose))
        assert "valuation_bridge" in result.missing_codes

    def test_a_document_satisfying_nothing_scores_zero(self):
        empty = document(text="PHR looks cheap. Buy it.\n")
        result = score_document(empty, replies(**PERFECT))
        assert result.score == 0
        assert all(item.rejected for item in result.items)


class TestBadReplies:
    def test_an_unparseable_reply_scores_zero_without_stopping_the_batch(self):
        result = score_document(document(), lambda _p: "I read the memo and it is good.")
        assert result.score == 0
        assert "not JSON" in result.parse_error

    def test_a_json_array_is_refused_as_the_wrong_shape(self):
        result = score_document(document(), lambda _p: '["source_timestamp"]')
        assert result.score == 0
        assert "JSON object" in result.parse_error

    def test_a_fenced_reply_is_still_read(self):
        payload = json.dumps(PERFECT)
        result = score_document(document(), lambda _p: f"```json\n{payload}\n```")
        assert result.score == MAX_SCORE

    def test_parse_reply_rejects_a_bare_string(self):
        with pytest.raises(Exception, match="JSON object"):
            parse_reply('"yes"')


class TestPrompt:
    def test_the_prompt_tells_the_model_it_cannot_award_points(self):
        text = build_prompt(document())
        assert "You cannot award points" in text
        assert "every span is searched for in the\ndocument" in text

    def test_the_prompt_carries_every_rubric_item_and_its_requirement(self):
        text = build_prompt(document())
        for item in RUBRIC:
            assert item.code in text
            assert item.question in text
            assert item.requirement in text

    def test_the_prompt_carries_the_document_and_its_provenance(self):
        text = build_prompt(document())
        assert MEMO in text
        assert "2026-06-30T09:00:00Z" in text


DEBATE = """The CRO objected: FOX profit is counted in both the segment line and
the consolidated line, so 2026 earnings are overstated by 340 billion.
Analyst accepted and removed the duplicate.
Risk also noted the Q2 figure was already in the 25/07 memo but nobody checked it.
"""


class TestClassifyErrors:
    def _reply(self, errors):
        return lambda _p: json.dumps({"errors": errors})

    def test_a_caught_mistake_becomes_an_auditable_entry(self):
        doc = document(text=DEBATE, path="debate.md")
        entries, evidence, refused = classify_errors(
            doc,
            self._reply([
                {
                    "code": "double_count",
                    "quote": "FOX profit is counted in both the segment line and",
                    "round": 2,
                    "description": "FOX earnings added twice",
                }
            ]),
        )
        assert refused == []
        assert entries[0]["code"] == "double_count"
        assert entries[0]["round"] == 2
        assert entries[0]["evidence_id"] == evidence[0].evidence_id

    def test_the_entries_satisfy_the_process_record_contract(self):
        """ProcessRecord refuses an uncited catch; these must never be refused."""
        from src.learning.records import ProcessRecord

        doc = document(text=DEBATE, path="debate.md")
        entries, _, _ = classify_errors(
            doc,
            self._reply([
                {"code": "stale_crosscheck", "quote": "nobody checked it", "round": 1}
            ]),
        )
        record = ProcessRecord(source_session_id="s", errors_caught=entries)
        assert record.error_taxonomy == ["stale_crosscheck"]

    def test_a_code_outside_the_taxonomy_is_dropped(self):
        """The vocabulary is closed so recurrence can be counted at all."""
        doc = document(text=DEBATE, path="debate.md")
        entries, _, refused = classify_errors(
            doc, self._reply([{"code": "sloppy_thinking", "quote": "Analyst accepted"}])
        )
        assert entries == []
        assert "not in the taxonomy" in refused[0]

    def test_a_quote_that_is_not_in_the_document_is_dropped(self):
        doc = document(text=DEBATE, path="debate.md")
        entries, _, refused = classify_errors(
            doc,
            self._reply([{"code": "double_count", "quote": "The analyst double counted."}]),
        )
        assert entries == []
        assert "not in the document" in refused[0]

    def test_no_mistakes_shown_is_an_empty_list_not_a_failure(self):
        doc = document(text=DEBATE, path="debate.md")
        entries, evidence, refused = classify_errors(doc, self._reply([]))
        assert (entries, evidence, refused) == ([], [], [])

    def test_an_unusable_reply_returns_a_reason_rather_than_raising(self):
        doc = document(text=DEBATE, path="debate.md")
        entries, _, refused = classify_errors(doc, lambda _p: "no errors found, all good")
        assert entries == []
        assert refused and "not JSON" in refused[0]

    def test_the_prompt_names_every_code_with_the_incident_behind_it(self):
        from src.learning.records import ERROR_TAXONOMY

        text = build_error_prompt(document(text=DEBATE))
        for code in ERROR_TAXONOMY:
            assert code in text
        assert "cannot invent a category" in text
        assert "FOX earnings" in text


class TestDisagreement:
    def _pass(self, quotes):
        return [score_document(document(), replies(**quotes))]

    def test_two_identical_passes_agree_completely(self):
        result = disagreement(self._pass(PERFECT), self._pass(PERFECT))
        assert result["agreement"] == 1.0
        assert result["score_disagreements"] == []

    def test_a_differing_item_is_located_not_just_counted(self):
        other = {**PERFECT, "catalyst": None}
        result = disagreement(self._pass(PERFECT), self._pass(other))
        assert result["agreement"] == pytest.approx(5 / 6)
        assert result["per_item"]["catalyst"]["agreement"] == 0.0
        assert result["per_item"]["data_cutoff"]["agreement"] == 1.0
        assert result["score_disagreements"][0]["left"] == MAX_SCORE
        assert result["score_disagreements"][0]["right"] == MAX_SCORE - 1

    def test_no_shared_document_reports_nothing_rather_than_perfect_agreement(self):
        left = [score_document(document(), replies(**PERFECT))]
        right = [score_document(document(path="other.md"), replies(**PERFECT))]
        right[0].doc_id = "doc_2"
        result = disagreement(left, right)
        assert result["documents_compared"] == 0
        assert result["agreement"] is None


class TestRecurrence:
    def test_an_error_caught_twice_in_two_runs_is_a_process_that_has_not_learned(self):
        records = [
            {"process_id": "p1", "errors_caught": [{"code": "unit_error"}]},
            {"process_id": "p2", "errors_caught": [{"code": "unit_error"}]},
        ]
        result = recurrence(records)
        assert result["per_code"]["unit_error"] == {"caught": 2, "runs": 2}
        assert result["repeat_rate"] == 1.0

    def test_the_same_error_twice_in_one_run_is_not_a_recurrence(self):
        records = [
            {
                "process_id": "p1",
                "errors_caught": [{"code": "unit_error"}, {"code": "unit_error"}],
            }
        ]
        result = recurrence(records)
        assert result["per_code"]["unit_error"] == {"caught": 2, "runs": 1}
        assert result["repeat_rate"] == 0.0

    def test_codes_are_ordered_by_how_often_they_bite(self):
        records = [
            {"process_id": "p1", "errors_caught": [{"code": "lookahead"}]},
            {"process_id": "p2", "errors_caught": [{"code": "unit_error"}]},
            {"process_id": "p3", "errors_caught": [{"code": "unit_error"}]},
        ]
        assert list(recurrence(records)["per_code"])[0] == "unit_error"

    def test_nothing_caught_yields_no_rate_rather_than_a_perfect_one(self):
        assert recurrence([])["repeat_rate"] is None


class TestStalls:
    """The loop already knows when it is stuck; nothing was reading it."""

    def _run(self, tmp_path, name, events):
        run = tmp_path / name
        run.mkdir()
        (run / "trace.jsonl").write_text(
            "\n".join(json.dumps(event) for event in events), encoding="utf-8"
        )
        return run

    def test_a_recorded_stall_is_found_with_the_iteration_it_hit(self, tmp_path):
        run = self._run(
            tmp_path,
            "r1",
            [
                {"type": "tool_call", "iter": 1},
                {
                    "type": "goal_continuation_suppressed",
                    "iter": 7,
                    "goal_id": "g1",
                    "continuations": 3,
                    "progress": [2, 5],
                },
            ],
        )
        result = stalls([run])
        assert result["stalls"] == 1
        assert result["detail"][0]["iteration"] == 7
        assert result["detail"][0]["continuations"] == 3

    def test_a_trace_with_no_stall_reports_zero_beside_the_traces_read(self, tmp_path):
        """Zero stalls and zero traces are different facts."""
        run = self._run(tmp_path, "r1", [{"type": "tool_call", "iter": 1}])
        assert stalls([run]) == {
            "traces_read": 1,
            "stalls": 0,
            "runs_that_stalled": 0,
            "detail": [],
        }

    def test_no_trace_file_is_not_counted_as_a_trace_read(self, tmp_path):
        empty = tmp_path / "no_trace"
        empty.mkdir()
        assert stalls([empty])["traces_read"] == 0

    def test_a_corrupt_line_does_not_stop_the_rest_of_the_file(self, tmp_path):
        run = tmp_path / "r1"
        run.mkdir()
        (run / "trace.jsonl").write_text(
            "{not json at all\n"
            + json.dumps({"type": "goal_continuation_suppressed", "iter": 4}),
            encoding="utf-8",
        )
        assert stalls([run])["stalls"] == 1

    def test_stalls_are_counted_per_run_as_well_as_in_total(self, tmp_path):
        event = {"type": "goal_continuation_suppressed", "iter": 2}
        first = self._run(tmp_path, "r1", [event, event])
        second = self._run(tmp_path, "r2", [event])
        result = stalls([first, second])
        assert result["stalls"] == 3
        assert result["runs_that_stalled"] == 2


class TestCompletionRate:
    def _record(self, completed, output, cache_read):
        return {
            "completed": completed,
            "tokens": output + cache_read,
            "token_usage": {"output_tokens": output, "cache_read_input_tokens": cache_read},
        }

    def test_the_cost_of_the_unfinished_runs_is_counted_beside_the_rate(self):
        """3 of 18 completing is a budget line, not a scheduling annoyance."""
        records = [self._record(False, 1000, 0) for _ in range(15)]
        records += [self._record(True, 2000, 0) for _ in range(3)]
        result = completion_rate(records)
        assert result["completion_rate"] == pytest.approx(3 / 18)
        assert result["output_tokens_on_unfinished_runs"] == 15_000
        assert result["output_wasted_share"] == pytest.approx(15_000 / 21_000)
        assert result["output_tokens_per_completed_run"] == pytest.approx(7000.0)

    def test_generated_work_is_reported_apart_from_re_read_context(self):
        """One real session read 308M cached tokens against 1,2M generated.

        Adding those together answers no question anyone has, so the raw sum
        is kept only for older records and labelled as a size, not a spend.
        """
        records = [self._record(True, 1_200_000, 308_000_000)]
        result = completion_rate(records)
        assert result["output_tokens_total"] == 1_200_000
        assert result["raw_counter_total"] == 309_200_000
        assert "not a spend" in result["raw_counter_note"]

    def test_a_record_with_no_breakdown_still_reports_the_rate(self):
        """Records captured before the breakdown existed must not crash."""
        result = completion_rate([{"completed": True, "tokens": 500}])
        assert result["completion_rate"] == 1.0
        assert result["output_tokens_total"] == 0
        assert result["raw_counter_total"] == 500

    def test_no_runs_reports_nothing_rather_than_zero(self):
        result = completion_rate([])
        assert result["completion_rate"] is None
        assert result["output_wasted_share"] is None
