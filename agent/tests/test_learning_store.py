"""Tests for the append-only learning ledger.

The property under test throughout is the one the vault never had: a rewrite
must not be able to destroy what was there before.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.learning.records import (
    CallRecord,
    Evidence,
    HindsightViolation,
    Lesson,
    Outcome,
    ProcessRecord,
    RecordValidationError,
    episode_id_for,
)
from src.learning.store import (
    LearningStore,
    LedgerError,
    append_call_with_evidence,
    default_db_path,
)


@pytest.fixture
def store(tmp_path):
    ledger = LearningStore(tmp_path / "learning.db")
    yield ledger
    ledger.close()


def _evidence(observed_at: str = "2026-08-27T09:00:00Z", uuid: str = "uuid-1") -> Evidence:
    return Evidence(
        kind="transcript_event",
        observed_at=observed_at,
        source_session_id="sess-fpt",
        source_uuid=uuid,
        excerpt="close 2026-08-27: 72200",
    )


def _call(target: float = 58_800.0, revision: int = 1, evidence_ids=None) -> CallRecord:
    return CallRecord(
        ticker="FPT",
        as_of="2026-08-27",
        action="reduce",
        known_at=f"2026-08-27T{9 + revision:02d}:00:00Z",
        revision=revision,
        thesis_episode="dcf-2026h2",
        ref_price=72_200.0,
        target=target,
        confidence=0.6,
        source_session_id="sess-fpt",
        source_event_sha256=f"event-{revision}",
        evidence_ids=evidence_ids or [],
    )


# --- append and read ----------------------------------------------------------


def test_append_then_read_back(store):
    record = _call()
    result = store.append_call(record)
    assert result.appended is True
    assert result.version == 1
    assert store.get_call(record.call_id) == record


def test_identical_content_is_ignored_so_backfill_can_re_run(store):
    record = _call()
    store.append_call(record)
    second = store.append_call(record)
    assert second.appended is False
    assert second.version == 1
    assert len(store.call_history(record.call_id)) == 1


def test_changed_content_appends_a_version_and_keeps_the_old_one(store):
    original = _call(target=59_000.0)
    store.append_call(original)
    corrected = CallRecord.from_dict({**original.to_dict(), "target": 58_800.0})
    result = store.append_call(corrected)

    assert corrected.call_id == original.call_id  # same observation
    assert result.appended is True
    assert result.version == 2
    history = store.call_history(original.call_id)
    assert [item.target for item in history] == [59_000.0, 58_800.0]
    assert store.get_call(original.call_id).target == 58_800.0


def test_audit_trail_records_both_writes_and_no_ops(store):
    record = _call()
    store.append_call(record)
    store.append_call(record)
    actions = [row["action"] for row in store.audit_trail(record.call_id)]
    assert actions == ["append", "duplicate_ignored"]


# --- append-only is enforced by the database ---------------------------------


def _seed_every_table(store) -> None:
    """Put one row in each append-only table.

    A row-level trigger cannot fire on an empty table, so a guard test that
    skips this proves nothing.
    """
    thesis_evidence = _evidence()
    store.append_evidence(thesis_evidence)
    record = _call(evidence_ids=[thesis_evidence.evidence_id])
    store.append_call(record)
    price_evidence = Evidence(
        kind="price_series",
        observed_at="2026-11-27T10:00:00Z",
        source_path="_fpt_research/fpt_daily.csv",
        excerpt="close 60000",
    )
    store.append_evidence(price_evidence)
    store.append_outcome(
        Outcome(
            call_id=record.call_id,
            resolved_at="2026-11-27",
            checkpoint_sessions=63,
            verdict="hit",
            resolved_price=60_000.0,
            evidence_ids=[price_evidence.evidence_id],
        )
    )
    store.append_process(ProcessRecord(source_session_id="sess-fpt", rounds=4))
    store.append_lesson(Lesson(domain="vimo", statement="ERP âm giải thích index yếu"))
    assert all(count >= 1 for count in store.counts().values())


@pytest.mark.parametrize("table", ["calls", "evidence", "outcomes", "process_records", "lessons"])
def test_update_is_refused_by_trigger(store, table):
    _seed_every_table(store)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        store._conn.execute(f"UPDATE {table} SET content_hash = 'tampered'")


@pytest.mark.parametrize("table", ["calls", "evidence", "outcomes", "process_records", "lessons"])
def test_delete_is_refused_by_trigger(store, table):
    _seed_every_table(store)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        store._conn.execute(f"DELETE FROM {table}")


# --- the evidence gate --------------------------------------------------------


def test_citing_unknown_evidence_is_refused(store):
    with pytest.raises(LedgerError, match="never seen"):
        store.append_call(_call(evidence_ids=["ev_ghost"]))


def test_evidence_must_predate_the_call(store):
    late = _evidence(observed_at="2026-08-28T09:00:00Z", uuid="uuid-late")
    store.append_evidence(late)
    with pytest.raises(HindsightViolation):
        store.append_call(_call(evidence_ids=[late.evidence_id]))


def test_evidence_at_or_before_the_wall_is_accepted(store):
    early = _evidence(observed_at="2026-08-27T09:30:00Z")
    store.append_evidence(early)
    record = _call(evidence_ids=[early.evidence_id])
    assert store.append_call(record).appended is True
    assert store.get_evidence(early.evidence_id) == early


def test_helper_appends_evidence_before_the_call(store):
    evidence = _evidence()
    record = _call(evidence_ids=[evidence.evidence_id])
    assert append_call_with_evidence(store, record, [evidence]).appended is True


def test_helper_refuses_a_citation_it_was_not_given(store):
    record = _call(evidence_ids=["ev_ghost"])
    with pytest.raises(RecordValidationError, match="not supplied"):
        append_call_with_evidence(store, record, [])


# --- episodes -----------------------------------------------------------------


def test_episode_scoring_point_is_the_last_revision_in_force(store):
    for index, target in enumerate((93_000.0, 69_500.0, 59_000.0, 58_800.0)):
        store.append_call(_call(target=target, revision=index + 1))
    episode_id = _call().episode_id

    assert len(store.episode_revisions(episode_id)) == 4
    assert store.scoring_point(episode_id).target == 58_800.0
    assert store.scoring_point(episode_id, cutoff="2026-08-27T11:30:00Z").target == 69_500.0


def test_list_calls_filters_by_ticker_and_date(store):
    store.append_call(_call())
    store.append_call(
        CallRecord(
            ticker="VRE",
            as_of="2026-07-31",
            action="buy",
            known_at="2026-07-31T10:00:00Z",
            target=24_000.0,
            confidence=0.55,
            source_session_id="sess-vre",
            source_event_sha256="event-vre",
        )
    )
    assert [item.ticker for item in store.list_calls()] == ["VRE", "FPT"]
    assert [item.ticker for item in store.list_calls(ticker="fpt")] == ["FPT"]
    assert [item.ticker for item in store.list_calls(since="2026-08-01")] == ["FPT"]


# --- one episode is one call, however many documents state it -----------------


def _episode_call(episode_key: str, sha: str, target: float, known_at: str) -> CallRecord:
    """One ticker's call as a given folder's document states it."""
    return CallRecord(
        ticker="HAH",
        as_of="2026-06-15",
        action="neutral",
        known_at=known_at,
        episode_id=episode_id_for(episode_key, "HAH", ""),
        ref_price=54_500.0,
        target=target,
        confidence=0.5,
        source_path=f"../{episode_key}/{sha}.md",
        source_event_sha256=sha,
    )


def test_two_documents_of_one_episode_are_one_call(store):
    """The HAH case: two drafts of one report, one decision, one row to score.

    ``_HAH_research`` holds ``HAH_BaoCao.md`` and ``report.md``. Both state the
    same call, so both land in one episode with different call ids -- reading a
    fuller draft is not the desk calling the stock a second time, and it must
    not move the denominator of a hit rate.
    """
    store.append_call(_episode_call("_HAH_research", "a" * 64, 57_400.0, "2026-06-15T09:00:00Z"))
    store.append_call(_episode_call("_HAH_research", "b" * 64, 57_900.0, "2026-06-16T09:00:00Z"))

    listed = store.list_calls(ticker="HAH")
    assert len(listed) == 1
    # The later reading is the one in force, matching scoring_point exactly.
    assert listed[0].target == 57_900.0
    assert listed[0].call_id == store.scoring_point(listed[0].episode_id).call_id
    # Nothing was destroyed: both readings are still there to be inspected.
    assert len(store.episode_revisions(listed[0].episode_id)) == 2


def test_the_same_ticker_in_two_folders_stays_two_calls(store):
    """The collapse must not reach across episodes.

    HPG is called once by its own research folder and again by the VRE
    committee's execution table. Those are two decisions on two dates, and
    folding them into one would hide a call rather than de-duplicate one.
    """
    store.append_call(_episode_call("_hpg_research", "c" * 64, 27_000.0, "2026-06-17T09:00:00Z"))
    store.append_call(_episode_call("_vre_committee", "d" * 64, 21_000.0, "2026-07-31T09:00:00Z"))

    listed = store.list_calls(ticker="HAH")
    assert len(listed) == 2
    assert {record.target for record in listed} == {27_000.0, 21_000.0}


# --- outcomes -----------------------------------------------------------------


def test_outcome_needs_a_call_on_the_ledger(store):
    with pytest.raises(LedgerError, match="not on the ledger"):
        store.append_outcome(
            Outcome(call_id="call_ghost", resolved_at="2026-11-27", checkpoint_sessions=63)
        )


def test_outcome_is_stored_and_read_back(store):
    record = _call()
    store.append_call(record)
    price_evidence = Evidence(
        kind="price_series",
        observed_at="2026-11-27T10:00:00Z",
        source_path="_fpt_research/fpt_daily.csv",
        locator="FPT 2026-11-27",
        excerpt="close 60000",
    )
    store.append_evidence(price_evidence)
    outcome = Outcome(
        call_id=record.call_id,
        episode_id=record.episode_id,
        resolved_at="2026-11-27",
        checkpoint_sessions=63,
        verdict="hit",
        resolved_price=60_000.0,
        realized_ret=-0.169,
        evidence_ids=[price_evidence.evidence_id],
    )
    store.append_outcome(outcome)
    assert store.outcomes_for(record.call_id) == [outcome]


def test_outcome_evidence_cannot_postdate_the_resolution(store):
    record = _call()
    store.append_call(record)
    future = Evidence(
        kind="price_series",
        observed_at="2026-12-01T10:00:00Z",
        source_path="_fpt_research/fpt_daily.csv",
        excerpt="close 61000",
    )
    store.append_evidence(future)
    with pytest.raises(HindsightViolation):
        store.append_outcome(
            Outcome(
                call_id=record.call_id,
                resolved_at="2026-11-27",
                checkpoint_sessions=63,
                verdict="hit",
                resolved_price=60_000.0,
                evidence_ids=[future.evidence_id],
            )
        )


# --- process records and lessons ---------------------------------------------


def test_process_record_round_trips(store):
    record = ProcessRecord(
        source_session_id="sess-fpt",
        preset="fundamental_research_team",
        rounds=4,
        errors_caught=[
            {"code": "double_count", "description": "lãi FOX", "round": 1, "evidence_id": "ev_1"}
        ],
        tokens=120_000,
        completed=True,
        known_at="2026-08-27T12:00:00Z",
    )
    store.append_process(record)
    assert store.get_process(record.process_id) == record


def test_live_lessons_drop_retired_and_expired(store):
    fresh = Lesson(domain="vimo", statement="ERP âm giải thích index yếu")
    retired = Lesson(domain="vimo", statement="Quy tắc cũ", status="retired")
    stale = Lesson(
        domain="vimo", statement="Bài học hết hạn", created_at="2026-01-01T00:00:00Z"
    )
    for lesson in (fresh, retired, stale):
        store.append_lesson(lesson)

    live = store.live_lessons(domain="vimo", as_of="2026-08-27")
    assert [item.statement for item in live] == ["ERP âm giải thích index yếu"]


def test_counts_report_distinct_records(store):
    store.append_call(_call())
    store.append_call(_call(target=59_000.0))  # a second version of the same call
    store.append_lesson(Lesson(domain="banle", statement="Không đuổi giá trần"))
    assert store.counts()["calls"] == 1
    assert store.counts()["lessons"] == 1


# --- schema and migration -----------------------------------------------------


def test_fresh_database_is_stamped_with_the_schema_version(tmp_path):
    with LearningStore(tmp_path / "new.db") as ledger:
        assert ledger.schema_version == 1


def test_unstamped_database_is_migrated_in_place(tmp_path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(str(path))
    connection.execute("CREATE TABLE leftovers (x INTEGER)")
    connection.commit()
    connection.close()

    with LearningStore(path) as ledger:
        assert ledger.schema_version == 1
        assert ledger.append_call(_call()).appended is True
    # the pre-existing table is left alone rather than dropped
    connection = sqlite3.connect(str(path))
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    connection.close()
    assert "leftovers" in tables and "calls" in tables


def test_reopening_preserves_data(tmp_path):
    path = tmp_path / "reopen.db"
    record = _call()
    with LearningStore(path) as ledger:
        ledger.append_call(record)
    with LearningStore(path) as ledger:
        assert ledger.get_call(record.call_id) == record
        assert ledger.append_call(record).appended is False


def test_a_newer_schema_is_refused_rather_than_written_to(tmp_path):
    path = tmp_path / "future.db"
    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA user_version=99")
    connection.commit()
    connection.close()
    with pytest.raises(LedgerError, match="schema 99"):
        LearningStore(path)


def test_db_path_honours_the_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_LEARNING_DB_PATH", str(tmp_path / "custom.db"))
    assert default_db_path() == tmp_path / "custom.db"
