from pathlib import Path
import socket
import subprocess
import sys

import pytest

from src.learning import cli
from src.learning.extract import episode_key_for_path
from src.learning.records import CallRecord, Evidence, Outcome, episode_id_for
from src.learning.store import LearningStore


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "research_workspace"
    (root / "agent").mkdir(parents=True)
    monkeypatch.setattr(cli, "__file__", str(root / "agent/src/learning/cli.py"))
    db = tmp_path / "learning.db"
    monkeypatch.setenv("VIBE_TRADING_LEARNING_DB_PATH", str(db))
    with LearningStore(db):
        pass
    return root, db


def document(root, relative):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Committee decision\n", encoding="utf-8")
    return path


def call(store, path, ticker="AAA", revision=1):
    record = CallRecord(
        ticker=ticker,
        as_of="2026-06-15",
        known_at="2026-06-15T09:00:00Z",
        action="avoid",
        source_path=str(path),
        source_event_sha256=str(path),
        episode_id=episode_id_for(episode_key_for_path(path), ticker, ""),
        revision=revision,
    )
    store.append_call(record)
    return record


def output(capsys):
    assert cli.main(["status"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


@pytest.mark.parametrize("source_style", ["absolute", "repo_relative", "agent_relative"])
def test_covered_episode_retelling_is_never_in_backfill(workspace, capsys, source_style):
    root, db = workspace
    source = document(root, "_vre_committee/PM_DECISION.md")
    revision = document(root, "_vre_committee/PM_DECISION_v2.md")
    document(root, "_vre_committee/BAO_CAO_TONG_HOP_VRE.md")
    if source_style == "repo_relative":
        source = source.relative_to(root)
    elif source_style == "agent_relative":
        source = Path("..") / source.relative_to(root)
    with LearningStore(db) as store:
        call(store, source, "VRE")
        call(store, revision, "VRE", revision=2)

    text = output(capsys)
    backfill, covered = text.split("covered episodes (directory-level coverage):\n")
    assert "uncovered episodes (backfill queue):\n  none" in backfill
    assert "_vre_committee" not in backfill
    assert "  covered _vre_committee" in covered
    assert "_vre_committee/PM_DECISION.md [stored call source]" in covered
    assert "_vre_committee/PM_DECISION_v2.md [stored call source]" in covered
    assert (
        "_vre_committee/BAO_CAO_TONG_HOP_VRE.md "
        "[not a stored call source]"
    ) in covered
    assert "CANDIDATE RETELLING" not in covered


def test_covered_section_warns_that_a_different_ticker_is_real_backfill(workspace, capsys):
    root, db = workspace
    with LearningStore(db) as store:
        call(store, document(root, "_bankdata/TPB_valuation.md"), "TPB")
    document(root, "_bankdata/TCB_valuation.md").write_text(
        "# TCB\nNew decision: buy TCB.\n", encoding="utf-8",
    )
    covered = output(capsys).split("covered episodes (directory-level coverage):\n")[1]
    covered = covered.split("\ncheckpoint due dates")[0]
    assert (
        "Coverage is judged per directory; an episode is (directory, ticker). "
        "A document about a DIFFERENT ticker in a covered directory is a real "
        "backfill item even though it is listed here. "
        "Offline status cannot determine a document's ticker."
    ) in covered
    assert "_bankdata/TPB_valuation.md [stored call source]" in covered
    assert "_bankdata/TCB_valuation.md [not a stored call source]" in covered


def test_uncovered_episode_groups_documents_and_uses_existing_html_policy(workspace, capsys):
    root, _ = workspace
    document(root, "_new/report.md")
    document(root, "_new/summary.md")
    document(root, "_new/presentation.html")
    document(root, "_html/report.html")
    document(root, "_html/report.pdf")
    text = output(capsys)
    backfill = text.split("covered episodes (directory-level coverage):\n")[0]
    assert backfill.count("  uncovered _new\n") == 1
    assert "_new/report.md" in backfill
    assert "_new/summary.md" in backfill
    assert "  uncovered _html\n" in backfill
    assert "_html/report.html" in backfill
    assert "presentation.html" not in text
    assert "report.pdf" not in text


def test_order_is_identical_across_runs_and_sorted_by_episode_key(workspace, capsys):
    root, _ = workspace
    for folder in ("_zulu", "_alpha", "_middle"):
        document(root, f"{folder}/z.md")
        document(root, f"{folder}/a.md")
    first = output(capsys)
    assert first == output(capsys)
    assert first.index("uncovered _alpha") < first.index("uncovered _middle")
    assert first.index("uncovered _middle") < first.index("uncovered _zulu")
    assert first.index("_zulu/a.md") < first.index("_zulu/z.md")


def test_summary_counts_distinct_scored_calls_and_only_lists_unscored_in_force(workspace, capsys):
    root, db = workspace
    with LearningStore(db) as store:
        old = call(store, document(root, "_a/old.md"))
        current = call(store, document(root, "_a/new.md"), revision=2)
        scored = call(store, document(root, "_b/report.md"), "BBB")
        for record in (old, scored):
            for checkpoint in (21, 63):
                store.append_outcome(Outcome(
                    call_id=record.call_id, episode_id=record.episode_id,
                    resolved_at="2026-09-01", checkpoint_sessions=checkpoint,
                ))
        store.append_evidence(Evidence(
            kind="markdown", observed_at="2026-06-15T09:00:00Z", excerpt="one quote",
            source_path=str(root / "_a/old.md"),
        ))
    text = output(capsys)
    assert "episodes: 2\n" in text
    assert "calls in force: 2\n" in text
    assert "distinct calls with outcomes: 2\n" in text
    assert "evidence: 1\n" in text
    pending = text.split("calls with no outcome yet (run `resolve` to score; needs DataPro):\n")[1]
    assert current.call_id in pending
    assert old.call_id not in pending
    assert scored.call_id not in pending
    assert "AAA avoid as_of=2026-06-15" in pending


def test_status_is_offline_without_a_model_or_datapro(workspace, monkeypatch, capsys):
    root, db = workspace
    with LearningStore(db) as store:
        record = call(store, document(root, "_offline/report.md"))

    def refuse(*args, **kwargs):
        raise AssertionError("status must stay offline and must not launch a model")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(cli, "resolve_ledger", refuse)
    monkeypatch.setattr(cli, "extract_document", refuse)
    monkeypatch.setitem(sys.modules, "vndata", None)
    text = output(capsys)
    assert "covered _offline" in text
    assert record.call_id in text


def test_status_uses_the_house_store_pattern_and_leaves_bytes_unchanged(workspace, monkeypatch, capsys):
    root, db = workspace
    with LearningStore(db) as store:
        call(store, document(root, "_readonly/report.md"))
    before = db.read_bytes()
    opened = []

    def open_store(database):
        assert database == db
        opened.append(database)
        return LearningStore(database)

    monkeypatch.setattr(cli, "LearningStore", open_store)
    assert "calls in force: 1" in output(capsys)
    assert len(opened) == 1
    assert db.read_bytes() == before


def test_missing_ledger_is_initialized_by_the_house_store_pattern(workspace, monkeypatch, capsys):
    root, _ = workspace
    missing = root / "absent" / "learning.db"
    monkeypatch.setenv("VIBE_TRADING_LEARNING_DB_PATH", str(missing))
    document(root, "_new/report.md")
    text = output(capsys)
    assert "episodes: 0\n" in text
    assert "calls in force: 0\n" in text
    assert "distinct calls with outcomes: 0\n" in text
    assert "evidence: 0\n" in text
    assert "uncovered _new" in text
    assert missing.is_file()
    with LearningStore(missing) as store:
        assert all(count == 0 for count in store.counts().values())
