"""Command line entry point for the learning ledger.

Four verbs, in two pairs.

``capture`` is what the ``SessionEnd`` hook runs; ``scan`` is the catch-up for
the sessions ``SessionEnd`` never fires for -- a killed terminal, a crash, a
machine that slept. Neither needs a model.

``prompt`` and ``extract`` are the two halves of the call backfill, split
deliberately. ``prompt`` prints the contract plus one document; whatever plays
the extractor answers with JSON; ``extract`` reads that answer back from a file
and stores only what the validator can verify. Keeping the reply on disk is the
difference between a backfill and a one-off: the same input can be re-run
against an improved parser, and the store recognises it as the same
observation rather than a second one.

The verbs the plan also lists (``resolve``, ``report``, ``retro``) wait for the
phases that give them something to do, because a subcommand that prints an
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

from src.learning.extract import (
    assign_revisions,
    build_prompt,
    extract_document,
    load_document,
    store_result,
)
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


def _run_prompt(doc: str) -> str:
    return build_prompt(load_document(doc))


def _run_extract(doc: str, reply: str) -> str:
    """Validate a recorded extraction reply and store what survives.

    The reply is read from a file rather than taken on the command line so the
    exact text a model produced stays on disk. A backfill nobody can re-run
    against the same input is not a backfill, it is a one-off.
    """
    document = load_document(doc)
    text = Path(reply).read_text(encoding="utf-8")
    result = extract_document(document, lambda _prompt: text)
    result.calls = assign_revisions(result.calls)
    with LearningStore(default_db_path()) as store:
        store_result(store, result)
    refused = ", ".join(f"{item.code}" for item in result.rejections) or "none"
    tickers = ", ".join(sorted({record.ticker for record in result.calls})) or "-"
    return (
        f"extract {document.path}: {len(result.calls)} call(s) [{tickers}], "
        f"{len(result.evidence)} evidence, refused: {refused}"
    )


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
    prompt = sub.add_parser("prompt", help="print the extraction prompt for one document")
    prompt.add_argument("--doc", required=True, help="document to extract calls from")
    extract = sub.add_parser("extract", help="validate a recorded reply and store the calls")
    extract.add_argument("--doc", required=True, help="document the reply was produced from")
    extract.add_argument("--reply", required=True, help="file holding the model's JSON reply")
    args = parser.parse_args(argv)

    try:
        if args.command == "capture":
            message = _run_capture(sys.stdin.read())
        elif args.command == "scan":
            message = _run_scan(args.directory)
        elif args.command == "prompt":
            print(_run_prompt(args.doc))
            return 0
        else:
            message = _run_extract(args.doc, args.reply)
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
