"""Tests for feeding the ledger back into the next piece of work.

Recall is an enhancement, never a dependency: the tests that matter most here
are the ones checking that a broken ledger costs a run nothing.
"""

from __future__ import annotations

import pytest

from src.learning.recall import MAX_CHARS, MAX_LESSONS, playbook_block, render_block
from src.learning.records import Lesson


def lesson(statement, *, domain="calibration", status="provisional", support=3):
    return Lesson(
        domain=domain,
        statement=statement,
        status=status,
        support_count=support,
        evidence_ids=["ev_1"] if status == "confirmed" else [],
    )


class TestRenderBlock:
    def test_nothing_learned_renders_nothing_at_all(self):
        """A header announcing an empty playbook spends tokens saying nothing."""
        assert render_block([]) == ""

    def test_a_lesson_arrives_with_its_weight_attached(self):
        block = render_block([lesson("Confidence runs high.", support=7)])
        assert "Confidence runs high." in block
        assert "provisional, n=7" in block
        assert "[calibration]" in block

    def test_confirmed_lessons_lead(self):
        block = render_block([
            lesson("Weak.", support=99),
            lesson("Strong.", status="confirmed", support=8),
        ])
        assert block.index("Strong.") < block.index("Weak.")

    def test_within_a_status_the_better_evidenced_line_leads(self):
        block = render_block([lesson("Thin.", support=2), lesson("Thick.", support=40)])
        assert block.index("Thick.") < block.index("Thin.")

    def test_the_block_is_capped_so_it_stays_read_rather_than_skimmed(self):
        lessons = [lesson(f"Finding number {index}.", support=index) for index in range(40)]
        block = render_block(lessons)
        assert block.count("\n- **") == MAX_LESSONS

    def test_an_overlong_block_is_truncated_visibly(self):
        lessons = [lesson("x" * 900 + f" {index}", support=index) for index in range(10)]
        block = render_block(lessons)
        assert len(block) <= MAX_CHARS + 40
        assert "_(truncated)_" in block

    def test_the_header_invites_contradiction_rather_than_obedience(self):
        """A playbook that only accumulates agreement amplifies its own bias."""
        block = render_block([lesson("Something.")])
        assert "argued with" in block
        assert "not written by a model" in block
        assert "provisional line" in block


class TestPlaybookBlock:
    def test_it_reads_the_live_lessons_from_a_store(self, tmp_path):
        from src.learning.store import LearningStore

        with LearningStore(tmp_path / "l.db") as store:
            store.append_lesson(lesson("Measured thing.", support=5))
            block = playbook_block(store=store)
        assert "Measured thing." in block

    def test_a_domain_filter_is_honoured(self, tmp_path):
        from src.learning.store import LearningStore

        with LearningStore(tmp_path / "l.db") as store:
            store.append_lesson(lesson("Calibration thing.", domain="calibration"))
            store.append_lesson(lesson("Process thing.", domain="process"))
            block = playbook_block(domain="process", store=store)
        assert "Process thing." in block
        assert "Calibration thing." not in block

    def test_a_broken_ledger_costs_the_run_nothing(self):
        """The decisive one: research that works without a playbook must not
        fail because of one."""

        class Exploding:
            def live_lessons(self, domain=None):
                raise RuntimeError("database is locked")

        assert playbook_block(store=Exploding()) == ""

    def test_a_missing_database_returns_an_empty_block(self, tmp_path, monkeypatch):
        monkeypatch.setenv(
            "VIBE_TRADING_LEARNING_DB_PATH", str(tmp_path / "nope" / "missing.db")
        )
        assert isinstance(playbook_block(), str)


class TestWorkerPrompt:
    def _spec(self, system_prompt="Do the work."):
        from src.swarm.models import SwarmAgentSpec

        return SwarmAgentSpec(id="a1", role="Analyst", system_prompt=system_prompt)

    def test_the_playbook_reaches_the_worker_prompt(self):
        from src.swarm.worker import build_worker_prompt

        prompt = build_worker_prompt(
            self._spec(), {}, "(no matching skills)", playbook_block="## Lessons\n- one"
        )
        assert "## Lessons" in prompt

    def test_it_does_not_ride_on_the_upstream_placeholder(self):
        """A preset that omits {upstream_context} drops that content silently.

        A playbook attached to it would be sometimes-present with no signal,
        which is worse than never present.
        """
        from src.swarm.worker import build_worker_prompt

        prompt = build_worker_prompt(
            self._spec(system_prompt="No placeholder here."),
            {"prior": "upstream text"},
            "(no matching skills)",
            playbook_block="## Lessons\n- one",
        )
        assert "upstream text" not in prompt  # the documented trap, unchanged
        assert "## Lessons" in prompt  # and the playbook survives it

    def test_no_playbook_leaves_the_prompt_exactly_as_it_was(self):
        from src.swarm.worker import build_worker_prompt

        without = build_worker_prompt(self._spec(), {}, "(no matching skills)")
        explicit = build_worker_prompt(
            self._spec(), {}, "(no matching skills)", playbook_block=""
        )
        assert without == explicit


def test_the_skill_exists_and_points_at_the_real_entry_points():
    """A skill naming a function that does not exist is worse than no skill."""
    from pathlib import Path

    skill = Path(__file__).resolve().parents[1] / "src" / "skills" / "research-memory" / "SKILL.md"
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert "name: research-memory" in text
    for reference in ("src.learning.recall", "playbook_block", "src.learning.lessons"):
        assert reference in text
