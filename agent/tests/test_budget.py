"""Tests for the per-run token ceiling.

The ledger says 81% of everything generated went to runs that finished
nothing. A ceiling cannot make a run converge; it stops one paying for the
discovery that it will not.
"""

from __future__ import annotations

import pytest

from src.core.budget import BUDGET_ENV, check, configured_budget


class TestConfiguredBudget:
    def test_unset_means_unlimited(self):
        """Off by default. A limit invented here would kill a real run."""
        assert configured_budget("") is None

    def test_a_positive_integer_is_the_ceiling(self):
        assert configured_budget("250000") == 250_000

    def test_a_typo_is_treated_as_absent_not_as_zero(self):
        """Reading BUDGET=abc as "stop immediately" halts every run on a typo."""
        assert configured_budget("abc") is None
        assert configured_budget("1e6") is None

    def test_zero_and_negative_are_treated_as_absent(self):
        assert configured_budget("0") is None
        assert configured_budget("-5") is None

    def test_it_reads_the_environment_when_given_nothing(self, monkeypatch):
        monkeypatch.setenv(BUDGET_ENV, "1234")
        assert configured_budget() == 1234


class TestCheck:
    def test_no_ceiling_permits_anything_and_says_the_ceiling_is_absent(self):
        verdict = check(10_000_000, limit=None)
        assert verdict.exceeded is False
        assert verdict.limit is None

    def test_spending_under_the_ceiling_is_allowed(self):
        assert check(999, limit=1000).exceeded is False

    def test_spending_exactly_the_ceiling_is_still_allowed(self):
        assert check(1000, limit=1000).exceeded is False

    def test_passing_the_ceiling_stops_the_run_with_both_numbers_named(self):
        verdict = check(1500, limit=1000)
        assert verdict.exceeded is True
        assert "1,500" in verdict.reason
        assert "1,000" in verdict.reason
        assert BUDGET_ENV in verdict.reason

    def test_a_negative_spend_is_floored_rather_than_wrapping(self):
        assert check(-5, limit=1000).spent == 0

    def test_the_environment_supplies_the_ceiling_when_none_is_passed(self, monkeypatch):
        monkeypatch.setenv(BUDGET_ENV, "100")
        assert check(101).exceeded is True
        assert check(99).exceeded is False

    def test_it_counts_generated_tokens_only(self, monkeypatch):
        """Cache reads dominate a raw total by 30-100x.

        A ceiling against the sum would fire on a run's third turn or never,
        depending on how much context it happened to re-read.
        """
        monkeypatch.setenv(BUDGET_ENV, "1000")
        # A run that generated 900 tokens is under, whatever it re-read.
        assert check(900).exceeded is False


class TestRuntimeStopsAtTheBoundary:
    def test_the_runtime_checks_the_budget_between_layers(self):
        """Between layers is where the run is between commitments."""
        import inspect

        from src.swarm import runtime

        source = inspect.getsource(runtime.SwarmRuntime._execute_run)
        assert "budget_check(run.total_output_tokens)" in source
        assert "run_over_budget" in source

    def test_the_over_budget_event_carries_what_was_spent_and_the_limit(self):
        import inspect

        from src.swarm import runtime

        source = inspect.getsource(runtime.SwarmRuntime._execute_run)
        assert "spent_output_tokens" in source
        assert '"limit": verdict.limit' in source
