"""Tests for why runs do not finish.

The finding these are built around: on this machine every failed swarm run
failed on the provider, and none failed because the research went wrong. That
makes the completion rate a statement about an unpaid account, and the tests
below are mostly about keeping those two readings apart.
"""

from __future__ import annotations

import pytest

from src.scheduler.reliability import (
    PROVIDER_CAUSES,
    RunReliability,
    classify_error,
    render,
    summarise,
)


class TestClassifyError:
    def test_no_error_is_not_a_cause(self):
        assert classify_error(None) is None
        assert classify_error("") is None

    @pytest.mark.parametrize(
        "message,expected",
        [
            (
                "LLM call failed at iteration 0: Error code: 402 - {'error': "
                "{'message': 'Insufficient Balance'}}",
                "provider_no_balance",
            ),
            (
                "LLM call failed at iteration 0: Error code: 401 - "
                "{'error': {'message': 'User not found.'}}",
                "provider_bad_credentials",
            ),
            (
                "LLM call failed at iteration 0: OpenAI Codex is not logged in. "
                "Run: vibe-trading provider login",
                "provider_not_logged_in",
            ),
            (
                'LLM call failed at iteration 0: OpenAI Codex HTTP 429: '
                '{"error":{"type":"usage_limit_reached"}}',
                "provider_rate_limited",
            ),
            (
                "LLM call failed at iteration 14: OpenAI Codex response failed: "
                "{'type': 'service_unavailable'}",
                "provider_unavailable",
            ),
            ("LLM call failed at iteration 0: Connection error.", "provider_unavailable"),
            ("Worker exceeded layer deadline of 900s", "timeout"),
        ],
    )
    def test_the_real_messages_off_disk_are_classified(self, message, expected):
        """Every string here was copied out of a run directory on this machine."""
        assert classify_error(message) == expected

    def test_blocked_is_checked_before_the_word_failed_inside_it(self):
        """A blocked task quotes its upstream's status and would double-count."""
        assert (
            classify_error("Blocked: upstream not completed (task-valuation=failed)")
            == "blocked_by_upstream"
        )

    def test_an_unrecognised_error_is_named_other_rather_than_dropped(self):
        """A classifier that discards its misses reports a cleaner world."""
        assert classify_error("something nobody has seen before") == "other"

    def test_blocked_is_not_counted_as_the_providers_fault(self):
        assert "blocked_by_upstream" not in PROVIDER_CAUSES
        assert "other" not in PROVIDER_CAUSES
        assert "timeout" not in PROVIDER_CAUSES


class TestBlame:
    def test_all_provider_failures_are_reported_as_such(self):
        summary = RunReliability(18, 3, {"provider_no_balance": 15}, {}, 15)
        assert "all 15 failed runs died on the provider" in summary.blame()
        assert "none failed for a research reason" in summary.blame()

    def test_a_mix_is_split_rather_than_rounded_to_the_bigger_half(self):
        summary = RunReliability(10, 2, {"provider_no_balance": 5, "other": 3}, {}, 5)
        blame = summary.blame()
        assert "5/8 failed runs died on the provider" in blame
        assert "3 for other reasons" in blame

    def test_nothing_failed_is_said_plainly(self):
        assert "no failed runs" in RunReliability(3, 3, {}, {}, 0).blame()

    def test_the_completion_rate_is_none_with_no_runs(self):
        """Not zero: an unmeasured machine is not a failing one."""
        assert RunReliability(0, 0, {}, {}, 0).completion_rate is None


class TestSummariseAgainstTheRealRuns:
    """The fixtures above were written here. This one reads .swarm/runs."""

    def test_it_finds_the_runs_and_none_of_them_failed_on_research(self):
        summary = summarise()
        if not summary.runs:
            pytest.skip("no swarm runs on this machine")
        failed = summary.runs - summary.completed
        assert summary.provider_failed_runs == failed, (
            "a run failed for a non-provider reason -- that is new, and worth "
            "reading before this assertion is relaxed"
        )
        assert summary.dominant_cause == "provider_no_balance"

    def test_every_failed_task_gets_a_cause_and_none_is_unknown(self):
        summary = summarise()
        if not summary.runs:
            pytest.skip("no swarm runs on this machine")
        assert "unknown" not in summary.failed_runs_by_cause
        assert "other" not in summary.failed_tasks_by_cause

    def test_a_missing_runs_directory_is_zeros_rather_than_an_exception(self, tmp_path):
        summary = summarise(runs_root=tmp_path / "nope")
        assert summary.runs == 0
        assert summary.completion_rate is None

    def test_the_rendering_names_the_causes(self):
        summary = summarise()
        if not summary.runs:
            pytest.skip("no swarm runs on this machine")
        text = render(summary)
        assert "reached a conclusion" in text
        assert "failed runs by cause" in text
        assert "provider_no_balance" in text
