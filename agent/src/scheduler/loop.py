"""Read the ledger, ask the valves, and do nothing unless all of them agree.

This is the whole scheduler. It is small on purpose: the valuable part of an
unattended loop is not the loop, it is the set of conditions under which it is
allowed to spend money without anybody watching, and those live in
:mod:`src.scheduler.valves`.

What it does when the valves agree is open a pull request, never a commit. The
plan says so and the reason is worth keeping in front of the reader: work that
lands unreviewed on a branch nobody reads is the same failure as work that
lands on main, arriving more politely. The research itself runs through the
existing swarm runtime, under the per-cycle token ceiling the valves computed.

On this machine today it does not get that far. ``status`` prints the refusal:
3 of 18 swarm runs have reached a conclusion, and the reliability gate stops
there -- naming, because it now can, that every one of the fifteen failures was
the provider's rather than the research's.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from src.learning.store import LearningStore, default_db_path
from src.scheduler.reliability import summarise
from src.scheduler.valves import (
    CycleDecision,
    decide,
    prs_opened_this_month,
    record_pr_opened,
    render,
)

logger = logging.getLogger(__name__)

#: Tickers a cycle may pick from when no universe is supplied. VN30 is fetched
#: live elsewhere in this repo; here the caller passes what it wants looked at,
#: and an empty default means "nothing to research" rather than a guess at what
#: the desk cares about this week.
DEFAULT_UNIVERSE: tuple[str, ...] = ()


@dataclass(frozen=True)
class CycleResult:
    """What one tick of the scheduler did.

    Attributes:
        decision: The valves' answer.
        launched: Whether research was started. False whenever the decision
            refused, and also whenever ``dry_run`` was asked for.
        detail: One line describing what happened.
    """

    decision: CycleDecision
    launched: bool
    detail: str
    run_id: str = ""
    branch: str = ""


def read_decision(
    *,
    universe: Sequence[str] = DEFAULT_UNIVERSE,
    today: date | None = None,
    db_path: str | None = None,
) -> CycleDecision:
    """Ask the valves, using what is actually on the ledger.

    Args:
        universe: Tickers the cycle may consider.
        today: Date to measure novelty and the monthly cap from.
        db_path: Ledger to read. Defaults to the configured one.

    Returns:
        The decision. Reading the ledger is offline -- no model, no network --
        so this is safe to call from a status command or a cron probe.
    """
    with LearningStore(db_path or default_db_path()) as store:
        calls = [call.to_dict() for call in store.list_calls()]
        lessons = [lesson.to_dict() for lesson in store.live_lessons()]
    return decide(
        run_reliability=summarise(),
        calls=calls,
        lessons=lessons,
        universe=universe,
        prs_this_month=prs_opened_this_month(today=today),
        today=today,
    )


def run_cycle(
    *,
    universe: Sequence[str] = DEFAULT_UNIVERSE,
    today: date | None = None,
    dry_run: bool = True,
    db_path: str | None = None,
    launcher: Callable[[list[str], int], str] | None = None,
) -> CycleResult:
    """Run one tick.

    Args:
        universe: Tickers the cycle may consider.
        today: Date to measure novelty and the monthly cap from.
        dry_run: When true -- the default -- decide and report without
            launching. The default is this way round because the failure mode
            of a scheduler is spending, and a caller who wants to spend can say
            so in one word.
        db_path: Ledger to read.
        launcher: Called with the candidates and the cycle token ceiling, and
            expected to start the research and return a run id. Injected rather
            than hard-wired to SwarmRuntime for a reason that is not testing
            convenience: no provider on this machine can complete a request
            today -- the configured one answers 402 -- so a launcher written
            here could not be exercised, and an unexercised code path presented
            as working is the bug this branch keeps finding. The caller supplies
            one when it has a provider that works.

    Returns:
        What happened, including the decision behind it.
    """
    decision = read_decision(universe=universe, today=today, db_path=db_path)
    if not decision.allowed:
        detail = "; ".join(decision.blockers())
        logger.info("Scheduler cycle refused: %s", detail)
        return CycleResult(decision, False, f"refused: {detail}")

    if dry_run:
        return CycleResult(
            decision,
            False,
            f"would research {', '.join(decision.candidates[:3])} "
            f"under a {decision.cycle_token_ceiling:,}-token ceiling",
        )

    if launcher is None:
        return CycleResult(
            decision,
            False,
            "no launcher supplied; the caller decides what runs research",
        )

    ceiling = decision.cycle_token_ceiling
    run_id = launcher(list(decision.candidates), ceiling)
    logger.info("Scheduler launched run %s under a %d-token ceiling", run_id, ceiling)
    return CycleResult(decision, True, f"launched {run_id}", run_id=run_id)


def _git(args: Sequence[str], *, cwd: str | None, runner: Callable[..., Any]) -> str:
    completed = runner(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return (completed.stdout or "").strip()


def open_pull_request(
    *,
    title: str,
    body: str,
    paths: Sequence[str],
    cwd: str | None = None,
    today: date | None = None,
    root: Path | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> str:
    """Put the cycle's output on a branch and open a pull request for it.

    A pull request and not a commit, because the point of the review step is
    that a person sees the work before it is part of the repository. Unattended
    work that lands on a branch nobody reads is the same failure in better
    manners, so this ends by asking for a review and records that it did --
    the monthly cap is what stops the loop turning into a queue of review work
    faster than anyone clears it.

    Args:
        title: Pull-request title.
        body: Pull-request body.
        paths: Files to include. Only these are staged: `git add -A` on this
            repository would sweep in an untracked vault of client research,
            and the repository is public.
        cwd: Repository directory.
        today: Date the PR counts against, for the monthly cap.
        root: Directory holding the monthly-count file. Defaults to
            ``~/.vibe-trading``. It is a parameter because without one a test
            of this function increments the operator's real cap -- which is
            exactly what happened the first time this ran, taking two slots off
            a live counter before anyone opened a pull request.
        runner: Process runner, injected for testing.

    Returns:
        The branch name.

    Raises:
        ValueError: If no paths were given. A pull request with nothing in it
            spends a slot from the monthly cap on an empty review.
    """
    if not paths:
        raise ValueError("refusing to open a pull request with no files in it")

    stamp = (today or datetime.now(timezone.utc).date()).strftime("%Y%m%d")
    branch = f"scheduler/{stamp}-{datetime.now(timezone.utc).strftime('%H%M%S')}"

    _git(["checkout", "-b", branch], cwd=cwd, runner=runner)
    _git(["add", "--", *paths], cwd=cwd, runner=runner)
    _git(["commit", "-m", title], cwd=cwd, runner=runner)
    _git(["push", "-u", "origin", branch], cwd=cwd, runner=runner)
    runner(
        ["gh", "pr", "create", "--title", title, "--body", body, "--head", branch],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    record_pr_opened(root=root, today=today)
    return branch


def status(*, universe: Sequence[str] = DEFAULT_UNIVERSE, today: date | None = None) -> str:
    """Return what the scheduler would do right now, and why."""
    return render(read_decision(universe=universe, today=today))
