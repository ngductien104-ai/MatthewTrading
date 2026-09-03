"""Tests for the scheduler's tick and its pull-request step.

The PR step is the one place the scheduler writes to the world, so most of
this file is about what it refuses to do: stage more than it was given, spend
a slot from the monthly cap on an empty review, or commit instead of asking
for one.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.scheduler.loop import CycleResult, open_pull_request, read_decision, run_cycle, status
from src.scheduler.valves import prs_opened_this_month


class _Runner:
    """Records the commands it was asked to run, and runs none of them."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, args, **kwargs):
        self.calls.append(list(args))

        class _Completed:
            stdout = ""
            returncode = 0

        return _Completed()

    def flat(self) -> str:
        return " | ".join(" ".join(call) for call in self.calls)


class TestRunCycle:
    def test_a_refused_cycle_launches_nothing_and_says_why(self):
        result = run_cycle(universe=["VNM"])
        assert isinstance(result, CycleResult)
        assert result.launched is False
        assert "refused" in result.detail
        assert "automates the failing" in result.detail

    def test_a_refused_cycle_never_calls_the_launcher(self):
        called = []
        run_cycle(universe=["VNM"], launcher=lambda c, t: called.append((c, t)) or "run-1")
        assert called == []

    def test_dry_run_is_the_default(self, monkeypatch):
        """The failure mode of a scheduler is spending; make that the opt-in."""
        import inspect

        signature = inspect.signature(run_cycle)
        assert signature.parameters["dry_run"].default is True

    def test_an_allowed_cycle_hands_the_ceiling_to_the_launcher(self, monkeypatch):
        from src.scheduler import loop
        from src.scheduler.valves import CycleDecision, Valve

        decision = CycleDecision(
            allowed=True,
            valves=(Valve("enabled", True, "on"),),
            candidates=("VNM", "GAS"),
            cycle_token_ceiling=4242,
        )
        monkeypatch.setattr(loop, "read_decision", lambda **kwargs: decision)
        seen: list[tuple[list[str], int]] = []

        def launcher(candidates, ceiling):
            seen.append((candidates, ceiling))
            return "run-77"

        result = run_cycle(universe=["VNM"], dry_run=False, launcher=launcher)
        assert seen == [(["VNM", "GAS"], 4242)]
        assert result.launched is True
        assert result.run_id == "run-77"

    def test_an_allowed_cycle_with_no_launcher_still_launches_nothing(self, monkeypatch):
        from src.scheduler import loop
        from src.scheduler.valves import CycleDecision, Valve

        monkeypatch.setattr(
            loop,
            "read_decision",
            lambda **kwargs: CycleDecision(
                allowed=True, valves=(Valve("enabled", True, "on"),), candidates=("VNM",)
            ),
        )
        result = run_cycle(dry_run=False)
        assert result.launched is False
        assert "no launcher" in result.detail


class TestOpenPullRequest:
    """Scoped home patch: these tests write, the ledger-reading ones must not
    have their store redirected, so the safeguard lives on this class only."""

    @pytest.fixture(autouse=True)
    def _never_the_operators_home(self, tmp_path, monkeypatch):
        """Send the monthly-count file somewhere disposable, always.

        The first run of this file incremented the real ~/.vibe-trading counter
        twice, taking two slots off a live cap before anybody had opened a pull
        request. Passing root= at each call site fixes the calls that remember
        to; this covers the one that forgets.
        """
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    def test_it_stages_only_the_paths_it_was_given(self, tmp_path):
        """`git add -A` here would sweep an untracked vault onto a public repo."""
        runner = _Runner()
        open_pull_request(
            title="t",
            body="b",
            paths=["reports/vnm.md"],
            cwd=str(tmp_path),
            today=date(2026, 9, 4),
            root=tmp_path,
            runner=runner,
        )
        assert ["git", "add", "--", "reports/vnm.md"] in runner.calls
        assert not any("-A" in call for call in runner.calls)

    def test_it_opens_a_pull_request_rather_than_pushing_to_the_branch_in_use(
        self, tmp_path
    ):
        runner = _Runner()
        branch = open_pull_request(
            title="t",
            body="b",
            paths=["x.md"],
            cwd=str(tmp_path),
            today=date(2026, 9, 4),
            root=tmp_path,
            runner=runner,
        )
        assert branch.startswith("scheduler/20260904-")
        assert ["git", "checkout", "-b", branch] in runner.calls
        assert "gh pr create" in runner.flat()

    def test_an_empty_pull_request_is_refused_before_it_costs_a_slot(self, tmp_path):
        runner = _Runner()
        with pytest.raises(ValueError, match="no files"):
            open_pull_request(
                title="t", body="b", paths=[], cwd=str(tmp_path), runner=runner
            )
        assert runner.calls == []

    def test_opening_one_counts_against_the_monthly_cap(self, tmp_path):
        runner = _Runner()
        open_pull_request(
            title="t",
            body="b",
            paths=["x.md"],
            cwd=str(tmp_path),
            today=date(2026, 9, 4),
            root=tmp_path,
            runner=runner,
        )
        assert prs_opened_this_month(root=tmp_path, today=date(2026, 9, 4)) == 1



class TestStatusIsSafeToCallAnywhere:
    def test_it_reads_the_real_ledger_and_refuses(self):
        text = status(universe=["VNM", "GAS"])
        assert "cycle REFUSED" in text
        assert "nothing was launched" in text

    def test_read_decision_evaluates_every_valve(self):
        decision = read_decision(universe=["VNM"])
        assert {valve.name for valve in decision.valves} == {
            "enabled",
            "reliability",
            "novelty",
            "evidence",
            "budget",
        }
