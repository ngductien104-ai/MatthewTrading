"""Capture what a Claude Code session did, without anyone remembering to ask.

Every write path this repository had before was voluntary, and after sixteen
sessions the learning store held nothing at all. So this module is built to run
from a hook, and the hook is the part that must not be trusted:
``SessionEnd`` fires on ``clear``, ``resume``, ``logout`` and
``prompt_input_exit`` -- but not when the terminal is killed, the machine
sleeps, or the process crashes. A capture that only works when the hook fires
would recreate the same hole in a new place.

Two properties make the missed sessions harmless:

* **Everything captured here is derived, never asserted.** Token counts, wall
  time and rework come out of the transcript itself, so no model has to be
  running and nothing needs a provider that currently has no balance.
* **A capture is idempotent by content.** ``process_id`` is seeded from the
  session's *first* event, so re-running over the same transcript lands on the
  same record; ``known_at`` is the session's last observed instant rather than
  "now", so an unchanged transcript hashes to the payload already stored and
  the ledger records ``duplicate_ignored`` instead of inventing a second
  observation of one session.

Those two together mean :func:`scan_transcripts` can be run at any time -- at
session start, from cron, by hand -- and will fill in whatever the hook missed
without duplicating what it caught.

What is deliberately *not* captured here: ``errors_caught``, ``rounds`` and
``data_violations``. Those need a reader that can tell a caught mistake from an
ordinary correction, every entry needs a citation to survive
:class:`~src.learning.records.ProcessRecord`'s evidence gate, and inventing
them from tool counts would be exactly the fabrication the ledger exists to
prevent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

from src.learning.records import ProcessRecord, parse_timestamp
from src.learning.store import AppendResult, LearningStore
from src.learning.transcript import Transcript, iter_transcripts, parse_transcript

#: Tools that write a file. ``MultiEdit`` is included because older transcripts
#: still carry it.
_WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")

#: Where a research artifact lives. One ``_xxx_research/`` folder is one
#: episode, which is why the folder prefix is what identifies it.
_RESEARCH_PREFIX = "_"


@dataclass
class CaptureResult:
    """What one capture produced.

    Attributes:
        process: The record built, or ``None`` when nothing could be captured.
        append: Ledger outcome; ``appended`` is ``False`` for a re-run over an
            unchanged transcript.
        research_paths: Research files this session wrote, in path order. Kept
            for the extraction pass, which needs a model and therefore does not
            run inside a hook.
        skipped: Why nothing was captured, empty on success.
    """

    process: ProcessRecord | None = None
    append: AppendResult | None = None
    research_paths: list[str] = field(default_factory=list)
    skipped: str = ""


def _is_research_path(path: str) -> bool:
    """Return whether a written path sits inside a research folder."""
    parts = Path(str(path).replace("\\", "/")).parts
    return any(part.startswith(_RESEARCH_PREFIX) and part != "_" for part in parts)


def research_writes(transcript: Transcript) -> list[str]:
    """Return the research files a session wrote, deduplicated.

    Args:
        transcript: Parsed session.

    Returns:
        Sorted unique paths under a ``_*`` folder that the session wrote to.
    """
    paths: set[str] = set()
    for call in transcript.tool_calls.values():
        if call.name not in _WRITE_TOOLS:
            continue
        for key in ("file_path", "notebook_path", "path"):
            value = call.tool_input.get(key)
            if isinstance(value, str) and value and _is_research_path(value):
                paths.add(value)
    return sorted(paths)


def rework_count(transcript: Transcript) -> int:
    """Return how many research writes were rewrites of a file already written.

    This is the only honest proxy the transcript offers for "a conclusion was
    rewritten": the first write to a file is the work, every later write to the
    same file is rework. It counts writes, not quality, and is named for what
    it measures.
    """
    seen: set[str] = set()
    rewrites = 0
    for call in sorted(transcript.tool_calls.values(), key=lambda item: item.request_line):
        if call.name not in _WRITE_TOOLS:
            continue
        for key in ("file_path", "notebook_path", "path"):
            value = call.tool_input.get(key)
            if not (isinstance(value, str) and value and _is_research_path(value)):
                continue
            if value in seen:
                rewrites += 1
            seen.add(value)
            break
    return rewrites


def _wall_time_sec(transcript: Transcript) -> float:
    """Return the session's span, measured on the monotonic clock.

    ``observed_at`` is used rather than the raw timestamps because those run
    backwards -- thirty-six times across the corpus, three of them by about two
    minutes -- and a negative duration would be recorded as fact.
    """
    if not transcript.events:
        return 0.0
    first = parse_timestamp(transcript.first_observed_at, "first_observed_at")
    last = parse_timestamp(transcript.last_observed_at, "last_observed_at")
    return max((last - first).total_seconds(), 0.0)


def build_process_record(transcript: Transcript, *, completed: bool = False) -> ProcessRecord:
    """Derive a process record from a parsed transcript.

    Args:
        transcript: The session to describe.
        completed: Whether the session ended in a way the harness reported.
            ``False`` for a catch-up scan, where nobody can say how it ended.

    Returns:
        A record whose every field was computed from the transcript.

    Raises:
        ValueError: The transcript has no events, so there is nothing to say
            about it.
    """
    if not transcript.events:
        raise ValueError(f"{transcript.path} has no content events")

    root = transcript.events[0]
    usage = transcript.usage
    return ProcessRecord(
        source_session_id=transcript.session_id,
        source_uuid=root.uuid,
        source_event_sha256=root.sha256,
        tokens=sum(int(value) for value in usage.values()),
        token_usage={str(k): int(v) for k, v in usage.items()},
        wall_time_sec=_wall_time_sec(transcript),
        rework_count=rework_count(transcript),
        completed=completed,
        known_at=transcript.last_observed_at,
    )


def _append_capture(
    transcript: Transcript, store: LearningStore, *, completed: bool
) -> CaptureResult:
    """Build and append one session's record, never un-knowing what is stored.

    ``completed`` only ever goes from false to true. A catch-up scan cannot tell
    how a session ended, so without this a scan following a hook would rewrite
    ``completed`` back to false, the payload would differ, and the ledger would
    grow a new version on every run -- one observation flip-flopping forever.
    """
    stored = store.process_for_session(transcript.session_id)
    record = build_process_record(
        transcript, completed=completed or bool(stored and stored.completed)
    )
    return CaptureResult(
        process=record,
        append=store.append_process(record),
        research_paths=research_writes(transcript),
    )


def capture_transcript(
    path: str | Path, store: LearningStore, *, completed: bool = False
) -> CaptureResult:
    """Parse one transcript and append its process record to the ledger.

    Args:
        path: Transcript file.
        store: Open ledger.
        completed: Whether the harness reported how the session ended.

    Returns:
        The capture, with ``skipped`` set when the transcript could not be used.
    """
    source = Path(path)
    if not source.exists():
        return CaptureResult(skipped=f"transcript not found: {source}")
    transcript = parse_transcript(source)
    if not transcript.events:
        return CaptureResult(skipped=f"transcript has no content events: {source}")
    return _append_capture(transcript, store, completed=completed)


def capture_session(payload: dict[str, Any], store: LearningStore) -> CaptureResult:
    """Capture the session a ``SessionEnd`` hook was fired for.

    Args:
        payload: The hook's JSON input. Only ``transcript_path`` and ``reason``
            are read; everything else is derived from the transcript, so a
            change in the hook contract cannot corrupt a record.
        store: Open ledger.

    Returns:
        The capture. A missing ``transcript_path`` is reported through
        ``skipped`` rather than raised, because a hook that throws is a hook
        that gets removed.
    """
    transcript_path = str(payload.get("transcript_path") or "").strip()
    if not transcript_path:
        return CaptureResult(skipped="hook payload carried no transcript_path")
    return capture_transcript(
        transcript_path, store, completed=bool(str(payload.get("reason") or "").strip())
    )


def scan_transcripts(
    store: LearningStore, directory: str | Path | None = None
) -> Iterator[CaptureResult]:
    """Capture every transcript on disk, filling in what the hook missed.

    ``SessionEnd`` does not fire when the terminal is killed or the process
    crashes, so this is what keeps those sessions from being lost. It is safe to
    run repeatedly: an unchanged transcript produces the payload already stored
    and is ignored by the ledger.

    Args:
        store: Open ledger.
        directory: Transcript directory; the configured default when omitted.

    Yields:
        One :class:`CaptureResult` per transcript, in the order they are read.
    """
    for transcript in iter_transcripts(directory):
        if not transcript.events:
            yield CaptureResult(skipped=f"transcript has no content events: {transcript.path}")
            continue
        yield _append_capture(transcript, store, completed=False)


def summarize(results: Iterable[CaptureResult]) -> str:
    """Return a one-line summary of a capture run, for the hook log."""
    captured = appended = skipped = 0
    for result in results:
        if result.skipped:
            skipped += 1
            continue
        captured += 1
        if result.append and result.append.appended:
            appended += 1
    return (
        f"captured {captured} session(s), {appended} new version(s), {skipped} skipped"
    )
