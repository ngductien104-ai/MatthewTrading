"""Command line entry point for the learning ledger.

Only the two commands a hook needs exist here. ``capture`` is what
``SessionEnd`` runs; ``scan`` is the catch-up for the sessions ``SessionEnd``
never fires for -- a killed terminal, a crash, a machine that slept. The
remaining verbs the plan lists (``resolve``, ``report``, ``retro``) wait for
the phases that give them something to do, because a subcommand that prints an
empty scorecard is worse than one that does not exist yet.

A hook that throws is a hook that gets deleted, so every failure here is caught,
written to ``~/.vibe-trading/hook.log`` with a timestamp, and reported through
the exit code -- never by raising into the harness.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Sequence

from src.learning.records import utc_now
from src.learning.session import capture_session, scan_transcripts, summarize
from src.learning.store import LearningStore, default_db_path


def log_path() -> Path:
    """Return the hook log, which lives beside the ledger."""
    return default_db_path().parent / "hook.log"


def _log(message: str) -> None:
    """Append one timestamped line to the hook log, failing silently.

    The log is the only place a hook failure is visible after the session has
    closed, so it is written before anything else can go wrong -- but a
    filesystem that refuses the write must not turn into a second failure.
    """
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{utc_now()} {message}\n")
    except OSError:
        pass


def _run_capture(raw: str) -> str:
    payload = json.loads(raw) if raw.strip() else {}
    if not isinstance(payload, dict):
        raise ValueError(f"hook payload must be a JSON object, got {type(payload).__name__}")
    with LearningStore(default_db_path()) as store:
        result = capture_session(payload, store)
    if result.skipped:
        return f"capture skipped: {result.skipped}"
    session = result.process.source_session_id if result.process else "?"
    state = "new" if result.append and result.append.appended else "unchanged"
    return (
        f"capture {session} {state} process_id={result.process.process_id} "
        f"tokens={result.process.tokens} rework={result.process.rework_count} "
        f"research_writes={len(result.research_paths)}"
    )


def _run_scan(directory: str | None) -> str:
    with LearningStore(default_db_path()) as store:
        results = list(scan_transcripts(store, directory))
    return "scan: " + summarize(results)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments, defaulting to ``sys.argv[1:]``.

    Returns:
        ``0`` on success, ``1`` on a handled failure. Never raises: the caller
        is a hook, and the exit code is how it reports.
    """
    parser = argparse.ArgumentParser(prog="src.learning.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capture", help="capture the session described by hook JSON on stdin")
    scan = sub.add_parser("scan", help="capture every transcript, filling in missed sessions")
    scan.add_argument("--dir", dest="directory", default=None, help="transcript directory")
    args = parser.parse_args(argv)

    try:
        if args.command == "capture":
            message = _run_capture(sys.stdin.read())
        else:
            message = _run_scan(args.directory)
    except Exception as exc:  # noqa: BLE001 - a hook must not raise into the harness
        _log(f"{args.command} FAILED {type(exc).__name__}: {exc}")
        _log(traceback.format_exc().strip().replace("\n", " | "))
        print(f"learning {args.command} failed: {exc}", file=sys.stderr)
        return 1

    _log(message)
    print(message)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the hook
    raise SystemExit(main())
