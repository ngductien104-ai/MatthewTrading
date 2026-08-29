"""Parser for Claude Code session transcripts.

This is the primary capture surface for the learning loop. The framework's own
``AgentLoop`` has one real session on disk after three months; the research that
actually happened -- FPT, NLG, MWG, VRE, PHR -- lives in twenty JSONL
transcripts under ``~/.claude/projects/``.

Three properties of that format were measured across all twenty files before
this parser was written, and each one shapes the code:

**A transcript is a DAG of events, not a log.** Of 1,946 tool results, **648
did not arrive on the line after their request**. Tools issued in parallel
interleave, so pairing a result with the nearest preceding request misattributes
a third of the evidence in the ledger. Results are matched by
``tool_use.id`` <-> ``tool_result.tool_use_id`` and by nothing else.

**Some requests never get a result.** Four tool calls across the corpus were cut
off mid-flight. They are kept with ``status="unresolved"`` rather than dropped,
because a call that was issued and abandoned is itself a fact about the run.

**Timestamps run backwards.** Thirty-six regressions were measured; most are
sub-second jitter, but three jump back a full two minutes. Line order is
therefore the authoritative sequence, and every event also carries
:attr:`TranscriptEvent.observed_at` -- the running maximum of the timestamps
seen so far. Anti-hindsight walls must use that monotonic value, otherwise clock
jitter alone raises false violations against evidence that structurally came
first.

One measured absence matters as much: **there are zero sidechain events**.
Sub-agent reasoning is not written to these files, so a ``ProcessRecord`` built
from a transcript sees the orchestrator's view of a swarm and no more. That is a
ceiling on backfill, not a bug in this parser.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

#: Event types that carry conversation content.
CONTENT_TYPES = ("user", "assistant", "system")

#: Event types the harness writes for its own bookkeeping. Listed exhaustively
#: rather than skipped by default so that a new one shows up in
#: :attr:`Transcript.unknown_types` instead of being silently discarded.
HARNESS_TYPES = frozenset(
    {
        "agent-name",
        "ai-title",
        "atis-latch",
        "attachment",
        "bridge-session",
        "cost-state",
        "custom-title",
        "file-history-delta",
        "file-history-snapshot",
        "last-prompt",
        "mode",
        "permission-mode",
        "queue-operation",
    }
)

_ENV_DIR = "VIBE_TRADING_TRANSCRIPT_DIR"


def default_transcript_dir(project_slug: str = "C--Users-VVVZV-MatthewTrading") -> Path:
    """Return the directory holding this project's Claude Code transcripts.

    Args:
        project_slug: Directory name Claude Code derives from the project path.

    Returns:
        Env override when ``VIBE_TRADING_TRANSCRIPT_DIR`` is set, otherwise
        ``~/.claude/projects/<project_slug>``.
    """
    override = os.environ.get(_ENV_DIR, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude" / "projects" / project_slug


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _block_text(content: Any) -> str:
    """Flatten a message ``content`` field into plain text.

    Accepts the three shapes the format actually uses: a bare string, a list of
    typed blocks, or a list of bare strings. ``thinking`` blocks are dropped --
    they are the model's scratch space, they are not part of what was said, and
    including them would let a backfill quote reasoning the user never saw.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "\n".join(part for part in parts if part)


@dataclass
class ToolCall:
    """A tool request paired with its result by id, never by position.

    Attributes:
        tool_use_id: The id both halves agree on.
        name: Tool name as invoked.
        request_uuid: Event the request was issued from.
        request_line: 0-based line of that event.
        requested_at: Monotonic timestamp of the request.
        tool_input: Arguments as recorded.
        result_uuid: Event carrying the result, empty when unresolved.
        result_line: Line of that event, ``-1`` when unresolved.
        completed_at: Monotonic timestamp of the result.
        result_text: Flattened result content.
        status: ``ok``, ``error`` or ``unresolved``.
    """

    tool_use_id: str
    name: str
    request_uuid: str
    request_line: int
    requested_at: str
    tool_input: dict[str, Any] = field(default_factory=dict)
    result_uuid: str = ""
    result_line: int = -1
    completed_at: str = ""
    result_text: str = ""
    status: str = "unresolved"

    @property
    def line_gap(self) -> int:
        """Return how many lines sat between request and result.

        ``1`` means the result followed immediately. Anything else is a case
        that positional pairing would have got wrong.
        """
        if self.result_line < 0:
            return -1
        return self.result_line - self.request_line


@dataclass
class TranscriptEvent:
    """One content event from a transcript.

    Attributes:
        uuid: Event identifier, the provenance handle stored on records.
        parent_uuid: Parent in the DAG, empty at a root.
        session_id: Session the event belongs to.
        kind: One of :data:`CONTENT_TYPES`.
        line_no: 0-based line, the authoritative ordering.
        timestamp: Raw timestamp as written. May run backwards.
        observed_at: Running maximum of timestamps up to this line. Use this,
            not ``timestamp``, for any cutoff comparison.
        text: Visible text, with thinking blocks removed.
        tool_use_ids: Tool requests issued by this event.
        tool_result_for: Tool request this event answers, when it is a result.
        sha256: Hash of the raw JSON line, the idempotency handle.
        has_thinking: Whether reasoning blocks were dropped from ``text``.
        git_branch: Branch recorded at the time.
        cwd: Working directory recorded at the time.
        cli_version: Claude Code version that wrote the line.
    """

    uuid: str
    parent_uuid: str
    session_id: str
    kind: str
    line_no: int
    timestamp: str = ""
    observed_at: str = ""
    text: str = ""
    tool_use_ids: list[str] = field(default_factory=list)
    tool_result_for: str = ""
    sha256: str = ""
    has_thinking: bool = False
    git_branch: str = ""
    cwd: str = ""
    cli_version: str = ""

    @property
    def is_tool_result(self) -> bool:
        """Return whether this event exists only to carry a tool result."""
        return bool(self.tool_result_for)


@dataclass
class Transcript:
    """A parsed session transcript.

    Attributes:
        session_id: Session identifier.
        path: File the events were read from.
        events: Content events in line order.
        tool_calls: Tool calls keyed by ``tool_use_id``.
        unknown_types: Event types this parser has never seen, with counts. A
            non-empty mapping means the harness format moved and the parser
            needs a look -- it is surfaced rather than swallowed.
        malformed_lines: Lines that were not valid JSON.
        usage: Summed token counters from assistant events.
    """

    session_id: str
    path: Path
    events: list[TranscriptEvent] = field(default_factory=list)
    tool_calls: dict[str, ToolCall] = field(default_factory=dict)
    unknown_types: dict[str, int] = field(default_factory=dict)
    malformed_lines: int = 0
    usage: dict[str, int] = field(default_factory=dict)

    def event_by_uuid(self, uuid: str) -> TranscriptEvent | None:
        """Return the event with this uuid, or ``None``."""
        for event in self.events:
            if event.uuid == uuid:
                return event
        return None

    def thread(self, uuid: str) -> list[TranscriptEvent]:
        """Return the ancestry chain from the root down to ``uuid``.

        Walking ``parentUuid`` is the only correct way to say what an event was
        replying to; line adjacency is not, for the same reason tool pairing is
        not.

        Args:
            uuid: Event to trace.

        Returns:
            Events ordered root-first, empty when the uuid is unknown.
        """
        index = {event.uuid: event for event in self.events}
        current = index.get(uuid)
        chain: list[TranscriptEvent] = []
        seen: set[str] = set()
        while current is not None and current.uuid not in seen:
            seen.add(current.uuid)
            chain.append(current)
            current = index.get(current.parent_uuid) if current.parent_uuid else None
        chain.reverse()
        return chain

    def unresolved_tool_calls(self) -> list[ToolCall]:
        """Return tool requests that never received a result."""
        return [call for call in self.tool_calls.values() if call.status == "unresolved"]

    def misordered_tool_calls(self) -> list[ToolCall]:
        """Return resolved calls whose result did not follow immediately.

        These are exactly the calls a position-based parser would misattribute.
        """
        return [call for call in self.tool_calls.values() if call.line_gap > 1]

    def events_until(self, cutoff: str) -> list[TranscriptEvent]:
        """Return events observed at or before ``cutoff``.

        Uses the monotonic ``observed_at``, so a two-minute clock regression
        cannot drop an event that structurally preceded the cutoff.
        """
        return [event for event in self.events if event.observed_at and event.observed_at <= cutoff]

    @property
    def first_observed_at(self) -> str:
        """Return the earliest monotonic timestamp, or an empty string."""
        return self.events[0].observed_at if self.events else ""

    @property
    def last_observed_at(self) -> str:
        """Return the latest monotonic timestamp, or an empty string."""
        return self.events[-1].observed_at if self.events else ""


def parse_transcript(path: str | Path) -> Transcript:
    """Parse one transcript file.

    Args:
        path: Path to a ``.jsonl`` transcript.

    Returns:
        The parsed :class:`Transcript`. Malformed lines are counted rather than
        raised on: a truncated tail must not cost the whole session.

    Raises:
        FileNotFoundError: The path does not exist.
    """
    path = Path(path)
    transcript = Transcript(session_id="", path=path)
    high_water = ""

    with path.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle):
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                transcript.malformed_lines += 1
                continue
            if not isinstance(payload, dict):
                transcript.malformed_lines += 1
                continue

            kind = str(payload.get("type", ""))
            if kind not in CONTENT_TYPES:
                if kind not in HARNESS_TYPES:
                    transcript.unknown_types[kind] = transcript.unknown_types.get(kind, 0) + 1
                continue

            session_id = str(payload.get("sessionId") or payload.get("session_id") or "")
            if session_id and not transcript.session_id:
                transcript.session_id = session_id

            timestamp = str(payload.get("timestamp") or "")
            if timestamp > high_water:
                high_water = timestamp

            message = payload.get("message")
            content = message.get("content") if isinstance(message, dict) else payload.get("content")

            event = TranscriptEvent(
                uuid=str(payload.get("uuid") or ""),
                parent_uuid=str(payload.get("parentUuid") or ""),
                session_id=session_id,
                kind=kind,
                line_no=line_no,
                timestamp=timestamp,
                observed_at=high_water,
                text=_block_text(content),
                sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                git_branch=str(payload.get("gitBranch") or ""),
                cwd=str(payload.get("cwd") or ""),
                cli_version=str(payload.get("version") or ""),
            )

            if isinstance(message, dict):
                usage = message.get("usage")
                if isinstance(usage, dict):
                    for key, value in usage.items():
                        if isinstance(value, int):
                            transcript.usage[key] = transcript.usage.get(key, 0) + value

            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type")
                    if block_type == "thinking":
                        event.has_thinking = True
                    elif block_type == "tool_use":
                        tool_use_id = str(block.get("id") or "")
                        if not tool_use_id:
                            continue
                        event.tool_use_ids.append(tool_use_id)
                        tool_input = block.get("input")
                        transcript.tool_calls[tool_use_id] = ToolCall(
                            tool_use_id=tool_use_id,
                            name=str(block.get("name") or ""),
                            request_uuid=event.uuid,
                            request_line=line_no,
                            requested_at=high_water,
                            tool_input=tool_input if isinstance(tool_input, dict) else {},
                        )
                    elif block_type == "tool_result":
                        tool_use_id = str(block.get("tool_use_id") or "")
                        if not tool_use_id:
                            continue
                        event.tool_result_for = tool_use_id
                        call = transcript.tool_calls.get(tool_use_id)
                        if call is None:
                            # A result whose request is missing: the file starts
                            # mid-conversation. Keep it, flagged, rather than
                            # dropping evidence on the floor.
                            call = ToolCall(
                                tool_use_id=tool_use_id,
                                name="",
                                request_uuid="",
                                request_line=-1,
                                requested_at="",
                            )
                            transcript.tool_calls[tool_use_id] = call
                        call.result_uuid = event.uuid
                        call.result_line = line_no
                        call.completed_at = high_water
                        call.result_text = _block_text(block.get("content"))
                        call.status = "error" if _as_bool(block.get("is_error")) else "ok"

            transcript.events.append(event)

    if not transcript.session_id:
        transcript.session_id = path.stem
    return transcript


def iter_transcripts(directory: str | Path | None = None) -> Iterator[Transcript]:
    """Parse every transcript in a directory, oldest file first.

    Args:
        directory: Directory to scan. Defaults to :func:`default_transcript_dir`.

    Yields:
        One :class:`Transcript` per ``.jsonl`` file.
    """
    root = Path(directory) if directory is not None else default_transcript_dir()
    for path in sorted(root.glob("*.jsonl"), key=lambda item: item.stat().st_mtime):
        yield parse_transcript(path)


def tool_calls_by_name(transcript: Transcript, names: Sequence[str]) -> list[ToolCall]:
    """Return the transcript's calls to any of ``names``, in request order.

    Used to find where a number came from: a price read through ``vn_ohlcv`` is
    citable evidence, a number typed into prose is not.
    """
    wanted = {str(name) for name in names}
    matches = [call for call in transcript.tool_calls.values() if call.name in wanted]
    matches.sort(key=lambda call: call.request_line)
    return matches
