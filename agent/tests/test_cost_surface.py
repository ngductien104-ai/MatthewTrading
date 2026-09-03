"""Tests for cost per conclusion.

Most of these are about the two absences the ledger actually contains: months
where nothing finished, and months whose records predate the generated-token
counter. Both look like zero if nobody stops them, and a zero that reads as a
measurement is the failure this branch keeps finding.
"""

from __future__ import annotations

import pytest

from src.learning.process_score import cost_per_conclusion, render_cost_surface
from src.learning.store import LearningStore, default_db_path


def _record(month: str, *, completed: bool, output: int | None, wall: float = 3600.0):
    record = {
        "known_at": f"2026-{month}-15T00:00:00Z",
        "completed": completed,
        "wall_time_sec": wall,
    }
    if output is not None:
        record["token_usage"] = {"output_tokens": output}
    return record


class TestAnEmptyDenominatorIsNotAZero:
    def test_a_month_with_no_conclusion_reports_none_not_zero(self):
        """Zero would say the month was free. It was not; it bought nothing."""
        surface = cost_per_conclusion([_record("07", completed=False, output=500_000)])
        assert surface["by_month"][0]["output_tokens_per_conclusion"] is None

    def test_and_not_a_very_large_number_either(self):
        """Infinity implies an upper bound the data cannot supply."""
        surface = cost_per_conclusion([_record("07", completed=False, output=500_000)])
        rendered = render_cost_surface(surface)
        assert "inf" not in rendered.lower()
        assert "-" in rendered

    def test_a_ledger_with_nothing_finished_says_so_in_words(self):
        rendered = render_cost_surface(
            cost_per_conclusion([_record("07", completed=False, output=1)])
        )
        assert "no cost per conclusion yet" in rendered


class TestCoverageTravelsWithEveryFigure:
    def test_records_without_the_counter_are_reported_as_unmeasured(self):
        """July 2026 on the real ledger is two runs and no counter at all."""
        surface = cost_per_conclusion(
            [_record("07", completed=False, output=None) for _ in range(2)]
        )
        row = surface["by_month"][0]
        assert row["runs"] == 2
        assert row["records_with_counter"] == 0
        assert "not measured" in render_cost_surface(surface)

    def test_partial_coverage_is_printed_as_a_fraction(self):
        surface = cost_per_conclusion(
            [
                _record("08", completed=True, output=100),
                _record("08", completed=False, output=None),
            ]
        )
        assert surface["by_month"][0]["records_with_counter"] == 1
        assert "1/2" in render_cost_surface(surface)


class TestArithmetic:
    def test_cost_per_conclusion_divides_by_conclusions_not_by_runs(self):
        surface = cost_per_conclusion(
            [
                _record("08", completed=True, output=300),
                _record("08", completed=False, output=300),
            ]
        )
        assert surface["by_month"][0]["output_tokens_per_conclusion"] == 600.0

    def test_months_come_out_in_order_and_overall_covers_them_all(self):
        surface = cost_per_conclusion(
            [
                _record("09", completed=True, output=10),
                _record("06", completed=True, output=20),
                _record("08", completed=False, output=30),
            ]
        )
        assert [row["month"] for row in surface["by_month"]] == [
            "2026-06",
            "2026-08",
            "2026-09",
        ]
        assert surface["overall"]["runs"] == 3
        assert surface["overall"]["output_tokens"] == 60

    def test_wall_time_is_reported_in_hours(self):
        surface = cost_per_conclusion([_record("08", completed=True, output=1, wall=7200.0)])
        assert surface["overall"]["wall_hours"] == 2.0

    def test_a_record_with_no_timestamp_is_bucketed_rather_than_dropped(self):
        surface = cost_per_conclusion([{"completed": True, "token_usage": {"output_tokens": 5}}])
        assert surface["by_month"][0]["month"] == "unknown"
        assert surface["overall"]["runs"] == 1


class TestAgainstTheRealLedger:
    """The stub above is one this file wrote. This one asks the ledger."""

    def test_the_surface_renders_from_what_is_actually_stored(self):
        with LearningStore(default_db_path()) as store:
            records = [record.to_dict() for record in store.all_process_records()]
        if not records:
            pytest.skip("no process records on this machine")
        surface = cost_per_conclusion(records)
        assert surface["overall"]["runs"] == len(records)
        rendered = render_cost_surface(surface)
        assert "cost per conclusion" in rendered
        assert rendered.count("\n") >= len(surface["by_month"])

    def test_the_enumerator_returns_one_row_per_process_not_one_per_revision(self):
        """The table holds a revision per capture; a rate over revisions is wrong."""
        with LearningStore(default_db_path()) as store:
            records = store.all_process_records()
            if not records:
                pytest.skip("no process records on this machine")
            raw = store._conn.execute("SELECT COUNT(*) FROM process_records").fetchone()[0]
            distinct = store._conn.execute(
                "SELECT COUNT(DISTINCT process_id) FROM process_records"
            ).fetchone()[0]
        assert len(records) == distinct
        assert len({record.process_id for record in records}) == len(records)
        assert raw >= distinct
