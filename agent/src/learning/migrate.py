"""Rebuild the ledger when a rule that derives its identifiers changes.

``call_id_for`` promises that re-parsing the same source event lands on the same
``call_id``, so an improved parser produces a *revision* of an observation
rather than a second one. Keeping that promise means the id rules occasionally
have to change -- and the rows already written under the old rule then carry
identifiers the current code would never produce again.

They cannot be edited where they lie. Every table in this ledger is append-only,
enforced by ``BEFORE UPDATE`` and ``BEFORE DELETE`` triggers rather than by
convention, and that is a property worth more than the convenience of an
in-place fix. So a migration is a **rebuild**: read every row of the old file in
the order it was written, derive each identifier again, and write it into a new
one. The old file is left exactly as it was, which is also the rollback.

Two decisions in here are not obvious:

**It writes through ``LearningStore``, not with SQL.** Copying payloads straight
across would be faster and would preserve rows that the current gates would now
refuse -- which is precisely what we do not want to happen silently. Every row
goes back through the same validation any new row faces, and anything refused is
reported instead of dropped.

**It copies every revision, not the latest.** ``SELECT count(*) FROM outcomes``
returns 45 for 15 outcomes here, because a re-scored outcome is appended rather
than overwritten. Collapsing that history to current values would erase the one
thing an append-only ledger is for.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from src.learning.extract import episode_key_for_path
from src.learning.records import (
    CallRecord,
    Evidence,
    Lesson,
    Outcome,
    ProcessRecord,
    episode_id_for,
)
from src.learning.store import LearningStore

#: Written in this order because ``append_call`` refuses a call whose evidence
#: the ledger has not seen yet, and ``append_outcome`` refuses one whose call is
#: unknown. The order is a constraint, not a preference.
TABLE_ORDER = ("evidence", "calls", "outcomes", "lessons", "process_records")


@dataclass
class MigrationReport:
    """What a rebuild moved, changed, collapsed, and refused."""

    rows: dict[str, int] = field(default_factory=dict)
    remapped_calls: dict[str, str] = field(default_factory=dict)
    remapped_episodes: dict[str, str] = field(default_factory=dict)
    collapsed: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """One line per table, then what changed identity, collapsed, or failed."""
        counts = " · ".join(f"{name}={self.rows.get(name, 0)}" for name in TABLE_ORDER)
        lines = [counts, f"calls with a new id: {len(self.remapped_calls)}"]
        for old, new in sorted(self.remapped_calls.items()):
            lines.append(f"  {old} -> {new}")
        if self.collapsed:
            lines.append(
                f"collapsed as identical content: {len(self.collapsed)} "
                "(two serializations of one record, not a lost revision)"
            )
            lines.extend(f"  {label}" for label in self.collapsed)
        if self.refused:
            lines.append(f"refused: {len(self.refused)}")
            lines.extend(f"  {reason}" for reason in self.refused)
        return "\n".join(lines)


def _read_payloads(source: Path, table: str) -> Iterator[dict[str, Any]]:
    """Yield every stored payload of one table, oldest first.

    Opened read-only: a migration that can write to the file it is reading is a
    migration that can lose the rollback.
    """
    conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        for row in conn.execute(f"SELECT payload FROM {table} ORDER BY seq"):
            yield json.loads(row[0])
    finally:
        conn.close()


def recomputed_call(payload: dict[str, Any]) -> CallRecord:
    """Return the call this payload describes, with its identifiers re-derived.

    A call read out of a document keeps its episode from the container it was
    found in -- a research folder, or a swarm run -- and no longer from the
    thesis sentence the model wrote, which was never the same twice. A call read
    out of a transcript is left alone: one interactive session genuinely can
    hold two arguments about one ticker, and there the thesis is what tells them
    apart.
    """
    data = dict(payload)
    if data.get("source_session_id"):
        return CallRecord.from_dict(data)
    key = episode_key_for_path(str(data.get("source_path") or ""))
    data["episode_id"] = episode_id_for(key, str(data.get("ticker") or ""), "")
    data["call_id"] = ""
    return CallRecord.from_dict(data)


def rebuild_ledger(source: Path | str, target: Path | str) -> MigrationReport:
    """Copy one ledger into a new file, re-deriving every identifier.

    Args:
        source: Existing ledger. Opened read-only and never modified.
        target: Path to create. Must not already exist -- writing into a ledger
            that already holds rows would mix two histories.

    Returns:
        What moved, what changed identity, and what the current gates refused.

    Raises:
        FileNotFoundError: The source does not exist.
        FileExistsError: The target does.
    """
    source, target = Path(source), Path(target)
    if not source.exists():
        raise FileNotFoundError(source)
    if target.exists():
        raise FileExistsError(target)

    report = MigrationReport()

    def book(table: str, result: Any, label: str) -> None:
        """Count one row, and say so when the store recognised it as a duplicate.

        A rebuild that changes a row count without saying why is indistinguishable
        from a rebuild that lost something. This ledger really does hold rows that
        differ only in serialization -- one ``ProcessRecord`` predates
        ``token_usage`` and stores ``None`` where the field now normalises to
        ``{}`` -- and the append-only uniqueness on ``(id, content_hash)``
        collapses them. That is correct, and it is reported rather than left for
        somebody to discover by subtracting two numbers.
        """
        report.rows[table] = report.rows.get(table, 0) + 1
        if not result.appended:
            report.collapsed.append(f"{table} {label}")

    with LearningStore(target) as store:
        for payload in _read_payloads(source, "evidence"):
            record = Evidence.from_dict(payload)
            book("evidence", store.append_evidence(record), record.evidence_id)

        for payload in _read_payloads(source, "calls"):
            record = recomputed_call(payload)
            was = str(payload.get("call_id") or "")
            if was and was != record.call_id:
                report.remapped_calls[was] = record.call_id
                report.remapped_episodes[str(payload["episode_id"])] = record.episode_id
            try:
                result = store.append_call(record)
            except Exception as exc:  # refused by a gate, and worth reporting
                report.refused.append(f"call {was or record.call_id}: {exc}")
                continue
            book("calls", result, record.call_id)

        for payload in _read_payloads(source, "outcomes"):
            data = dict(payload)
            data["call_id"] = report.remapped_calls.get(data["call_id"], data["call_id"])
            data["episode_id"] = report.remapped_episodes.get(
                data.get("episode_id", ""), data.get("episode_id", "")
            )
            outcome = Outcome.from_dict(data)
            try:
                result = store.append_outcome(outcome)
            except Exception as exc:
                report.refused.append(f"outcome {outcome.outcome_id}: {exc}")
                continue
            book("outcomes", result, outcome.outcome_id)

        for payload in _read_payloads(source, "lessons"):
            lesson = Lesson.from_dict(payload)
            book("lessons", store.append_lesson(lesson), lesson.lesson_id)

        for payload in _read_payloads(source, "process_records"):
            process = ProcessRecord.from_dict(payload)
            book("process_records", store.append_process(process), process.process_id)

    return report


def install(rebuilt: Path | str, live: Path | str) -> Path:
    """Put a rebuilt ledger in place of the live one, keeping the old as backup.

    Args:
        rebuilt: Ledger produced by :func:`rebuild_ledger`.
        live: Path it should take over.

    Returns:
        Where the previous ledger was moved to. That file is the rollback: put
        it back and the old identifiers are current again.

    The sidecars move with the file they belong to. A ``-wal`` left behind from
    the replaced database would be applied to the new one on its next open,
    which is a corrupt ledger arrived at by tidy-looking steps.
    """
    rebuilt, live = Path(rebuilt), Path(live)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    backup = Path(f"{live}.bak-{stamp}")
    for suffix in ("", "-wal", "-shm"):
        existing = Path(f"{live}{suffix}")
        if existing.exists():
            existing.rename(f"{backup}{suffix}")
    for suffix in ("", "-wal", "-shm"):
        produced = Path(f"{rebuilt}{suffix}")
        if produced.exists():
            produced.rename(f"{live}{suffix}")
    return backup


def main(argv: list[str] | None = None) -> int:
    """Rebuild a ledger from the command line.

    Deliberately not a subcommand of ``src.learning.cli``: that surface is for
    things the loop does routinely, and a rebuild happens when an id rule
    changes. It still needs to be runnable rather than retyped, because a
    migration nobody can re-run is the same problem as a backfill nobody can
    re-run.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="src.learning.migrate", description=__doc__)
    parser.add_argument("--source", default="", help="ledger to read; default is the live one")
    parser.add_argument("--target", default="", help="file to write; default is <source>.rebuilt")
    parser.add_argument(
        "--install",
        action="store_true",
        help="put the rebuilt ledger in place, keeping the old one as .bak-<stamp>",
    )
    args = parser.parse_args(argv)

    from src.learning.store import default_db_path

    source = Path(args.source) if args.source else default_db_path()
    target = Path(args.target) if args.target else Path(f"{source}.rebuilt")
    report = rebuild_ledger(source, target)
    print(report.summary())
    if report.refused:
        print("\nnothing installed: the rebuild refused rows, so the two ledgers disagree")
        return 1
    if args.install:
        backup = install(target, source)
        print(f"\ninstalled {target.name} as {source.name}; previous ledger at {backup.name}")
    else:
        print(f"\nrebuilt at {target} (not installed; pass --install to swap it in)")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by hand
    raise SystemExit(main())


__all__ = [
    "TABLE_ORDER",
    "MigrationReport",
    "install",
    "main",
    "rebuild_ledger",
    "recomputed_call",
]
