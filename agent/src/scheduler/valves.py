"""The valves that decide whether an unattended research cycle may run.

The plan is blunt about this module's purpose: *a scheduler on a runtime where
three runs in twenty-four reach a conclusion automates the failing.* So the
first thing here is not a scheduler, it is the set of refusals that must pass
before one is allowed to start, and the honest reading of this ledger today is
that they do not pass.

Five gates, each answering a different question, each able to refuse alone.

``enabled``
    An explicit opt-in. A scheduler that runs because it was merged is a
    scheduler nobody decided to run.

``reliability``
    The completion rate of **swarm runs**, measured off the runs themselves
    rather than asserted. This is the gate the plan actually asks for, and at
    the time of writing it fails: 3 of 18 runs reached a conclusion, 17%. An
    unattended run cannot be more reliable than an attended one, so scheduling
    on this number automates spending without producing. It also names the
    cause -- every failure on this machine so far has been the provider's, and
    a refusal that implied the research was at fault would point the reader at
    the wrong repair.

``novelty``
    Do not re-research what the ledger already covers. A candidate is novel
    when no call on it is still inside the recency window; sixteen calls
    covering fourteen tickers is a small enough universe that without this the
    loop would grind the same names.

``evidence``
    Only act on lessons that survived their own evidence bar. ``lessons``
    marks a finding ``confirmed`` at eight observations and ``provisional``
    below it, and provisional findings expire. A loop that steers on
    provisional lessons amplifies its own guesses, which is the exact failure
    the lessons module was shaped to avoid.

``budget``
    A token ceiling per cycle and a cap on pull requests per month. The first
    bounds one cycle, the second bounds the loop: a scheduler that opens
    thirty PRs a month has not automated research, it has automated review
    work for a person.

Nothing here launches anything. :func:`decide` returns a decision and the
reasons behind it; acting on it belongs to the caller, and the caller opens a
pull request rather than committing, because unattended work that writes to a
branch nobody reviews is the same failure wearing a nicer name.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:  # pragma: no cover - import cycle at runtime, types only
    from src.scheduler.reliability import RunReliability

#: Explicit opt-in. Anything but "1"/"true"/"yes" leaves the scheduler off.
ENABLED_ENV = "VIBE_TRADING_SCHEDULER_ENABLED"

#: Minimum share of runs that must have reached a conclusion.
FLOOR_ENV = "VIBE_TRADING_SCHEDULER_MIN_COMPLETION"

#: Generated-token ceiling for one cycle.
CYCLE_BUDGET_ENV = "VIBE_TRADING_SCHEDULER_CYCLE_TOKENS"

#: Pull requests the loop may open in a calendar month.
PR_CAP_ENV = "VIBE_TRADING_SCHEDULER_MONTHLY_PRS"

#: Days within which an existing call makes a ticker un-novel.
NOVELTY_DAYS_ENV = "VIBE_TRADING_SCHEDULER_NOVELTY_DAYS"

#: Default completion floor. This is a judgement, not a measurement, and is
#: labelled as one: an unattended run cannot be more reliable than an attended
#: one, so a machine that finishes fewer than half of its supervised runs
#: should not be starting unsupervised ones. Configurable, because the right
#: number is an operator's call -- but not absent, because a floor that has to
#: be set before it applies is a floor nobody sets.
DEFAULT_COMPLETION_FLOOR = 0.5

#: Default recency window for novelty, in days. One quarter: the period after
#: which a Vietnamese listed company has published new financials and the
#: previous call is answering a question about different numbers.
DEFAULT_NOVELTY_DAYS = 90

#: Default cycle ceiling in generated tokens, and monthly PR cap. Both are
#: deliberately small. A first unattended cycle that costs little and produces
#: one reviewable thing is the only version of this worth switching on.
DEFAULT_CYCLE_TOKENS = 200_000
DEFAULT_MONTHLY_PRS = 4


@dataclass(frozen=True)
class Valve:
    """One gate's answer.

    Attributes:
        name: Gate name, as it appears in a decision.
        passed: Whether this gate permits the cycle.
        detail: What it measured, in numbers, whether it passed or not.
    """

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CycleDecision:
    """Whether a cycle may run, and everything that went into saying so.

    Attributes:
        allowed: True only when every valve passed.
        valves: Each gate's answer, in evaluation order.
        candidates: Tickers that passed the novelty gate, in ledger order.
        cycle_token_ceiling: Ceiling that would apply to this cycle.
    """

    allowed: bool
    valves: tuple[Valve, ...]
    candidates: tuple[str, ...] = ()
    cycle_token_ceiling: int = 0

    def blockers(self) -> list[str]:
        """Return the detail of every gate that refused."""
        return [valve.detail for valve in self.valves if not valve.passed]


def _flag(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _positive_int(raw: str | None, default: int) -> int:
    """Return a positive integer, falling back on anything unparseable.

    A malformed ceiling is treated as absent rather than as zero, for the same
    reason the run budget does it: reading a typo as "allow nothing" turns a
    configuration slip into a silent shutdown, and reading it as "allow
    everything" turns one into an unbounded spend. The default is neither.
    """
    value = (raw or "").strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _fraction(raw: str | None, default: float) -> float:
    value = (raw or "").strip()
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if 0.0 <= parsed <= 1.0 else default


def enabled_valve(raw: str | None = None) -> Valve:
    """Refuse unless someone opted in explicitly."""
    on = _flag(raw if raw is not None else os.getenv(ENABLED_ENV))
    return Valve(
        "enabled",
        on,
        f"{ENABLED_ENV} is set" if on else f"{ENABLED_ENV} is not set; scheduler is off",
    )


def reliability_valve(
    summary: "RunReliability | None" = None, *, floor: float | None = None
) -> Valve:
    """Refuse while too few *swarm runs* reach a conclusion.

    The first version of this gate counted ``ProcessRecord`` rows, which
    describe Claude Code **sessions** -- none of them carries a ``run_id`` or a
    ``preset``, and ``completed`` there means an editor session closed cleanly.
    Gating an unattended swarm scheduler on that is not a loose proxy, it is a
    different population measured on a different event. It went unnoticed
    because the two numbers happen to sit a percentage point apart: 4/25 of the
    sessions, 3/18 of the runs.

    The refusal now names what has actually been stopping runs. On this machine
    every failed run died on the provider, so the fix is a billing one, and a
    message implying the research is unreliable would send the reader to the
    wrong job.

    The rate itself is **not** adjusted for cause. Excluding provider failures
    would take it to 3 of 3 and open the gate, and that would be wrong: an
    unattended cycle on a machine whose provider is dead produces nothing
    regardless of whose fault it is.

    Args:
        summary: Run reliability. Read from disk when omitted.
        floor: Minimum completion share. Defaults to the configured one.

    Returns:
        The valve. With no runs at all it refuses: a completion rate over zero
        runs is not a high number, it is no number, and treating an unmeasured
        machine as a reliable one is precisely the mistake.
    """
    from src.scheduler.reliability import summarise

    limit = floor if floor is not None else _fraction(os.getenv(FLOOR_ENV), DEFAULT_COMPLETION_FLOOR)
    stats = summary if summary is not None else summarise()
    if not stats.runs:
        return Valve("reliability", False, "no swarm runs on disk; completion rate is unmeasured")
    rate = stats.completion_rate or 0.0
    passed = rate >= limit
    detail = (
        f"{stats.completed}/{stats.runs} runs reached a conclusion ({rate:.0%}); "
        f"floor is {limit:.0%}"
    )
    if not passed:
        detail += f" -- {stats.blame()}"
    return Valve("reliability", passed, detail)


def novelty_valve(
    universe: Sequence[str],
    calls: Sequence[Mapping[str, Any]],
    *,
    today: date | None = None,
    window_days: int | None = None,
) -> tuple[Valve, tuple[str, ...]]:
    """Keep only tickers the ledger has not covered recently.

    Args:
        universe: Candidate tickers to consider.
        calls: Call payloads, each carrying ``ticker`` and ``as_of``.
        today: Date to measure recency from. Defaults to today, UTC.
        window_days: Recency window. Defaults to the configured one.

    Returns:
        The valve and the surviving candidates, in the order given. The valve
        refuses when nothing survives -- a cycle with no novel candidate has
        nothing to research, and running it anyway re-researches a name whose
        answer is already on the ledger.
    """
    days = window_days if window_days is not None else _positive_int(
        os.getenv(NOVELTY_DAYS_ENV), DEFAULT_NOVELTY_DAYS
    )
    now = today or datetime.now(timezone.utc).date()
    cutoff = now - timedelta(days=days)

    recent: set[str] = set()
    for call in calls:
        stamp = str(call.get("as_of") or "")
        try:
            when = date.fromisoformat(stamp[:10])
        except ValueError:
            # An unparseable date is treated as recent. Guessing it is old
            # would let the loop re-research a name on the strength of a
            # field it could not read.
            recent.add(str(call.get("ticker") or "").upper())
            continue
        if when >= cutoff:
            recent.add(str(call.get("ticker") or "").upper())

    survivors = tuple(
        ticker for ticker in universe if ticker.upper() not in recent
    )
    return (
        Valve(
            "novelty",
            bool(survivors),
            f"{len(survivors)}/{len(universe)} candidates have no call since "
            f"{cutoff.isoformat()}",
        ),
        survivors,
    )


def evidence_valve(lessons: Sequence[Mapping[str, Any]]) -> Valve:
    """Refuse unless at least one lesson has cleared its evidence bar.

    ``lessons`` marks a finding confirmed at eight observations and provisional
    below it. A loop steering on provisional findings is amplifying its own
    guesses, which is the failure the lessons module is shaped to avoid, so the
    gate asks for at least one confirmed lesson before the loop is allowed to
    act on any of them.
    """
    confirmed = [item for item in lessons if item.get("status") == "confirmed"]
    return Valve(
        "evidence",
        bool(confirmed),
        f"{len(confirmed)} confirmed of {len(lessons)} lessons",
    )


def budget_valve(
    prs_this_month: int,
    *,
    cycle_tokens: int | None = None,
    monthly_prs: int | None = None,
) -> tuple[Valve, int]:
    """Bound one cycle, and bound the loop.

    Args:
        prs_this_month: Pull requests the loop has already opened this month.
        cycle_tokens: Ceiling for this cycle. Defaults to the configured one.
        monthly_prs: Cap on pull requests. Defaults to the configured one.

    Returns:
        The valve and the token ceiling that would apply.
    """
    ceiling = cycle_tokens if cycle_tokens is not None else _positive_int(
        os.getenv(CYCLE_BUDGET_ENV), DEFAULT_CYCLE_TOKENS
    )
    cap = monthly_prs if monthly_prs is not None else _positive_int(
        os.getenv(PR_CAP_ENV), DEFAULT_MONTHLY_PRS
    )
    passed = prs_this_month < cap
    return (
        Valve(
            "budget",
            passed,
            f"{prs_this_month}/{cap} pull requests opened this month; "
            f"cycle ceiling {ceiling:,} generated tokens"
            + ("" if passed else " -- monthly cap reached"),
        ),
        ceiling,
    )


def decide(
    *,
    run_reliability: "RunReliability | None" = None,
    calls: Sequence[Mapping[str, Any]],
    lessons: Sequence[Mapping[str, Any]],
    universe: Sequence[str],
    prs_this_month: int = 0,
    today: date | None = None,
    enabled: str | None = None,
) -> CycleDecision:
    """Return whether an unattended cycle may run, and why.

    Every valve is evaluated, including the ones after the first refusal.
    Short-circuiting would report one blocker at a time and turn a machine with
    four problems into four consecutive discoveries.
    """
    novelty, candidates = novelty_valve(universe, calls, today=today)
    budget, ceiling = budget_valve(prs_this_month)
    valves = (
        enabled_valve(enabled),
        reliability_valve(run_reliability),
        novelty,
        evidence_valve(lessons),
        budget,
    )
    return CycleDecision(
        allowed=all(valve.passed for valve in valves),
        valves=valves,
        candidates=candidates,
        cycle_token_ceiling=ceiling,
    )


def render(decision: CycleDecision) -> str:
    """Render a decision as something a person can act on."""
    head = "cycle ALLOWED" if decision.allowed else "cycle REFUSED"
    lines = [f"scheduler: {head}"]
    for valve in decision.valves:
        mark = "ok  " if valve.passed else "STOP"
        lines.append(f"  [{mark}] {valve.name:<12} {valve.detail}")
    if decision.candidates:
        shown = ", ".join(decision.candidates[:12])
        more = "" if len(decision.candidates) <= 12 else f" (+{len(decision.candidates) - 12})"
        lines.append(f"  candidates: {shown}{more}")
    if not decision.allowed:
        lines.append("  nothing was launched")
    return "\n".join(lines)


# -- monthly pull-request accounting ------------------------------------------


def _state_path(root: Path | None = None) -> Path:
    base = root or (Path.home() / ".vibe-trading")
    return base / "scheduler_prs.json"


def prs_opened_this_month(*, root: Path | None = None, today: date | None = None) -> int:
    """Return how many pull requests the loop opened in the current month.

    A missing or unreadable file counts as zero. That is the permissive
    direction, and it is chosen deliberately: the cap exists to stop a loop
    running away, and a loop that has never opened a PR has no file. The
    alternative -- treating an unreadable file as "cap reached" -- would jam
    the scheduler shut on a corrupted byte with no way to tell why.
    """
    now = today or datetime.now(timezone.utc).date()
    try:
        data = json.loads(_state_path(root).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - absent or corrupt is zero
        return 0
    return int(data.get(now.strftime("%Y-%m"), 0) or 0)


def record_pr_opened(*, root: Path | None = None, today: date | None = None) -> int:
    """Record that a pull request was opened, and return the new count."""
    now = today or datetime.now(timezone.utc).date()
    key = now.strftime("%Y-%m")
    path = _state_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        data = {}
    data[key] = int(data.get(key, 0) or 0) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data[key]


__all__ = [
    "CYCLE_BUDGET_ENV",
    "CycleDecision",
    "DEFAULT_COMPLETION_FLOOR",
    "DEFAULT_CYCLE_TOKENS",
    "DEFAULT_MONTHLY_PRS",
    "DEFAULT_NOVELTY_DAYS",
    "ENABLED_ENV",
    "FLOOR_ENV",
    "NOVELTY_DAYS_ENV",
    "PR_CAP_ENV",
    "Valve",
    "budget_valve",
    "decide",
    "enabled_valve",
    "evidence_valve",
    "novelty_valve",
    "prs_opened_this_month",
    "record_pr_opened",
    "reliability_valve",
    "render",
]
