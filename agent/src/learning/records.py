"""Immutable, machine-readable records for the research learning loop.

The data contract is frozen here, before any storage, parser or scoring code
exists, because with ``n`` around eighteen calls the *counting rule* moves the
scorecard more than the data does.

Four decisions are baked into this module and are not re-litigated downstream:

1. **The observation unit is an episode, not a revision.** One research session
   that walks a target price 93,000 -> 69,500 -> 59,000 -> 58,800 is *one*
   observation. Counting it as four is pseudo-replication: it inflates ``n`` and
   shrinks every confidence interval. Each price is stored as a
   :class:`CallRecord` revision inside the same episode; the scoring point is
   the last revision still in force at the cutoff, and the earlier revisions are
   kept only to measure calibration drift.
2. **``ref_price`` is the close of the day the call is made** -- not the next
   session's open, and not the price at the moment the sentence was written.
3. **Horizons count trading sessions, not calendar days.** ``known_at + 90
   days`` lands on a weekend or inside Tet often enough to matter, so the
   authoritative field is :attr:`CallRecord.horizon_sessions` (default 63, about
   three months) and ``deadline`` is a *derived* date that stays empty until a
   real trading calendar reaches it. See :func:`resolve_deadline`.
4. **Provenance is the transcript event, not a git commit.** The Claude Code
   transcripts live outside this repository, so a commit hash proves nothing
   about them. Every record carries ``source_session_id`` + ``source_uuid`` +
   ``source_event_sha256`` instead.

The anti-hindsight wall is enforced per piece of evidence
(:func:`assert_no_hindsight`), not per record timestamp: a record dated
correctly can still be built out of a document written a month later.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

#: Bump when a parser change alters the *content* extracted from an unchanged
#: source event. Deliberately excluded from every identifier below, so that a
#: parser upgrade re-visits records instead of duplicating them.
PARSER_VERSION = "1"

#: Default forecast horizon when a call does not state one: 63 trading
#: sessions, roughly three months on HOSE.
DEFAULT_HORIZON_SESSIONS = 63

#: Scoring checkpoints, in trading sessions.
CHECKPOINT_SESSIONS = (21, 63, 126)

#: A lesson with no evidence behind it dies after this many days.
LESSON_TTL_DAYS = 90

ACTIONS = (
    "buy",
    "accumulate",
    "hold",
    "neutral",
    "reduce",
    "sell",
    "avoid",
    "wait",
)

#: Wording actually used in committee notes, mapped onto the canonical
#: vocabulary. Keys retain their accents so evidence matching cannot confuse
#: ``bán`` with ``ban``; :func:`normalize_action` folds them only when reading
#: the model's proposed action.
ACTION_ALIASES = {
    "accumulation": "accumulate",
    "outperform": "buy",
    "overweight": "buy",
    "trim": "reduce",
    "underperform": "reduce",
    "underweight": "reduce",
    "mua": "buy",
    "mua được": "buy",
    "mua có điều kiện": "buy",
    "mua vào": "buy",
    "tích lũy": "accumulate",
    "mua theo đợt": "accumulate",
    "gom": "accumulate",
    "khả quan": "buy",
    "tăng tỷ trọng": "accumulate",
    "nắm giữ": "hold",
    "nắm": "hold",
    "giữ": "hold",
    "trung lập": "neutral",
    "giảm tỷ trọng": "reduce",
    "hạ tỷ trọng": "reduce",
    "kém khả quan": "reduce",
    "chốt lời": "reduce",
    "bán": "sell",
    "bán hết": "sell",
    "tránh": "avoid",
    "không mua": "avoid",
    "không đuổi": "avoid",
    "loại": "avoid",
    "loại tuyệt đối": "avoid",
    "chờ": "wait",
    "quan sát": "wait",
    "theo dõi": "wait",
    "đứng ngoài": "wait",
}

VERDICTS = ("hit", "miss", "open", "invalidated")

LESSON_STATUSES = ("provisional", "confirmed", "retired")

EXTRACTION_STATUSES = ("complete", "incomplete", "needs_review")

EVIDENCE_KINDS = (
    "transcript_event",
    "markdown",
    "research_report",
    "price_series",
    "run_artifact",
    "external",
)

#: Error classes the debate rounds have actually caught, kept as a closed
#: vocabulary so recurrence can be counted. ``double_count`` is the FOX profit
#: added twice; ``causal_misread`` the ROIC drop read as an accounting effect;
#: ``cashflow_unreconciled`` the year-one FCFF that never met real cash flow;
#: ``stale_crosscheck`` the VRE number Risk already had five days earlier.
ERROR_TAXONOMY = (
    "double_count",
    "causal_misread",
    "cashflow_unreconciled",
    "unit_error",
    "lookahead",
    "source_mismatch",
    "unverified_assumption",
    "stale_crosscheck",
)


class RecordValidationError(ValueError):
    """A record violates the data contract and must not be stored."""


class HindsightViolation(RecordValidationError):
    """Evidence was observed after the wall it is supposed to sit behind."""


def _strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _fold(text: str) -> str:
    return " ".join(_strip_accents(str(text)).lower().split())


def fold_text(text: str) -> str:
    """Return ``text`` accent-stripped, lowercased and whitespace-collapsed.

    Exposed because the extractor has to compare an action phrase against the
    quotes it was supposedly read from, and both sides must be folded the same
    way the action vocabulary is.
    """
    return _fold(text)


def sha256_text(text: str) -> str:
    """Return the hex sha256 of ``text`` encoded as UTF-8."""
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def utc_now() -> str:
    """Return the current UTC instant as ``YYYY-MM-DDTHH:MM:SSZ``."""
    stamp = datetime.now(timezone.utc).replace(microsecond=0)
    return stamp.isoformat().replace("+00:00", "Z")


def _as_utc_text(value: datetime) -> str:
    stamp = value.astimezone(timezone.utc).replace(microsecond=0)
    return stamp.isoformat().replace("+00:00", "Z")


def normalize_action(value: str) -> str:
    """Map a stated recommendation onto the canonical action vocabulary.

    Args:
        value: Action as written, English or Vietnamese, accents optional.

    Returns:
        One of :data:`ACTIONS`.

    Raises:
        RecordValidationError: The wording is not in the vocabulary. Guessing
            here would silently reclassify a call, so the extractor is forced to
            be explicit instead.
    """
    folded = _fold(value)
    if not folded:
        raise RecordValidationError("action is required")
    if folded in ACTIONS:
        return folded
    for wording, canonical in ACTION_ALIASES.items():
        if _fold(wording) == folded:
            return canonical
    allowed = ", ".join(ACTIONS)
    hint = (
        " This looks like a whole sentence: pass only its recommendation phrase and put "
        "the sentence in the evidence instead."
        if len(folded.split()) > 4
        else " Add an entry to ACTION_ALIASES rather than guessing."
    )
    raise RecordValidationError(
        f"unknown action {value!r}. Canonical actions: {allowed}." + hint
    )


def parse_date(value: Any, field_name: str) -> date:
    """Parse an ISO ``YYYY-MM-DD`` date, raising a contract error on failure."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise RecordValidationError(
            f"{field_name} must be an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def parse_timestamp(value: Any, field_name: str) -> datetime:
    """Parse an ISO timestamp, accepting a trailing ``Z`` and assuming UTC."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise RecordValidationError(
            f"{field_name} must be an ISO timestamp, got {value!r}"
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [str(item) for item in value if str(item)]


def _coerce_optional_float(
    value: Any, field_name: str, *, positive: bool = False
) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field_name} must be numeric, got {value!r}") from exc
    if number != number:  # NaN
        raise RecordValidationError(f"{field_name} must not be NaN")
    if positive and number <= 0:
        raise RecordValidationError(f"{field_name} must be positive, got {number}")
    return number


def sessions_between(start: Any, end: Any, sessions: Sequence[str]) -> int:
    """Count trading sessions from ``start`` (excluded) to ``end`` (included).

    Args:
        start: Session date the count starts from.
        end: Session date the count ends at.
        sessions: Ascending ISO dates of real trading sessions, normally the
            index of a VNINDEX price series rather than a hand-written calendar.

    Returns:
        Number of sessions elapsed. Negative when ``end`` precedes ``start``.

    Raises:
        RecordValidationError: Either endpoint is outside ``sessions``.
    """
    index = {str(day): position for position, day in enumerate(sessions)}
    start_key = parse_date(start, "start").isoformat()
    end_key = parse_date(end, "end").isoformat()
    for key, name in ((start_key, "start"), (end_key, "end")):
        if key not in index:
            raise RecordValidationError(
                f"{name} {key} is not a trading session in the calendar"
            )
    return index[end_key] - index[start_key]


def resolve_deadline(as_of: Any, horizon_sessions: int, sessions: Sequence[str]) -> str | None:
    """Return the session date ``horizon_sessions`` after ``as_of``.

    Args:
        as_of: The session the call was made on; must exist in ``sessions``.
        horizon_sessions: Forecast horizon in trading sessions.
        sessions: Ascending ISO dates of real trading sessions.

    Returns:
        The deadline as an ISO date, or ``None`` when the calendar does not
        reach that far yet. ``None`` is the normal state for a fresh call and
        must not be papered over with a calendar-day estimate -- that
        approximation is what this contract exists to remove.

    Raises:
        RecordValidationError: ``as_of`` is not a trading session, or the
            horizon is not positive.
    """
    if int(horizon_sessions) < 1:
        raise RecordValidationError(f"horizon_sessions must be >= 1, got {horizon_sessions}")
    key = parse_date(as_of, "as_of").isoformat()
    ordered = [str(day) for day in sessions]
    try:
        position = ordered.index(key)
    except ValueError as exc:
        raise RecordValidationError(
            f"as_of {key} is not a trading session in the calendar"
        ) from exc
    target = position + int(horizon_sessions)
    if target >= len(ordered):
        return None
    return ordered[target]


def episode_id_for(source_session_id: str, ticker: str, thesis_episode: str) -> str:
    """Build the stable episode key ``(session, ticker, thesis)``."""
    seed = f"{source_session_id}|{str(ticker).upper()}|{_fold(thesis_episode) or 'default'}"
    return "ep_" + sha256_text(seed)[:12]


def call_id_for(episode_id: str, revision: int, source_event_sha256: str) -> str:
    """Build a deterministic call identifier.

    The parser version is deliberately *not* part of the seed. Re-parsing the
    same source event with improved logic must land on the same ``call_id`` so
    the store can recognise it as the same observation; a content change is then
    a new record superseding the old one, not a second observation.
    """
    seed = f"{episode_id}|{int(revision)}|{source_event_sha256}"
    return "call_" + sha256_text(seed)[:12]


@dataclass
class Evidence:
    """A single citable thing a record leans on.

    Attributes:
        evidence_id: Stable identifier, derived when omitted.
        kind: One of :data:`EVIDENCE_KINDS`.
        observed_at: When this content became observable. This is the field the
            hindsight wall is checked against -- not when it was cited.
        source_session_id: Claude Code session the event came from, when any.
        source_uuid: Transcript event UUID, when any.
        source_path: File the content was read from.
        locator: Span within the source: line range, cell, ticker plus date.
        sha256: Hash of the cited content, so a later edit is detectable.
        excerpt: Verbatim quote. The rubric is scored in code; the model is only
            allowed to supply the quote.
    """

    evidence_id: str = ""
    kind: str = "transcript_event"
    observed_at: str = ""
    source_session_id: str = ""
    source_uuid: str = ""
    source_path: str = ""
    locator: str = ""
    sha256: str = ""
    excerpt: str = ""

    def __post_init__(self) -> None:
        if self.kind not in EVIDENCE_KINDS:
            allowed = ", ".join(EVIDENCE_KINDS)
            raise RecordValidationError(
                f"unknown evidence kind {self.kind!r}. Allowed: {allowed}"
            )
        self.observed_at = _as_utc_text(parse_timestamp(self.observed_at, "observed_at"))
        if not self.sha256:
            self.sha256 = sha256_text(self.excerpt)
        if not (self.source_uuid or self.source_path):
            raise RecordValidationError(
                "evidence needs a provenance handle: source_uuid or source_path"
            )
        if not self.evidence_id:
            seed = "|".join(
                (
                    self.source_session_id,
                    self.source_uuid,
                    self.source_path,
                    self.locator,
                    self.sha256,
                )
            )
            self.evidence_id = "ev_" + sha256_text(seed)[:12]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain JSON-compatible data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        """Rebuild from persisted data, ignoring unknown keys."""
        return cls(**{key: data[key] for key in data if key in cls.__dataclass_fields__})


@dataclass
class CallRecord:
    """One revision of an investment call, inside an episode.

    See the module docstring for why the episode, not this record, is the unit
    of observation.

    Attributes:
        ticker: Upper-case symbol, unsuffixed (``FPT``, not ``FPT.VN``).
        as_of: Trading date of the call; ``ref_price`` is this day's close.
        action: Canonical action from :data:`ACTIONS`.
        known_at: UTC instant the call became known. Evidence observed after
            this is hindsight.
        call_id: Deterministic identifier, derived when omitted.
        episode_id: Deterministic ``(session, ticker, thesis)`` key.
        revision: 1-based position within the episode.
        thesis_episode: Slug distinguishing two live theses on one ticker in one
            session. ``default`` collapses them into a single episode.
        ref_price: Close on ``as_of``.
        target: Stated target price.
        bull: Bull-case price.
        bear: Bear-case price.
        stop: Stop level.
        horizon_sessions: Authoritative horizon in trading sessions.
        deadline: Derived session date; empty until the calendar reaches it.
        confidence: Stated confidence as a fraction in ``[0, 1]``.
        thesis_bullets: Reasons given, verbatim where possible.
        invalidation_triggers: What would falsify the call.
        evidence_ids: Evidence backing the thesis, all observed at or before
            ``known_at``.
        source_session_id: Claude Code session id.
        source_uuid: Transcript event UUID the call was read from.
        source_event_sha256: Hash of that event, the idempotency handle.
        source_path: Artifact the call was crystallised into, when any.
        artifact_sha256: Hash of that artifact.
        parser_version: Extractor version that produced this content.
        extraction_status: ``complete`` only when target and confidence are both
            present; downgraded automatically otherwise.
        supersedes: ``call_id`` this revision replaces.
        notes: Free text for the manual review queue.
    """

    ticker: str
    as_of: str
    action: str
    known_at: str
    call_id: str = ""
    episode_id: str = ""
    revision: int = 1
    thesis_episode: str = "default"
    ref_price: float | None = None
    target: float | None = None
    bull: float | None = None
    bear: float | None = None
    stop: float | None = None
    horizon_sessions: int = DEFAULT_HORIZON_SESSIONS
    deadline: str = ""
    confidence: float | None = None
    thesis_bullets: list[str] = field(default_factory=list)
    invalidation_triggers: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    source_session_id: str = ""
    source_uuid: str = ""
    source_event_sha256: str = ""
    source_path: str = ""
    artifact_sha256: str = ""
    parser_version: str = PARSER_VERSION
    extraction_status: str = "complete"
    supersedes: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        self.ticker = str(self.ticker or "").strip().upper()
        if not self.ticker:
            raise RecordValidationError("ticker is required")
        as_of = parse_date(self.as_of, "as_of")
        self.as_of = as_of.isoformat()
        self.action = normalize_action(self.action)

        known_at = parse_timestamp(self.known_at, "known_at")
        if known_at.astimezone(timezone.utc).date() < as_of:
            raise RecordValidationError(
                f"known_at {self.known_at} precedes as_of {self.as_of}: a call cannot be "
                "known before the session it is made on"
            )
        self.known_at = _as_utc_text(known_at)

        self.revision = int(self.revision)
        if self.revision < 1:
            raise RecordValidationError(f"revision must be >= 1, got {self.revision}")
        self.horizon_sessions = int(self.horizon_sessions)
        if self.horizon_sessions < 1:
            raise RecordValidationError(
                f"horizon_sessions must be >= 1, got {self.horizon_sessions}"
            )

        for name in ("ref_price", "target", "bull", "bear", "stop"):
            setattr(self, name, _coerce_optional_float(getattr(self, name), name, positive=True))

        self.confidence = _coerce_optional_float(self.confidence, "confidence")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise RecordValidationError(
                f"confidence must be a fraction in [0, 1], got {self.confidence}. "
                "A stated 62% is 0.62 -- the percent form is the unit bug this "
                "contract exists to stop."
            )

        if self.deadline:
            self.deadline = parse_date(self.deadline, "deadline").isoformat()

        self.thesis_bullets = _coerce_str_list(self.thesis_bullets)
        self.invalidation_triggers = _coerce_str_list(self.invalidation_triggers)
        self.evidence_ids = _coerce_str_list(self.evidence_ids)
        self.thesis_episode = str(self.thesis_episode or "default").strip() or "default"

        if self.extraction_status not in EXTRACTION_STATUSES:
            allowed = ", ".join(EXTRACTION_STATUSES)
            raise RecordValidationError(
                f"unknown extraction_status {self.extraction_status!r}. Allowed: {allowed}"
            )
        if self.extraction_status == "complete" and (
            self.target is None or self.confidence is None
        ):
            self.extraction_status = "incomplete"

        if not self.episode_id:
            self.episode_id = episode_id_for(
                self.source_session_id, self.ticker, self.thesis_episode
            )
        if not self.call_id:
            self.call_id = call_id_for(self.episode_id, self.revision, self.source_event_sha256)

    @property
    def upside(self) -> float | None:
        """Return the stated upside to target as a fraction, when computable."""
        if self.target is None or self.ref_price is None:
            return None
        return self.target / self.ref_price - 1.0

    def with_deadline(self, sessions: Sequence[str]) -> "CallRecord":
        """Return a copy with ``deadline`` resolved against a trading calendar.

        The copy is a new record rather than an edit, because the ledger is
        append-only; the caller decides whether to store it as a revision.
        """
        resolved = resolve_deadline(self.as_of, self.horizon_sessions, sessions)
        data = self.to_dict()
        data["deadline"] = resolved or ""
        return CallRecord.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain JSON-compatible data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CallRecord":
        """Rebuild from persisted data, ignoring unknown keys."""
        return cls(**{key: data[key] for key in data if key in cls.__dataclass_fields__})


@dataclass
class ProcessRecord:
    """What a research run cost and what its debate rounds caught.

    This is the fast-learning signal. Market outcomes give one observation per
    horizon; a debate round gives one per round.

    Attributes:
        source_session_id: Claude Code session, where most real work happened.
        run_id: Swarm run identifier, when the work went through the swarm.
        process_id: Deterministic identifier, derived when omitted.
        preset: Swarm preset or workflow name.
        rounds: Number of critique rounds completed.
        errors_caught: Findings, each a mapping with ``code`` drawn from
            :data:`ERROR_TAXONOMY`, plus ``description``, ``round`` and a
            mandatory ``evidence_id``.
        data_violations: Breaches of the data rules (invented numbers, missing
            cross-check, wrong source).
        rework_count: How many times a conclusion was rewritten.
        tokens: Total tokens spent reaching the conclusion.
        wall_time_sec: Wall-clock seconds spent.
        cost_usd: Money spent, when the provider reports it.
        git_commit: Repository state the run executed against.
        seed: Sampling seed, when set.
        temperature: Sampling temperature, when set.
        playbook_version: Playbook revision loaded into the run.
        completed: Whether the run finished, so completion rate is measurable.
        known_at: UTC instant the record was captured.
        source_uuid: Transcript event UUID, when any.
        source_event_sha256: Hash of that event, the idempotency handle.
        parser_version: Extractor version that produced this content.
    """

    source_session_id: str = ""
    run_id: str = ""
    process_id: str = ""
    preset: str = ""
    rounds: int = 0
    errors_caught: list[dict[str, Any]] = field(default_factory=list)
    data_violations: list[str] = field(default_factory=list)
    rework_count: int = 0
    tokens: int = 0
    wall_time_sec: float = 0.0
    cost_usd: float | None = None
    git_commit: str = ""
    seed: int | None = None
    temperature: float | None = None
    playbook_version: str = ""
    completed: bool = False
    known_at: str = ""
    source_uuid: str = ""
    source_event_sha256: str = ""
    parser_version: str = PARSER_VERSION

    def __post_init__(self) -> None:
        if not (self.run_id or self.source_session_id):
            raise RecordValidationError("process record needs a run_id or a source_session_id")
        if not self.known_at:
            self.known_at = utc_now()
        self.known_at = _as_utc_text(parse_timestamp(self.known_at, "known_at"))

        normalized: list[dict[str, Any]] = []
        for position, raw in enumerate(self.errors_caught):
            if not isinstance(raw, dict):
                raise RecordValidationError(
                    f"errors_caught[{position}] must be a mapping, got {type(raw).__name__}"
                )
            code = str(raw.get("code", "")).strip()
            if code not in ERROR_TAXONOMY:
                allowed = ", ".join(ERROR_TAXONOMY)
                raise RecordValidationError(
                    f"errors_caught[{position}] has unknown code {code!r}. Allowed: {allowed}"
                )
            evidence_id = str(raw.get("evidence_id", "")).strip()
            if not evidence_id:
                raise RecordValidationError(
                    f"errors_caught[{position}] needs an evidence_id: an uncited catch "
                    "cannot be audited and would inflate the process score"
                )
            normalized.append(
                {
                    "code": code,
                    "description": str(raw.get("description", "")),
                    "round": int(raw.get("round", 0)),
                    "evidence_id": evidence_id,
                }
            )
        self.errors_caught = normalized
        self.data_violations = _coerce_str_list(self.data_violations)

        for name in ("rounds", "rework_count", "tokens"):
            value = int(getattr(self, name))
            if value < 0:
                raise RecordValidationError(f"{name} must be >= 0, got {value}")
            setattr(self, name, value)
        self.wall_time_sec = float(self.wall_time_sec)
        if self.wall_time_sec < 0:
            raise RecordValidationError(f"wall_time_sec must be >= 0, got {self.wall_time_sec}")
        self.cost_usd = _coerce_optional_float(self.cost_usd, "cost_usd")
        self.temperature = _coerce_optional_float(self.temperature, "temperature")
        self.completed = bool(self.completed)

        if not self.process_id:
            seed = f"{self.source_session_id}|{self.run_id}|{self.source_event_sha256}"
            self.process_id = "proc_" + sha256_text(seed)[:12]

    @property
    def error_taxonomy(self) -> list[str]:
        """Return the distinct error codes caught, in first-seen order."""
        seen: list[str] = []
        for item in self.errors_caught:
            if item["code"] not in seen:
                seen.append(item["code"])
        return seen

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain JSON-compatible data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessRecord":
        """Rebuild from persisted data, ignoring unknown keys."""
        return cls(**{key: data[key] for key in data if key in cls.__dataclass_fields__})


@dataclass
class Outcome:
    """A scored call at one checkpoint.

    An outcome may only be closed against real price evidence. A verdict other
    than ``open`` therefore requires both a resolved price and at least one
    ``evidence_id``; the model is never allowed to declare a hit.

    Attributes:
        call_id: The revision being scored -- the last one in force at cutoff.
        resolved_at: Session date the checkpoint fell on.
        checkpoint_sessions: One of :data:`CHECKPOINT_SESSIONS`.
        verdict: One of :data:`VERDICTS`.
        outcome_id: Deterministic identifier, derived when omitted.
        episode_id: The call's episode, so scores aggregate at the observation
            unit rather than per revision.
        resolved_price: Close on ``resolved_at``.
        realized_ret: Return from ``ref_price`` to ``resolved_price``.
        vni_ret: VN-Index return over the same window.
        vn30_ret: VN30 return over the same window.
        sector_ret: Sector return over the same window.
        alpha: Excess over the stated benchmark.
        target_error: ``resolved_price / target - 1``, the price-accuracy term.
        trigger_fired: Whether an invalidation trigger fired inside the window.
        regime: Market regime label, so results are never read as absolutes.
        base_rate_pctile: Percentile of ``realized_ret`` within the regime base
            rate. Beating zero is not the bar; beating the regime is.
        evidence_ids: Price-series evidence supporting the numbers above.
        parser_version: Resolver version that produced this score.
        notes: Free text.
    """

    call_id: str
    resolved_at: str
    checkpoint_sessions: int
    verdict: str = "open"
    outcome_id: str = ""
    episode_id: str = ""
    resolved_price: float | None = None
    realized_ret: float | None = None
    vni_ret: float | None = None
    vn30_ret: float | None = None
    sector_ret: float | None = None
    alpha: float | None = None
    target_error: float | None = None
    trigger_fired: bool = False
    regime: str = ""
    base_rate_pctile: float | None = None
    evidence_ids: list[str] = field(default_factory=list)
    parser_version: str = PARSER_VERSION
    notes: str = ""

    def __post_init__(self) -> None:
        if not str(self.call_id or "").strip():
            raise RecordValidationError("call_id is required")
        self.resolved_at = parse_date(self.resolved_at, "resolved_at").isoformat()
        self.checkpoint_sessions = int(self.checkpoint_sessions)
        if self.checkpoint_sessions not in CHECKPOINT_SESSIONS:
            allowed = ", ".join(str(item) for item in CHECKPOINT_SESSIONS)
            raise RecordValidationError(
                f"checkpoint_sessions must be one of {allowed}, got {self.checkpoint_sessions}"
            )
        if self.verdict not in VERDICTS:
            allowed = ", ".join(VERDICTS)
            raise RecordValidationError(f"unknown verdict {self.verdict!r}. Allowed: {allowed}")

        self.resolved_price = _coerce_optional_float(
            self.resolved_price, "resolved_price", positive=True
        )
        for name in (
            "realized_ret",
            "vni_ret",
            "vn30_ret",
            "sector_ret",
            "alpha",
            "target_error",
            "base_rate_pctile",
        ):
            setattr(self, name, _coerce_optional_float(getattr(self, name), name))
        self.trigger_fired = bool(self.trigger_fired)
        self.evidence_ids = _coerce_str_list(self.evidence_ids)

        if self.verdict != "open":
            if self.resolved_price is None:
                raise RecordValidationError(
                    f"verdict {self.verdict!r} needs a resolved_price from real price data"
                )
            if not self.evidence_ids:
                raise RecordValidationError(
                    f"verdict {self.verdict!r} needs at least one evidence_id pointing at "
                    "the price series it was scored against"
                )

        if not self.outcome_id:
            seed = f"{self.call_id}|{self.checkpoint_sessions}|{self.resolved_at}"
            self.outcome_id = "out_" + sha256_text(seed)[:12]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain JSON-compatible data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Outcome":
        """Rebuild from persisted data, ignoring unknown keys."""
        return cls(**{key: data[key] for key in data if key in cls.__dataclass_fields__})


@dataclass
class Lesson:
    """A playbook line with a source and an expiry date.

    A lesson with no evidence behind it is forced to ``provisional`` and dies
    after :data:`LESSON_TTL_DAYS`. Without that rule the playbook amplifies its
    own bias, which is worse than having no playbook.

    Attributes:
        domain: Playbook file the line belongs to (``nganhang``, ``vimo``, ...).
        statement: The line itself.
        lesson_id: Deterministic identifier, derived when omitted.
        evidence_ids: Resolved calls or run cards supporting it.
        support_count: Times the line has held up.
        contradicted_count: Times it has not. Mirrors the ``ShadowRule`` pattern
            already used for user rules, with the agent as the subject.
        status: One of :data:`LESSON_STATUSES`.
        created_at: UTC instant the line was first written.
        expires_at: ISO date after which a provisional line is dropped.
        superseded_by: Lesson that replaced this one.
        parser_version: Curator version that produced this line.
    """

    domain: str
    statement: str
    lesson_id: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    support_count: int = 0
    contradicted_count: int = 0
    status: str = "provisional"
    created_at: str = ""
    expires_at: str = ""
    superseded_by: str = ""
    parser_version: str = PARSER_VERSION

    def __post_init__(self) -> None:
        self.domain = str(self.domain or "").strip()
        self.statement = str(self.statement or "").strip()
        if not self.domain:
            raise RecordValidationError("domain is required")
        if not self.statement:
            raise RecordValidationError("statement is required")
        if self.status not in LESSON_STATUSES:
            allowed = ", ".join(LESSON_STATUSES)
            raise RecordValidationError(
                f"unknown lesson status {self.status!r}. Allowed: {allowed}"
            )
        self.evidence_ids = _coerce_str_list(self.evidence_ids)
        for name in ("support_count", "contradicted_count"):
            value = int(getattr(self, name))
            if value < 0:
                raise RecordValidationError(f"{name} must be >= 0, got {value}")
            setattr(self, name, value)

        if not self.created_at:
            self.created_at = utc_now()
        created = parse_timestamp(self.created_at, "created_at")
        self.created_at = _as_utc_text(created)

        if not self.evidence_ids and self.status == "confirmed":
            raise RecordValidationError(
                "a confirmed lesson needs at least one evidence_id; an unsourced line "
                "stays provisional"
            )
        if self.status == "provisional" and not self.expires_at:
            self.expires_at = (created.date() + timedelta(days=LESSON_TTL_DAYS)).isoformat()
        if self.expires_at:
            self.expires_at = parse_date(self.expires_at, "expires_at").isoformat()

        if not self.lesson_id:
            seed = f"{self.domain}|{_fold(self.statement)}"
            self.lesson_id = "les_" + sha256_text(seed)[:12]

    def is_expired(self, as_of: Any = None) -> bool:
        """Return whether the lesson has passed its expiry date."""
        if not self.expires_at:
            return False
        today = parse_date(as_of, "as_of") if as_of else datetime.now(timezone.utc).date()
        return today > date.fromisoformat(self.expires_at)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain JSON-compatible data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Lesson":
        """Rebuild from persisted data, ignoring unknown keys."""
        return cls(**{key: data[key] for key in data if key in cls.__dataclass_fields__})


def assert_no_hindsight(wall: str, evidences: Iterable[Evidence]) -> None:
    """Fail when any evidence was observed after the wall it sits behind.

    The check is per piece of evidence, not per record: a record can carry a
    correct ``as_of`` and still be reconstructed from a document written weeks
    later, which is exactly how a backfill quietly invents a better thesis than
    the one that was actually held.

    Args:
        wall: The cutoff instant -- ``known_at`` for a call, ``resolved_at`` for
            an outcome.
        evidences: Evidence objects backing the record.

    Raises:
        HindsightViolation: One or more items were observed after ``wall``.
    """
    limit = parse_timestamp(wall, "wall")
    offenders = [
        f"{item.evidence_id} observed_at={item.observed_at}"
        for item in evidences
        if parse_timestamp(item.observed_at, "observed_at") > limit
    ]
    if offenders:
        raise HindsightViolation(
            f"evidence observed after the {_as_utc_text(limit)} wall: " + "; ".join(offenders)
        )


def latest_revision(records: Iterable[CallRecord], cutoff: Any = None) -> CallRecord | None:
    """Return the scoring point of an episode: the last revision in force.

    Args:
        records: Revisions of a single episode.
        cutoff: Optional UTC instant; revisions known after it are ignored, so a
            resolver never scores a revision that did not yet exist.

    Returns:
        The highest-revision record at or before ``cutoff``, or ``None`` when no
        revision qualifies.
    """
    limit = parse_timestamp(cutoff, "cutoff") if cutoff else None
    eligible = [
        record
        for record in records
        if limit is None or parse_timestamp(record.known_at, "known_at") <= limit
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda record: (record.revision, record.known_at))
