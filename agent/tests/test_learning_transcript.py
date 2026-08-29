"""Tests for the Claude Code transcript parser.

The golden fixture is hand-built rather than sliced out of a real session: this
repository is public and the transcripts hold client research. Every structural
trap it reproduces was measured on the real corpus first -- results arriving out
of order, a request that never resolves, a timestamp that runs backwards, a
thinking block, harness noise, an unknown event type and a truncated tail.

The last test in the file runs against the real transcripts when they are
present, asserting invariants rather than counts so it does not rot as sessions
accumulate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.learning.transcript import (
    HARNESS_TYPES,
    default_transcript_dir,
    iter_transcripts,
    parse_transcript,
    tool_calls_by_name,
)

FIXTURE = Path(__file__).parent / "fixtures" / "transcript_golden.jsonl"


@pytest.fixture
def golden():
    return parse_transcript(FIXTURE)


# --- pairing is by id, never by position -------------------------------------


def test_results_are_paired_by_id_not_by_line_order(golden):
    # toolu_fin was requested second and answered first. A parser that pairs a
    # result with the nearest preceding request swaps these two.
    assert golden.tool_calls["toolu_price"].result_text == "close 2026-08-27: 72200"
    assert golden.tool_calls["toolu_fin"].result_text == "OCF H1 2026: 1.842 tỷ"


def test_parallel_requests_share_one_event(golden):
    request = golden.event_by_uuid("a1")
    assert request is not None
    assert request.tool_use_ids == ["toolu_price", "toolu_fin"]


def test_misordered_calls_are_reported(golden):
    misordered = {call.tool_use_id for call in golden.misordered_tool_calls()}
    assert misordered == {"toolu_price", "toolu_fin"}
    assert golden.tool_calls["toolu_price"].line_gap == 4
    assert golden.tool_calls["toolu_fin"].line_gap == 2


def test_interrupted_request_is_kept_as_unresolved(golden):
    unresolved = golden.unresolved_tool_calls()
    assert [call.tool_use_id for call in unresolved] == ["toolu_cut"]
    assert unresolved[0].line_gap == -1
    assert unresolved[0].result_text == ""


def test_tool_calls_can_be_found_by_name(golden):
    calls = tool_calls_by_name(golden, ["vn_ohlcv", "vn_financials"])
    assert [call.name for call in calls] == ["vn_ohlcv", "vn_financials"]
    assert calls[0].tool_input["symbol"] == "FPT"


def test_result_status_is_recorded(golden):
    assert golden.tool_calls["toolu_price"].status == "ok"
    assert golden.tool_calls["toolu_cut"].status == "unresolved"


# --- timestamps are advisory, line order is authoritative ---------------------


def test_observed_at_never_goes_backwards(golden):
    stamps = [event.observed_at for event in golden.events]
    assert stamps == sorted(stamps)


def test_raw_timestamp_regression_is_preserved_but_not_used(golden):
    late = golden.event_by_uuid("u2")
    regressed = golden.event_by_uuid("u3")
    assert late is not None and regressed is not None
    assert regressed.timestamp < late.timestamp  # the clock went backwards
    assert regressed.observed_at == late.observed_at  # the wall did not


def test_events_until_uses_the_monotonic_wall(golden):
    kept = {event.uuid for event in golden.events_until("2026-08-27T02:00:11.000Z")}
    assert kept == {"u1", "a1", "u2", "u3"}


def test_events_are_returned_in_line_order(golden):
    assert [event.uuid for event in golden.events] == ["u1", "a1", "u2", "u3", "a2", "s1", "a3"]
    assert [event.line_no for event in golden.events] == [1, 3, 5, 7, 8, 10, 12]


# --- content filtering --------------------------------------------------------


def test_thinking_is_excluded_from_text_but_flagged(golden):
    event = golden.event_by_uuid("a1")
    assert event is not None
    assert event.has_thinking is True
    assert "suy luận" not in event.text
    assert event.text == "Em lấy giá và báo cáo tài chính cùng lúc."


def test_string_and_block_content_both_parse(golden):
    assert golden.event_by_uuid("u1").text == "Phân tích FPT giúp anh."
    assert "Mục tiêu 58.800" in golden.event_by_uuid("a2").text


def test_harness_bookkeeping_is_dropped_silently(golden):
    kinds = {event.kind for event in golden.events}
    assert kinds == {"user", "assistant", "system"}
    assert not kinds & HARNESS_TYPES


def test_unknown_event_type_is_surfaced_not_swallowed(golden):
    assert golden.unknown_types == {"harness-invented-later": 1}


def test_truncated_tail_is_counted_not_raised(golden):
    assert golden.malformed_lines == 1
    assert len(golden.events) == 7


# --- provenance and the DAG ---------------------------------------------------


def test_each_event_hashes_its_own_raw_line(golden):
    hashes = [event.sha256 for event in golden.events]
    assert len(set(hashes)) == len(hashes)
    assert all(len(item) == 64 for item in hashes)


def test_thread_walks_parent_uuid_to_the_root(golden):
    chain = [event.uuid for event in golden.thread("a3")]
    assert chain == ["u1", "a1", "u2", "u3", "a2", "s1", "a3"]


def test_thread_of_an_unknown_uuid_is_empty(golden):
    assert golden.thread("nope") == []


def test_session_and_environment_are_carried(golden):
    event = golden.event_by_uuid("a1")
    assert golden.session_id == "sess-golden"
    assert event.git_branch == "main"
    assert event.cli_version == "2.1.247"


def test_usage_is_summed_for_the_process_record(golden):
    assert golden.usage["input_tokens"] == 2200
    assert golden.usage["output_tokens"] == 800
    assert golden.usage["cache_read_input_tokens"] == 8000


def test_orphan_result_is_kept_when_the_file_starts_mid_conversation(tmp_path):
    path = tmp_path / "partial.jsonl"
    path.write_text(
        '{"type":"user","uuid":"u1","parentUuid":null,"sessionId":"s","timestamp":'
        '"2026-08-27T02:00:00.000Z","message":{"content":[{"type":"tool_result",'
        '"tool_use_id":"toolu_missing","content":"kết quả mồ côi","is_error":true}]}}\n',
        encoding="utf-8",
    )
    transcript = parse_transcript(path)
    call = transcript.tool_calls["toolu_missing"]
    assert call.request_line == -1
    assert call.status == "error"
    assert call.result_text == "kết quả mồ côi"


def test_session_id_falls_back_to_the_filename(tmp_path):
    path = tmp_path / "abc123.jsonl"
    path.write_text("", encoding="utf-8")
    assert parse_transcript(path).session_id == "abc123"


def test_transcript_dir_honours_the_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_TRANSCRIPT_DIR", str(tmp_path))
    assert default_transcript_dir() == tmp_path


def test_iter_transcripts_reads_a_directory(tmp_path):
    import shutil

    shutil.copy(FIXTURE, tmp_path / "one.jsonl")
    shutil.copy(FIXTURE, tmp_path / "two.jsonl")
    assert len(list(iter_transcripts(tmp_path))) == 2


# --- the real corpus, when it is on this machine ------------------------------


@pytest.mark.skipif(
    not default_transcript_dir().exists(), reason="Claude Code transcripts not on this machine"
)
def test_real_transcripts_satisfy_the_parser_invariants():
    seen = 0
    for transcript in iter_transcripts():
        seen += 1
        assert transcript.malformed_lines == 0
        assert transcript.unknown_types == {}, (
            f"{transcript.path.name} has event types this parser has never seen: "
            f"{transcript.unknown_types}. The harness format moved."
        )
        stamps = [event.observed_at for event in transcript.events]
        assert stamps == sorted(stamps)
        for call in transcript.tool_calls.values():
            if call.status == "unresolved":
                assert call.result_line == -1
            else:
                assert call.result_line >= 0
                assert call.result_uuid
    assert seen > 0
