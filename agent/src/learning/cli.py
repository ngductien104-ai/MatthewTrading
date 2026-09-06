"""Command line entry point for the learning ledger.

Six verbs: two pairs and two singles.

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

``resolve`` needs no model at all, only DataPro, and it is the verb that turns
a ledger of opinions into a ledger of results. It refuses to run on the
sponsored fallback, so a day when DataPro is down produces an error rather than
a scorecard nobody can reproduce.

``report`` reads the ledger back and needs nothing at all -- no model, no
network -- because everything it prints was written to the evidence when the
outcome was scored. It cannot therefore disagree with the numbers the resolver
stood behind.

The verb the plan also lists (``retro``) waits for the phase that gives it
something to do, because a subcommand that prints an empty playbook is worse
than one that does not exist yet.

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
    episode_key_for_path,
    extract_document,
    iter_research_documents,
    load_document,
    overridden_actions,
    store_result,
)
from src.learning.records import CHECKPOINT_SESSIONS, utc_now
from src.learning.report import build_scorecard
from src.learning.process_score import cost_per_conclusion, render_cost_surface
from src.learning.resolve import resolve_ledger
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


def _run_extract(doc: str, reply: str = "", proposer: str = "") -> str:
    """Extract the calls in one document and store what survives.

    A recorded reply stays supported and stays the reproducible path: the exact
    text a model produced is on disk, and a backfill nobody can re-run against
    the same input is not a backfill, it is a one-off. Asking a live proposer
    honours the same rule by writing its reply out before returning it, so both
    paths leave the same trail.
    """
    document = load_document(doc)
    if reply:
        text = Path(reply).read_text(encoding="utf-8")
        propose = lambda _prompt: text  # noqa: E731 - the recorded path
    else:
        from src.learning.propose import configured_proposer

        propose = configured_proposer(proposer)
    result = extract_document(document, propose)
    result.calls = assign_revisions(result.calls)
    with LearningStore(default_db_path()) as store:
        overrides = overridden_actions(store, result.calls)
        store_result(store, result)
    refused = ", ".join(f"{item.code}" for item in result.rejections) or "none"
    tickers = ", ".join(sorted({record.ticker for record in result.calls})) or "-"
    lines = [
        f"extract {document.path}: {len(result.calls)} call(s) [{tickers}], "
        f"{len(result.evidence)} evidence, refused: {refused}"
    ]
    lines.extend(f"  ! {item}" for item in overrides)
    return "\n".join(lines)


def _run_resolve(ticker: str | None, today: str | None, dry_run: bool) -> str:
    """Score every call the calendar has caught up with.

    The warnings are printed rather than logged away: a ``ref_price`` that is an
    entry level instead of a close is a defect in the *extraction*, and it is
    only visible from here, where the stated number meets the traded one.
    """
    with LearningStore(default_db_path()) as store:
        report = resolve_ledger(store, ticker=ticker, today=today, write=not dry_run)
    lines = [("dry run: " if dry_run else "") + "resolve " + report.summary()]
    lines.extend(f"  ! {warning}" for warning in report.warnings)
    return "\n".join(lines)


def _run_cost() -> str:
    """Return what a conclusion has cost, read straight off the ledger.

    Offline like the scorecard: no model, no network. The number this prints is
    the one the plan wants read before any run is scheduled unattended, because
    a loop that launches runs is buying conclusions at whatever this says.
    """
    with LearningStore(default_db_path()) as store:
        records = [record.to_dict() for record in store.all_process_records()]
    if not records:
        return "no process records on the ledger yet"
    return render_cost_surface(cost_per_conclusion(records))


def _run_report(checkpoint: int) -> str:
    """Render the scorecard. Reads the ledger only -- no model, no network."""
    with LearningStore(default_db_path()) as store:
        return build_scorecard(store, checkpoint=checkpoint).to_text()


def _status_source_path(source: str, root: Path) -> Path:
    """Normalize a source path relative to the repository or agent directory."""
    path = Path(source)
    if not path.is_absolute():
        base = root / "agent" if path.parts and path.parts[0] == ".." else root
        path = base / path
    return path.resolve()


def _run_status() -> str:
    """Report directory coverage and unscored calls without external services."""
    root = Path(__file__).resolve().parents[3]
    with LearningStore(default_db_path()) as store:
        calls = store.list_calls()
        revisions = [
            record
            for call in calls
            for record in store.episode_revisions(call.episode_id)
        ]
        scored = {
            record.call_id for record in revisions if store.outcomes_for(record.call_id)
        }
        evidence_count = store.counts()["evidence"]

    sources: dict[str, set[Path]] = {}
    for record in revisions:
        if record.source_path:
            key = episode_key_for_path(record.source_path)
            sources.setdefault(key, set()).add(_status_source_path(record.source_path, root))

    documents: dict[str, set[Path]] = {}
    for document in iter_research_documents(root):
        key = episode_key_for_path(document.path)
        documents.setdefault(key, set()).add(Path(document.path).resolve())

    lines = [
        "ledger summary:",
        f"  episodes: {len({call.episode_id for call in calls})}",
        f"  calls in force: {len(calls)}",
        f"  distinct calls with outcomes: {len(scored)}",
        f"  evidence: {evidence_count}",
        "",
        "uncovered episodes (backfill queue):",
    ]
    uncovered = sorted(documents.keys() - sources.keys())
    if not uncovered:
        lines.append("  none")
    for key in uncovered:
        lines.append(f"  uncovered {key}")
        lines.extend(
            f"    {document.relative_to(root).as_posix()}"
            for document in sorted(documents[key])
        )

    lines.extend([
        "",
        "covered episodes (directory-level coverage):",
        "  Coverage is judged per directory; an episode is (directory, ticker). "
        "A document about a DIFFERENT ticker in a covered directory is a real "
        "backfill item even though it is listed here. "
        "Offline status cannot determine a document's ticker.",
    ])
    covered = sorted(documents.keys() & sources.keys())
    if not covered:
        lines.append("  none")
    for key in covered:
        lines.append(f"  covered {key}")
        for document in sorted(documents[key]):
            label = (
                "stored call source" if document in sources[key]
                else "not a stored call source"
            )
            lines.append(f"    {document.relative_to(root).as_posix()} [{label}]")

    # resolve_deadline needs sessions from VNINDEX prices; do not guess due dates.
    checkpoints = ", ".join(str(value) for value in CHECKPOINT_SESSIONS)
    lines.extend([
        "",
        f"checkpoint due dates need the VNINDEX price calendar ({checkpoints} sessions).",
        "calls with no outcome yet (run `resolve` to score; needs DataPro):",
    ])
    pending = sorted(
        (call for call in calls if call.call_id not in scored),
        key=lambda call: (call.as_of, call.episode_id, call.call_id),
    )
    if not pending:
        lines.append("  none")
    for call in pending:
        lines.append(
            f"  {call.call_id} {call.ticker} {call.action} as_of={call.as_of} "
            f"episode={call.episode_id} [{call.extraction_status}]"
        )
    return "\n".join(lines)


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
    extract = sub.add_parser(
        "extract", help="extract the calls in one document and store what survives"
    )
    extract.add_argument("--doc", required=True, help="document to extract calls from")
    extract.add_argument(
        "--reply",
        default="",
        help=(
            "file holding a recorded model reply; omit to ask the configured "
            "proposer now (the live reply is saved either way)"
        ),
    )
    extract.add_argument(
        "--proposer",
        default="",
        help="override VIBE_TRADING_PROPOSER for this run (claude|codex)",
    )
    resolve = sub.add_parser("resolve", help="score the calls the calendar has caught up with")
    resolve.add_argument("--ticker", default=None, help="restrict to one symbol")
    resolve.add_argument("--today", default=None, help="last session to consider, YYYY-MM-DD")
    resolve.add_argument(
        "--dry-run", action="store_true", help="score and report without writing outcomes"
    )
    sub.add_parser("cost", help="print what a conclusion has cost, by month")
    sub.add_parser("status", help="print the offline episode backfill and outcome queues")
    scheduler = sub.add_parser(
        "scheduler", help="print whether an unattended cycle would be allowed, and why"
    )
    scheduler.add_argument(
        "--universe",
        default="",
        help="comma-separated tickers the cycle may consider",
    )
    scheduler.add_argument(
        "--run",
        action="store_true",
        help=(
            "actually launch research if every gate allows it; without this "
            "the command only reports what it would do"
        ),
    )
    report = sub.add_parser("report", help="print the scorecard for one checkpoint")
    report.add_argument(
        "--checkpoint", type=int, default=21, help="checkpoint in trading sessions"
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "capture":
            message = _run_capture(sys.stdin.read())
        elif args.command == "scan":
            message = _run_scan(args.directory)
        elif args.command == "prompt":
            print(_run_prompt(args.doc))
            return 0
        elif args.command == "report":
            print(_run_report(args.checkpoint))
            return 0
        elif args.command == "cost":
            print(_run_cost())
            return 0
        elif args.command == "status":
            print(_run_status())
            return 0
        elif args.command == "scheduler":
            universe = [t.strip().upper() for t in args.universe.split(",") if t.strip()]
            if args.run:
                # The gates still decide. This flag only says the caller is
                # willing to spend if they allow it, which is why launching
                # takes an explicit word and reporting does not.
                from src.scheduler.launcher import swarm_launcher
                from src.scheduler.loop import run_cycle

                kwargs = {"dry_run": False, "launcher": swarm_launcher()}
                if universe:
                    kwargs["universe"] = universe
                print(run_cycle(**kwargs).detail)
                return 0
            from src.scheduler.loop import status as scheduler_status

            print(scheduler_status(universe=universe))
            return 0
        elif args.command == "resolve":
            message = _run_resolve(args.ticker, args.today, args.dry_run)
        else:
            message = _run_extract(args.doc, args.reply, args.proposer)
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
