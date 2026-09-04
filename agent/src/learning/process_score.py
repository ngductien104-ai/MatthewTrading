"""Score how a piece of research was *made*, not whether it turned out right.

Market outcomes arrive one per horizon. Nothing on the ledger has reached 63
sessions yet, and the 21-session hit rate carries a confidence interval that
covers most of the unit interval. Process quality arrives one observation per
document, which is why the plan calls this the fastest learning available here.

The design constraint that shapes everything below
--------------------------------------------------
A model that writes the research and also grades it is marking its own work,
and will return a high number with no information in it. So the split is
strict, and it is the same split ``extract`` already uses:

* the model may **only quote**. It is asked, per rubric item, for a verbatim
  span of the document that satisfies it.
* the **code decides**. Every quote is located with :meth:`str.find` -- an
  offset a model reports is an assertion, one found by searching is a fact --
  and for the items where the claim has a checkable shape, the quote must also
  contain that shape. A quote offered for ``data_cutoff`` that contains no date
  earns nothing, however confidently it was offered.

No item is worth a point for being *asserted*. The score is the count of items
whose evidence survived being checked.

Why these six items
-------------------
They are the ones that are observable in the text and that this desk has
actually been burned by. ``source_timestamp`` and ``data_cutoff`` are the vault
rule about not quoting a number without saying when it was true.
``valuation_bridge`` is the FCFF that never met real cash flow.
``falsification`` is the invalidation trigger, which the resolver can only
check when one exists. ``position_size`` is the constraint the portfolio review
found missing from the buy decisions that lost money. ``catalyst`` is the
question "why now", which separates a view from a trade.

Scoring is deliberately unweighted. A weighting is a claim about relative
importance that nothing here has measured, and six equal points that mean what
they say beat a weighted composite that means nothing precise.

Reading the number
------------------
A rubric is a measuring instrument and has to be measured itself. Score two
independent passes over the same documents and run :func:`disagreement` before
believing any of it: if two passes disagree on a third of the items, the number
is noise, and the rubric needs sharper items rather than more documents.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from src.learning.extract import ExtractionError, SourceDocument, _locate
from src.learning.records import Evidence

#: A date in any form this desk writes them: 2026-08-27, 27/08/2026, 27/08,
#: "Q2 2026", "quy 2/2026", or a bare year in a filing context.
_DATE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|"
    r"(?:Q|q|quy|quý)\s*[1-4][/\s-]*\d{2,4}|20\d{2})\b"
)

#: A number, with or without thousands separators or a decimal comma.
_NUMBER = re.compile(r"\d[\d.,]*")

#: A percentage or an explicit weight.
_PERCENT = re.compile(r"\d[\d.,]*\s*%")


def _has_date(quote: str) -> bool:
    return bool(_DATE.search(quote))


def _has_number(quote: str) -> bool:
    return bool(_NUMBER.search(quote))


def _has_percent(quote: str) -> bool:
    return bool(_PERCENT.search(quote))


def _always(quote: str) -> bool:
    """Accept any located quote. Used where the claim has no checkable shape."""
    return bool(quote.strip())


@dataclass(frozen=True)
class RubricItem:
    """One observable property of a research document.

    Attributes:
        code: Stable key.
        question: What the model is asked to find, in the words it will see.
        check: Code-side predicate the located quote must also satisfy. This is
            what stops an item being earned by assertion.
        requirement: What the check enforces, quoted back in a rejection so the
            failure is legible.
    """

    code: str
    question: str
    check: Callable[[str], bool]
    requirement: str


#: The rubric. Order is the order the prompt asks in and the report prints in.
RUBRIC: tuple[RubricItem, ...] = (
    RubricItem(
        "source_timestamp",
        "a line naming when the underlying data was published or retrieved",
        _has_date,
        "must contain a date",
    ),
    RubricItem(
        "data_cutoff",
        "a line stating the period the figures cover, or where the data stops",
        _has_date,
        "must contain a date or period",
    ),
    RubricItem(
        "valuation_bridge",
        "a line connecting a stated assumption to the number it produces",
        _has_number,
        "must contain a number, since a bridge with no number crosses nothing",
    ),
    RubricItem(
        "catalyst",
        "a line saying what would make this happen, and roughly when",
        _always,
        "must be a located span",
    ),
    RubricItem(
        "falsification",
        "a line stating what would prove the view wrong",
        _always,
        "must be a located span",
    ),
    RubricItem(
        "position_size",
        "a line constraining how much to hold, as a weight, a cap or a band",
        _has_percent,
        "must contain a percentage, which is what makes a size a constraint",
    ),
)

RUBRIC_BY_CODE = {item.code: item for item in RUBRIC}

#: The maximum a document can score.
MAX_SCORE = len(RUBRIC)

PROMPT_TEMPLATE = """You are extracting evidence, not grading. You cannot award points.

For each item below, find ONE verbatim span of the document that satisfies it.
Copy it character-for-character. If the document does not satisfy an item,
return null for that item -- a missing item costs nothing to report and an
invented one is discarded anyway, because every span is searched for in the
document and dropped when it is not found.

Items:
{items}

Reply with JSON only:
{{"source_timestamp": "<quote or null>", "data_cutoff": "<quote or null>",
  "valuation_bridge": "<quote or null>", "catalyst": "<quote or null>",
  "falsification": "<quote or null>", "position_size": "<quote or null>"}}

Rules checked in code, so breaking one only loses the item:
{requirements}

DOCUMENT ({path}, observed {observed_at}):
---
{text}
---
"""


def build_prompt(document: SourceDocument) -> str:
    """Return the extraction prompt for one document."""
    items = "\n".join(f"  {item.code}: {item.question}" for item in RUBRIC)
    requirements = "\n".join(
        f"  - {item.code} {item.requirement}; the span must appear in the document"
        for item in RUBRIC
    )
    return PROMPT_TEMPLATE.format(
        items=items,
        requirements=requirements,
        path=document.path,
        observed_at=document.observed_at,
        text=document.text,
    )


@dataclass
class ItemResult:
    """One rubric item, after the code has checked it.

    Attributes:
        code: Rubric item key.
        earned: Whether the point was awarded.
        quote: The located span, empty when nothing was earned.
        evidence: Citable evidence for the span, when located.
        rejected: Why the point was refused, empty when earned.
    """

    code: str
    earned: bool
    quote: str = ""
    evidence: Evidence | None = None
    rejected: str = ""


@dataclass
class ProcessScore:
    """A scored document.

    Attributes:
        doc_id: Which document.
        path: Where it came from.
        items: One result per rubric item, in rubric order.
        parse_error: Set when the reply was not usable at all.
    """

    doc_id: str
    path: str
    items: list[ItemResult] = field(default_factory=list)
    parse_error: str = ""

    @property
    def score(self) -> int:
        """Return the number of items whose evidence survived checking."""
        return sum(1 for item in self.items if item.earned)

    @property
    def earned_codes(self) -> list[str]:
        """Return the codes that were earned, in rubric order."""
        return [item.code for item in self.items if item.earned]

    @property
    def missing_codes(self) -> list[str]:
        """Return the codes that were not."""
        return [item.code for item in self.items if not item.earned]

    def evidence(self) -> list[Evidence]:
        """Return the evidence behind every earned item."""
        return [item.evidence for item in self.items if item.earned and item.evidence]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the score without the evidence objects."""
        return {
            "doc_id": self.doc_id,
            "path": self.path,
            "score": self.score,
            "max_score": MAX_SCORE,
            "earned": self.earned_codes,
            "missing": self.missing_codes,
            "parse_error": self.parse_error,
        }


def parse_reply(raw: str) -> dict[str, Any]:
    """Return the model's item-to-quote mapping.

    Raises:
        ExtractionError: The reply is not a JSON object.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"reply is not JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ExtractionError(f"reply must be a JSON object, got {type(parsed).__name__}")
    return parsed


def score_document(document: SourceDocument, propose: Callable[[str], str]) -> ProcessScore:
    """Score one document against the rubric.

    Args:
        document: The document to score.
        propose: Called with the prompt, returns the model's JSON reply.

    Returns:
        The score. A reply that cannot be parsed yields a zero score carrying
        ``parse_error`` rather than raising, so one bad document does not stop
        a batch -- the same choice the call backfill made.
    """
    result = ProcessScore(doc_id=document.doc_id, path=document.path)
    try:
        proposed = parse_reply(propose(build_prompt(document)))
    except Exception as exc:  # noqa: BLE001 - one document must not stop the batch
        result.parse_error = f"{type(exc).__name__}: {exc}"
        result.items = [ItemResult(item.code, False, rejected="no usable reply") for item in RUBRIC]
        return result

    for item in RUBRIC:
        quote = proposed.get(item.code)
        if not isinstance(quote, str) or not quote.strip():
            result.items.append(ItemResult(item.code, False, rejected="not claimed"))
            continue
        try:
            first, last, excerpt = _locate(quote, document)
        except ExtractionError:
            result.items.append(
                ItemResult(item.code, False, rejected="quote is not in the document")
            )
            continue
        if not item.check(quote):
            result.items.append(
                ItemResult(item.code, False, quote=quote, rejected=item.requirement)
            )
            continue
        result.items.append(
            ItemResult(
                item.code,
                True,
                quote=quote,
                evidence=Evidence(
                    kind=document.kind,
                    observed_at=document.observed_at,
                    source_session_id=document.session_id,
                    source_uuid=document.source_uuid,
                    source_path=document.path,
                    locator=f"L{first}-L{last}",
                    excerpt=excerpt,
                ),
            )
        )
    return result


ERROR_PROMPT_TEMPLATE = """You are classifying mistakes that were CAUGHT and corrected
during this work, not judging the work. You cannot invent a category.

For each mistake the text shows being caught, return its code and ONE verbatim
span showing it being caught. Return an empty list if none is shown. A missing
catch costs nothing; an invented one is discarded, because every span is
searched for in the document and every code is checked against the list below.

Codes, and what each one means here:
{codes}

Reply with JSON only:
{{"errors": [{{"code": "<one of the codes>", "quote": "<verbatim span>",
              "round": <integer, 0 if unknown>, "description": "<short>"}}]}}

DOCUMENT ({path}, observed {observed_at}):
---
{text}
---
"""

#: What each taxonomy code meant the one time it actually bit, so the model is
#: matching against a remembered incident rather than a bare word.
ERROR_MEANING = {
    "double_count": "the same profit or cash added twice (the FOX earnings)",
    "causal_misread": "a number read as caused by the wrong thing (the ROIC drop)",
    "cashflow_unreconciled": "a projected cash flow that never met real cash flow (year-one FCFF)",
    "unit_error": "a scale or unit mistake -- thousands, billions, fraction vs percent",
    "lookahead": "information used that was not available at the time",
    "source_mismatch": "two sources disagreeing, or the wrong source quoted",
    "unverified_assumption": "an assumption carried into a number without a check",
    "stale_crosscheck": "a correct figure already existed elsewhere and nobody looked (VRE)",
}


def build_error_prompt(document: SourceDocument) -> str:
    """Return the error-classification prompt for one document."""
    from src.learning.records import ERROR_TAXONOMY

    codes = "\n".join(f"  {code}: {ERROR_MEANING.get(code, '')}" for code in ERROR_TAXONOMY)
    return ERROR_PROMPT_TEMPLATE.format(
        codes=codes,
        path=document.path,
        observed_at=document.observed_at,
        text=document.text,
    )


def classify_errors(
    document: SourceDocument, propose: Callable[[str], str]
) -> tuple[list[dict[str, Any]], list[Evidence], list[str]]:
    """Extract the caught mistakes a document shows, as auditable entries.

    Same split as the rubric: the model proposes a code and a span, and the
    code decides. A span that is not in the document is dropped, and a code
    outside :data:`~src.learning.records.ERROR_TAXONOMY` is dropped -- the
    vocabulary is closed precisely so recurrence can be counted, and a model
    inventing a category would make the count meaningless.

    Returns:
        Entries shaped for ``ProcessRecord.errors_caught``, the evidence each
        one cites, and the reasons anything was refused.
    """
    from src.learning.records import ERROR_TAXONOMY

    entries: list[dict[str, Any]] = []
    evidence: list[Evidence] = []
    refused: list[str] = []
    try:
        payload = parse_reply(propose(build_error_prompt(document)))
    except Exception as exc:  # noqa: BLE001 - one document must not stop the batch
        return [], [], [f"{type(exc).__name__}: {exc}"]

    proposed = payload.get("errors")
    if not isinstance(proposed, list):
        return [], [], ["reply has no 'errors' list"]

    for position, raw in enumerate(proposed):
        if not isinstance(raw, dict):
            refused.append(f"errors[{position}] is not an object")
            continue
        code = str(raw.get("code", "")).strip()
        quote = raw.get("quote")
        if code not in ERROR_TAXONOMY:
            refused.append(f"errors[{position}] has code {code!r}, which is not in the taxonomy")
            continue
        if not isinstance(quote, str) or not quote.strip():
            refused.append(f"errors[{position}] ({code}) has no quote")
            continue
        try:
            first, last, excerpt = _locate(quote, document)
        except ExtractionError:
            refused.append(f"errors[{position}] ({code}) quotes text not in the document")
            continue
        cited = Evidence(
            kind=document.kind,
            observed_at=document.observed_at,
            source_session_id=document.session_id,
            source_uuid=document.source_uuid,
            source_path=document.path,
            locator=f"L{first}-L{last}",
            excerpt=excerpt,
        )
        evidence.append(cited)
        entries.append(
            {
                "code": code,
                "description": str(raw.get("description", "")),
                "round": int(raw.get("round", 0) or 0),
                "evidence_id": cited.evidence_id,
            }
        )
    return entries, evidence, refused


def disagreement(left: Sequence[ProcessScore], right: Sequence[ProcessScore]) -> dict[str, Any]:
    """Measure how much two independent passes disagree.

    A rubric is a measuring instrument, and an instrument nobody has measured
    is not evidence. Run this over five to ten documents scored twice before
    believing any score it produces.

    Args:
        left: One pass.
        right: An independent pass over the same documents.

    Returns:
        Per-item and overall agreement rates, plus the documents whose totals
        differ. ``items_compared`` of zero means the two passes shared no
        document, which is reported rather than returned as perfect agreement.
    """
    by_doc_left = {score.doc_id: score for score in left}
    by_doc_right = {score.doc_id: score for score in right}
    shared = [doc_id for doc_id in by_doc_left if doc_id in by_doc_right]

    per_item: dict[str, dict[str, int]] = {
        item.code: {"agree": 0, "compared": 0} for item in RUBRIC
    }
    score_gaps: list[dict[str, Any]] = []
    for doc_id in shared:
        one, two = by_doc_left[doc_id], by_doc_right[doc_id]
        earned_one = set(one.earned_codes)
        earned_two = set(two.earned_codes)
        for item in RUBRIC:
            per_item[item.code]["compared"] += 1
            if (item.code in earned_one) == (item.code in earned_two):
                per_item[item.code]["agree"] += 1
        if one.score != two.score:
            score_gaps.append(
                {"doc_id": doc_id, "left": one.score, "right": two.score, "path": one.path}
            )

    compared = sum(counts["compared"] for counts in per_item.values())
    agreed = sum(counts["agree"] for counts in per_item.values())
    return {
        "documents_compared": len(shared),
        "items_compared": compared,
        "agreement": agreed / compared if compared else None,
        "per_item": {
            code: {
                **counts,
                "agreement": counts["agree"] / counts["compared"] if counts["compared"] else None,
            }
            for code, counts in per_item.items()
        },
        "score_disagreements": score_gaps,
    }


def recurrence(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Count how often each error class comes back.

    An error caught twice is a process that has not learned. An error caught
    once is a process that worked.

    Args:
        records: ``ProcessRecord``-shaped mappings, each with ``errors_caught``.

    Returns:
        Per-code totals and the number of distinct runs each code appeared in,
        plus ``repeat_rate``: the share of codes seen in more than one run.
    """
    per_code: dict[str, dict[str, Any]] = {}
    for record in records:
        run_key = str(record.get("process_id") or record.get("source_session_id") or "")
        for caught in record.get("errors_caught") or []:
            code = str(caught.get("code", ""))
            if not code:
                continue
            entry = per_code.setdefault(code, {"caught": 0, "runs": set()})
            entry["caught"] += 1
            entry["runs"].add(run_key)

    summary = {
        code: {"caught": entry["caught"], "runs": len(entry["runs"])}
        for code, entry in per_code.items()
    }
    repeated = sum(1 for entry in summary.values() if entry["runs"] > 1)
    return {
        "per_code": dict(sorted(summary.items(), key=lambda kv: -kv[1]["caught"])),
        "distinct_codes": len(summary),
        "repeated_codes": repeated,
        "repeat_rate": repeated / len(summary) if summary else None,
    }


#: The counter that tracks generation rather than context size, and the only
#: one of the four that can be compared across runs of different lengths.
WORK_COUNTER = "output_tokens"

#: The trace event the agent loop already writes when it notices a goal is not
#: advancing. See :func:`stalls`.
STALL_EVENT = "goal_continuation_suppressed"


def stalls(run_dirs: Iterable[Any]) -> dict[str, Any]:
    """Count the stalls the agent loop already detects and then discards.

    ``agent/src/agent/loop.py`` compares goal progress against the previous
    iteration and, when nothing moved, writes ``goal_continuation_suppressed``
    and stops continuing. That is a correct thing to do and the right moment to
    notice -- "what makes this loop get stuck" is a lesson nobody is currently
    collecting, because the event is written to a trace file and never read
    back.

    Args:
        run_dirs: Directories that may hold a ``trace.jsonl``.

    Returns:
        The stalls found, per run and in total, plus ``traces_read``. On this
        machine the count is currently zero across every run on disk, which is
        not evidence that the loop never stalls: that surface carries almost no
        traffic, since nearly all real work goes through Claude Code sessions
        rather than the agent loop. The zero is reported with ``traces_read``
        beside it so the two cannot be confused.
    """
    from pathlib import Path

    found: list[dict[str, Any]] = []
    traces_read = 0
    for run_dir in run_dirs:
        trace = Path(run_dir) / "trace.jsonl"
        if not trace.exists():
            continue
        traces_read += 1
        for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
            if STALL_EVENT not in line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == STALL_EVENT:
                found.append(
                    {
                        "run_dir": str(run_dir),
                        "iteration": event.get("iter"),
                        "goal_id": event.get("goal_id"),
                        "continuations": event.get("continuations"),
                        "progress": event.get("progress"),
                    }
                )
    return {
        "traces_read": traces_read,
        "stalls": len(found),
        "runs_that_stalled": len({item["run_dir"] for item in found}),
        "detail": found,
    }


def completion_rate(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return how many runs finished, and what the unfinished ones consumed.

    The unfinished runs are the point. Work spent on a run that never produced
    a conclusion is the cost of unreliability, and until it is counted next to
    the completion rate it reads as a scheduling annoyance rather than a budget
    line.

    Two measures are reported and they are not interchangeable. ``output_*`` is
    generated tokens, which is what the run actually produced. ``raw_*`` is the
    sum of every counter, which ``cache_read_input_tokens`` dominates by thirty
    to a hundred times -- so the raw figure measures how much context was
    re-read, not how much was spent, and is reported only because it is what
    older records carry. Ratios computed from either are comparable; the
    absolute raw number is not money and must not be quoted as though it were.
    """
    total = len(records)
    done = [record for record in records if record.get("completed")]

    def raw(record: Mapping[str, Any]) -> int:
        return int(record.get("tokens") or 0)

    def work(record: Mapping[str, Any]) -> int:
        return int((record.get("token_usage") or {}).get(WORK_COUNTER, 0) or 0)

    raw_spent = sum(raw(record) for record in records)
    raw_wasted = sum(raw(record) for record in records if not record.get("completed"))
    work_spent = sum(work(record) for record in records)
    work_wasted = sum(work(record) for record in records if not record.get("completed"))
    return {
        "runs": total,
        "completed": len(done),
        "completion_rate": len(done) / total if total else None,
        "output_tokens_total": work_spent,
        "output_tokens_on_unfinished_runs": work_wasted,
        "output_wasted_share": work_wasted / work_spent if work_spent else None,
        "output_tokens_per_completed_run": work_spent / len(done) if done else None,
        "raw_counter_total": raw_spent,
        "raw_counter_on_unfinished_runs": raw_wasted,
        "raw_wasted_share": raw_wasted / raw_spent if raw_spent else None,
        "raw_counter_note": (
            "sum of every token counter, dominated by cache reads; a size, not a spend"
        ),
    }


def cost_per_conclusion(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return what a conclusion has cost, overall and month by month.

    :func:`completion_rate` says how much was wasted. This says how much a
    finished piece of work costs, which is the number a decision is made
    against: whether to launch another run of this shape, and -- the reason the
    plan puts this before any scheduler -- whether an unattended loop would be
    buying anything at that price.

    Two rules, both learned from the records this reads.

    **A period with no conclusion has no cost per conclusion.** It is reported
    as ``None``, never as zero and never as a very large number. Zero would say
    the period was free; a large number would imply an upper bound the data
    cannot supply. The honest statement is that the denominator is empty.

    **Every figure carries its coverage.** ``token_usage`` was added to
    ``ProcessRecord`` only recently, so older records carry no generated-token
    counter at all. Summing them produces a month that appears to have cost
    nothing -- which on this ledger is exactly what July 2026 looks like, two
    runs and zero tokens, because neither record has the counter. Each row
    therefore reports ``records_with_counter`` beside its total, and a row whose
    coverage is zero means "not measured", not "free".

    The dimension is time, not preset. Every process record on this ledger has
    an empty ``preset`` -- they come from Claude Code sessions rather than swarm
    runs -- and a breakdown by a field that is empty everywhere is a table of
    one row wearing a disguise.

    Args:
        records: ProcessRecord payloads, newest or oldest first, either way.

    Returns:
        ``{"overall": {...}, "by_month": [...]}``. Each entry carries ``runs``,
        ``completed``, ``output_tokens``, ``records_with_counter``,
        ``wall_hours`` and ``output_tokens_per_conclusion``.
    """

    def work(record: Mapping[str, Any]) -> int:
        return int((record.get("token_usage") or {}).get(WORK_COUNTER, 0) or 0)

    def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        done = sum(1 for row in rows if row.get("completed"))
        tokens = sum(work(row) for row in rows)
        measured = sum(1 for row in rows if work(row) > 0)
        wall = sum(float(row.get("wall_time_sec") or 0.0) for row in rows)
        return {
            "runs": len(rows),
            "completed": done,
            "output_tokens": tokens,
            "records_with_counter": measured,
            "wall_hours": round(wall / 3600.0, 1),
            # None, not zero and not infinity: with nothing finished there is
            # no cost per conclusion to report.
            "output_tokens_per_conclusion": (tokens / done) if done and tokens else None,
        }

    months: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        stamp = str(record.get("known_at") or "")
        months.setdefault(stamp[:7] or "unknown", []).append(record)

    return {
        "overall": summarise(list(records)),
        "by_month": [
            {"month": month, **summarise(months[month])} for month in sorted(months)
        ],
    }


def render_cost_surface(surface: Mapping[str, Any]) -> str:
    """Render :func:`cost_per_conclusion` as a table meant to be read.

    A row with no conclusions prints ``-`` in the cost column, and a row with
    no counter coverage says so, because both are absences and neither is a
    number.
    """
    overall = surface["overall"]
    lines = [
        "cost per conclusion (generated tokens; cache reads excluded)",
        f"{'month':<9}{'runs':>5}{'done':>5}{'out tokens':>13}"
        f"{'per conclusion':>16}{'wall h':>8}  coverage",
    ]
    for row in list(surface["by_month"]) + [{**overall, "month": "ALL"}]:
        per = row["output_tokens_per_conclusion"]
        per_text = f"{per:,.0f}" if per else "-"
        coverage = (
            f"{row['records_with_counter']}/{row['runs']}"
            if row["records_with_counter"]
            else f"0/{row['runs']} not measured"
        )
        lines.append(
            f"{row['month']:<9}{row['runs']:>5}{row['completed']:>5}"
            f"{row['output_tokens']:>13,}{per_text:>16}{row['wall_hours']:>8.1f}  {coverage}"
        )
    if not overall["completed"]:
        lines.append("no run has reached a conclusion; there is no cost per conclusion yet")
    return "\n".join(lines)
