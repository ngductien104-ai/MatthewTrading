"""Turn research prose into ledger records, with the model kept on a short leash.

The plan's phrase for this module is *"the LLM extracts, pure code decides"*.
That split is the whole point, so it is worth being precise about where the line
falls:

* the model is allowed to say **where** a call is -- ticker, date, action, and a
  **verbatim quote** for every number it claims;
* the model is not allowed to say **what the number is**. Every price is
  re-parsed from the quote by :func:`parse_prices`, and a claim whose value
  cannot be found in its own quote is rejected, not repaired.

Three traps come from the corpus rather than from theory. They were measured
across 229 research markdown files (4.3 MB) before a line of this was written:

1. **Thousands are written four different ways and one of them has no unit.**
   ``72.200 đ``, ``58,8k``, ``25.000`` and a bare ``64`` all mean thousands of
   dong; 12,130 grouped-thousand tokens and 441 ``k`` tokens sit in the same
   documents as bare ones (``chốt/giảm tỷ trọng vùng 64–65``, ``stop dưới 60``).
   Reading ``64`` as sixty-four dong, or silently multiplying it by a thousand,
   both corrupt the ledger. :func:`resolve_scale` multiplies **only when the
   arithmetic proves it** against an anchored reference price, and refuses when
   both readings are plausible.
2. **Fair value is quoted as a band far more often than as a point** -- 5,510
   range tokens. ``22.000–27.500, trung điểm 25.000`` states its own midpoint;
   ``gom 50,5–51,8`` does not. A band is accepted as support for its midpoint,
   and the band is kept verbatim in ``notes`` so the choice stays auditable.
3. **A heading can carry two actions at once** (``BÁN / TRÁNH MUA ĐUỔI``,
   ``GIẢM TỶ TRỌNG / KHÔNG MUA``). The extractor must pick one and quote it;
   :func:`~src.learning.records.normalize_action` rejects anything outside the
   closed vocabulary rather than guessing which half was meant.

Two source families exist beyond the transcripts, and neither carries a Claude
Code session id. The episode key therefore comes from the container -- one
``_xxx_research/`` folder, or one swarm run, is one episode -- while
``source_session_id`` stays empty rather than being filled with a lie.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Sequence

from src.learning.records import (
    CallRecord,
    Evidence,
    RecordValidationError,
    episode_id_for,
    normalize_action,
    parse_date,
    sha256_text,
)
from src.learning.store import AppendResult, LearningStore

#: A target more than five times, or less than a fifth of, the reference price
#: is not a forecast -- it is a unit bug. The widest real call in the corpus is
#: FPT's bear at -63.8%, comfortably inside.
PLAUSIBLE_RATIO = (0.2, 5.0)

#: Reasons a candidate is refused. Closed, so recurrence can be counted the way
#: :data:`~src.learning.records.ERROR_TAXONOMY` counts debate findings.
REJECTION_CODES = (
    "bad_json",
    "missing_field",
    "unknown_action",
    "no_evidence",
    "quote_not_found",
    "number_not_in_evidence",
    "scale_ambiguous",
    "implausible_target",
    "future_dated",
    "invalid_record",
)

#: Fields the model may propose. Anything else in its JSON is dropped rather
#: than forwarded, so an invented field cannot reach the ledger.
CANDIDATE_FIELDS = (
    "ticker",
    "as_of",
    "action",
    "thesis_episode",
    "ref_price",
    "target",
    "bull",
    "bear",
    "stop",
    "horizon_sessions",
    "confidence",
    "thesis_bullets",
    "invalidation_triggers",
    "quotes",
    "notes",
)

_PRICE_FIELDS = ("ref_price", "target", "bull", "bear", "stop")

_NUMBER_RE = re.compile(
    r"(?<![\w.,])"
    r"(?P<num>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
    r"\s*(?P<unit>k\b|nghìn\b|đồng\b|đ/cp|đ|vnd\b|vnđ\b|%|tỷ\b|triệu\b)?",
    re.IGNORECASE,
)

_RANGE_RE = re.compile(
    r"(?P<low>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
    r"\s*[-–—]\s*"
    r"(?P<high>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
)


class ExtractionError(RecordValidationError):
    """A candidate failed a gate and must not become a record."""


@dataclass(frozen=True)
class ParsedNumber:
    """One number found in text, with its unit read rather than assumed.

    Attributes:
        raw: The matched text, kept for error messages.
        value: Value in dong for prices, as written for the other kinds.
        anchored: Whether the writing pins the scale -- a grouped thousand
            (``25.000``) or an explicit unit (``k``, ``đ``). A bare ``64`` is
            not anchored, and that is the whole difficulty.
        kind: ``price``, ``percent``, ``billion``, ``million`` or ``date``.
            Only ``price`` is allowed to vouch for a claimed price.
    """

    raw: str
    value: float
    anchored: bool
    kind: str = "price"


@dataclass(frozen=True)
class SourceDocument:
    """A document a call can be read out of, with its provenance attached.

    Attributes:
        doc_id: Stable id, derived from the path.
        kind: Evidence kind to stamp on quotes taken from this document.
        path: Where it was read from.
        text: Full text; the only thing quotes are checked against.
        sha256: Hash of ``text``, the idempotency handle for re-extraction.
        observed_at: When the content became observable. For a file this is its
            mtime, which is late rather than early -- an error in the one
            direction that cannot manufacture foresight.
        episode_key: The container that defines one episode: a research folder
            or a swarm run id.
        session_id: Claude Code session, empty when the source is not a
            transcript. Left empty rather than filled with the episode key.
        source_uuid: Transcript event uuid, when there is one.
    """

    doc_id: str
    kind: str
    path: str
    text: str
    sha256: str
    observed_at: str
    episode_key: str
    session_id: str = ""
    source_uuid: str = ""


@dataclass(frozen=True)
class Rejection:
    """A candidate that was refused, kept so refusals can be counted."""

    code: str
    message: str
    doc_id: str
    ticker: str = ""
    candidate: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Everything an extraction produced: records, their quotes, and refusals."""

    calls: list[CallRecord] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)

    def extend(self, other: "ExtractionResult") -> None:
        """Absorb another result in place."""
        self.calls.extend(other.calls)
        self.evidence.extend(other.evidence)
        self.rejections.extend(other.rejections)


# -- reading numbers ----------------------------------------------------------


def _to_float(token: str) -> float:
    """Read a Vietnamese-formatted number: ``.`` groups, ``,`` decimates."""
    return float(token.replace(".", "").replace(",", "."))


def _in_date(text: str, token: str, start: int, end: int) -> bool:
    """Return whether a number sits inside a ``27/08/2026``-style date.

    Dates are dense in these documents and a stray ``2026`` in the support pool
    would let a fabricated index level pass the citation check. The slash alone
    is not enough to decide, because prices are divided inline too
    (``19.170/2``), so a date part also has to be a plain integer of at most
    four digits -- which a grouped thousand never is.
    """
    if not re.fullmatch(r"\d{1,4}", token):
        return False
    before = text[start - 1] if start else ""
    after = text[end] if end < len(text) else ""
    return before == "/" or after == "/"


def parse_prices(text: str) -> list[ParsedNumber]:
    """Return every number in ``text`` with its scale read from the writing.

    Args:
        text: Any prose, normally a quoted excerpt.

    Returns:
        Numbers in order of appearance. Percentages, billions, millions and
        date parts are included but tagged, so a target price is never matched
        against ``6.932 tỷ`` or against the day the report was written.
    """
    found: list[ParsedNumber] = []
    for match in _NUMBER_RE.finditer(text):
        token = match.group("num")
        unit = (match.group("unit") or "").strip().lower()
        if _in_date(text, token, match.start("num"), match.end("num")):
            found.append(ParsedNumber(match.group(0), _to_float(token), True, "date"))
            continue
        grouped = bool(re.search(r"\.\d{3}", token))
        value = _to_float(token)
        if unit == "%":
            found.append(ParsedNumber(match.group(0), value, True, "percent"))
        elif unit.startswith("tỷ"):
            found.append(ParsedNumber(match.group(0), value, True, "billion"))
        elif unit.startswith("triệu"):
            found.append(ParsedNumber(match.group(0), value, True, "million"))
        elif unit in ("k", "nghìn"):
            found.append(ParsedNumber(match.group(0), value * 1000.0, True))
        else:
            found.append(ParsedNumber(match.group(0), value, grouped))
    return found


def _band_midpoints(text: str) -> list[float]:
    """Return midpoints of quoted ``A-B`` bands, at both possible scales."""
    midpoints: list[float] = []
    for match in _RANGE_RE.finditer(text):
        low, high = _to_float(match.group("low")), _to_float(match.group("high"))
        if high < low:
            continue
        mid = (low + high) / 2.0
        midpoints.extend((mid, mid * 1000.0))
    return midpoints


def _matches_any(value: float, candidates: Iterable[float]) -> bool:
    return any(math.isclose(value, other, rel_tol=1e-6, abs_tol=1e-9) for other in candidates)


def _supported(value: float, quoted: str) -> bool:
    """Return whether ``value`` is actually present in the quoted text.

    The check is deliberately scale-blind -- ``58,8`` and ``58.800`` both vouch
    for a claim of either, because the model was told to report what is written
    and :func:`resolve_scale` is what decides which reading is meant. A quoted
    band vouches for its own midpoint.
    """
    candidates: list[float] = []
    for number in parse_prices(quoted):
        if number.kind != "price":
            continue
        candidates.extend((number.value, number.value * 1000.0, number.value / 1000.0))
    candidates.extend(_band_midpoints(quoted))
    return _matches_any(value, candidates)


def _confidence_supported(value: float, quoted: str) -> bool:
    """Return whether a stated confidence appears in the quotes.

    Confidence is written as a percentage (``Confidence: 61%``) far more often
    than as a fraction, so the percent tokens :func:`_supported` filters out are
    exactly the ones that matter here.
    """
    candidates: list[float] = []
    for number in parse_prices(quoted):
        candidates.extend((number.value, number.value / 100.0))
    return _matches_any(value, candidates)


def resolve_scale(value: float, anchor: float | None, field_name: str) -> tuple[float, str]:
    """Return ``value`` in dong, multiplying by a thousand only when provable.

    Args:
        value: The number as written.
        anchor: An anchored reference price for the same call, when one exists.
        field_name: Field being resolved, used in the error message.

    Returns:
        The resolved value, and a note describing any correction applied.

    Raises:
        ExtractionError: There is no anchor to measure against, or both
            readings are plausible against it, or neither is. Guessing here
            silently rewrites a call, which is the failure this module exists
            to prevent.
    """
    if value >= 1000.0:
        return value, ""
    if anchor is None:
        raise ExtractionError(
            f"{field_name}={value:g} is written without a unit and there is no ref_price "
            "to settle its scale against. State ref_price, or quote the price with its unit."
        )
    low, high = PLAUSIBLE_RATIO
    as_written = low <= value / anchor <= high
    as_thousands = low <= (value * 1000.0) / anchor <= high
    if as_written and not as_thousands:
        return value, ""
    if as_thousands and not as_written:
        note = (
            f"{field_name} {value:g} read as {value * 1000.0:.0f} "
            f"against ref_price {anchor:.0f}"
        )
        return value * 1000.0, note
    both = "are" if as_written else "are not"
    raise ExtractionError(
        f"{field_name}={value:g} is ambiguous against ref_price {anchor:.0f}: "
        f"both {value:g} and {value * 1000.0:.0f} {both} plausible. "
        "Quote the price with its unit instead of leaving the scale to inference."
    )


# -- source documents ---------------------------------------------------------


def _mtime_utc(path: Path) -> str:
    stamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0)
    return stamp.isoformat().replace("+00:00", "Z")


def _document(path: Path, kind: str, episode_key: str, text: str | None = None) -> SourceDocument:
    body = path.read_text(encoding="utf-8", errors="replace") if text is None else text
    return SourceDocument(
        doc_id="doc_" + sha256_text(str(path))[:12],
        kind=kind,
        path=str(path),
        text=body,
        sha256=sha256_text(body),
        observed_at=_mtime_utc(path),
        episode_key=episode_key,
    )


def iter_research_documents(root: str | Path) -> Iterator[SourceDocument]:
    """Yield markdown under the ``_*`` research folders, one episode per folder."""
    base = Path(root)
    for folder in sorted(p for p in base.iterdir() if p.is_dir() and p.name.startswith("_")):
        for path in sorted(folder.rglob("*.md")):
            yield _document(path, "markdown", folder.name)


def iter_vault_documents(vault: str | Path) -> Iterator[SourceDocument]:
    """Yield ``*_MOC.md`` and ``Home.md`` from the Obsidian vault.

    These are cross-checks, never sources of truth: the vault is not in git, so
    the copy on disk is the only version that has ever existed and the call it
    describes may already have been overwritten by a later one.
    """
    base = Path(vault)
    for path in sorted(base.rglob("*_MOC.md")):
        yield _document(path, "markdown", f"vault:{path.stem}")
    for path in sorted(base.rglob("Home.md")):
        yield _document(path, "markdown", f"vault:{path.stem}")


def iter_run_documents(runs_dir: str | Path) -> Iterator[SourceDocument]:
    """Yield the ``final_report`` of each swarm run that actually wrote one.

    Of the eighteen runs on disk, three carry a report and fifteen hold an empty
    string. The empty ones are skipped rather than yielded as blank documents,
    so the extractor is never asked to find a call in nothing.
    """
    base = Path(runs_dir)
    for path in sorted(base.glob("*/run.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        report = str(payload.get("final_report") or "").strip()
        if not report:
            continue
        yield _document(path, "run_artifact", path.parent.name, text=report)


# -- prompting ----------------------------------------------------------------

PROMPT_TEMPLATE = """Read the research document below and list every investment call it states.

A call is a stated recommendation on one ticker: what to do, at what price, by when.
Return JSON only, shaped as {{"calls": [...]}}, where each call has:

  ticker      required, e.g. "FPT"
  as_of       required, ISO date of the call, "YYYY-MM-DD"
  action      required, exactly as written in the document (Vietnamese is fine)
  quotes      required, a list of verbatim excerpts from the document
  ref_price / target / bull / bear / stop   numbers, omit any that is not stated
  confidence  a fraction in [0, 1]; a stated 61% is 0.61
  horizon_sessions, thesis_episode, thesis_bullets, invalidation_triggers, notes

Rules that are checked in code, so breaking one only loses the call:
  - Every quote must appear character-for-character in the document.
  - Every number you report must appear in one of your own quotes.
  - Never convert or round a price. Report what is written; the scale is resolved here.
  - If the document states two actions at once, pick the operative one and quote it.
  - Omit a field you cannot quote. A missing target is recorded as incomplete;
    an invented one is a fabricated forecast.

Document: {path}
Observed at: {observed_at}

---
{text}
---
"""


def build_prompt(document: SourceDocument) -> str:
    """Return the extraction prompt for one document."""
    return PROMPT_TEMPLATE.format(
        path=document.path, observed_at=document.observed_at, text=document.text
    )


def parse_proposal(raw: str) -> list[dict[str, Any]]:
    """Parse the model's reply into candidate dicts.

    Args:
        raw: Reply text, optionally wrapped in a fenced code block.

    Returns:
        The candidate list, with unknown keys dropped.

    Raises:
        ExtractionError: The reply is not JSON, or not the agreed shape.
    """
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"proposal is not JSON: {exc}") from exc
    if isinstance(payload, list):
        payload = {"calls": payload}
    if not isinstance(payload, dict) or not isinstance(payload.get("calls"), list):
        raise ExtractionError('proposal must be an object shaped {"calls": [...]}')
    candidates = []
    for item in payload["calls"]:
        if not isinstance(item, dict):
            raise ExtractionError(f"each call must be an object, got {type(item).__name__}")
        candidates.append({key: item[key] for key in item if key in CANDIDATE_FIELDS})
    return candidates


# -- validation ---------------------------------------------------------------


def _as_number(value: Any, field_name: str) -> float:
    """Coerce a proposed field to a float, or refuse the candidate.

    A model that answers ``"58.800 đ"`` where a number was asked for has not
    made a typing mistake -- it has skipped the step where the scale gets
    settled -- so this raises the extraction error rather than the ``ValueError``
    that would escape :func:`extract_document` and stop a whole backfill.
    """
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ExtractionError(
            f"{field_name}={value!r} is not a number. Report the digits alone and "
            "let the quote carry the unit."
        ) from exc


def _locate(quote: str, document: SourceDocument) -> tuple[int, int]:
    """Return the 1-based line span of ``quote`` inside the document.

    The span is computed here rather than taken from the model: an offset the
    model reports is an assertion, an offset found by :meth:`str.find` is a
    fact.

    Raises:
        ExtractionError: The quote is not in the document.
    """
    start = document.text.find(quote)
    if start < 0:
        raise ExtractionError(
            f"quote not found in {document.path}: {quote[:80]!r}. "
            "Quotes are checked character-for-character; a paraphrase is not a citation."
        )
    first = document.text.count("\n", 0, start) + 1
    return first, first + quote.count("\n")


def _build_evidence(quote: str, document: SourceDocument) -> Evidence:
    first, last = _locate(quote, document)
    return Evidence(
        kind=document.kind,
        observed_at=document.observed_at,
        source_session_id=document.session_id,
        source_uuid=document.source_uuid,
        source_path=document.path,
        locator=f"L{first}-L{last}",
        excerpt=quote,
    )


def _anchor_price(stated: float | None, quoted: str) -> tuple[float | None, str]:
    """Return the reference price on the dong scale, or refuse to guess.

    A reference price is the ruler every other price on the call is measured
    against, so it is the one number that must not be re-scaled on a hunch: it
    is rescaled only when the quotes contain an anchored price that equals it
    exactly at a thousand times.
    """
    if stated is None or stated >= 1000.0:
        return stated, ""
    for number in parse_prices(quoted):
        if number.kind != "price" or not number.anchored:
            continue
        if math.isclose(number.value, stated * 1000.0, rel_tol=1e-6):
            note = f"ref_price {stated:g} read as {number.value:.0f} from {number.raw!r}"
            return number.value, note
    raise ExtractionError(
        f"ref_price={stated:g} is written without a unit and no quote states it with one, "
        "so its scale cannot be settled. ref_price is the ruler every other price on this "
        "call is measured against; it is the one number that must not be inferred."
    )


def validate_candidate(
    candidate: dict[str, Any], document: SourceDocument, revision: int = 1
) -> tuple[CallRecord, list[Evidence]]:
    """Turn one proposal into a record, or refuse it.

    Args:
        candidate: One entry from :func:`parse_proposal`.
        document: The document it was read from.
        revision: Position within the episode.

    Returns:
        The validated call and the evidence it cites, in that order.

    Raises:
        ExtractionError: The candidate fails one of the gates above.
        RecordValidationError: The contract in ``records.py`` refuses it.
    """
    for name in ("ticker", "as_of", "action"):
        if not str(candidate.get(name) or "").strip():
            raise ExtractionError(
                f"{name} is required and was not stated; a call without it cannot be scored"
            )
    quotes = [str(item) for item in candidate.get("quotes") or [] if str(item).strip()]
    if not quotes:
        raise ExtractionError(
            "no quotes supplied; an uncited call cannot be told apart from an invented one"
        )

    evidences = [_build_evidence(quote, document) for quote in quotes]
    quoted = "\n".join(quotes)
    action = normalize_action(str(candidate["action"]))

    as_of = parse_date(candidate["as_of"], "as_of")
    written_on = datetime.fromisoformat(document.observed_at.replace("Z", "+00:00")).date()
    if as_of > written_on:
        raise ExtractionError(
            f"as_of {as_of.isoformat()} is after the document was written "
            f"({written_on.isoformat()}): a document cannot report a call from its own future"
        )

    notes: list[str] = []
    numbers: dict[str, float | None] = {}
    for name in _PRICE_FIELDS:
        value = candidate.get(name)
        if value in (None, ""):
            numbers[name] = None
            continue
        number = _as_number(value, name)
        if not _supported(number, quoted):
            raise ExtractionError(
                f"{name}={number:g} does not appear in the supplied quotes. "
                "Quote the sentence that states the price, or omit the field."
            )
        numbers[name] = number

    anchor, note = _anchor_price(numbers["ref_price"], quoted)
    numbers["ref_price"] = anchor
    if note:
        notes.append(note)
    for name in _PRICE_FIELDS:
        if name == "ref_price" or numbers[name] is None:
            continue
        numbers[name], note = resolve_scale(numbers[name], anchor, name)
        if note:
            notes.append(note)

    target = numbers["target"]
    if target is not None and anchor:
        ratio = target / anchor
        low, high = PLAUSIBLE_RATIO
        if not low <= ratio <= high:
            raise ExtractionError(
                f"target {target:.0f} is {ratio:.1f}x ref_price {anchor:.0f}, outside "
                f"[{low}, {high}]. That is a unit error, not a forecast."
            )

    confidence = candidate.get("confidence")
    if confidence in (None, ""):
        confidence = None
    else:
        confidence = _as_number(confidence, "confidence")
        if not _confidence_supported(confidence, quoted):
            raise ExtractionError(
                f"confidence={confidence:g} does not appear in the supplied quotes"
            )

    band = _RANGE_RE.search(quoted)
    if band:
        notes.append(f"band quoted: {band.group(0)}")
    supplied = str(candidate.get("notes") or "").strip()
    if supplied:
        notes.append(supplied)

    ticker = str(candidate["ticker"])
    thesis = str(candidate.get("thesis_episode") or "default")
    record = CallRecord(
        ticker=ticker,
        as_of=as_of.isoformat(),
        action=action,
        known_at=document.observed_at,
        episode_id=episode_id_for(document.episode_key, ticker, thesis),
        revision=revision,
        thesis_episode=thesis,
        ref_price=numbers["ref_price"],
        target=numbers["target"],
        bull=numbers["bull"],
        bear=numbers["bear"],
        stop=numbers["stop"],
        horizon_sessions=int(_as_number(candidate.get("horizon_sessions") or 63, "horizon_sessions")),
        confidence=confidence,
        thesis_bullets=candidate.get("thesis_bullets") or [],
        invalidation_triggers=candidate.get("invalidation_triggers") or [],
        evidence_ids=[item.evidence_id for item in evidences],
        source_session_id=document.session_id,
        source_uuid=document.source_uuid,
        source_event_sha256=document.sha256,
        source_path=document.path,
        artifact_sha256=document.sha256,
        notes=" | ".join(notes),
    )
    return record, evidences


def _rejection_code(error: Exception) -> str:
    text = str(error)
    table = (
        ("is required and was not stated", "missing_field"),
        ("no quotes supplied", "no_evidence"),
        ("quote not found", "quote_not_found"),
        ("does not appear in the supplied quotes", "number_not_in_evidence"),
        ("is ambiguous against ref_price", "scale_ambiguous"),
        ("is written without a unit", "scale_ambiguous"),
        ("not a forecast", "implausible_target"),
        ("its own future", "future_dated"),
        ("unknown action", "unknown_action"),
    )
    for needle, code in table:
        if needle in text:
            return code
    return "invalid_record"


def extract_document(document: SourceDocument, propose: Callable[[str], str]) -> ExtractionResult:
    """Extract every call in one document, refusing the ones that fail a gate.

    Args:
        document: Document to read.
        propose: Callable taking a prompt and returning the model's raw reply.
            Injected rather than wired to a provider: which provider this repo
            actually uses is still unsettled (two ``.env`` files disagree), and
            a backfill has to be reproducible from a recorded reply anyway.

    Returns:
        Records, their evidence, and one :class:`Rejection` per refused
        candidate. A malformed reply becomes a single ``bad_json`` rejection
        rather than an exception, so one broken document cannot halt a backfill.
    """
    result = ExtractionResult()
    try:
        candidates = parse_proposal(propose(build_prompt(document)))
    except ExtractionError as exc:
        result.rejections.append(Rejection("bad_json", str(exc), document.doc_id))
        return result

    seen: dict[str, int] = {}
    for candidate in candidates:
        ticker = str(candidate.get("ticker") or "").upper()
        episode = f"{ticker}|{candidate.get('thesis_episode') or 'default'}"
        revision = seen.get(episode, 0) + 1
        try:
            record, evidences = validate_candidate(candidate, document, revision=revision)
        except (ExtractionError, RecordValidationError) as exc:
            result.rejections.append(
                Rejection(_rejection_code(exc), str(exc), document.doc_id, ticker, candidate)
            )
            continue
        seen[episode] = revision
        result.calls.append(record)
        result.evidence.extend(evidences)
    return result


def assign_revisions(records: Sequence[CallRecord]) -> list[CallRecord]:
    """Renumber revisions within each episode and link each to the one before.

    A folder like ``_fpt_research/`` walks a target 93,000 -> 69,500 -> 59,000
    -> 58,800 across several documents. Those are four revisions of one episode,
    not four observations, and only the last is the scoring point -- so the
    numbering has to be right before anything is counted.

    Args:
        records: Calls from one or more documents, in any order.

    Returns:
        New records with ``revision`` and ``supersedes`` set. The inputs are
        left untouched, because the ledger is append-only.
    """
    grouped: dict[str, list[CallRecord]] = {}
    for record in records:
        grouped.setdefault(record.episode_id, []).append(record)

    renumbered: list[CallRecord] = []
    for episode_id in sorted(grouped):
        ordered = sorted(
            grouped[episode_id],
            key=lambda record: (record.as_of, record.known_at, record.source_path, record.revision),
        )
        previous = ""
        for position, record in enumerate(ordered, start=1):
            data = record.to_dict()
            data.update({"revision": position, "supersedes": previous, "call_id": ""})
            rebuilt = CallRecord.from_dict(data)
            previous = rebuilt.call_id
            renumbered.append(rebuilt)
    return renumbered


def store_result(store: LearningStore, result: ExtractionResult) -> list[AppendResult]:
    """Write an extraction to the ledger, evidence first as the store demands.

    Args:
        store: Open ledger.
        result: What :func:`extract_document` or :func:`extract_all` produced.

    Returns:
        One :class:`~src.learning.store.AppendResult` per call, in order.
    """
    for evidence in result.evidence:
        store.append_evidence(evidence)
    return [store.append_call(record) for record in result.calls]


def extract_all(
    documents: Iterable[SourceDocument], propose: Callable[[str], str]
) -> ExtractionResult:
    """Run :func:`extract_document` over many documents and settle revisions."""
    combined = ExtractionResult()
    for document in documents:
        combined.extend(extract_document(document, propose))
    combined.calls = assign_revisions(combined.calls)
    return combined
