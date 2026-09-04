"""Why runs do not finish, read off the runs themselves.

The reliability gate shipped in the previous commit asked ``ProcessRecord``
whether runs complete. ``ProcessRecord`` describes **Claude Code sessions**:
none of the twenty-five on this ledger carries a ``run_id`` or a ``preset``,
and its ``completed`` flag means the session-end hook fired. So an unattended
*swarm* scheduler was being gated on whether somebody's editor session closed
cleanly, which is not merely a loose proxy -- it is a different population
measured on a different event.

This module asks the swarm runs. Eighteen on disk, three completed. The number
barely moves (16.7% against 16%), and that near-coincidence is exactly why the
wrong table went unnoticed.

The second thing it asks is *why*, and the answer changes what the rate means:

    15 of 15 failed runs failed on the provider.
    52 failed tasks: 35 provider errors, 17 blocked behind one.
    Zero failed because research went wrong, timed out, or hit bad data.

So the completion rate on this machine is a statement about an unpaid account,
not about whether the research converges. Both facts matter and they are not
interchangeable, which is why :func:`summarise` reports them side by side and
refuses to collapse them into one number.

Updated 2026-09-04. A local ollama gave the machine a provider that completes,
and the first run launched onto it failed for a research reason rather than a
billing one: the 3B model answered in prose where the task required tool calls,
and the output contract rejected the result. So "zero research failures" above
is now one, and the distinction the module was built to draw has finally been
drawn against a real example rather than an imagined one.

**The rate is not adjusted for this.** It would be easy to exclude provider
failures, watch the rate jump to 3 of 3, and open the gate -- and it would be
wrong. An unattended cycle on a machine whose provider is dead produces
nothing regardless of whose fault that is, and reclassifying a failure does
not make a conclusion appear. What the cause is *for* is telling the operator
which thing to fix, because "top up the account" and "improve the research"
are different jobs and the refusal used to imply the second one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Ordered longest-match-first: a message can contain several of these, and the
#: first one that fits is the one that stopped the task. "Blocked" is checked
#: first because a task blocked behind a provider failure carries the word
#: "failed" from its upstream and would otherwise be counted twice.
_CAUSE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("blocked: upstream", "blocked_by_upstream"),
    ("insufficient balance", "provider_no_balance"),
    ("error code: 402", "provider_no_balance"),
    ("user not found", "provider_bad_credentials"),
    ("error code: 401", "provider_bad_credentials"),
    ("error code: 403", "provider_bad_credentials"),
    ("not logged in", "provider_not_logged_in"),
    ("usage_limit", "provider_rate_limited"),
    ("error code: 429", "provider_rate_limited"),
    ("http 429", "provider_rate_limited"),
    ("service_unavailab", "provider_unavailable"),
    ("connection error", "provider_unavailable"),
    ("exceeded layer deadline", "timeout"),
    ("timed out", "timeout"),
    # First observed 2026-09-04, against a local 3B model: the worker talked
    # instead of acting, so the output contract rejected it. This is a research
    # failure and not the provider's -- the completion was served fine -- and
    # the two want different fixes, which is what the split below is for.
    ("output contract not met", "output_contract_unmet"),
    # The stale-run reaper's own message. The host process died before the run
    # finished -- a crashed harness, a killed terminal, a machine that slept.
    # Neither the provider's fault nor the research's, and it recurs often
    # enough during development to deserve a name rather than landing in
    # "other" and making every novel cause harder to spot.
    ("run reaped", "host_exited"),
)

#: Causes that are the provider's, not the research's.
PROVIDER_CAUSES = frozenset(
    {
        "provider_no_balance",
        "provider_bad_credentials",
        "provider_not_logged_in",
        "provider_rate_limited",
        "provider_unavailable",
    }
)


def classify_error(error: str | None) -> str | None:
    """Return the cause of one task failure, or ``None`` when there is none.

    An error that matches nothing is ``other``, deliberately not silently
    dropped: a cause nobody has a name for is the interesting one, and a
    classifier that quietly discards its misses reports a cleaner world than
    the one it is looking at.
    """
    if not error:
        return None
    haystack = error.lower()
    for needle, cause in _CAUSE_PATTERNS:
        if needle in haystack:
            return cause
    return "other"


@dataclass(frozen=True)
class RunReliability:
    """How runs have gone, and why the failures failed.

    Attributes:
        runs: Runs inspected.
        completed: Runs that reached a conclusion.
        failed_runs_by_cause: Cause of each failed run, counted once per run.
        failed_tasks_by_cause: Cause of every failed task.
        provider_failed_runs: Failed runs whose cause was the provider's.
    """

    runs: int
    completed: int
    failed_runs_by_cause: dict[str, int]
    failed_tasks_by_cause: dict[str, int]
    provider_failed_runs: int

    @property
    def completion_rate(self) -> float | None:
        """Share of runs that reached a conclusion, or ``None`` with no runs."""
        return (self.completed / self.runs) if self.runs else None

    @property
    def dominant_cause(self) -> str:
        """The cause behind the most failed runs, empty when none failed."""
        if not self.failed_runs_by_cause:
            return ""
        return max(self.failed_runs_by_cause.items(), key=lambda kv: kv[1])[0]

    def blame(self) -> str:
        """Return one sentence naming what has actually been stopping runs."""
        failed = self.runs - self.completed
        if not failed:
            return "no failed runs to explain"
        if self.provider_failed_runs == failed:
            return (
                f"all {failed} failed runs died on the provider "
                f"(mostly {self.dominant_cause}); none failed for a research reason"
            )
        research = failed - self.provider_failed_runs
        return (
            f"{self.provider_failed_runs}/{failed} failed runs died on the provider, "
            f"{research} for other reasons (most common: {self.dominant_cause})"
        )


def summarise(*, runs_root: Path | None = None, limit: int = 500) -> RunReliability:
    """Read the swarm runs on disk and say how they went, and why.

    Args:
        runs_root: Directory holding run folders. Defaults to the configured one.
        limit: Maximum runs to inspect, newest first.

    Returns:
        The summary. A directory with no runs yields zeros rather than raising:
        a machine that has never run anything is a real state, and the gate
        above treats it as unmeasured rather than as healthy.
    """
    from src.swarm.store import SwarmStore, swarm_runs_root
    from src.swarm.task_store import TaskStore

    root = runs_root or swarm_runs_root()
    if not Path(root).is_dir():
        return RunReliability(0, 0, {}, {}, 0)

    store = SwarmStore(Path(root))
    try:
        runs = store.list_runs(limit=limit)
    except Exception:  # noqa: BLE001 - an unreadable store is "unmeasured"
        return RunReliability(0, 0, {}, {}, 0)

    completed = 0
    failed_runs: dict[str, int] = {}
    failed_tasks: dict[str, int] = {}
    provider_failed = 0

    for run in runs:
        if run.status.value == "completed":
            completed += 1
            continue
        try:
            tasks = TaskStore(store.run_dir(run.id)).load_all()
        except Exception:  # noqa: BLE001
            tasks = []

        causes = [classify_error(task.error) for task in tasks]
        for cause in causes:
            if cause:
                failed_tasks[cause] = failed_tasks.get(cause, 0) + 1

        # A run's cause is the first one that is not "blocked": every blocked
        # task is downstream of something else, and counting it as the reason
        # would report the symptom that spreads rather than the one that
        # started.
        primary = next(
            (c for c in causes if c and c != "blocked_by_upstream"), "unknown"
        )
        failed_runs[primary] = failed_runs.get(primary, 0) + 1
        if primary in PROVIDER_CAUSES:
            provider_failed += 1

    return RunReliability(
        runs=len(runs),
        completed=completed,
        failed_runs_by_cause=failed_runs,
        failed_tasks_by_cause=failed_tasks,
        provider_failed_runs=provider_failed,
    )


def render(summary: RunReliability) -> str:
    """Render the summary as something that names the next action."""
    rate = summary.completion_rate
    rate_text = f"{rate:.0%}" if rate is not None else "unmeasured"
    lines = [
        f"swarm runs: {summary.completed}/{summary.runs} reached a conclusion ({rate_text})",
        f"  {summary.blame()}",
    ]
    if summary.failed_runs_by_cause:
        lines.append("  failed runs by cause:")
        for cause, count in sorted(
            summary.failed_runs_by_cause.items(), key=lambda kv: -kv[1]
        ):
            lines.append(f"    {count:3d}  {cause}")
    if summary.failed_tasks_by_cause:
        lines.append("  failed tasks by cause:")
        for cause, count in sorted(
            summary.failed_tasks_by_cause.items(), key=lambda kv: -kv[1]
        ):
            lines.append(f"    {count:3d}  {cause}")
    return "\n".join(lines)


__all__ = [
    "PROVIDER_CAUSES",
    "RunReliability",
    "classify_error",
    "render",
    "summarise",
]
