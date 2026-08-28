"""Regression: a dead provider account must stop the run, not every task in turn.

On 2026-08-27 the runs on disk showed 31 tasks each failing with the same
``402 Insufficient Balance``, plus 8 with ``401 User not found`` — every one
having first burned its full retry budget, and every later layer walking into
the same wall. Only 3 of 18 runs completed.

The error strings below are copied verbatim from ``agent/.swarm/runs``.
"""

import pytest

from src.swarm.runtime import classify_fatal_provider_error

FATAL = [
    "LLM call failed at iteration 0: Error code: 402 - {'error': {'message': "
    "'Insufficient Balance', 'type': 'unknown_error', 'param': None, 'code': None}}",
    "LLM call failed at iteration 0: Error code: 401 - {'error': {'message': "
    "'User not found.', 'code': 401}}",
]

RETRYABLE = [
    "LLM call failed at iteration 0: Connection error.",
    "LLM call failed at iteration 14: OpenAI Codex response failed: "
    "{'type': 'service_unavailable_error', 'code': 'server_is_overloaded'}",
    "Error code: 429 - rate limit exceeded",
    "Worker exceeded layer deadline of 3660s",
    "Blocked: upstream not completed (task-risk=blocked)",
]


@pytest.mark.parametrize("error", FATAL)
def test_credential_and_billing_failures_are_fatal(error):
    assert classify_fatal_provider_error(error) is not None


@pytest.mark.parametrize("error", RETRYABLE)
def test_transient_failures_stay_retryable(error):
    """Overload, rate limits and timeouts must NOT abort the run.

    Cancelling on a 503 would be worse than the bug being fixed: those are
    exactly the failures a retry is for.
    """
    assert classify_fatal_provider_error(error) is None


def test_no_error_is_not_fatal():
    assert classify_fatal_provider_error(None) is None
    assert classify_fatal_provider_error("") is None


def test_a_number_that_merely_contains_402_is_not_fatal():
    """A loose substring match would cancel healthy runs.

    Token counts, timestamps and task ids routinely contain these digits;
    the patterns are anchored to how providers actually phrase the error.
    """
    assert classify_fatal_provider_error(
        "LLM call failed at iteration 3: request used 21402 prompt tokens"
    ) is None
    assert classify_fatal_provider_error("run swarm-20260827-064019-4021abcd timed out") is None
