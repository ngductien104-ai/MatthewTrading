"""Tell a provider failure worth retrying from one that never will be.

On 2026-08-27 a single exhausted balance took down 31 tasks one at a time.
Each burned its full retry budget against an error that no amount of waiting
could fix, and every later layer walked into the same wall. Distinguishing the
two kinds of failure is the difference between a run that fails in seconds and
one that fails in an hour having spent a budget on nothing.

The patterns are anchored to how providers actually phrase these ("Error code:
402 - ..."), not to the bare number. A loose "402" would also match a token
count or a timestamp, and a false positive here cancels a healthy run.
"""

from __future__ import annotations

#: Provider failures that no amount of retrying will fix: a revoked key, an
#: exhausted balance, a forbidden account.
FATAL_PROVIDER_PATTERNS: tuple[tuple[str, str], ...] = (
    ("insufficient balance", "provider account is out of credit"),
    ("insufficient_quota", "provider account is out of credit"),
    ("error code: 402", "provider returned 402 (payment required)"),
    ("status 402", "provider returned 402 (payment required)"),
    ("payment required", "provider returned 402 (payment required)"),
    ("error code: 401", "provider returned 401 (credentials rejected)"),
    ("status 401", "provider returned 401 (credentials rejected)"),
    ("invalid_api_key", "provider rejected the API key"),
    ("incorrect api key", "provider rejected the API key"),
    ("error code: 403", "provider returned 403 (account forbidden)"),
    ("status 403", "provider returned 403 (account forbidden)"),
)


def classify_fatal_provider_error(error: str | None) -> str | None:
    """Return a reason when *error* is a non-retryable provider failure.

    Args:
        error: Error text from a worker result, if any.

    Returns:
        A short reason string, or None when the error is worth retrying --
        rate limits, overload, timeouts, transient network faults.
    """
    if not error:
        return None
    haystack = error.lower()
    for needle, reason in FATAL_PROVIDER_PATTERNS:
        if needle in haystack:
            return reason
    return None
