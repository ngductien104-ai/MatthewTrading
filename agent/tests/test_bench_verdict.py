"""Tests for carrying a strict-bench verdict onto a hypothesis.

The bench already knows which alphas survived a permutation control out of
sample. Until this bridge existed the answer was returned to a model and
dropped, while ``status`` could be set to ``validated`` by typing it.
"""

from __future__ import annotations

import pytest

from src.hypotheses.bench_verdict import (
    BENCH_STATUS,
    BenchVerdictError,
    apply_bench_verdict,
    verdict_for,
)
from src.hypotheses.registry import HypothesisRegistry


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_HYPOTHESES_PATH", str(tmp_path / "hyp.json"))
    return HypothesisRegistry()


def bench(category="confirmed_alive", alpha_id="alpha_001", **overrides):
    """A strict-bench result shaped like run_bench_strict's."""
    result = {
        "status": "ok",
        "zoo": "alpha101",
        "universe": "csi300",
        "period": "2020-2024",
        "oos_split": "2023-01-01",
        "alpha_t_threshold": 3.5,
        "random_control": True,
        "n_random_seeds": 5,
        "skipped": [],
        "rows": [
            {
                "id": alpha_id,
                "_category": category,
                "alpha_t_full": 4.1,
                "alpha_t_train": 4.4,
                "alpha_t_test": 3.7,
                "ic_mean": 0.031,
                "random_ic_mean": 0.001,
            },
            {"id": "alpha_002", "_category": "noise", "alpha_t_full": 0.2},
        ],
    }
    result.update(overrides)
    return result


class TestVerdictFor:
    def test_only_the_out_of_sample_survivor_graduates(self):
        assert BENCH_STATUS["confirmed_alive"] == "validated"
        assert verdict_for(bench(), "alpha_001")["status"] == "validated"

    @pytest.mark.parametrize("category", ["train_only", "reversed_strict", "noise"])
    def test_every_other_label_is_a_rejection_not_a_pause(self, category):
        """train_only is not an incomplete result, it is the shape of an overfit."""
        verdict = verdict_for(bench(category), "alpha_001")
        assert verdict["status"] == "rejected"
        assert verdict["reason"]

    def test_the_verdict_carries_the_statistics_it_was_derived_from(self):
        verdict = verdict_for(bench(), "alpha_001")
        assert verdict["alpha_t_test"] == 3.7
        assert verdict["alpha_t_threshold"] == 3.5
        assert verdict["random_control"] is True
        assert verdict["n_random_seeds"] == 5

    def test_a_failed_bench_settles_nothing(self):
        result = bench()
        result["status"] = "error"
        result["error"] = "universe panel empty"
        with pytest.raises(BenchVerdictError, match="settles nothing"):
            verdict_for(result, "alpha_001")

    def test_an_alpha_the_bench_never_scored_is_refused(self):
        with pytest.raises(BenchVerdictError, match="not in this bench result"):
            verdict_for(bench(), "alpha_999")

    def test_a_skipped_alpha_says_it_was_skipped_and_why(self):
        result = bench()
        result["skipped"] = [{"id": "alpha_003", "reason": "empty IC series"}]
        with pytest.raises(BenchVerdictError, match="empty IC series"):
            verdict_for(result, "alpha_003")

    def test_an_unknown_label_is_refused_rather_than_defaulted(self):
        """Every available default would claim a measurement nobody made."""
        with pytest.raises(BenchVerdictError, match="unrecognised bench category"):
            verdict_for(bench("promising"), "alpha_001")

    def test_the_public_category_key_is_read_when_the_private_one_is_stripped(self):
        result = bench()
        result["rows"][0] = {"id": "alpha_001", "category": "confirmed_alive"}
        assert verdict_for(result, "alpha_001")["status"] == "validated"


class TestApplyVerdict:
    def _hypothesis(self, registry):
        return registry.create(title="Reversal carries", thesis="Short-term reversal pays.")

    def test_a_confirmed_alpha_validates_the_hypothesis(self, registry):
        hyp = self._hypothesis(registry)
        updated = apply_bench_verdict(registry, hyp.hypothesis_id, bench(), "alpha_001")
        assert updated.status == "validated"

    def test_the_evidence_is_on_the_record_before_the_status_moves(self, registry):
        hyp = self._hypothesis(registry)
        updated = apply_bench_verdict(registry, hyp.hypothesis_id, bench(), "alpha_001")
        card = updated.run_cards[-1]
        assert card["metrics"]["bench_category"] == "confirmed_alive"
        assert "strict bench" in card["notes"]
        assert "alpha101" in card["run_card_path"]

    def test_a_failing_alpha_rejects_it(self, registry):
        hyp = self._hypothesis(registry)
        updated = apply_bench_verdict(
            registry, hyp.hypothesis_id, bench("train_only"), "alpha_001"
        )
        assert updated.status == "rejected"
        assert updated.run_cards[-1]["metrics"]["bench_category"] == "train_only"

    def test_a_rerun_adds_a_verdict_rather_than_replacing_the_first(self, registry):
        hyp = self._hypothesis(registry)
        apply_bench_verdict(registry, hyp.hypothesis_id, bench("noise"), "alpha_001")
        updated = apply_bench_verdict(registry, hyp.hypothesis_id, bench(), "alpha_001")
        assert len(updated.run_cards) == 2
        assert [card["metrics"]["bench_category"] for card in updated.run_cards] == [
            "noise",
            "confirmed_alive",
        ]

    def test_a_refused_verdict_leaves_the_hypothesis_untouched(self, registry):
        hyp = self._hypothesis(registry)
        with pytest.raises(BenchVerdictError):
            apply_bench_verdict(registry, hyp.hypothesis_id, bench(), "alpha_999")
        after = next(h for h in registry.list() if h.hypothesis_id == hyp.hypothesis_id)
        assert after.status == "exploring"
        assert after.run_cards == []


class TestValidatedNeedsEvidence:
    def test_typing_validated_is_refused(self, registry):
        hyp = registry.create(title="Momentum", thesis="Winners keep winning.")
        with pytest.raises(ValueError, match="cannot be set to 'validated'"):
            registry.update(hyp.hypothesis_id, status="validated")

    def test_a_bench_verdict_unlocks_it(self, registry):
        hyp = registry.create(title="Momentum", thesis="Winners keep winning.")
        apply_bench_verdict(registry, hyp.hypothesis_id, bench(), "alpha_001")
        # And it stays reachable afterwards, since the evidence is now linked.
        assert registry.update(hyp.hypothesis_id, status="validated").status == "validated"

    def test_an_override_is_allowed_but_written_down(self, registry):
        hyp = registry.create(title="Momentum", thesis="Winners keep winning.")
        updated = registry.update(
            hyp.hypothesis_id, status="validated", evidence_override="replicated from the paper"
        )
        assert updated.status == "validated"
        assert "replicated from the paper" in updated.invalidation_notes
        assert "validated by override" in updated.invalidation_notes

    def test_an_override_survives_a_same_call_note_replacement(self, registry):
        """Otherwise the update that claimed validated could erase its own reason."""
        hyp = registry.create(title="Momentum", thesis="Winners keep winning.")
        updated = registry.update(
            hyp.hypothesis_id,
            status="validated",
            evidence_override="replicated from the paper",
            invalidation_notes="watch decay",
        )
        assert "watch decay" in updated.invalidation_notes
        assert "replicated from the paper" in updated.invalidation_notes

    def test_a_new_hypothesis_cannot_be_born_validated(self, registry):
        """Guarding only update would leave the door it never came through open."""
        with pytest.raises(ValueError, match="cannot start at 'validated'"):
            registry.create(title="Carry", thesis="Carry pays.", status="validated")

    def test_a_rejection_needs_no_evidence_because_it_claims_none(self, registry):
        hyp = registry.create(title="Carry", thesis="Carry pays.")
        assert registry.update(hyp.hypothesis_id, status="rejected").status == "rejected"
        assert registry.update(hyp.hypothesis_id, status="monitoring").status == "monitoring"


def test_the_bridge_covers_every_label_the_bench_can_emit():
    """Read the vocabulary off the bench itself.

    A label the bench emits and this map has no entry for would raise on a
    real run, having passed every test above.
    """
    import typing

    from src.factors.bench_runner_strict import StrictCategory

    assert set(BENCH_STATUS) == set(typing.get_args(StrictCategory))
