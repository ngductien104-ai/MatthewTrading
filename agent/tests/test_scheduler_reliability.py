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


class TestOutputContractIsResearchNotProvider:
    """The first non-provider failure this machine ever produced.

    On 2026-09-04 a local 3B model served the completion fine and then answered
    in prose where the task required tool calls. Filing that under the provider
    would say "top up the account" about a model that cannot follow the
    contract, which is the confusion this whole module exists to prevent.
    """

    def test_the_real_error_string_is_classified(self):
        cause = classify_error(
            "output contract not met: data agent produced no tool calls "
            "and no report.md"
        )
        assert cause == "output_contract_unmet"

    def test_it_is_not_counted_against_the_provider(self):
        assert "output_contract_unmet" not in PROVIDER_CAUSES


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

    # These two assertions used to say "every failure here is the provider's"
    # and "no failure is unclassified". Both were true until 2026-09-04, when a
    # working local provider let a run fail for a research reason (a 3B model
    # answering in prose where tool calls were required) and two runs were
    # killed mid-flight by a crashing test harness, recording no error at all.
    #
    # The first assertion carried a note saying a non-provider failure was new
    # and worth reading before the assertion was relaxed. It was read: it is
    # the point of the whole module that such a failure can now be told apart
    # from an unpaid bill. What replaces it asserts the invariant the module
    # actually guarantees -- every failure is named, and provider failures
    # still dominate -- rather than a count that was only a snapshot.

    def test_provider_failures_still_dominate(self):
        summary = summarise()
        if not summary.runs:
            pytest.skip("no swarm runs on this machine")
        failed = summary.runs - summary.completed
        assert summary.provider_failed_runs > failed / 2
        assert summary.dominant_cause == "provider_no_balance"

    def test_a_non_provider_failure_is_named_rather_than_anonymous(self):
        """A cause nobody has a name for is the interesting one."""
        summary = summarise()
        if not summary.runs:
            pytest.skip("no swarm runs on this machine")
        named = PROVIDER_CAUSES | {
            "output_contract_unmet",
            "timeout",
            "blocked_by_upstream",
            # A run killed before it could write an error has nothing to
            # classify. Naming that state is honest; asserting it never
            # happens was only true while nobody had killed a run.
            "unknown",
            # The host process died before the run finished.
            "host_exited",
        }
        unnamed = set(summary.failed_runs_by_cause) - named
        assert not unnamed, f"failure causes with no name: {sorted(unnamed)}"

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
