"""Tests for the ledger rebuild that follows an identifier rule change.

The subject is not "does it copy rows". It is the four ways a migration can be
quietly wrong:

* it can lose a revision, so the append-only history it was meant to preserve
  comes out shorter than it went in;
* it can leave an outcome pointing at a ``call_id`` that no longer exists,
  which is a score attached to nothing;
* it can touch the file it read, taking the rollback with it;
* it can be non-idempotent, so running it twice produces a third ledger.

Each of those has a test here. The fixture is built the way the real ledger was
built -- evidence first, then a call citing it -- because ``append_call``
refuses a call whose evidence the ledger has not seen, and a migration has to
satisfy that same gate in the same order.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.learning.extract import episode_key_for_path
from src.learning.migrate import install, main, rebuild_ledger, recomputed_call
from src.learning.records import CallRecord, Evidence, Outcome, episode_id_for
from src.learning.store import LearningStore

KNOWN_AT = "2026-06-30T09:00:00Z"


def _evidence(excerpt: str) -> Evidence:
    return Evidence(
        kind="markdown",
        observed_at=KNOWN_AT,
        source_path="../_phr_committee/PM_DECISION.md",
        locator="L1-L2",
        excerpt=excerpt,
    )


def _call(thesis: str, evidence_ids: list[str], ticker: str = "PHR") -> CallRecord:
    """A call shaped like the ones the extractor writes: no session, a folder key."""
    return CallRecord(
        ticker=ticker,
        as_of="2026-06-30",
        action="accumulate",
        known_at=KNOWN_AT,
        episode_id=episode_id_for("_phr_committee", ticker, thesis),
        thesis_episode=thesis,
        ref_price=62000.0,
        target=72000.0,
        confidence=0.61,
        evidence_ids=evidence_ids,
        source_path="../_phr_committee/PM_DECISION.md",
        source_event_sha256="a" * 64,
    )


@pytest.fixture
def old_ledger(tmp_path):
    """A ledger written under the rule that let the thesis into the episode key."""
    path = tmp_path / "learning.db"
    with LearningStore(path) as store:
        first = _evidence("**Giá tham chiếu:** 62,0")
        second = _evidence("> Khuyến nghị: MUA THEO ĐỢT")
        store.append_evidence(first)
        store.append_evidence(second)
        call = _call("Đền bù VSIP III + neo định giá RNAV", [first.evidence_id, second.evidence_id])
        store.append_call(call)
        store.append_outcome(
            Outcome(
                call_id=call.call_id,
                episode_id=call.episode_id,
                checkpoint_sessions=63,
                resolved_at="2026-09-30",
                verdict="hit",
                resolved_price=70000.0,
                evidence_ids=[first.evidence_id],
            )
        )
    return path


def _rows(path, table: str) -> int:
    conn = sqlite3.connect(path)
    try:
        return int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()


# -- the identifier actually changes ------------------------------------------


def test_a_document_call_loses_the_thesis_from_its_episode(old_ledger, tmp_path):
    report = rebuild_ledger(old_ledger, tmp_path / "new.db")
    assert len(report.remapped_calls) == 1
    with LearningStore(tmp_path / "new.db") as store:
        moved = store.list_calls()[0]
    expected = episode_id_for(episode_key_for_path("../_phr_committee/PM_DECISION.md"), "PHR", "")
    assert moved.episode_id == expected
    assert moved.thesis_episode == "Đền bù VSIP III + neo định giá RNAV"


def test_a_transcript_call_keeps_its_thesis(tmp_path):
    """One interactive session can hold two arguments about one ticker."""
    payload = _call("hai luận điểm", []).to_dict()
    payload["source_session_id"] = "sess-1"
    payload["episode_id"] = episode_id_for("sess-1", "PHR", "hai luận điểm")
    rebuilt = recomputed_call(payload)
    assert rebuilt.episode_id == payload["episode_id"]


# -- the four ways it could be quietly wrong ----------------------------------


def test_the_outcome_follows_the_call_to_its_new_id(old_ledger, tmp_path):
    """A score whose call_id no longer exists is a score attached to nothing."""
    report = rebuild_ledger(old_ledger, tmp_path / "new.db")
    new_call_id = next(iter(report.remapped_calls.values()))
    with LearningStore(tmp_path / "new.db") as store:
        assert [outcome.verdict for outcome in store.outcomes_for(new_call_id)] == ["hit"]


def test_every_revision_survives(old_ledger, tmp_path):
    """The ledger records corrections by appending; a rebuild must not collapse them."""
    with LearningStore(old_ledger) as store:
        call = store.list_calls()[0]
        revised = CallRecord.from_dict({**call.to_dict(), "target": 75000.0})
        store.append_call(revised)
    assert _rows(old_ledger, "calls") == 2

    report = rebuild_ledger(old_ledger, tmp_path / "new.db")
    assert report.rows["calls"] == 2
    assert report.collapsed == []
    assert _rows(tmp_path / "new.db", "calls") == 2


def test_the_source_is_left_exactly_as_it_was(old_ledger, tmp_path):
    """The old file is the rollback, so the migration opens it read-only."""
    before = old_ledger.read_bytes()
    rebuild_ledger(old_ledger, tmp_path / "new.db")
    assert old_ledger.read_bytes() == before


def test_running_it_twice_changes_nothing_the_second_time(old_ledger, tmp_path):
    rebuild_ledger(old_ledger, tmp_path / "once.db")
    second = rebuild_ledger(tmp_path / "once.db", tmp_path / "twice.db")
    assert second.remapped_calls == {}
    assert second.rows == {"evidence": 2, "calls": 1, "outcomes": 1}
    assert second.collapsed == []


def test_a_rebuild_that_would_collapse_content_says_so(old_ledger, tmp_path):
    """Two serializations of one record are not a lost revision, and are named."""
    conn = sqlite3.connect(old_ledger)
    try:
        row = conn.execute("SELECT * FROM calls").fetchone()
        columns = [description[0] for description in conn.execute("SELECT * FROM calls").description]
        data = dict(zip(columns, row))
        data["seq"] = None
        data["content_hash"] = "0" * 64
        placeholders = ", ".join("?" for _ in columns)
        conn.execute(f"INSERT INTO calls VALUES ({placeholders})", [data[name] for name in columns])
        conn.commit()
    finally:
        conn.close()

    report = rebuild_ledger(old_ledger, tmp_path / "new.db")
    assert report.rows["calls"] == 2
    assert len(report.collapsed) == 1
    assert "calls" in report.collapsed[0]


# -- refusing to write over a ledger that already holds rows -------------------


def test_it_refuses_a_target_that_exists(old_ledger, tmp_path):
    (tmp_path / "new.db").write_bytes(b"")
    with pytest.raises(FileExistsError):
        rebuild_ledger(old_ledger, tmp_path / "new.db")


def test_it_refuses_a_source_that_does_not(tmp_path):
    with pytest.raises(FileNotFoundError):
        rebuild_ledger(tmp_path / "absent.db", tmp_path / "new.db")


# -- installing -----------------------------------------------------------------


def test_installing_keeps_the_old_ledger_as_the_rollback(old_ledger, tmp_path):
    rebuild_ledger(old_ledger, tmp_path / "new.db")
    backup = install(tmp_path / "new.db", old_ledger)
    assert backup.exists()
    assert old_ledger.exists()
    assert not (tmp_path / "new.db").exists()
    with LearningStore(backup) as store:
        assert store.list_calls()[0].thesis_episode == "Đền bù VSIP III + neo định giá RNAV"


def test_the_command_line_does_not_install_unless_told(old_ledger, tmp_path, capsys):
    code = main(["--source", str(old_ledger), "--target", str(tmp_path / "new.db")])
    assert code == 0
    assert "not installed" in capsys.readouterr().out
    assert (tmp_path / "new.db").exists()
