"""Contract tests for the decision-ledger records.

The fixtures deliberately reuse the real FPT session of 27/08/2026, where one
research episode walked its target price 93,000 -> 69,500 -> 59,000 -> 58,800.
That episode is the reason the contract counts episodes rather than revisions.
"""

from __future__ import annotations

import pytest

from src.learning.records import (
    DEFAULT_HORIZON_SESSIONS,
    CallRecord,
    Evidence,
    HindsightViolation,
    Lesson,
    Outcome,
    ProcessRecord,
    RecordValidationError,
    assert_no_hindsight,
    call_id_for,
    latest_revision,
    normalize_action,
    resolve_deadline,
    sessions_between,
)

FPT_TARGETS = (93_000.0, 69_500.0, 59_000.0, 58_800.0)


def _fpt_revision(revision: int, target: float, *, hour: int) -> CallRecord:
    return CallRecord(
        ticker="FPT",
        as_of="2026-08-27",
        action="reduce",
        known_at=f"2026-08-27T{hour:02d}:00:00Z",
        revision=revision,
        thesis_episode="dcf-2026h2",
        ref_price=72_200.0,
        target=target,
        confidence=0.6,
        source_session_id="sess-fpt",
        source_event_sha256=f"event-{revision}",
    )


def _fpt_episode() -> list[CallRecord]:
    return [
        _fpt_revision(index + 1, target, hour=9 + index)
        for index, target in enumerate(FPT_TARGETS)
    ]


# --- episode is the observation unit -----------------------------------------


def test_four_target_revisions_form_one_episode():
    records = _fpt_episode()
    assert len({record.episode_id for record in records}) == 1
    assert len({record.call_id for record in records}) == 4


def test_latest_revision_is_the_scoring_point():
    chosen = latest_revision(_fpt_episode())
    assert chosen is not None
    assert chosen.revision == 4
    assert chosen.target == 58_800.0


def test_latest_revision_respects_cutoff():
    chosen = latest_revision(_fpt_episode(), cutoff="2026-08-27T10:30:00Z")
    assert chosen is not None
    assert chosen.revision == 2
    assert chosen.target == 69_500.0


def test_latest_revision_returns_none_when_nothing_is_known_yet():
    assert latest_revision(_fpt_episode(), cutoff="2026-08-27T08:00:00Z") is None


def test_upside_is_measured_against_the_close_of_the_call_day():
    record = _fpt_revision(4, 58_800.0, hour=12)
    assert record.upside == pytest.approx(58_800.0 / 72_200.0 - 1.0)


# --- required fields and the unit traps --------------------------------------


@pytest.mark.parametrize("missing", ["ticker", "as_of", "action"])
def test_missing_required_field_is_rejected(missing):
    payload = {
        "ticker": "VRE",
        "as_of": "2026-07-31",
        "action": "buy",
        "known_at": "2026-07-31T10:00:00Z",
    }
    payload[missing] = ""
    with pytest.raises(RecordValidationError):
        CallRecord(**payload)


def test_missing_target_or_confidence_is_accepted_but_flagged():
    record = CallRecord(
        ticker="VRE",
        as_of="2026-07-31",
        action="buy",
        known_at="2026-07-31T10:00:00Z",
        ref_price=24_300.0,
    )
    assert record.extraction_status == "incomplete"
    assert record.upside is None


def test_confidence_stated_as_percent_is_rejected():
    with pytest.raises(RecordValidationError, match="fraction"):
        CallRecord(
            ticker="PHR",
            as_of="2026-06-30",
            action="accumulate",
            known_at="2026-06-30T10:00:00Z",
            target=72_000.0,
            confidence=61,
        )


def test_negative_price_is_rejected():
    with pytest.raises(RecordValidationError, match="ref_price"):
        CallRecord(
            ticker="PHR",
            as_of="2026-06-30",
            action="accumulate",
            known_at="2026-06-30T10:00:00Z",
            ref_price=-1.0,
        )


def test_known_at_cannot_precede_as_of():
    with pytest.raises(RecordValidationError, match="precedes as_of"):
        CallRecord(
            ticker="MWG",
            as_of="2026-07-24",
            action="buy",
            known_at="2026-07-23T10:00:00Z",
        )


# --- action vocabulary --------------------------------------------------------


@pytest.mark.parametrize(
    ("stated", "canonical"),
    [
        ("MUA", "buy"),
        ("Tích lũy", "accumulate"),
        ("MUA THEO ĐỢT", "accumulate"),
        ("TRUNG LẬP", "neutral"),
        ("nắm giữ", "hold"),
        ("Chờ", "wait"),
        ("giảm tỷ trọng", "reduce"),
        ("BÁN", "sell"),
        ("không đuổi", "avoid"),
        ("hold", "hold"),
        ("ACCUMULATION", "accumulate"),
        ("OUTPERFORM", "buy"),
        ("OVERWEIGHT", "buy"),
        ("TRIM", "reduce"),
        ("UNDERPERFORM", "reduce"),
        ("UNDERWEIGHT", "reduce"),
    ],
)
def test_vietnamese_actions_normalize(stated, canonical):
    assert normalize_action(stated) == canonical


def test_unknown_action_raises_rather_than_guessing():
    with pytest.raises(RecordValidationError, match="unknown action"):
        normalize_action("có thể cân nhắc")


@pytest.mark.parametrize("swap_word", ["switch", "SWITCH", "swap", "hoán đổi"])
def test_a_swap_is_refused_rather_than_split_onto_one_side(swap_word):
    """A switch is a relation between two tickers, so it is not one's action.

    The TPB-HDB memo writes "switch" fourteen times and the ledger holds it as
    TPB reduce plus HDB accumulate. Registering the word would hand one record
    a meaning that lives in another, and an alias could not even say which side
    of the swap it meant. This is the guard on that: the vocabulary refuses,
    loudly, instead of picking a side. Measuring swap calls means linking two
    records -- see the note on ACTIONS -- not widening this table.
    """
    with pytest.raises(RecordValidationError, match="unknown action"):
        normalize_action(swap_word)


# --- horizons are trading sessions -------------------------------------------


TET_CALENDAR = ["2026-02-10", "2026-02-11", "2026-02-24", "2026-02-25", "2026-02-26"]


def test_deadline_skips_the_tet_gap():
    # Calendar-day arithmetic would land on 2026-02-12, which is not a session.
    assert resolve_deadline("2026-02-10", 2, TET_CALENDAR) == "2026-02-24"


def test_deadline_is_none_when_the_calendar_has_not_reached_it():
    assert resolve_deadline("2026-02-25", DEFAULT_HORIZON_SESSIONS, TET_CALENDAR) is None


def test_deadline_requires_as_of_to_be_a_trading_session():
    with pytest.raises(RecordValidationError, match="not a trading session"):
        resolve_deadline("2026-02-12", 1, TET_CALENDAR)


def test_with_deadline_returns_a_new_record():
    record = CallRecord(
        ticker="HPG",
        as_of="2026-02-10",
        action="buy",
        known_at="2026-02-10T10:00:00Z",
        horizon_sessions=2,
        target=30_000.0,
        confidence=0.55,
    )
    dated = record.with_deadline(TET_CALENDAR)
    assert record.deadline == ""
    assert dated.deadline == "2026-02-24"
    assert dated.call_id == record.call_id


def test_sessions_between_counts_sessions_not_days():
    assert sessions_between("2026-02-10", "2026-02-24", TET_CALENDAR) == 2
    assert sessions_between("2026-02-24", "2026-02-10", TET_CALENDAR) == -2


def test_sessions_between_rejects_a_non_session_endpoint():
    with pytest.raises(RecordValidationError, match="not a trading session"):
        sessions_between("2026-02-10", "2026-02-14", TET_CALENDAR)


# --- identity and idempotency -------------------------------------------------


def test_call_id_is_stable_across_parser_versions():
    common = {
        "ticker": "NLG",
        "as_of": "2026-08-20",
        "action": "accumulate",
        "known_at": "2026-08-20T10:00:00Z",
        "source_session_id": "sess-nlg",
        "source_event_sha256": "abc123",
        "target": 31_000.0,
        "confidence": 0.6,
    }
    first = CallRecord(parser_version="1", **common)
    second = CallRecord(parser_version="2", **common)
    assert first.call_id == second.call_id
    assert first.parser_version != second.parser_version


def test_call_id_helper_matches_the_derived_id():
    record = _fpt_revision(2, 69_500.0, hour=10)
    assert record.call_id == call_id_for(record.episode_id, 2, "event-2")


def test_different_thesis_episodes_split_the_episode():
    base = {
        "ticker": "TPB",
        "as_of": "2026-06-29",
        "action": "hold",
        "known_at": "2026-06-29T10:00:00Z",
        "source_session_id": "sess-switch",
    }
    first = CallRecord(thesis_episode="switch-to-hdb", **base)
    second = CallRecord(thesis_episode="standalone-fa", **base)
    assert first.episode_id != second.episode_id


def test_round_trip_preserves_the_record():
    record = _fpt_revision(3, 59_000.0, hour=11)
    assert CallRecord.from_dict(record.to_dict()) == record


# --- the hindsight wall -------------------------------------------------------


def _evidence(observed_at: str, uuid: str) -> Evidence:
    return Evidence(
        kind="transcript_event",
        observed_at=observed_at,
        source_session_id="sess-fpt",
        source_uuid=uuid,
        excerpt="OCF H1 chỉ đạt 17-26% cả năm",
    )


def test_evidence_needs_a_provenance_handle():
    with pytest.raises(RecordValidationError, match="provenance handle"):
        Evidence(observed_at="2026-08-27T09:00:00Z", excerpt="no source")


def test_hindsight_wall_rejects_later_evidence():
    record = _fpt_revision(1, 93_000.0, hour=9)
    later = _evidence("2026-08-28T09:00:00Z", "uuid-late")
    with pytest.raises(HindsightViolation, match="uuid|ev_"):
        assert_no_hindsight(record.known_at, [later])


def test_hindsight_wall_accepts_evidence_at_the_wall():
    record = _fpt_revision(1, 93_000.0, hour=9)
    assert_no_hindsight(record.known_at, [_evidence("2026-08-27T09:00:00Z", "uuid-ok")])


# --- outcomes may only close against price evidence ---------------------------


def test_outcome_stays_open_without_a_price():
    outcome = Outcome(call_id="call_x", resolved_at="2026-11-27", checkpoint_sessions=63)
    assert outcome.verdict == "open"
    assert outcome.resolved_price is None


def test_outcome_cannot_be_a_hit_without_evidence():
    with pytest.raises(RecordValidationError, match="evidence_id"):
        Outcome(
            call_id="call_x",
            resolved_at="2026-11-27",
            checkpoint_sessions=63,
            verdict="hit",
            resolved_price=60_000.0,
        )


def test_outcome_cannot_be_a_hit_without_a_resolved_price():
    with pytest.raises(RecordValidationError, match="resolved_price"):
        Outcome(
            call_id="call_x",
            resolved_at="2026-11-27",
            checkpoint_sessions=63,
            verdict="hit",
            evidence_ids=["ev_price"],
        )


def test_outcome_closes_with_price_evidence():
    outcome = Outcome(
        call_id="call_x",
        resolved_at="2026-11-27",
        checkpoint_sessions=63,
        verdict="hit",
        resolved_price=60_000.0,
        realized_ret=-0.169,
        vn30_ret=-0.02,
        alpha=-0.149,
        regime="overheat",
        evidence_ids=["ev_price"],
    )
    assert outcome.outcome_id.startswith("out_")


def test_outcome_rejects_an_unlisted_checkpoint():
    with pytest.raises(RecordValidationError, match="checkpoint_sessions"):
        Outcome(call_id="call_x", resolved_at="2026-11-27", checkpoint_sessions=90)


# --- process records ----------------------------------------------------------


def _caught(code: str, round_index: int) -> dict[str, object]:
    return {
        "code": code,
        "description": "lãi FOX bị cộng trùng vào EBITDA",
        "round": round_index,
        "evidence_id": f"ev_{code}_{round_index}",
    }


def test_process_record_counts_distinct_error_codes():
    record = ProcessRecord(
        source_session_id="sess-fpt",
        preset="fundamental_research_team",
        rounds=4,
        errors_caught=[
            _caught("double_count", 1),
            _caught("causal_misread", 2),
            _caught("double_count", 3),
            _caught("cashflow_unreconciled", 4),
        ],
        completed=True,
    )
    assert record.error_taxonomy == ["double_count", "causal_misread", "cashflow_unreconciled"]
    assert record.process_id.startswith("proc_")


def test_process_record_rejects_an_uncited_catch():
    with pytest.raises(RecordValidationError, match="evidence_id"):
        ProcessRecord(
            source_session_id="sess-fpt",
            errors_caught=[{"code": "double_count", "description": "no citation"}],
        )


def test_process_record_rejects_an_unknown_error_code():
    with pytest.raises(RecordValidationError, match="unknown code"):
        ProcessRecord(
            source_session_id="sess-fpt",
            errors_caught=[{"code": "vibes", "evidence_id": "ev_1"}],
        )


def test_process_record_needs_a_run_or_session_handle():
    with pytest.raises(RecordValidationError, match="run_id or a source_session_id"):
        ProcessRecord()


# --- lessons expire unless they are sourced -----------------------------------


def test_unsourced_lesson_is_provisional_and_expires_in_ninety_days():
    lesson = Lesson(
        domain="nganhang",
        statement="Định giá NH dùng RI + P/B mục tiêu, không dùng DCF",
        created_at="2026-08-27T00:00:00Z",
    )
    assert lesson.status == "provisional"
    assert lesson.expires_at == "2026-11-25"
    assert lesson.is_expired("2026-11-26") is True
    assert lesson.is_expired("2026-11-25") is False


def test_confirmed_lesson_requires_evidence():
    with pytest.raises(RecordValidationError, match="evidence_id"):
        Lesson(domain="vimo", statement="ERP âm giải thích index yếu", status="confirmed")


def test_confirmed_lesson_with_evidence_does_not_expire_by_default():
    lesson = Lesson(
        domain="vimo",
        statement="ERP âm giải thích index yếu",
        status="confirmed",
        evidence_ids=["ev_macro_forum"],
    )
    assert lesson.expires_at == ""
    assert lesson.is_expired("2030-01-01") is False


def test_lesson_id_is_stable_across_accents_and_spacing():
    first = Lesson(domain="banle", statement="Không đuổi giá  trần")
    second = Lesson(domain="banle", statement="khong duoi gia tran")
    assert first.lesson_id == second.lesson_id


# -- the vocabulary the corpus actually uses -----------------------------------


@pytest.mark.parametrize(
    "written, canonical",
    [
        ("KHẢ QUAN", "buy"),
        ("TĂNG TỶ TRỌNG", "accumulate"),
        ("nắm", "hold"),
        ("đứng ngoài", "wait"),
        ("loại tuyệt đối", "avoid"),
        ("KÉM KHẢ QUAN", "reduce"),
        ("chốt lời", "reduce"),
    ],
)
def test_the_broker_rating_words_map_to_canonical_actions(written, canonical):
    """These are standard Vietnamese rating words, measured in the corpus."""
    assert normalize_action(written) == canonical


def test_a_whole_sentence_is_refused_with_a_usable_hint():
    """The first backfill failed exactly here: the model sent sentences.

    The vocabulary stays closed -- matching a keyword inside a sentence would be
    the guessing this gate exists to stop -- so the error has to say what to
    send instead.
    """
    with pytest.raises(RecordValidationError, match="whole sentence") as caught:
        normalize_action("CÓ, cổ phiếu này đáng đầu tư nhưng không phải ở giá hôm nay")
    assert "recommendation phrase" in str(caught.value)
