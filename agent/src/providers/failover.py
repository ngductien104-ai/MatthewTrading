"""Move a run onto a provider that can work, when the one it has cannot.

On 2026-08-27 an exhausted balance took down thirty-one tasks. Every one of
them burned its full retry budget against an error no amount of waiting could
fix, and the run ended having spent an hour to produce nothing.
``classify_fatal_provider_error`` stopped the retrying; this stops the run
ending there, when another provider is configured and healthy.

Four decisions, each of which the alternative gets wrong.

**Only on failures that waiting cannot fix.** A rate limit is transient, and
leaving a provider over one abandons an account that is about to work. The
switch fires on the same classification the retry loop already trusts: a
revoked key, an exhausted balance, a forbidden account.

**A candidate is probed before the run moves onto it.** Switching to an
untested provider swaps a known-dead endpoint for an unknown one, and the run
finds out one task at a time -- which is the failure this whole gate exists to
end. ``probe_provider`` ends with a real completion, so "healthy" means the
account can spend, not that a key parses.

**A fallback declares its model, not just its provider.** ``deepseek-v4-pro``
does not exist on Groq. Carrying the old model name across a switch produces a
404 that reads like a broken candidate, so the configuration format is
``provider:model`` and an entry without a model is refused by name.

**Off unless configured, and never silent.** ``VIBE_TRADING_PROVIDER_FALLBACKS``
is unset by default. A run that changes provider halfway has changed what
produced the research, and this branch just added ``git_commit`` and ``seed``
to ``SwarmRun`` so that a change in output quality has something to be
attributed to. A switch nobody recorded would undo that, so every switch is
returned to the caller to be written onto the run.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass

from src.providers.health import ProviderHealth, probe_provider

#: Comma-separated ``provider:model`` entries, tried in order.
FALLBACKS_ENV = "VIBE_TRADING_PROVIDER_FALLBACKS"

#: Serialises the probe-and-switch. Several workers hit the same wall within
#: milliseconds of each other; without this they would each probe every
#: candidate and race to write the environment.
_switch_lock = threading.Lock()


@dataclass(frozen=True)
class Candidate:
    """One configured fallback.

    Attributes:
        provider: Provider name, as ``LANGCHAIN_PROVIDER`` would carry it.
        model: Model name. Never empty -- an entry without one is not parsed.
    """

    provider: str
    model: str

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass(frozen=True)
class Switch:
    """A provider change that happened, or the reason none did.

    Attributes:
        switched: Whether the process is now pointed at a new provider.
        from_provider: What it was on.
        to_provider: What it is on now, empty when nothing changed.
        reason: Why no switch happened, empty when one did.
        probed: Each candidate tried and what it answered, for the record.
    """

    switched: bool
    from_provider: str = ""
    to_provider: str = ""
    reason: str = ""
    probed: tuple[str, ...] = ()


def configured_fallbacks(raw: str | None = None) -> list[Candidate]:
    """Return the declared fallback chain, in order.

    Args:
        raw: Value to parse instead of the environment, for testing.

    Returns:
        Parsed candidates. Entries that do not name both a provider and a model
        are dropped: a provider without a model cannot be probed, and guessing
        one would put the run on an endpoint nobody chose.
    """
    value = (raw if raw is not None else os.getenv(FALLBACKS_ENV, "")).strip()
    if not value:
        return []
    candidates: list[Candidate] = []
    for entry in value.split(","):
        provider, _, model = entry.strip().partition(":")
        provider, model = provider.strip(), model.strip()
        if provider and model:
            candidates.append(Candidate(provider, model))
    return candidates


def current_provider() -> str:
    """Return the provider the process is pointed at."""
    return (os.getenv("LANGCHAIN_PROVIDER") or "").strip()


def activate(candidate: Candidate) -> None:
    """Point the process at *candidate*.

    The provider layer reads ``LANGCHAIN_PROVIDER`` and ``LANGCHAIN_MODEL_NAME``
    and derives the OpenAI-compatible variables from them, so the derived ones
    are cleared first: leaving the previous base URL in place would send the new
    provider's model to the old provider's endpoint.
    """
    from src.providers.llm import _sync_provider_env

    os.environ["LANGCHAIN_PROVIDER"] = candidate.provider
    os.environ["LANGCHAIN_MODEL_NAME"] = candidate.model
    for stale in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_BASE"):
        os.environ.pop(stale, None)
    _sync_provider_env()


def failover(*, fallbacks: list[Candidate] | None = None) -> Switch:
    """Move onto the first configured fallback that can actually work.

    Probes candidates in order and switches to the first whose completion is
    accepted. A candidate that answers with its own dead credentials is skipped
    rather than switched to, which is the entire point of probing first.

    Args:
        fallbacks: Chain to use instead of the configured one, for testing.

    Returns:
        The switch, or a :class:`Switch` with ``switched=False`` and a reason.
        Never raises: a failover that throws turns a recoverable provider
        failure into a crash.
    """
    chain = configured_fallbacks() if fallbacks is None else fallbacks
    origin = current_provider()
    if not chain:
        return Switch(False, from_provider=origin, reason=f"no {FALLBACKS_ENV} configured")

    with _switch_lock:
        # Re-read inside the lock. While this thread waited, another worker may
        # already have moved the process onto a healthy provider, and switching
        # again would walk past it for no reason.
        origin = current_provider()
        probed: list[str] = []
        for candidate in chain:
            if candidate.provider == origin:
                probed.append(f"{candidate} skipped (already current)")
                continue
            try:
                health = probe_provider(
                    provider=candidate.provider, model=candidate.model
                )
            except Exception as exc:  # noqa: BLE001 - a broken probe is a result
                probed.append(f"{candidate} probe failed: {exc}")
                continue
            probed.append(f"{candidate} {health.status}")
            if health.ok:
                try:
                    activate(candidate)
                except Exception as exc:  # noqa: BLE001
                    probed.append(f"{candidate} activation failed: {exc}")
                    continue
                return Switch(
                    True,
                    from_provider=origin,
                    to_provider=str(candidate),
                    probed=tuple(probed),
                )
        return Switch(
            False,
            from_provider=origin,
            reason="no configured fallback is healthy",
            probed=tuple(probed),
        )


def describe(switch: Switch) -> str:
    """Return one line saying what happened, including what was tried."""
    if switch.switched:
        head = f"provider failover: {switch.from_provider or 'unset'} -> {switch.to_provider}"
    else:
        head = f"provider failover not taken: {switch.reason}"
    return f"{head} [{'; '.join(switch.probed)}]" if switch.probed else head


__all__ = [
    "Candidate",
    "FALLBACKS_ENV",
    "ProviderHealth",
    "Switch",
    "activate",
    "configured_fallbacks",
    "current_provider",
    "describe",
    "failover",
]
