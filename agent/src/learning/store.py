"""Append-only SQLite ledger for the learning loop.

The disease this treats is specific. ``Home.md`` in the vault holds roughly
eighteen calls in a "latest view" column and is **overwritten** on every update,
the vault is not in git, and ``_mwg_research/`` has already lost its source
markdown. Every rewrite destroys a call permanently. So nothing here updates and
nothing here deletes -- not by convention, but by SQL trigger.

Two mechanisms carry that guarantee:

**Rows are appended, never edited.** Each table has a surrogate ``seq`` primary
key; a record's own id is a plain indexed column. Re-recording a call appends a
row and the highest ``seq`` wins, so the earlier version stays readable forever.
``BEFORE UPDATE`` and ``BEFORE DELETE`` triggers abort, which means a future
caller cannot quietly reintroduce the ``Home.md`` failure mode.

**Idempotency is by content, not by timing.** The unique index is
``(record_id, content_hash)``, so re-running a backfill over unchanged
transcripts inserts nothing, while a parser improvement that genuinely changes
the extracted content appends a new version of the same observation. This is why
``call_id`` deliberately excludes ``parser_version``.

The evidence gate is enforced on write: a call or outcome naming an
``evidence_id`` the ledger has never seen is rejected, and every piece of
evidence it does name is checked against the record's hindsight wall. Writing
the call first and the evidence later would leave the wall unchecked, so the
order is forced rather than trusted.

The ``goal`` store's ``_validate_completion_audit`` is deliberately *not* reused
here. It gates goal completion, which is a different question, and it proves
nothing about append-only storage.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence, TypeVar

from src.learning.records import (
    CallRecord,
    Evidence,
    Lesson,
    Outcome,
    ProcessRecord,
    RecordValidationError,
    assert_no_hindsight,
    latest_revision,
    sha256_text,
    utc_now,
)

SCHEMA_VERSION = 1

_DB_PATH_ENV = "VIBE_TRADING_LEARNING_DB_PATH"

_APPEND_ONLY_TABLES = ("evidence", "calls", "outcomes", "process_records", "lessons")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    kind TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source_session_id TEXT NOT NULL DEFAULT '',
    source_uuid TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL,
    written_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_identity
    ON evidence(evidence_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_evidence_id ON evidence(evidence_id, seq);

CREATE TABLE IF NOT EXISTS calls (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    ticker TEXT NOT NULL,
    as_of TEXT NOT NULL,
    action TEXT NOT NULL,
    known_at TEXT NOT NULL,
    extraction_status TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    source_session_id TEXT NOT NULL DEFAULT '',
    source_event_sha256 TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL,
    written_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_calls_identity ON calls(call_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_calls_id ON calls(call_id, seq);
CREATE INDEX IF NOT EXISTS idx_calls_episode ON calls(episode_id, revision);
CREATE INDEX IF NOT EXISTS idx_calls_ticker ON calls(ticker, as_of);

CREATE TABLE IF NOT EXISTS outcomes (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    outcome_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    episode_id TEXT NOT NULL DEFAULT '',
    checkpoint_sessions INTEGER NOT NULL,
    resolved_at TEXT NOT NULL,
    verdict TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload TEXT NOT NULL,
    written_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_outcomes_identity
    ON outcomes(outcome_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_outcomes_call ON outcomes(call_id, checkpoint_sessions, seq);

CREATE TABLE IF NOT EXISTS process_records (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    process_id TEXT NOT NULL,
    run_id TEXT NOT NULL DEFAULT '',
    source_session_id TEXT NOT NULL DEFAULT '',
    preset TEXT NOT NULL DEFAULT '',
    completed INTEGER NOT NULL DEFAULT 0,
    known_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload TEXT NOT NULL,
    written_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_process_identity
    ON process_records(process_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_process_id ON process_records(process_id, seq);

CREATE TABLE IF NOT EXISTS lessons (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT NOT NULL,
    expires_at TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL,
    payload TEXT NOT NULL,
    written_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_lessons_identity
    ON lessons(lesson_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_lessons_domain ON lessons(domain, status, seq);

CREATE TABLE IF NOT EXISTS ledger_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    action TEXT NOT NULL,
    written_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_record ON ledger_audit(table_name, record_id);
"""


class LedgerError(RuntimeError):
    """The ledger refused a write or cannot be opened safely."""


F = TypeVar("F", bound=Callable)


def _synchronized(method: F) -> F:
    """Serialize access to the shared SQLite connection."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


def default_db_path() -> Path:
    """Return the configured learning ledger path.

    Returns:
        Env override when ``VIBE_TRADING_LEARNING_DB_PATH`` is set, otherwise
        ``~/.vibe-trading/learning.db``.
    """
    override = os.environ.get(_DB_PATH_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".vibe-trading" / "learning.db"


def content_hash(payload: dict[str, Any]) -> str:
    """Hash a record payload canonically, so equal content hashes equally."""
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str))


@dataclass
class AppendResult:
    """Outcome of an append.

    Attributes:
        record_id: Identifier of the record written or recognised.
        content_hash: Hash of the payload.
        appended: ``False`` when the exact content was already on the ledger.
        version: How many versions of this record now exist.
    """

    record_id: str
    content_hash: str
    appended: bool
    version: int


class LearningStore:
    """Append-only ledger for calls, outcomes, process records and lessons."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        """Open or create the ledger.

        Args:
            db_path: Database path. Defaults to :func:`default_db_path`.

        Raises:
            LedgerError: The file was written by a newer schema. Refusing to
                open is safer than writing rows a newer reader will misread.
        """
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._lock = threading.RLock()
        self._migrate()

    # -- schema ---------------------------------------------------------------

    @_synchronized
    def _migrate(self) -> None:
        found = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
        if found > SCHEMA_VERSION:
            raise LedgerError(
                f"{self.db_path} is at schema {found}, this build understands "
                f"{SCHEMA_VERSION}. Refusing to open rather than write rows a newer "
                "reader would misinterpret."
            )
        self._conn.executescript(_SCHEMA)
        self._install_append_only_triggers()
        if found < SCHEMA_VERSION:
            self._conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self._conn.commit()

    def _install_append_only_triggers(self) -> None:
        for table in _APPEND_ONLY_TABLES:
            for verb in ("UPDATE", "DELETE"):
                self._conn.execute(
                    f"CREATE TRIGGER IF NOT EXISTS {table}_no_{verb.lower()} "
                    f"BEFORE {verb} ON {table} BEGIN "
                    f"SELECT RAISE(ABORT, '{table} is append-only'); END"
                )

    @property
    def schema_version(self) -> int:
        """Return the schema version stamped on this database."""
        with self._lock:
            return int(self._conn.execute("PRAGMA user_version").fetchone()[0])

    def close(self) -> None:
        """Close the underlying connection."""
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "LearningStore":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- generic append -------------------------------------------------------

    def _append(
        self, table: str, record_id_column: str, record_id: str, columns: dict[str, Any],
        payload: dict[str, Any],
    ) -> AppendResult:
        digest = content_hash(payload)
        now = utc_now()
        row = {
            record_id_column: record_id,
            **columns,
            "content_hash": digest,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
            "written_at": now,
        }
        names = ", ".join(row)
        placeholders = ", ".join(f":{name}" for name in row)
        cursor = self._conn.execute(
            f"INSERT OR IGNORE INTO {table} ({names}) VALUES ({placeholders})", row
        )
        appended = cursor.rowcount > 0
        self._conn.execute(
            "INSERT INTO ledger_audit (table_name, record_id, content_hash, action, written_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (table, record_id, digest, "append" if appended else "duplicate_ignored", now),
        )
        version = int(
            self._conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {record_id_column} = ?", (record_id,)
            ).fetchone()[0]
        )
        self._conn.commit()
        return AppendResult(
            record_id=record_id, content_hash=digest, appended=appended, version=version
        )

    def _latest_payload(self, table: str, column: str, record_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            f"SELECT payload FROM {table} WHERE {column} = ? ORDER BY seq DESC LIMIT 1",
            (record_id,),
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    # -- evidence -------------------------------------------------------------

    @_synchronized
    def append_evidence(self, evidence: Evidence) -> AppendResult:
        """Record a piece of evidence. Must happen before anything cites it."""
        payload = evidence.to_dict()
        return self._append(
            "evidence",
            "evidence_id",
            evidence.evidence_id,
            {
                "kind": evidence.kind,
                "observed_at": evidence.observed_at,
                "source_session_id": evidence.source_session_id,
                "source_uuid": evidence.source_uuid,
            },
            payload,
        )

    @_synchronized
    def get_evidence(self, evidence_id: str) -> Evidence | None:
        """Return the latest version of one piece of evidence."""
        payload = self._latest_payload("evidence", "evidence_id", evidence_id)
        return Evidence.from_dict(payload) if payload else None

    def _require_evidence(self, evidence_ids: Sequence[str], wall: str, what: str) -> None:
        """Load cited evidence and check it against the hindsight wall.

        Raises:
            LedgerError: An id is unknown to the ledger. Accepting it would let
                a citation point at nothing, which is indistinguishable from an
                invented one.
            HindsightViolation: Cited evidence postdates the wall.
        """
        found: list[Evidence] = []
        missing: list[str] = []
        for evidence_id in evidence_ids:
            payload = self._latest_payload("evidence", "evidence_id", evidence_id)
            if payload is None:
                missing.append(evidence_id)
            else:
                found.append(Evidence.from_dict(payload))
        if missing:
            raise LedgerError(
                f"{what} cites evidence the ledger has never seen: {', '.join(missing)}. "
                "Append the evidence first; a citation that points at nothing cannot "
                "be told apart from an invented one."
            )
        assert_no_hindsight(wall, found)

    # -- calls ----------------------------------------------------------------

    @_synchronized
    def append_call(self, record: CallRecord) -> AppendResult:
        """Append one revision of a call.

        Re-appending identical content is a no-op, so a backfill can be re-run
        over unchanged transcripts safely. Changed content appends a new version
        and leaves the previous one readable.

        Raises:
            LedgerError: Cited evidence is unknown to the ledger.
            HindsightViolation: Cited evidence postdates ``known_at``.
        """
        self._require_evidence(record.evidence_ids, record.known_at, f"call {record.call_id}")
        return self._append(
            "calls",
            "call_id",
            record.call_id,
            {
                "episode_id": record.episode_id,
                "revision": record.revision,
                "ticker": record.ticker,
                "as_of": record.as_of,
                "action": record.action,
                "known_at": record.known_at,
                "extraction_status": record.extraction_status,
                "parser_version": record.parser_version,
                "source_session_id": record.source_session_id,
                "source_event_sha256": record.source_event_sha256,
            },
            record.to_dict(),
        )

    @_synchronized
    def get_call(self, call_id: str) -> CallRecord | None:
        """Return the current version of a call."""
        payload = self._latest_payload("calls", "call_id", call_id)
        return CallRecord.from_dict(payload) if payload else None

    @_synchronized
    def call_history(self, call_id: str) -> list[CallRecord]:
        """Return every stored version of a call, oldest first.

        This is what ``Home.md`` could never answer.
        """
        rows = self._conn.execute(
            "SELECT payload FROM calls WHERE call_id = ? ORDER BY seq ASC", (call_id,)
        ).fetchall()
        return [CallRecord.from_dict(json.loads(row["payload"])) for row in rows]

    @_synchronized
    def episode_revisions(self, episode_id: str) -> list[CallRecord]:
        """Return the current version of each revision in an episode."""
        rows = self._conn.execute(
            "SELECT call_id FROM calls WHERE episode_id = ? GROUP BY call_id "
            "ORDER BY MIN(revision), MIN(seq)",
            (episode_id,),
        ).fetchall()
        records = []
        for row in rows:
            payload = self._latest_payload("calls", "call_id", row["call_id"])
            if payload:
                records.append(CallRecord.from_dict(payload))
        return records

    def scoring_point(self, episode_id: str, cutoff: str | None = None) -> CallRecord | None:
        """Return the revision an episode should be scored on.

        Args:
            episode_id: Episode to resolve.
            cutoff: Optional instant; revisions known after it are ignored.

        Returns:
            The last revision in force, or ``None`` when the episode is empty.
        """
        return latest_revision(self.episode_revisions(episode_id), cutoff=cutoff)

    @_synchronized
    def list_calls(self, ticker: str | None = None, since: str | None = None) -> list[CallRecord]:
        """Return current versions of calls, oldest ``as_of`` first."""
        clauses, params = [], []
        if ticker:
            clauses.append("ticker = ?")
            params.append(ticker.upper())
        if since:
            clauses.append("as_of >= ?")
            params.append(since)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT call_id FROM calls {where} GROUP BY call_id ORDER BY MIN(as_of), MIN(seq)",
            params,
        ).fetchall()
        records = []
        for row in rows:
            payload = self._latest_payload("calls", "call_id", row["call_id"])
            if payload:
                records.append(CallRecord.from_dict(payload))
        return records

    # -- outcomes -------------------------------------------------------------

    @_synchronized
    def append_outcome(self, outcome: Outcome) -> AppendResult:
        """Append a scored outcome.

        Raises:
            LedgerError: The call is unknown, or cited evidence is unknown.
            HindsightViolation: Cited evidence postdates ``resolved_at``.
        """
        if self._latest_payload("calls", "call_id", outcome.call_id) is None:
            raise LedgerError(
                f"outcome scores call {outcome.call_id}, which is not on the ledger"
            )
        self._require_evidence(
            outcome.evidence_ids,
            f"{outcome.resolved_at}T23:59:59Z",
            f"outcome {outcome.outcome_id}",
        )
        return self._append(
            "outcomes",
            "outcome_id",
            outcome.outcome_id,
            {
                "call_id": outcome.call_id,
                "episode_id": outcome.episode_id,
                "checkpoint_sessions": outcome.checkpoint_sessions,
                "resolved_at": outcome.resolved_at,
                "verdict": outcome.verdict,
            },
            outcome.to_dict(),
        )

    @_synchronized
    def outcomes_for(self, call_id: str) -> list[Outcome]:
        """Return the current outcome at each checkpoint for one call."""
        rows = self._conn.execute(
            "SELECT outcome_id FROM outcomes WHERE call_id = ? GROUP BY outcome_id "
            "ORDER BY MIN(checkpoint_sessions)",
            (call_id,),
        ).fetchall()
        results = []
        for row in rows:
            payload = self._latest_payload("outcomes", "outcome_id", row["outcome_id"])
            if payload:
                results.append(Outcome.from_dict(payload))
        return results

    # -- process records and lessons -----------------------------------------

    @_synchronized
    def append_process(self, record: ProcessRecord) -> AppendResult:
        """Append a process record."""
        return self._append(
            "process_records",
            "process_id",
            record.process_id,
            {
                "run_id": record.run_id,
                "source_session_id": record.source_session_id,
                "preset": record.preset,
                "completed": int(record.completed),
                "known_at": record.known_at,
            },
            record.to_dict(),
        )

    @_synchronized
    def get_process(self, process_id: str) -> ProcessRecord | None:
        """Return the current version of a process record."""
        payload = self._latest_payload("process_records", "process_id", process_id)
        return ProcessRecord.from_dict(payload) if payload else None

    @_synchronized
    def process_for_session(self, session_id: str) -> ProcessRecord | None:
        """Return the current process record for a Claude Code session.

        The capture path needs this to avoid un-knowing things: a catch-up scan
        cannot say whether a session ended cleanly, so it must not overwrite a
        ``completed`` flag the session-end hook already set.
        """
        row = self._conn.execute(
            "SELECT process_id FROM process_records WHERE source_session_id = ? "
            "ORDER BY seq DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        return self.get_process(row["process_id"]) if row else None

    @_synchronized
    def append_lesson(self, lesson: Lesson) -> AppendResult:
        """Append a playbook lesson."""
        return self._append(
            "lessons",
            "lesson_id",
            lesson.lesson_id,
            {
                "domain": lesson.domain,
                "status": lesson.status,
                "expires_at": lesson.expires_at,
            },
            lesson.to_dict(),
        )

    @_synchronized
    def live_lessons(self, domain: str | None = None, as_of: str | None = None) -> list[Lesson]:
        """Return lessons that are neither retired nor expired.

        Args:
            domain: Restrict to one playbook domain.
            as_of: Date to test expiry against. Defaults to today.
        """
        where = "WHERE domain = ?" if domain else ""
        params = [domain] if domain else []
        rows = self._conn.execute(
            f"SELECT lesson_id FROM lessons {where} GROUP BY lesson_id ORDER BY MIN(seq)", params
        ).fetchall()
        live = []
        for row in rows:
            payload = self._latest_payload("lessons", "lesson_id", row["lesson_id"])
            if not payload:
                continue
            lesson = Lesson.from_dict(payload)
            if lesson.status != "retired" and not lesson.is_expired(as_of):
                live.append(lesson)
        return live

    # -- audit ----------------------------------------------------------------

    @_synchronized
    def audit_trail(self, record_id: str | None = None) -> list[dict[str, Any]]:
        """Return the write log, oldest first.

        Duplicate appends are logged too, so a re-run of a backfill is visible
        as work that happened and changed nothing.
        """
        if record_id:
            rows = self._conn.execute(
                "SELECT * FROM ledger_audit WHERE record_id = ? ORDER BY audit_id", (record_id,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM ledger_audit ORDER BY audit_id").fetchall()
        return [dict(row) for row in rows]

    @_synchronized
    def counts(self) -> dict[str, int]:
        """Return the number of distinct records held in each table."""
        columns = {
            "evidence": "evidence_id",
            "calls": "call_id",
            "outcomes": "outcome_id",
            "process_records": "process_id",
            "lessons": "lesson_id",
        }
        return {
            table: int(
                self._conn.execute(
                    f"SELECT COUNT(DISTINCT {column}) FROM {table}"
                ).fetchone()[0]
            )
            for table, column in columns.items()
        }


def append_call_with_evidence(
    store: LearningStore, record: CallRecord, evidences: Iterable[Evidence]
) -> AppendResult:
    """Append evidence then the call that cites it, in the required order.

    Raises:
        RecordValidationError: The call cites evidence not supplied here.
    """
    supplied = {item.evidence_id: item for item in evidences}
    unknown = [item for item in record.evidence_ids if item not in supplied]
    if unknown:
        raise RecordValidationError(
            f"call {record.call_id} cites evidence that was not supplied: {', '.join(unknown)}"
        )
    for evidence in supplied.values():
        store.append_evidence(evidence)
    return store.append_call(record)
