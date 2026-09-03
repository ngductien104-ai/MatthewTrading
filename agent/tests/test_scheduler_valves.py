"""Tests for the gates an unattended research cycle has to pass.

The one that matters most is the reliability gate, and the assertion that
matters most is that it currently refuses. The plan says a scheduler on a
runtime that finishes three runs in twenty-four automates the failing; this
file checks that the code says so too, against the real ledger rather than
against a fixture written to agree with it.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from src.scheduler import valves
from src.scheduler.valves import (
    CYCLE_BUDGET_ENV,
    ENABLED_ENV,
    FLOOR_ENV,
    NOVELTY_DAYS_ENV,
    PR_CAP_ENV,
    budget_valve,
    decide,
    enabled_valve,
    evidence_valve,
    novelty_valve,
    prs_opened_this_month,
    record_pr_opened,
    reliability_valve,
    render,
)


class TestEnabled:
    def test_off_unless_someone_opted_in(self):
        """A scheduler that runs because it was merged is one nobody chose."""
        assert enabled_valve("").passed is False
        assert enabled_valve(None if False else "").detail.startswith(ENABLED_ENV)

    @pytest.mark.parametrize("value", ["1", "true", "YES", "on"])
    def test_the_usual_affirmatives_all_work(self, value):
        assert enabled_valve(value).passed is True

    def test_anything_else_is_off(self):
        assert enabled_valve("maybe").passed is False
        assert enabled_valve("0").passed is False


class TestReliability:
    def test_it_refuses_below_the_floor(self):
        records = [{"completed": False}] * 21 + [{"completed": True}] * 4
        valve = reliability_valve(records, floor=0.5)
        assert valve.passed is False
        assert "16%" in valve.detail
        assert "automates the failing" in valve.detail

    def test_it_allows_at_or_above_the_floor(self):
        records = [{"completed": True}] * 5 + [{"completed": False}] * 5
        assert reliability_valve(records, floor=0.5).passed is True

    def test_no_records_is_a_refusal_not_a_pass(self):
        """A rate over zero runs is not a high number, it is no number."""
        valve = reliability_valve([], floor=0.5)
        assert valve.passed is False
        assert "unmeasured" in valve.detail

    def test_the_floor_comes_from_the_environment(self, monkeypatch):
        monkeypatch.setenv(FLOOR_ENV, "0.1")
        records = [{"completed": True}] + [{"completed": False}] * 4
        assert reliability_valve(records).passed is True

    def test_a_malformed_floor_falls_back_rather_than_disabling_the_gate(
        self, monkeypatch
    ):
        monkeypatch.setenv(FLOOR_ENV, "banana")
        records = [{"completed": True}] + [{"completed": False}] * 9
        assert reliability_valve(records).passed is False


class TestNovelty:
    CALLS = [
        {"ticker": "FPT", "as_of": "2026-08-27"},
        {"ticker": "MWG", "as_of": "2026-07-24"},
        {"ticker": "HAH", "as_of": "2026-06-15"},
    ]

    def test_a_recently_called_ticker_is_not_novel(self):
        valve, survivors = novelty_valve(
            ["FPT", "VNM"], self.CALLS, today=date(2026, 9, 4), window_days=90
        )
        assert survivors == ("VNM",)
        assert valve.passed is True

    def test_an_old_call_stops_blocking_once_it_leaves_the_window(self):
        _, survivors = novelty_valve(
            ["HAH"], self.CALLS, today=date(2026, 9, 4), window_days=30
        )
        assert survivors == ("HAH",)

    def test_nothing_novel_is_a_refusal(self):
        valve, survivors = novelty_valve(
            ["FPT"], self.CALLS, today=date(2026, 9, 4), window_days=90
        )
        assert survivors == ()
        assert valve.passed is False

    def test_an_unreadable_date_is_treated_as_recent(self):
        """Guessing it is old would re-research on an unreadable field."""
        _, survivors = novelty_valve(
            ["XYZ"], [{"ticker": "XYZ", "as_of": "not-a-date"}], today=date(2026, 9, 4)
        )
        assert survivors == ()

    def test_matching_ignores_case(self):
        _, survivors = novelty_valve(
            ["fpt"], self.CALLS, today=date(2026, 9, 4), window_days=90
        )
        assert survivors == ()

    def test_the_window_comes_from_the_environment(self, monkeypatch):
        monkeypatch.setenv(NOVELTY_DAYS_ENV, "5")
        _, survivors = novelty_valve(["MWG"], self.CALLS, today=date(2026, 9, 4))
        assert survivors == ("MWG",)


class TestEvidence:
    def test_a_provisional_lesson_does_not_open_the_gate(self):
        """Steering on provisional findings amplifies the loop's own guesses."""
        valve = evidence_valve([{"status": "provisional"}] * 4)
        assert valve.passed is False
        assert "0 confirmed of 4" in valve.detail

    def test_one_confirmed_lesson_is_enough(self):
        valve = evidence_valve([{"status": "confirmed"}, {"status": "provisional"}])
        assert valve.passed is True

    def test_no_lessons_at_all_refuses(self):
        assert evidence_valve([]).passed is False


class TestBudget:
    def test_under_the_monthly_cap_is_allowed(self):
        valve, ceiling = budget_valve(2, monthly_prs=4, cycle_tokens=1000)
        assert valve.passed is True
        assert ceiling == 1000

    def test_at_the_cap_is_refused(self):
        valve, _ = budget_valve(4, monthly_prs=4)
        assert valve.passed is False
        assert "monthly cap reached" in valve.detail

    def test_the_ceiling_comes_from_the_environment(self, monkeypatch):
        monkeypatch.setenv(CYCLE_BUDGET_ENV, "12345")
        monkeypatch.setenv(PR_CAP_ENV, "1")
        valve, ceiling = budget_valve(0)
        assert ceiling == 12345
        assert valve.passed is True

    def test_a_malformed_ceiling_falls_back_to_the_default(self, monkeypatch):
        monkeypatch.setenv(CYCLE_BUDGET_ENV, "lots")
        _, ceiling = budget_valve(0)
        assert ceiling == valves.DEFAULT_CYCLE_TOKENS


class TestMonthlyAccounting:
    def test_a_missing_file_counts_as_zero(self, tmp_path):
        assert prs_opened_this_month(root=tmp_path, today=date(2026, 9, 4)) == 0

    def test_opening_one_is_counted_against_its_month(self, tmp_path):
        record_pr_opened(root=tmp_path, today=date(2026, 9, 4))
        record_pr_opened(root=tmp_path, today=date(2026, 9, 20))
        assert prs_opened_this_month(root=tmp_path, today=date(2026, 9, 30)) == 2
        assert prs_opened_this_month(root=tmp_path, today=date(2026, 10, 1)) == 0

    def test_a_corrupt_file_does_not_jam_the_scheduler_shut(self, tmp_path):
        (tmp_path / "scheduler_prs.json").write_text("{not json", encoding="utf-8")
        assert prs_opened_this_month(root=tmp_path, today=date(2026, 9, 4)) == 0

    def test_the_file_stays_readable_json(self, tmp_path):
        record_pr_opened(root=tmp_path, today=date(2026, 9, 4))
        data = json.loads((tmp_path / "scheduler_prs.json").read_text(encoding="utf-8"))
        assert data == {"2026-09": 1}


class TestDecide:
    def _inputs(self, **overrides):
        base = dict(
            process_records=[{"completed": True}] * 8 + [{"completed": False}] * 2,
            calls=[{"ticker": "FPT", "as_of": "2026-08-27"}],
            lessons=[{"status": "confirmed"}],
            universe=["VNM", "GAS"],
            prs_this_month=0,
            today=date(2026, 9, 4),
            enabled="1",
        )
        base.update(overrides)
        return base

    def test_all_gates_open_allows_a_cycle(self):
        decision = decide(**self._inputs())
        assert decision.allowed is True
        assert decision.candidates == ("VNM", "GAS")

    def test_one_closed_gate_refuses(self):
        decision = decide(**self._inputs(enabled=""))
        assert decision.allowed is False
        assert len(decision.blockers()) == 1

    def test_every_gate_is_evaluated_even_after_the_first_refusal(self):
        """Otherwise four problems become four consecutive discoveries."""
        decision = decide(
            **self._inputs(
                enabled="",
                process_records=[{"completed": False}] * 10,
                lessons=[],
                universe=["FPT"],
            )
        )
        assert len(decision.valves) == 5
        assert len(decision.blockers()) == 4

    def test_the_rendering_names_each_gate_and_says_nothing_was_launched(self):
        text = render(decide(**self._inputs(enabled="")))
        assert "cycle REFUSED" in text
        assert "nothing was launched" in text
        for name in ("enabled", "reliability", "novelty", "evidence", "budget"):
            assert name in text


class TestAgainstTheRealLedger:
    """Fixtures above were written here. This asks the machine."""

    def test_the_scheduler_refuses_on_this_machine_today(self):
        from src.scheduler.loop import read_decision

        decision = read_decision(universe=["VNM", "GAS", "HPG"])
        assert decision.allowed is False, (
            "the plan forbids scheduling on this completion rate; if this ever "
            "passes, check the rate rather than deleting the test"
        )
        reliability = next(v for v in decision.valves if v.name == "reliability")
        assert reliability.passed is False
        assert "automates the failing" in reliability.detail

    def test_the_status_line_is_readable_and_offline(self):
        import socket

        from src.scheduler.loop import status

        original = socket.socket

        def refuse(*args, **kwargs):
            raise AssertionError("the scheduler status must not touch the network")

        socket.socket = refuse  # type: ignore[assignment]
        try:
            text = status(universe=["VNM"])
        finally:
            socket.socket = original  # type: ignore[assignment]
        assert "scheduler:" in text
