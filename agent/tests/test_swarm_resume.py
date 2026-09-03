"""Tests for resuming a swarm run instead of re-running it.

Built on a real run directory rather than a hand-written one. The fixture
below copies ``swarm-20260827-064250-5c3d38f8`` out of ``.swarm/runs``: a
fundamental_research_team run that failed with two of four tasks completed,
one failed and one blocked behind it. Three times in this branch a stub the
author wrote set an easier contract than the real source did, so what a
resume must survive is taken from disk.
"""

from __future__ import annotations

import shutil
import threading

import pytest

from src.swarm.models import TaskStatus, WorkerResult, WorkerStatus
from src.swarm.runtime import SwarmRuntime
from src.swarm.store import SwarmStore, swarm_runs_root
from src.swarm.task_store import TaskStore

REAL_RUN_ID = "swarm-20260827-064250-5c3d38f8"


@pytest.fixture
def resumable(tmp_path):
    """A copy of the real half-finished run, in a throwaway runs root."""
    source = swarm_runs_root() / REAL_RUN_ID
    if not source.is_dir():
        pytest.skip(f"real run {REAL_RUN_ID} not on this machine")
    root = tmp_path / "runs"
    root.mkdir()
    shutil.copytree(source, root / REAL_RUN_ID)
    return SwarmRuntime(store=SwarmStore(root)), root


class _Recorder:
    """Stands in for _execute_layer and records what it was asked to do."""

    def __init__(self):
        self.dispatched: list[list[str]] = []
        self.upstream_seen: list[dict[str, str]] = []

    def __call__(self, *, layer_task_ids, task_summaries, **kwargs):
        self.dispatched.append(list(layer_task_ids))
        self.upstream_seen.append(dict(task_summaries))
        return {
            tid: WorkerResult(
                status=WorkerStatus.completed,
                summary=f"resumed {tid}",
                output_tokens=10,
            )
            for tid in layer_task_ids
        }


def _resume_and_wait(runtime, recorder, monkeypatch, run_id=REAL_RUN_ID):
    """Resume synchronously enough to assert on, without a sleep."""
    monkeypatch.setattr(SwarmRuntime, "_execute_layer", lambda self, **kw: recorder(**kw))
    finished = threading.Event()
    real = SwarmRuntime._execute_run

    def traced(self, *args, **kwargs):
        try:
            real(self, *args, **kwargs)
        finally:
            finished.set()

    monkeypatch.setattr(SwarmRuntime, "_execute_run", traced)
    runtime.resume_run(run_id)
    assert finished.wait(timeout=60), "resume thread did not finish"


class TestResumeSkipsFinishedWork:
    def test_only_the_unfinished_tasks_are_dispatched(self, resumable, monkeypatch):
        """Two of four tasks completed. A resume must pay only for the rest."""
        runtime, _ = resumable
        recorder = _Recorder()
        _resume_and_wait(runtime, recorder, monkeypatch)

        dispatched = [tid for layer in recorder.dispatched for tid in layer]
        assert "task-valuation" in dispatched
        assert "task-report" in dispatched
        assert "task-financial" not in dispatched
        assert "task-quality" not in dispatched

    def test_the_completed_summaries_reach_the_downstream_task(self, resumable, monkeypatch):
        """Otherwise the retry writes its report with no upstream research."""
        runtime, _ = resumable
        recorder = _Recorder()
        _resume_and_wait(runtime, recorder, monkeypatch)

        last = recorder.upstream_seen[-1]
        assert "task-financial" in last
        assert "task-quality" in last
        assert "FPT" in last["task-financial"]

    def test_completed_work_is_not_overwritten(self, resumable, monkeypatch):
        runtime, root = resumable
        before = TaskStore(root / REAL_RUN_ID).load_task("task-financial").summary
        recorder = _Recorder()
        _resume_and_wait(runtime, recorder, monkeypatch)
        after = TaskStore(root / REAL_RUN_ID).load_task("task-financial").summary
        assert after == before

    def test_the_failed_task_is_returned_to_pending_before_dispatch(
        self, resumable, monkeypatch
    ):
        """A task left `failed` would be gated out by its own status."""
        runtime, root = resumable
        store = TaskStore(root / REAL_RUN_ID)
        assert store.load_task("task-valuation").status == TaskStatus.failed
        monkeypatch.setattr(SwarmRuntime, "_execute_run", lambda self, *a, **k: None)
        runtime.resume_run(REAL_RUN_ID)
        reset = store.load_task("task-valuation")
        assert reset.status == TaskStatus.pending
        assert reset.error is None

    def test_the_blocked_task_loses_its_stale_blockers(self, resumable, monkeypatch):
        runtime, root = resumable
        store = TaskStore(root / REAL_RUN_ID)
        assert store.load_task("task-report").status == TaskStatus.blocked
        monkeypatch.setattr(SwarmRuntime, "_execute_run", lambda self, *a, **k: None)
        runtime.resume_run(REAL_RUN_ID)
        assert store.load_task("task-report").blocked_by == []


class TestResumeRefusesWhatItCannotDoSafely:
    def test_an_unknown_run_is_a_named_error(self, resumable):
        runtime, _ = resumable
        with pytest.raises(FileNotFoundError):
            runtime.resume_run("swarm-does-not-exist")

    def test_a_live_run_is_refused(self, resumable):
        """Two executors on one run directory interleave writes to task files."""
        runtime, _ = resumable
        runtime._cancel_events[REAL_RUN_ID] = threading.Event()
        with pytest.raises(ValueError, match="still executing"):
            runtime.resume_run(REAL_RUN_ID)

    def test_resuming_a_finished_run_does_nothing_rather_than_failing(
        self, resumable, monkeypatch
    ):
        runtime, root = resumable
        store = TaskStore(root / REAL_RUN_ID)
        for task in store.load_all():
            store.update_status(task.id, TaskStatus.completed, summary="done")
        spawned = []
        monkeypatch.setattr(
            SwarmRuntime, "_execute_run", lambda self, *a, **k: spawned.append(a)
        )
        runtime.resume_run(REAL_RUN_ID)
        assert spawned == []


class TestResumeAndBudget:
    def test_the_spend_carries_over_rather_than_resetting(self, resumable, monkeypatch):
        """A budget that any failure resets is not a budget."""
        runtime, _ = resumable
        run = runtime._store.load_run(REAL_RUN_ID)
        assert run.total_output_tokens > 0
        monkeypatch.setenv("VIBE_TRADING_RUN_TOKEN_BUDGET", "1")
        recorder = _Recorder()
        _resume_and_wait(runtime, recorder, monkeypatch)
        assert recorder.dispatched == [], "an over-budget resume must not dispatch"
        events = runtime._store.read_events(REAL_RUN_ID)
        assert any(e.type == "run_over_budget" for e in events)


class TestResumeIsAudible:
    def test_it_records_what_it_skipped_and_what_it_still_owes(self, resumable, monkeypatch):
        runtime, _ = resumable
        monkeypatch.setattr(SwarmRuntime, "_execute_run", lambda self, *a, **k: None)
        runtime.resume_run(REAL_RUN_ID)
        events = runtime._store.read_events(REAL_RUN_ID)
        resumed = [e for e in events if e.type == "run_resumed"]
        assert resumed, "a resume that leaves no trace cannot be audited"
        assert resumed[-1].data["completed_tasks"] == 2
        assert resumed[-1].data["pending_tasks"] == 2


class TestTheRealLayerAcceptsAResumedState:
    """The recorder above bypasses _execute_layer, and the dependency gate
    lives inside it. A resume whose completed tasks the gate does not believe
    would block the downstream task all over again, so the gate is exercised
    against the real function with only the provider call replaced."""

    def test_the_dependency_gate_reads_the_resumed_statuses(
        self, resumable, monkeypatch
    ):
        runtime, root = resumable
        seen: dict[str, dict[str, str]] = {}

        def fake_worker(*, agent_spec, task, upstream_summaries, **kwargs):
            seen[task.id] = dict(upstream_summaries)
            return WorkerResult(
                status=WorkerStatus.completed,
                summary=f"worked {task.id}",
                output_tokens=5,
            )

        monkeypatch.setattr("src.swarm.runtime.run_worker", fake_worker)
        finished = threading.Event()
        real = SwarmRuntime._execute_run

        def traced(self, *args, **kwargs):
            try:
                real(self, *args, **kwargs)
            finally:
                finished.set()

        monkeypatch.setattr(SwarmRuntime, "_execute_run", traced)
        runtime.resume_run(REAL_RUN_ID)
        assert finished.wait(timeout=120)

        assert set(seen) == {"task-valuation", "task-report"}, (
            "the gate either re-ran finished work or blocked the report again"
        )
        store = TaskStore(root / REAL_RUN_ID)
        assert store.load_task("task-report").status == TaskStatus.completed
        run = runtime._store.load_run(REAL_RUN_ID)
        assert run.status.value == "completed"
