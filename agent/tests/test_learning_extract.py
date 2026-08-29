"""Tests for the extraction gates.

The property under test throughout is that the model cannot get a number into
the ledger by asserting it. Every price has to survive being re-read out of the
quote the model supplied, and every ambiguous scale has to be refused rather
than guessed -- because a target silently stored a thousand times too small
scores as a catastrophic miss and looks like a real one.

The sample strings are taken from the corpus this runs on, not invented: FPT's
27/08 report header, PHR's ``vùng 64-65`` entry band, VRE's ``22.000-27.500,
trung điểm 25.000``, MWG's ``Base 85-94k``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone

import pytest

from src.learning.extract import (
    ExtractionError,
    Rejection,
    SourceDocument,
    assign_revisions,
    build_prompt,
    extract_all,
    extract_document,
    iter_research_documents,
    iter_run_documents,
    load_document,
    parse_prices,
    parse_proposal,
    resolve_scale,
    store_result,
    validate_candidate,
)
from src.learning.records import RecordValidationError, latest_revision
from src.learning.store import LearningStore

FPT_HEADER = (
    "**Ngày báo cáo:** 27/08/2026 · **Giá chốt:** 72.200 đ/cp · "
    "**KLCP lưu hành:** 1.714.326.422"
)
FPT_CALL = "**Giá mục tiêu ~58.800 đ (−18,6%)** · Bear 26.100 đ (−63,8%)"


def _write(tmp_path, name: str, text: str, mtime: str = "2026-08-27T08:41:00Z"):
    """Write a document and pin its mtime, which is its ``observed_at``."""
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    stamp = datetime.fromisoformat(mtime.replace("Z", "+00:00")).timestamp()
    os.utime(path, (stamp, stamp))
    return path


@pytest.fixture
def document(tmp_path):
    body = "\n".join(["# FPT", "", FPT_HEADER, "", "> Khuyến nghị: GIẢM TỶ TRỌNG", FPT_CALL])
    path = _write(tmp_path, "_fpt_research/00_bao_cao.md", body)
    from src.learning.extract import _document

    return _document(path, "markdown", "_fpt_research")


def _candidate(**overrides):
    base = {
        "ticker": "FPT",
        "as_of": "2026-08-27",
        "action": "GIẢM TỶ TRỌNG",
        "ref_price": 72200,
        "target": 58800,
        "bear": 26100,
        "quotes": [FPT_HEADER, FPT_CALL],
    }
    base.update(overrides)
    return base


# -- reading numbers ----------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected_value, expected_anchored",
    [
        ("Giá mục tiêu ~58.800 đ", 58800.0, True),
        ("Base 85–94k", 94000.0, True),
        ("mua HDB khi lùi ≤25,8k", 25800.0, True),
        ("trung điểm 25.000", 25000.0, True),
        ("stop kỷ luật dưới **60**", 60.0, False),
    ],
)
def test_scale_is_read_from_the_writing(text, expected_value, expected_anchored):
    prices = [n for n in parse_prices(text) if n.kind == "price"]
    match = [n for n in prices if n.value == expected_value]
    assert match, f"{expected_value} not found in {[n.value for n in prices]}"
    assert match[0].anchored is expected_anchored


def test_billions_are_not_prices():
    kinds = {n.raw.strip(): n.kind for n in parse_prices("dùng 6.932 tỷ (biên 19,24%)")}
    assert kinds["6.932 tỷ"] == "billion"
    assert kinds["19,24%"] == "percent"


def test_date_parts_are_not_prices():
    """A stray 2026 must not be able to vouch for a fabricated index level."""
    kinds = {n.kind for n in parse_prices("**Ngày báo cáo:** 27/08/2026")}
    assert kinds == {"date"}


def test_share_count_is_read_at_full_scale():
    values = [n.value for n in parse_prices(FPT_HEADER) if n.kind == "price"]
    assert 72200.0 in values
    assert 1714326422.0 in values


def test_resolve_scale_multiplies_only_when_the_ratio_proves_it():
    value, note = resolve_scale(58.8, 72200.0, "target")
    assert value == 58800.0
    assert "58800" in note


def test_resolve_scale_leaves_an_already_anchored_price_alone():
    assert resolve_scale(58800.0, 72200.0, "target") == (58800.0, "")


def test_resolve_scale_refuses_when_neither_reading_is_plausible():
    with pytest.raises(ExtractionError, match="ambiguous"):
        resolve_scale(0.5, 72200.0, "target")


def test_resolve_scale_refuses_without_an_anchor():
    """No ruler, no answer. Storing 60 dong is worse than storing nothing."""
    with pytest.raises(ExtractionError, match="no ref_price"):
        resolve_scale(60.0, None, "stop")


# -- the citation gate --------------------------------------------------------


def test_a_quoted_call_becomes_a_record(document):
    record, evidence = validate_candidate(_candidate(), document)
    assert record.ticker == "FPT"
    assert record.action == "reduce"
    assert record.target == 58800.0
    assert record.bear == 26100.0
    assert record.known_at == document.observed_at
    assert [item.evidence_id for item in evidence] == record.evidence_ids


def test_the_line_span_is_computed_not_taken_on_trust(document):
    _, evidence = validate_candidate(_candidate(), document)
    spans = {item.excerpt: item.locator for item in evidence}
    assert spans[FPT_HEADER] == "L3-L3"
    assert spans[FPT_CALL] == "L6-L6"


def test_a_paraphrase_is_not_a_citation(document):
    candidate = _candidate(quotes=["Giá mục tiêu khoảng 58.800 đồng mỗi cổ phiếu"])
    with pytest.raises(ExtractionError, match="quote not found"):
        validate_candidate(candidate, document)


def test_a_number_absent_from_its_own_quote_is_refused(document):
    with pytest.raises(ExtractionError, match="does not appear"):
        validate_candidate(_candidate(target=61000), document)


def test_a_call_with_no_quotes_is_refused(document):
    with pytest.raises(ExtractionError, match="uncited"):
        validate_candidate(_candidate(quotes=[]), document)


@pytest.mark.parametrize("field_name", ["ticker", "as_of", "action"])
def test_the_three_required_fields_are_required(document, field_name):
    with pytest.raises(ExtractionError, match="is required"):
        validate_candidate(_candidate(**{field_name: ""}), document)


def test_an_action_outside_the_vocabulary_is_refused_not_guessed(document):
    with pytest.raises(RecordValidationError, match="unknown action"):
        validate_candidate(_candidate(action="CÂN NHẮC THÊM"), document)


def test_a_missing_target_is_incomplete_not_rejected(document):
    record, _ = validate_candidate(_candidate(target=None), document)
    assert record.target is None
    assert record.extraction_status == "incomplete"


def test_a_target_five_times_the_reference_price_is_a_unit_error(tmp_path):
    from src.learning.extract import _document

    body = "Giá chốt 72.200 đ · mục tiêu 580.000 đ"
    path = _write(tmp_path, "_x/doc.md", body)
    doc = _document(path, "markdown", "_x")
    candidate = _candidate(target=580000, bear=None, quotes=[body])
    with pytest.raises(ExtractionError, match="not a forecast"):
        validate_candidate(candidate, doc)


def test_a_document_cannot_report_a_call_from_its_own_future(document):
    with pytest.raises(ExtractionError, match="own future"):
        validate_candidate(_candidate(as_of="2026-08-28"), document)


# -- the thousands trap, end to end -------------------------------------------


def test_a_bare_target_is_rescaled_against_the_anchored_reference(tmp_path):
    """PHR's ``vùng 64-65`` sits beside an anchored close in the same report."""
    from src.learning.extract import _document

    body = "Giá đóng cửa 61.500 đ. Chốt/giảm tỷ trọng vùng 64–65, stop dưới 60."
    path = _write(tmp_path, "_phr/doc.md", body)
    doc = _document(path, "markdown", "_phr")
    candidate = {
        "ticker": "PHR",
        "as_of": "2026-08-27",
        "action": "giảm tỷ trọng",
        "ref_price": 61500,
        "target": 64,
        "stop": 60,
        "quotes": [body],
    }
    record, _ = validate_candidate(candidate, doc)
    assert record.target == 64000.0
    assert record.stop == 60000.0
    assert "read as 64000" in record.notes


def test_a_bare_reference_price_is_settled_only_by_an_anchored_quote(tmp_path):
    from src.learning.extract import _document

    body = "Giá đóng cửa 61.500 đ, tương đương 61,5 nghìn."
    path = _write(tmp_path, "_phr/doc.md", body)
    doc = _document(path, "markdown", "_phr")
    candidate = {
        "ticker": "PHR",
        "as_of": "2026-08-27",
        "action": "giữ",
        "ref_price": 61.5,
        "quotes": [body],
    }
    record, _ = validate_candidate(candidate, doc)
    assert record.ref_price == 61500.0


def test_an_unanchored_reference_price_is_refused(tmp_path):
    from src.learning.extract import _document

    body = "Vùng gom 50,5–51,8; mục tiêu 60."
    path = _write(tmp_path, "_pet/doc.md", body)
    doc = _document(path, "markdown", "_pet")
    candidate = {
        "ticker": "PET",
        "as_of": "2026-08-27",
        "action": "tích lũy",
        "ref_price": 51.15,
        "quotes": [body],
    }
    with pytest.raises(ExtractionError, match="must not be inferred"):
        validate_candidate(candidate, doc)


def test_a_band_vouches_for_its_own_midpoint(tmp_path):
    """VRE: ``giá trị hợp lý 22.000-27.500`` supports a 25.000 midpoint."""
    from src.learning.extract import _document

    body = "Giá 24.300 đ. Giá trị hợp lý 22.000–27.500."
    path = _write(tmp_path, "_vre/doc.md", body)
    doc = _document(path, "markdown", "_vre")
    candidate = {
        "ticker": "VRE",
        "as_of": "2026-08-27",
        "action": "trung lập",
        "ref_price": 24300,
        "target": 24750,
        "quotes": [body],
    }
    record, _ = validate_candidate(candidate, doc)
    assert record.target == 24750.0
    assert "band quoted" in record.notes


# -- confidence ---------------------------------------------------------------


def test_a_stated_percentage_backs_the_fraction(tmp_path):
    from src.learning.extract import _document

    body = "Giá 61.500 đ. **Confidence: 61%** (vừa phải-tích cực)."
    path = _write(tmp_path, "_phr/doc.md", body)
    doc = _document(path, "markdown", "_phr")
    candidate = {
        "ticker": "PHR",
        "as_of": "2026-08-27",
        "action": "mua theo đợt",
        "ref_price": 61500,
        "confidence": 0.61,
        "quotes": [body],
    }
    record, _ = validate_candidate(candidate, doc)
    assert record.confidence == 0.61


def test_confidence_written_as_a_percent_still_fails_the_unit_gate(tmp_path):
    from src.learning.extract import _document

    body = "Giá 61.500 đ. **Confidence: 61%**."
    path = _write(tmp_path, "_phr/doc.md", body)
    doc = _document(path, "markdown", "_phr")
    candidate = {
        "ticker": "PHR",
        "as_of": "2026-08-27",
        "action": "mua theo đợt",
        "ref_price": 61500,
        "confidence": 61,
        "quotes": [body],
    }
    with pytest.raises(RecordValidationError, match="fraction"):
        validate_candidate(candidate, doc)


# -- the proposal envelope ----------------------------------------------------


def test_a_fenced_reply_is_accepted():
    raw = '```json\n{"calls": [{"ticker": "FPT"}]}\n```'
    assert parse_proposal(raw) == [{"ticker": "FPT"}]


def test_a_bare_list_is_accepted():
    assert parse_proposal('[{"ticker": "FPT"}]') == [{"ticker": "FPT"}]


def test_unknown_fields_are_dropped_rather_than_forwarded():
    raw = '{"calls": [{"ticker": "FPT", "verdict": "hit", "realized_ret": 0.4}]}'
    assert parse_proposal(raw) == [{"ticker": "FPT"}]


def test_a_non_json_reply_is_an_extraction_error():
    with pytest.raises(ExtractionError, match="not JSON"):
        parse_proposal("I found three calls in this document.")


def test_the_prompt_carries_the_document_and_its_wall(document):
    prompt = build_prompt(document)
    assert document.observed_at in prompt
    assert FPT_CALL in prompt


# -- document level -----------------------------------------------------------


def test_a_broken_reply_does_not_halt_the_backfill(document):
    result = extract_document(document, lambda prompt: "not json at all")
    assert result.calls == []
    assert [item.code for item in result.rejections] == ["bad_json"]


def test_refusals_are_recorded_with_a_code(document):
    reply = json.dumps({"calls": [_candidate(target=61000), _candidate()]})
    result = extract_document(document, lambda prompt: reply)
    assert len(result.calls) == 1
    assert [item.code for item in result.rejections] == ["number_not_in_evidence"]


def test_two_calls_on_one_ticker_in_one_document_are_two_revisions(document):
    reply = json.dumps({"calls": [_candidate(target=None), _candidate()]})
    result = extract_document(document, lambda prompt: reply)
    assert [record.revision for record in result.calls] == [1, 2]
    assert len({record.call_id for record in result.calls}) == 2


# -- episodes -----------------------------------------------------------------


def test_the_fpt_walk_down_is_one_episode_of_four_revisions(tmp_path):
    """93.000 -> 69.500 -> 59.000 -> 58.800 is one observation, not four."""
    from src.learning.extract import _document

    targets = [93000, 69500, 59000, 58800]
    records = []
    for index, target in enumerate(targets):
        body = f"Giá chốt 72.200 đ · Giá mục tiêu {target:,.0f} đ".replace(",", ".")
        path = _write(
            tmp_path,
            f"_fpt_research/0{index}_round.md",
            body,
            mtime=f"2026-08-2{7 + index // 4}T0{index}:00:00Z",
        )
        doc = _document(path, "markdown", "_fpt_research")
        record, _ = validate_candidate(
            _candidate(target=target, bear=None, quotes=[body]), doc
        )
        records.append(record)

    ordered = assign_revisions(records)
    assert [record.revision for record in ordered] == [1, 2, 3, 4]
    assert len({record.episode_id for record in ordered}) == 1
    assert ordered[0].supersedes == ""
    assert ordered[3].supersedes == ordered[2].call_id
    assert latest_revision(ordered).target == 58800.0


def test_assign_revisions_leaves_the_inputs_untouched(document):
    record, _ = validate_candidate(_candidate(), document)
    before = record.to_dict()
    assign_revisions([record])
    assert record.to_dict() == before


def test_two_tickers_are_two_episodes(tmp_path):
    from src.learning.extract import _document

    body = "Giá chốt 72.200 đ · Giá mục tiêu 58.800 đ"
    path = _write(tmp_path, "_mixed/doc.md", body)
    doc = _document(path, "markdown", "_mixed")
    records = [
        validate_candidate(_candidate(ticker=ticker, bear=None, quotes=[body]), doc)[0]
        for ticker in ("FPT", "VRE")
    ]
    assert len({record.episode_id for record in assign_revisions(records)}) == 2


# -- the ledger ---------------------------------------------------------------


def test_an_extraction_reaches_the_ledger_evidence_first(tmp_path, document):
    reply = json.dumps({"calls": [_candidate()]})
    result = extract_document(document, lambda prompt: reply)
    with LearningStore(tmp_path / "learning.db") as store:
        appended = store_result(store, result)
        assert [item.appended for item in appended] == [True]
        stored = store.get_call(result.calls[0].call_id)
        assert stored.target == 58800.0
        assert store.counts()["evidence"] == 2


def test_re_running_the_same_extraction_appends_nothing(tmp_path, document):
    reply = json.dumps({"calls": [_candidate()]})
    with LearningStore(tmp_path / "learning.db") as store:
        first = store_result(store, extract_document(document, lambda p: reply))
        second = store_result(store, extract_document(document, lambda p: reply))
        assert [item.appended for item in first] == [True]
        assert [item.appended for item in second] == [False]
        assert store.counts()["calls"] == 1


def test_the_scoring_point_is_the_last_revision(tmp_path, document):
    reply = json.dumps({"calls": [_candidate(target=None), _candidate()]})
    result = extract_document(document, lambda prompt: reply)
    result.calls = assign_revisions(result.calls)
    with LearningStore(tmp_path / "learning.db") as store:
        store_result(store, result)
        point = store.scoring_point(result.calls[0].episode_id)
        assert point.revision == 2
        assert point.target == 58800.0


# -- source discovery ---------------------------------------------------------


def test_research_documents_are_grouped_by_folder(tmp_path):
    _write(tmp_path, "_fpt_research/00.md", "a")
    _write(tmp_path, "_fpt_research/01.md", "b")
    _write(tmp_path, "_vre_committee/BEAR.md", "c")
    _write(tmp_path, "notes/skipped.md", "d")
    documents = list(iter_research_documents(tmp_path))
    assert [item.episode_key for item in documents] == [
        "_fpt_research",
        "_fpt_research",
        "_vre_committee",
    ]


def test_runs_without_a_final_report_are_skipped(tmp_path):
    """Fifteen of the eighteen runs on disk hold an empty string."""
    runs = tmp_path / "runs"
    _write(runs, "swarm-a/run.json", json.dumps({"final_report": ""}))
    _write(runs, "swarm-b/run.json", json.dumps({"final_report": "MUA FPT ở 72.200 đ"}))
    _write(runs, "swarm-c/run.json", "{not json")
    documents = list(iter_run_documents(runs))
    assert [item.episode_key for item in documents] == ["swarm-b"]
    assert documents[0].kind == "run_artifact"


def test_a_markdown_source_carries_no_session_id(document):
    """The episode key is the folder; pretending it is a session would be a lie."""
    assert document.session_id == ""
    assert document.episode_key == "_fpt_research"
    record, _ = validate_candidate(_candidate(), document)
    assert record.source_session_id == ""
    assert record.source_path.endswith("00_bao_cao.md")


def test_extract_all_settles_revisions_across_documents(tmp_path):
    from src.learning.extract import _document

    documents = []
    for index, target in enumerate((69500, 58800)):
        body = f"Giá chốt 72.200 đ · Giá mục tiêu {target:,.0f} đ".replace(",", ".")
        path = _write(tmp_path, f"_fpt_research/0{index}.md", body, mtime=f"2026-08-27T0{index}:00:00Z")
        documents.append(_document(path, "markdown", "_fpt_research"))

    def propose(prompt: str) -> str:
        target = 69500 if "69.500" in prompt else 58800
        body = prompt.split("---\n")[1].split("\n---")[0].strip()
        return json.dumps({"calls": [_candidate(target=target, bear=None, quotes=[body])]})

    result = extract_all(documents, propose)
    assert [record.revision for record in result.calls] == [1, 2]
    assert latest_revision(result.calls).target == 58800.0


def test_a_rejection_is_a_plain_record_of_what_was_refused():
    rejection = Rejection("scale_ambiguous", "message", "doc_1", "PHR", {"ticker": "PHR"})
    assert rejection.code == "scale_ambiguous"
    assert rejection.candidate["ticker"] == "PHR"


def test_source_document_observed_at_is_the_file_mtime(tmp_path):
    from src.learning.extract import _document

    path = _write(tmp_path, "_x/doc.md", "body", mtime="2026-07-24T03:15:00Z")
    doc: SourceDocument = _document(path, "markdown", "_x")
    assert doc.observed_at == "2026-07-24T03:15:00Z"
    assert datetime.fromisoformat(doc.observed_at.replace("Z", "+00:00")).tzinfo == timezone.utc


# -- the real corpus, when it is on this machine -------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HAS_CORPUS = any(p.is_dir() and p.name.startswith("_") for p in _REPO_ROOT.iterdir())


@pytest.mark.skipif(not _HAS_CORPUS, reason="research folders not on this machine")
def test_real_research_documents_satisfy_the_parser_invariants():
    """Run the deterministic half over the 4.3 MB of prose it was measured on.

    No model is involved: this checks that the number reader never regresses
    into calling a percentage, a billion or a date part a price, which is the
    way a fabricated target would slip past the citation gate.
    """
    documents = 0
    kinds: set[str] = set()
    for document in iter_research_documents(_REPO_ROOT):
        documents += 1
        assert document.sha256
        assert document.episode_key.startswith("_")
        assert document.observed_at.endswith("Z")
        for number in parse_prices(document.text):
            kinds.add(number.kind)
            assert number.value == number.value  # never NaN
            assert number.value >= 0
            if number.kind == "price":
                assert "%" not in number.raw
                assert "tỷ" not in number.raw
                assert "triệu" not in number.raw
    assert documents > 50, f"expected the research corpus, found {documents} documents"
    assert {"price", "percent", "billion", "date"} <= kinds


def test_a_price_reported_as_text_is_refused_not_crashed(document):
    """``"58.800 đ"`` in a number field skips the step where the scale is settled."""
    result = extract_document(
        document, lambda prompt: json.dumps({"calls": [_candidate(target="58.800 đ")]})
    )
    assert result.calls == []
    assert [item.code for item in result.rejections] == ["invalid_record"]
    assert "is not a number" in result.rejections[0].message


# -- loading a document by path ------------------------------------------------


def test_the_episode_key_comes_from_the_research_folder(tmp_path):
    path = _write(tmp_path, "_fpt_research/sub/00.md", "Giá chốt 72.200 đ")
    document = load_document(path)
    assert document.episode_key == "_fpt_research"
    assert document.kind == "markdown"


def test_a_file_outside_a_research_folder_keeps_its_own_parent(tmp_path):
    """It must not silently join somebody else's episode."""
    path = _write(tmp_path, "notes/loose.md", "Giá chốt 72.200 đ")
    assert load_document(path).episode_key == "notes"


def test_a_run_artifact_is_unwrapped_to_its_report(tmp_path):
    path = _write(tmp_path, "runs/swarm-b/run.json", json.dumps({"final_report": "MUA FPT"}))
    document = load_document(path)
    assert document.text == "MUA FPT"
    assert (document.kind, document.episode_key) == ("run_artifact", "swarm-b")


def test_an_empty_run_report_is_refused_rather_than_loaded(tmp_path):
    path = _write(tmp_path, "runs/swarm-a/run.json", json.dumps({"final_report": ""}))
    with pytest.raises(ExtractionError, match="empty final_report"):
        load_document(path)


# -- the two decimal conventions this corpus mixes -----------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Giá tham chiếu **54.8**", 54.8),
        ("chỉ ≤ 53,5", 53.5),
        ("EPS_TTM ~2.700", 2700.0),
        ("Giá chốt 72.200 đ/cp", 72200.0),
        ("KLCP 1.714.326.422", 1714326422.0),
    ],
)
def test_a_dot_before_three_digits_groups_and_before_fewer_decimates(text, expected):
    """``54.8`` and ``53,5`` sit four lines apart in one real document.

    Reading the dot as a thousands group truncates the price to ``54``. The
    dot-decimal form appears 5,909 times across 32 research folders, so this is
    the convention, not an anomaly.
    """
    values = [number.value for number in parse_prices(text) if number.kind == "price"]
    assert expected in values


def test_only_the_grouped_form_is_anchored():
    """``26.35`` leaves the scale open; ``26.350`` pins it."""
    by_raw = {n.raw.strip(): n for n in parse_prices("26.35 và 26.350")}
    assert by_raw["26.35"].anchored is False
    assert by_raw["26.350"].anchored is True


def test_a_bare_reference_price_is_settled_by_any_anchored_price_quoted(tmp_path):
    """PHR states ``62,0`` but quotes ``~72k`` in the same call.

    Demanding an anchored token equal to ref_price x 1000 was too strict: what
    settles the scale is that one reading sits in a sane ratio to a price the
    document does state with a unit.
    """
    from src.learning.extract import _document

    body = "Giá tham chiếu 62,0 (đóng cửa). BASE: RNAV thận trọng ~72k."
    path = _write(tmp_path, "_phr/doc.md", body)
    doc = _document(path, "markdown", "_phr")
    candidate = {
        "ticker": "PHR",
        "as_of": "2026-08-27",
        "action": "mua theo đợt",
        "ref_price": 62.0,
        "target": 72,
        "quotes": [body],
    }
    record, _ = validate_candidate(candidate, doc)
    assert record.ref_price == 62000.0
    assert record.target == 72000.0


def test_a_share_count_is_not_allowed_to_be_the_ruler(tmp_path):
    """Only numbers inside a plausible share-price band settle the scale."""
    from src.learning.extract import _document

    body = "Giá tham chiếu 54.8. KLCP lưu hành 1.714.326.422."
    path = _write(tmp_path, "_pet/doc.md", body)
    doc = _document(path, "markdown", "_pet")
    candidate = {
        "ticker": "PET",
        "as_of": "2026-08-27",
        "action": "chờ",
        "ref_price": 54.8,
        "quotes": [body],
    }
    with pytest.raises(ExtractionError, match="no quote states any price"):
        validate_candidate(candidate, doc)
