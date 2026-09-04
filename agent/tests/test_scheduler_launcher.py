"""Tests for the scheduler's swarm launcher.

The first version of this launcher returned ``run.run_id``. The field is
``run.id``, so it raised AttributeError on the first real call -- and a stub
with a ``run_id`` attribute would have agreed with it happily. So the fake
runtime here returns a **real** SwarmRun built from a real preset, and the
tests read the id off that. A test may fake the orchestration; it may not
invent the data model it is supposed to be checking against.
"""

from __future__ import annotations

import os

import pytest

from src.core.budget import BUDGET_ENV
from src.scheduler.launcher import DEFAULT_PRESET, build_goal, swarm_launcher
from src.swarm.presets import build_run_from_preset


@pytest.fixture
def real_run():
    """A genuine SwarmRun, so the launcher is read against the real model."""
    return build_run_from_preset(
        DEFAULT_PRESET, {"market": "Vietnam / HOSE", "goal": "test"}
    )


class _FakeRuntime:
    def __init__(self, run):
        self._run = run
        self.calls = []

    def __call__(self, *args, **kwargs):
        return self

    def start_run(self, preset_name, user_vars, **kwargs):
        self.calls.append((preset_name, user_vars))
        return self._run


class TestBuildGoal:
    def test_every_candidate_reaches_the_goal(self):
        goal = build_goal(["FPT", "MWG", "VCB"])
        for ticker in ("FPT", "MWG", "VCB"):
            assert ticker in goal

    def test_the_goal_asks_what_would_falsify_the_thesis(self):
        """The playbook's standing requirement, not decoration."""
        assert "falsify" in build_goal(["FPT"])


class TestLauncher:
    def _patch(self, monkeypatch, run):
        fake = _FakeRuntime(run)
        monkeypatch.setattr("src.swarm.runtime.SwarmRuntime", fake)
        monkeypatch.setattr(
            "src.config.loader.load_swarm_agent_config", lambda: None
        )
        return fake

    def test_it_returns_the_id_the_real_model_carries(self, monkeypatch, real_run):
        """Guards the AttributeError that only a real call would have found."""
        self._patch(monkeypatch, real_run)
        run_id = swarm_launcher()(["FPT"], 200_000)
        assert run_id == real_run.id
        assert run_id

    def test_the_cycle_ceiling_is_set_before_the_run_starts(
        self, monkeypatch, real_run
    ):
        """A ceiling the run cannot see does not bind it."""
        monkeypatch.delenv(BUDGET_ENV, raising=False)
        seen = {}

        fake = self._patch(monkeypatch, real_run)
        original = fake.start_run

        def capture(preset_name, user_vars, **kwargs):
            seen["budget"] = os.getenv(BUDGET_ENV)
            return original(preset_name, user_vars, **kwargs)

        monkeypatch.setattr(fake, "start_run", capture)
        swarm_launcher()(["FPT"], 123_456)
        assert seen["budget"] == "123456"

    def test_the_candidates_are_what_gets_researched(self, monkeypatch, real_run):
        fake = self._patch(monkeypatch, real_run)
        swarm_launcher()(["FPT", "MWG"], 200_000)
        preset_name, user_vars = fake.calls[0]
        assert preset_name == DEFAULT_PRESET
        assert "FPT" in user_vars["goal"]
        assert "MWG" in user_vars["goal"]
        assert user_vars["market"]

    def test_it_matches_the_contract_run_cycle_calls_it_with(
        self, monkeypatch, real_run
    ):
        """run_cycle passes (list[str], int) positionally and expects a str."""
        self._patch(monkeypatch, real_run)
        from src.scheduler.loop import run_cycle  # noqa: F401 - contract check

        result = swarm_launcher()(["FPT"], 200_000)
        assert isinstance(result, str)
