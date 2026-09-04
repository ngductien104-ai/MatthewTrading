"""Tests for the session-end capture.

The property under test is the one that decides whether this survives contact
with reality: the hook does not always fire. ``SessionEnd`` is skipped when the
terminal is killed or the process crashes, so the catch-up scan has to be able
to run at any moment, over everything, without either losing what the hook
caught or inventing a second observation of a session it already knows.

That makes idempotence the subject of most of these tests, and one of them is a
regression guard for a real bug found while wiring the hook up: the scan was
rewriting a field it could not observe, so every run appended a fresh version of
the same session forever.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.learning import cli
from src.learning.session import (
    build_process_record,
    capture_session,
    capture_transcript,
    research_writes,
    rework_count,
    scan_transcripts,
    summarize,
)
from src.learning.store import LearningStore
from src.learning.transcript import parse_transcript

GOLDEN = Path(__file__).parent / "fixtures" / "transcript_golden.jsonl"
REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".claude" / "hooks" / "learning-capture.sh"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


@pytest.fixture
def store(tmp_path):
    ledger = LearningStore(tmp_path / "learning.db")
    yield ledger
    ledger.close()


def _event(uuid: str, parent: str, line_time: str, **extra):
    event = {
        "uuid": uuid,
        "parentUuid": parent,
        "sessionId": "sess-capture",
        "type": "assistant",
        "timestamp": line_time,
        "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
    }
    event.update(extra)
    return event


def _tool_event(uuid: str, parent: str, line_time: str, tool_id: str, name: str, path: str):
    return {
        "uuid": uuid,
        "parentUuid": parent,
        "sessionId": "sess-capture",
        "type": "assistant",
        "timestamp": line_time,
        "message": {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": tool_id, "name": name, "input": {"file_path": path}}
            ],
        },
    }


def _write_transcript(path: Path, events: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )
    return path


def _session_with_writes(tmp_path, name: str = "sess-capture.jsonl", paths=("_fpt_research/a.md",)):
    events = [_event("u0", "", "2026-08-27T02:00:00.000Z")]
    for index, target in enumerate(paths):
        events.append(
            _tool_event(
                f"u{index + 1}",
                f"u{index}",
                f"2026-08-27T02:00:{index + 1:02d}.000Z",
                f"t{index}",
                "Write",
                target,
            )
        )
    return _write_transcript(tmp_path / name, events)


# -- what is derived from the transcript --------------------------------------


def test_only_research_writes_are_counted(tmp_path):
    path = _session_with_writes(
        tmp_path,
        paths=("_fpt_research/00.md", "agent/src/learning/session.py", "_vre_committee/BEAR.md"),
    )
    assert research_writes(parse_transcript(path)) == [
        "_fpt_research/00.md",
        "_vre_committee/BEAR.md",
    ]


def test_a_second_write_to_one_file_is_rework(tmp_path):
    path = _session_with_writes(
        tmp_path, paths=("_fpt_research/00.md", "_fpt_research/01.md", "_fpt_research/00.md")
    )
    assert rework_count(parse_transcript(path)) == 1


def test_writing_different_files_is_not_rework(tmp_path):
    path = _session_with_writes(tmp_path, paths=("_fpt_research/00.md", "_fpt_research/01.md"))
    assert rework_count(parse_transcript(path)) == 0


def test_tokens_sum_every_counter_the_transcript_reports():
    record = build_process_record(parse_transcript(GOLDEN))
    assert record.tokens == 11000  # 2200 input + 800 output + 8000 cache read


def test_wall_time_uses_the_monotonic_clock():
    """Raw timestamps run backwards in this corpus; a negative span is not a fact."""
    record = build_process_record(parse_transcript(GOLDEN))
    assert record.wall_time_sec == 30.0


def test_an_empty_transcript_has_nothing_to_say(tmp_path):
    path = _write_transcript(tmp_path / "empty.jsonl", [])
    with pytest.raises(ValueError, match="no content events"):
        build_process_record(parse_transcript(path))


def test_the_record_is_anchored_to_the_first_event_not_the_last(tmp_path):
    """A growing session stays one observation; only its content is newer."""
    path = _session_with_writes(tmp_path)
    before = build_process_record(parse_transcript(path))
    events = json.loads("[" + ",".join(path.read_text(encoding="utf-8").splitlines()) + "]")
    events.append(_event("u9", "u1", "2026-08-27T02:05:00.000Z"))
    _write_transcript(path, events)
    after = build_process_record(parse_transcript(path))
    assert before.process_id == after.process_id
    assert after.wall_time_sec > before.wall_time_sec


def test_known_at_is_the_session_end_not_the_capture_time(tmp_path):
    """Using "now" would rehash the payload on every run and defeat idempotence."""
    path = _session_with_writes(tmp_path)
    record = build_process_record(parse_transcript(path))
    assert record.known_at == "2026-08-27T02:00:01Z"


# -- capture ------------------------------------------------------------------


def test_a_capture_lands_on_the_ledger(tmp_path, store):
    path = _session_with_writes(tmp_path)
    result = capture_transcript(path, store, completed=True)
    assert result.append.appended is True
    assert result.research_paths == ["_fpt_research/a.md"]
    assert store.process_for_session("sess-capture").completed is True


def test_capturing_the_same_transcript_twice_adds_nothing(tmp_path, store):
    path = _session_with_writes(tmp_path)
    first = capture_transcript(path, store, completed=True)
    second = capture_transcript(path, store, completed=True)
    assert (first.append.appended, second.append.appended) == (True, False)
    assert store.counts()["process_records"] == 1


def test_a_missing_transcript_is_reported_not_raised(tmp_path, store):
    result = capture_transcript(tmp_path / "gone.jsonl", store)
    assert result.process is None
    assert "not found" in result.skipped


def test_a_hook_payload_without_a_transcript_path_is_reported(store):
    result = capture_session({"reason": "clear"}, store)
    assert result.process is None
    assert "no transcript_path" in result.skipped


def test_a_reported_reason_is_what_marks_a_session_completed(tmp_path, store):
    path = _session_with_writes(tmp_path)
    payload = {"transcript_path": str(path), "hook_event_name": "SessionEnd"}
    assert capture_session(payload, store).process.completed is False
    assert capture_session({**payload, "reason": "clear"}, store).process.completed is True


# -- the catch-up scan --------------------------------------------------------


def test_the_scan_captures_every_transcript(tmp_path, store):
    _session_with_writes(tmp_path, name="a.jsonl")
    events = [_event("v0", "", "2026-08-27T03:00:00.000Z")]
    events[0]["sessionId"] = "sess-other"
    _write_transcript(tmp_path / "b.jsonl", events)
    results = list(scan_transcripts(store, tmp_path))
    assert len(results) == 2
    assert store.counts()["process_records"] == 2


def test_the_scan_never_un_knows_a_completed_session(tmp_path, store):
    """Regression: the scan rewrote a field it cannot observe, forever.

    A scan cannot tell how a session ended. Before this guard it wrote
    ``completed=False`` over the hook's ``True``, the payload differed, and
    every single run appended another version of the same observation.
    """
    path = _session_with_writes(tmp_path)
    capture_transcript(path, store, completed=True)
    first_scan = list(scan_transcripts(store, tmp_path))
    second_scan = list(scan_transcripts(store, tmp_path))
    assert store.process_for_session("sess-capture").completed is True
    assert first_scan[0].append.appended is False
    assert second_scan[0].append.appended is False
    assert store.counts()["process_records"] == 1


def test_the_scan_reports_what_it_did(tmp_path, store):
    _session_with_writes(tmp_path)
    assert summarize(scan_transcripts(store, tmp_path)) == (
        "captured 1 session(s), 1 new version(s), 0 skipped"
    )
    assert summarize(scan_transcripts(store, tmp_path)) == (
        "captured 1 session(s), 0 new version(s), 0 skipped"
    )


# -- the command line ---------------------------------------------------------


@pytest.fixture
def ledger_env(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_LEARNING_DB_PATH", str(tmp_path / "learning.db"))
    monkeypatch.setenv("VIBE_TRADING_TRANSCRIPT_DIR", str(tmp_path))
    return tmp_path


def test_capture_reads_the_hook_payload_from_stdin(ledger_env, monkeypatch, capsys):
    path = _session_with_writes(ledger_env)
    payload = json.dumps({"transcript_path": str(path), "reason": "logout"})
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(payload))
    assert cli.main(["capture"]) == 0
    assert "sess-capture new" in capsys.readouterr().out
    with LearningStore(cli.default_db_path()) as store:
        assert store.process_for_session("sess-capture").completed is True


def test_a_broken_payload_fails_loudly_but_does_not_raise(ledger_env, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO("not json"))
    assert cli.main(["capture"]) == 1
    assert "failed" in capsys.readouterr().err
    assert "capture FAILED" in cli.log_path().read_text(encoding="utf-8")


def test_the_log_sits_beside_the_ledger(ledger_env):
    assert cli.log_path().parent == cli.default_db_path().parent


def test_scan_from_the_command_line(ledger_env, capsys):
    _session_with_writes(ledger_env)
    assert cli.main(["scan"]) == 0
    assert "captured 1 session(s)" in capsys.readouterr().out


# -- the hook, as installed ---------------------------------------------------


def test_the_hook_is_registered_for_session_end():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entries = settings["hooks"]["SessionEnd"]
    commands = [hook for entry in entries for hook in entry["hooks"]]
    assert any("learning-capture.sh" in hook["command"] for hook in commands)


def test_the_hook_asks_for_more_than_the_default_budget():
    """SessionEnd hooks share 1.5 seconds unless a longer timeout raises it.

    A full capture plus catch-up scan takes several seconds, so leaving the
    timeout unset would kill the hook halfway on a machine with more
    transcripts than this one.
    """
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks = [
        hook
        for entry in settings["hooks"]["SessionEnd"]
        for hook in entry["hooks"]
        if "learning-capture.sh" in hook["command"]
    ]
    assert hooks and all(hook.get("timeout", 0) >= 10 for hook in hooks)


def test_the_pre_existing_gstack_hook_was_not_disturbed():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    matchers = [entry.get("matcher") for entry in settings["hooks"]["PreToolUse"]]
    assert "Skill" in matchers


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not on this machine")
def test_the_hook_script_runs_end_to_end(tmp_path):
    """Run the installed shell script the way the harness will run it."""
    transcripts = tmp_path / "transcripts"
    path = _session_with_writes(transcripts)
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(REPO_ROOT),
        "VIBE_TRADING_LEARNING_DB_PATH": str(tmp_path / "learning.db"),
        "VIBE_TRADING_TRANSCRIPT_DIR": str(transcripts),
    }
    payload = json.dumps({"transcript_path": str(path), "reason": "clear", "cwd": str(REPO_ROOT)})
    result = subprocess.run(
        [shutil.which("bash"), str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    with LearningStore(tmp_path / "learning.db") as store:
        record = store.process_for_session("sess-capture")
        assert record is not None and record.completed is True
        assert record.known_at.endswith("Z")


def test_the_capture_never_looks_into_the_future(tmp_path, store):
    """known_at is the last thing observed, so it cannot postdate the session."""
    path = _session_with_writes(tmp_path)
    record = capture_transcript(path, store).process
    written = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    known = datetime.fromisoformat(record.known_at.replace("Z", "+00:00"))
    assert known <= written


# -- the backfill verbs -------------------------------------------------------

_DOC_BODY = (
    "# FPT\n\n**Khuyến nghị: GIẢM TỶ TRỌNG**\n\n"
    "**Giá chốt:** 72.200 đ/cp · **Giá mục tiêu ~58.800 đ**\n"
)


def _research_doc(root: Path) -> Path:
    path = root / "_fpt_research" / "00.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_DOC_BODY, encoding="utf-8")
    return path


@pytest.mark.parametrize("command", ["report", "cost"])
def test_a_read_only_command_exits_cleanly_after_printing(ledger_env, capsys, command):
    """Both printed their answer and then crashed on the way out.

    ``report`` and ``cost`` print directly and, unlike every other branch, fell
    through to the shared ``_log(message)`` tail with ``message`` never
    assigned. That line sits outside the try, so the UnboundLocalError went
    straight to the caller: the scoreboard appeared in full, then the command
    exited non-zero with a traceback under it. Anything reading the exit code --
    a hook, a scheduler, a shell -- saw a failed run of a command that had
    worked.
    """
    assert cli.main([command]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip()
    assert "UnboundLocalError" not in captured.err


def test_prompt_prints_the_contract_and_the_document(ledger_env, capsys):
    doc = _research_doc(ledger_env)
    assert cli.main(["prompt", "--doc", str(doc)]) == 0
    printed = capsys.readouterr().out
    assert "Every quote must appear character-for-character" in printed
    assert "**Giá mục tiêu ~58.800 đ**" in printed


def test_extract_stores_only_what_the_validator_verifies(ledger_env, capsys):
    doc = _research_doc(ledger_env)
    reply = ledger_env / "reply.json"
    reply.write_text(
        json.dumps(
            {
                "calls": [
                    {
                        "ticker": "FPT",
                        "as_of": "2026-08-27",
                        "action": "giảm tỷ trọng",
                        "ref_price": 72200,
                        "target": 58800,
                        "quotes": [
                            "**Khuyến nghị: GIẢM TỶ TRỌNG**",
                            "**Giá chốt:** 72.200 đ/cp · **Giá mục tiêu ~58.800 đ**",
                        ],
                    },
                    {
                        "ticker": "FPT",
                        "as_of": "2026-08-27",
                        "action": "giảm tỷ trọng",
                        "target": 99999,
                        "quotes": ["**Khuyến nghị: GIẢM TỶ TRỌNG**", "**Giá mục tiêu ~58.800 đ**"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["extract", "--doc", str(doc), "--reply", str(reply)]) == 0
    printed = capsys.readouterr().out
    assert "1 call(s) [FPT]" in printed
    assert "number_not_in_evidence" in printed
    with LearningStore(cli.default_db_path()) as store:
        stored = store.list_calls("FPT")
        assert len(stored) == 1
        assert stored[0].target == 58800.0


def test_replaying_the_same_reply_adds_no_second_observation(ledger_env, capsys):
    doc = _research_doc(ledger_env)
    reply = ledger_env / "reply.json"
    reply.write_text(
        json.dumps(
            {
                "calls": [
                    {
                        "ticker": "FPT",
                        "as_of": "2026-08-27",
                        "action": "giảm tỷ trọng",
                        "ref_price": 72200,
                        "target": 58800,
                        "quotes": [
                            "**Khuyến nghị: GIẢM TỶ TRỌNG**",
                            "**Giá chốt:** 72.200 đ/cp · **Giá mục tiêu ~58.800 đ**",
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cli.main(["extract", "--doc", str(doc), "--reply", str(reply)])
    cli.main(["extract", "--doc", str(doc), "--reply", str(reply)])
    capsys.readouterr()
    with LearningStore(cli.default_db_path()) as store:
        assert store.counts()["calls"] == 1


def test_a_missing_reply_file_fails_without_raising(ledger_env, capsys):
    doc = _research_doc(ledger_env)
    assert cli.main(["extract", "--doc", str(doc), "--reply", str(ledger_env / "nope.json")]) == 1
    assert "failed" in capsys.readouterr().err
