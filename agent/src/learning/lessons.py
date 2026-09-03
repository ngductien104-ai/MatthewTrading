"""Derive playbook lessons from the ledger, by rule rather than by opinion.

The reference architecture for this stage is ACE (Agentic Context Engineering):
Generator writes, Reflector judges, Curator keeps, and the playbook grows by
increment rather than rewrite. Two of those three ideas survive contact with
this repository intact, and one does not.

**Kept: incremental delta.** A lesson's identity is derived from its domain and
its wording, so re-deriving the same finding lands on the same ``lesson_id`` and
updates its counts instead of writing a second copy. That is what protects
against context collapse -- a playbook rewritten wholesale each cycle erodes,
and the detail that erodes first is the specific, sector-level detail worth
keeping.

**Kept: expiry.** A lesson with no evidence stays provisional and dies after
ninety days, so the playbook cannot amplify its own bias.

**Dropped: the Reflector as a model.** Generator writes, Reflector grades,
Curator selects -- all three from the same model family -- is an examiner
marking its own paper, and it produces a confident number with nothing in it.
Every rule below is instead a **predicate over measured records**: an arithmetic
condition on outcomes the resolver scored against real prices, or on process
records parsed out of transcripts. A rule fires or it does not, and it cites the
records that made it fire. No model is asked whether a lesson is true.

The cost of that choice is that these lessons are narrow: they are about
calibration and process, because those are what the ledger currently measures.
Sector lessons -- the ``nganhang`` and ``batdongsan`` files the plan wants --
need per-sector evidence that eight graded calls cannot supply, and inventing
them from a language model is the exact failure this module is shaped to avoid.
They stay empty until the evidence exists, which is the honest state.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import TYPE_CHECKING, Any, Callable, Iterable, Mapping, Sequence

from src.learning.records import Lesson
from src.learning.store import LearningStore

if TYPE_CHECKING:  # pragma: no cover - types only
    from src.scheduler.reliability import RunReliability

#: Playbook domains. The sector files the plan names are listed so the layout
#: exists, and stay empty until sector-level evidence does.
DOMAINS = (
    "calibration",
    "process",
    "nganhang",
    "batdongsan",
    "banle",
    "vimo",
    "kythuat",
)

#: Fewest observations a rule may fire on. Below this the finding is an anecdote
#: with a decimal point, and writing it into a playbook that steers later work
#: is how a small sample becomes a standing belief.
MIN_OBSERVATIONS = 4

#: Observations required before a lesson is ``confirmed`` rather than
#: ``provisional``. Provisional lessons expire; confirmed ones do not, so this
#: is the threshold past which a finding is allowed to outlive its ninety days.
CONFIRM_OBSERVATIONS = 8

#: How far stated confidence may sit above the realised hit rate before it is
#: worth writing down, in points.
CALIBRATION_TOLERANCE = 5.0


@dataclass
class Candidate:
    """A lesson a rule proposes, with what made it fire.

    Attributes:
        domain: Playbook file it belongs in.
        statement: The line, written to be read by whoever starts the next
            analysis rather than by whoever wrote the rule.
        evidence_ids: Records that made the rule fire.
        observations: How many records that is. Becomes ``support_count``.
        rule: Which rule produced it, for auditing the deriver itself.
    """

    domain: str
    statement: str
    evidence_ids: list[str]
    observations: int
    rule: str

    def to_lesson(self) -> Lesson:
        """Return the storable lesson, with status set by evidence weight."""
        confirmed = self.observations >= CONFIRM_OBSERVATIONS and bool(self.evidence_ids)
        return Lesson(
            domain=self.domain,
            statement=self.statement,
            evidence_ids=self.evidence_ids,
            support_count=self.observations,
            status="confirmed" if confirmed else "provisional",
            rule=self.rule,
        )


def _graded(outcomes: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [item for item in outcomes if item.get("verdict") in ("hit", "miss")]


def calibration_rules(
    outcomes: Sequence[Mapping[str, Any]], calls: Mapping[str, Mapping[str, Any]]
) -> list[Candidate]:
    """Rules about whether stated numbers matched what happened."""
    found: list[Candidate] = []
    graded = _graded(outcomes)

    with_confidence = [
        (item, calls[item["call_id"]])
        for item in graded
        if item.get("call_id") in calls and calls[item["call_id"]].get("confidence") is not None
    ]
    if len(with_confidence) >= MIN_OBSERVATIONS:
        stated = fmean(call["confidence"] for _, call in with_confidence)
        realised = fmean(
            1.0 if item["verdict"] == "hit" else 0.0 for item, _ in with_confidence
        )
        gap = (stated - realised) * 100
        if gap > CALIBRATION_TOLERANCE:
            found.append(
                Candidate(
                    domain="calibration",
                    statement=(
                        f"Stated confidence runs about {gap:.0f} points above the realised "
                        f"hit rate ({stated:.0%} stated vs {realised:.0%} realised over "
                        f"{len(with_confidence)} graded calls). Before writing a confidence, "
                        "check it against this gap rather than against how the thesis feels."
                    ),
                    evidence_ids=sorted(
                        {eid for item, _ in with_confidence for eid in item.get("evidence_ids", [])}
                    ),
                    observations=len(with_confidence),
                    rule="calibration.overconfidence",
                )
            )

    # Benchmark disagreement. Reported as a rule because which benchmark is used
    # changed the answer on this ledger, and a hit rate quoted without saying
    # which one is not a measurement.
    disagreed = [
        item
        for item in graded
        if item.get("base_rate_pctile") is not None
        and _cross_verdict(item, calls) not in (None, item["verdict"])
    ]
    if len(disagreed) >= 2:
        tickers = sorted({calls[item["call_id"]]["ticker"] for item in disagreed})
        found.append(
            Candidate(
                domain="calibration",
                statement=(
                    f"The index and the median stock disagree about {len(disagreed)} of "
                    f"{len(graded)} graded calls ({', '.join(tickers)}). VN-Index is "
                    "cap-weighted, so beating it is not the same as beating the stock you "
                    "would otherwise have owned. Quote both, or say which one you mean."
                ),
                evidence_ids=sorted(
                    {eid for item in disagreed for eid in item.get("evidence_ids", [])}
                ),
                observations=len(graded),
                rule="calibration.benchmark_disagreement",
            )
        )

    # Stop-outs. An invalidated call is not a wrong direction, it is a position
    # that was closed, and if that keeps happening the entry is the problem.
    stopped = [item for item in outcomes if item.get("trigger_fired")]
    if len(stopped) >= 2:
        tickers = sorted({calls[item["call_id"]]["ticker"] for item in stopped if item["call_id"] in calls})
        found.append(
            Candidate(
                domain="calibration",
                statement=(
                    f"{len(stopped)} call(s) traded through their own stop inside the first "
                    f"21 sessions ({', '.join(tickers)}). The direction was not necessarily "
                    "wrong -- MWG finished the window up 12% -- but the entry was early "
                    "enough that the position did not survive to collect it. Treat a stop "
                    "that close to the entry as evidence the entry is wrong, not the thesis."
                ),
                evidence_ids=sorted(
                    {eid for item in stopped for eid in item.get("evidence_ids", [])}
                ),
                observations=len(stopped),
                rule="calibration.stopped_out",
            )
        )
    return found


def _cross_verdict(
    outcome: Mapping[str, Any], calls: Mapping[str, Mapping[str, Any]]
) -> str | None:
    """Return the verdict judged against peers instead of the index."""
    from src.learning.resolve import ACTION_DIRECTION

    percentile = outcome.get("base_rate_pctile")
    call = calls.get(outcome.get("call_id", ""))
    if percentile is None or call is None:
        return None
    direction = ACTION_DIRECTION.get(call.get("action", ""), 0)
    if direction == 0:
        return None
    return "hit" if ((percentile > 0.5) == (direction > 0)) else "miss"


def action_rules(
    outcomes: Sequence[Mapping[str, Any]], calls: Mapping[str, Mapping[str, Any]]
) -> list[Candidate]:
    """Rules about whether a class of recommendation has earned anything."""
    found: list[Candidate] = []
    by_action: dict[str, list[Mapping[str, Any]]] = {}
    for item in _graded(outcomes):
        call = calls.get(item.get("call_id", ""))
        if call:
            by_action.setdefault(call["action"], []).append(item)

    for action, group in sorted(by_action.items()):
        if len(group) < MIN_OBSERVATIONS:
            continue
        hits = sum(1 for item in group if item["verdict"] == "hit")
        alphas = [item["alpha"] for item in group if item.get("alpha") is not None]
        if hits * 2 > len(group):
            continue
        mean_alpha = fmean(alphas) if alphas else 0.0
        found.append(
            Candidate(
                domain="calibration",
                statement=(
                    f"'{action}' calls have gone {hits}/{len(group)} with mean alpha "
                    f"{mean_alpha:+.2%}. On this sample the class has produced no edge; "
                    "require a sharper reason than usual before writing another one, and "
                    f"note that {len(group)} observations cannot distinguish this from chance."
                ),
                evidence_ids=sorted({eid for item in group for eid in item.get("evidence_ids", [])}),
                observations=len(group),
                rule=f"action.no_edge.{action}",
            )
        )
    return found


def process_rules(
    records: Sequence[Mapping[str, Any]],
    run_reliability: "RunReliability | None" = None,
) -> list[Candidate]:
    """Rules about how the work ran, rather than how it turned out.

    Args:
        records: ProcessRecord payloads -- Claude Code sessions.
        run_reliability: Swarm-run statistics, when the caller has them. Passed
            in rather than read from disk: the first version called
            ``summarise()`` here, which meant deriving lessons for an empty test
            ledger picked up this machine's real run directories and returned a
            lesson about them. A rule that reads ambient state is not a function
            of the records it claims to be about.
    """
    from src.learning.process_score import completion_rate, recurrence

    found: list[Candidate] = []
    if len(records) >= MIN_OBSERVATIONS:
        stats = completion_rate(records)
        rate = stats["completion_rate"]
        if rate is not None and rate < 0.5:
            wasted = stats["output_wasted_share"]
            wasted_text = f" and {wasted:.0%} of everything generated" if wasted else ""
            found.append(
                Candidate(
                    domain="process",
                    statement=(
                        f"{stats['completed']} of {stats['runs']} Claude Code sessions "
                        f"ended with a conclusion ({rate:.0%}){wasted_text} went to "
                        "sessions that finished nothing. Budget a session's cost as its "
                        "expected cost divided by this rate."
                    ),
                    evidence_ids=[],
                    observations=stats["runs"],
                    rule="process.completion_rate",
                )
            )

    # The rule above counts Claude Code sessions, which is what ProcessRecord
    # describes. Swarm runs are a different population with a different failure
    # mode, and reading one as the other is what put an unattended scheduler
    # behind a gate measuring whether somebody's editor closed cleanly. Worse,
    # the sessions rule reads as a verdict on how the research is done -- so
    # when the runs are dying on an unpaid account, the playbook tells a worker
    # to improve its process while the actual repair is a billing one.
    runs = _swarm_run_rule(run_reliability)
    if runs is not None:
        found.append(runs)

    repeats = recurrence(records)
    for code, counts in repeats["per_code"].items():
        if counts["runs"] < 2:
            continue
        found.append(
            Candidate(
                domain="process",
                statement=(
                    f"'{code}' has been caught in {counts['runs']} separate runs "
                    f"({counts['caught']} times). An error caught twice is a process that "
                    "has not learned; add a check for it before the review round rather "
                    "than relying on the review round to find it again."
                ),
                evidence_ids=[],
                observations=counts["caught"],
                rule=f"process.recurrence.{code}",
            )
        )
    return found


def _swarm_run_rule(summary: "RunReliability | None") -> "Candidate | None":
    """Return a lesson about swarm runs, naming what actually stopped them.

    Returns ``None`` when no summary was supplied, when there are too few runs
    to say anything, or when the runs are finishing.
    """
    if summary is None:
        return None

    rate = summary.completion_rate
    if summary.runs < MIN_OBSERVATIONS or rate is None or rate >= 0.5:
        return None

    return Candidate(
        domain="process",
        statement=(
            f"{summary.completed} of {summary.runs} swarm runs reached a conclusion "
            f"({rate:.0%}), and {summary.blame()}. Read the cause before reading the "
            "rate: a low completion rate caused by the provider is a billing "
            "problem, and treating it as a research problem sends the work to the "
            "wrong repair."
        ),
        evidence_ids=[],
        observations=summary.runs,
        rule="process.swarm_completion_cause",
    )


#: Every rule family, in the order the playbook lists them.
RULES: tuple[Callable[..., list[Candidate]], ...] = (
    calibration_rules,
    action_rules,
    process_rules,
)


def derive(
    store: LearningStore,
    *,
    checkpoint: int = 21,
    run_reliability: "RunReliability | None" = None,
) -> list[Candidate]:
    """Run every rule over the ledger and return what fired.

    Args:
        store: The ledger.
        checkpoint: Which scoring checkpoint the outcome rules read.

    Returns:
        Candidates, in rule order. An empty list is a normal and honest result:
        it means nothing measured has crossed a threshold yet.
    """
    calls = {call.call_id: call.to_dict() for call in store.list_calls()}
    outcomes: list[Mapping[str, Any]] = []
    for call_id in calls:
        outcomes.extend(
            outcome.to_dict()
            for outcome in store.outcomes_for(call_id)
            if outcome.checkpoint_sessions == checkpoint
        )

    processes = [record.to_dict() for record in store.all_process_records()]

    found: list[Candidate] = []
    found.extend(calibration_rules(outcomes, calls))
    found.extend(action_rules(outcomes, calls))
    found.extend(process_rules(processes, run_reliability))
    return found


def curate(store: LearningStore, candidates: Iterable[Candidate]) -> list[Lesson]:
    """Store candidates as lessons, incrementing rather than rewriting.

    A candidate from a rule lands on that rule's ``lesson_id``, so re-deriving
    moves the counts on the lesson already there and keeps its history. That is
    the delta update ACE calls for, and the reason the playbook does not erode
    each time it is regenerated.

    It used to key on the *wording*, which defeated itself: a counting rule
    writes its numbers into its own statement, so every derivation hashed to a
    new id and the playbook accumulated near-duplicates of the same finding --
    growth rather than erosion, but equally a playbook nobody can read.

    A lesson left behind by a rule that has been reworded is **retired**, not
    left live. Two lines making the same claim with different numbers is worse
    than one, because the reader has to work out which is current.

    Returns:
        The lessons as stored.
    """
    live = store.live_lessons()
    existing = {lesson.lesson_id: lesson for lesson in live}
    stored: list[Lesson] = []
    for candidate in candidates:
        lesson = candidate.to_lesson()
        previous = existing.get(lesson.lesson_id)
        if previous is not None:
            lesson.created_at = previous.created_at
            lesson.contradicted_count = previous.contradicted_count
        store.append_lesson(lesson)
        stored.append(lesson)

        # Retire any other live lesson the same rule produced under an older
        # identity. Matching is on the rule, so a hand-written lesson -- which
        # carries none -- is never retired by a deriver.
        if not candidate.rule:
            continue
        for other in live:
            if other.rule == candidate.rule and other.lesson_id != lesson.lesson_id:
                superseded = Lesson.from_dict(other.to_dict())
                superseded.status = "retired"
                superseded.superseded_by = lesson.lesson_id
                store.append_lesson(superseded)
    return stored


def retire_lesson(store: LearningStore, lesson_id: str, superseded_by: str = "") -> bool:
    """Retire one lesson by id, for cleaning up what predates a rule.

    Lessons written before :attr:`Lesson.rule` existed cannot be matched to the
    rule that would now replace them, so the few of them are retired by hand.
    Kept as a named function rather than a script because it edits an
    append-only ledger and should be readable next to what reads it.

    Returns:
        Whether a live lesson was found and retired.
    """
    for lesson in store.live_lessons():
        if lesson.lesson_id != lesson_id:
            continue
        superseded = Lesson.from_dict(lesson.to_dict())
        superseded.status = "retired"
        superseded.superseded_by = superseded_by
        store.append_lesson(superseded)
        return True
    return False


def render_playbook(lessons: Sequence[Lesson], domain: str) -> str:
    """Render one domain's lessons as markdown with YAML frontmatter.

    The frontmatter is not decoration. 295 notes in the vault carry none, which
    is why none of them can be queried by Dataview; a playbook that cannot be
    queried is a file nobody opens twice.
    """
    lines = [
        "---",
        f"domain: {domain}",
        "type: playbook",
        f"lesson_count: {len(lessons)}",
        f"confirmed: {sum(1 for item in lessons if item.status == 'confirmed')}",
        "source: learning ledger, derived by rule",
        "---",
        "",
        f"# Playbook — {domain}",
        "",
    ]
    if not lessons:
        lines.append(
            "_No lesson has crossed its evidence threshold yet. This file is empty on "
            "purpose: a playbook line with nothing behind it steers later work using "
            "the confidence of a sentence rather than the weight of a measurement._"
        )
        return "\n".join(lines) + "\n"

    for lesson in lessons:
        lines.append(f"## {lesson.statement}")
        lines.append("")
        lines.append(f"- status: **{lesson.status}**")
        lines.append(f"- support: {lesson.support_count} · contradicted: {lesson.contradicted_count}")
        lines.append(f"- evidence: {len(lesson.evidence_ids)} record(s)")
        if lesson.expires_at:
            lines.append(f"- expires: {lesson.expires_at}")
        lines.append(f"- id: `{lesson.lesson_id}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def write_playbook(store: LearningStore, root: Any) -> dict[str, str]:
    """Write one markdown file per domain under *root*.

    Returns:
        Domain to the path written. Every domain gets a file, including the
        empty ones, because an absent file reads as "not done yet" and an empty
        one states that there is nothing evidenced to say.
    """
    from pathlib import Path

    directory = Path(root)
    directory.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for domain in DOMAINS:
        lessons = [item for item in store.live_lessons(domain=domain)]
        path = directory / f"{domain}.md"
        path.write_text(render_playbook(lessons, domain), encoding="utf-8")
        written[domain] = str(path)
    return written
