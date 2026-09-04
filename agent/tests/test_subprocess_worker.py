"""Tests for running a swarm task inside an external coding agent.

The reason this worker exists is that a weak model passed the output contract
with a report full of ``[Latest value]``. So the tests that matter most here are
the ones proving the subprocess is graded by the *same* classifier: a better
worker is the point, an easier contract is not.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from src.swarm.subprocess_worker import (
    EXECUTOR_ENV,
    build_contract_block,
    configured_executor,
    parse_events,
    run_subprocess_worker,
)


class TestConfiguredExecutor:
    def test_unset_means_the_in_process_worker(self, monkeypatch):
        monkeypatch.delenv(EXECUTOR_ENV, raising=False)
        assert configured_executor() == ""

    def test_codex_is_supported(self, monkeypatch):
        monkeypatch.setenv(EXECUTOR_ENV, "codex")
        assert configured_executor() == "codex"

    def test_a_typo_is_refused_rather_than_ignored(self, monkeypatch):
        """Falling back silently would hide why a run came out shallow."""
        monkeypatch.setenv(EXECUTOR_ENV, "codexx")
        with pytest.raises(ValueError, match="not supported"):
            configured_executor()


class TestParseEvents:
    def test_cached_input_tokens_are_not_added_to_the_total(self):
        """The 225x double count this branch already made once.

        ``cached_input_tokens`` is the cached portion of ``input_tokens``, not
        a separate quantity to add on top of it.
        """
        line = json.dumps(
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 18900,
                    "cached_input_tokens": 11520,
                    "output_tokens": 5,
                },
            }
        )
        input_tokens, output_tokens, _, _ = parse_events(line)
        assert input_tokens == 18900
        assert output_tokens == 5

    def test_usage_accumulates_across_turns(self):
        lines = "\n".join(
            json.dumps(
                {"type": "turn.completed", "usage": {"input_tokens": n, "output_tokens": 1}}
            )
            for n in (100, 200)
        )
        input_tokens, output_tokens, _, _ = parse_events(lines)
        assert (input_tokens, output_tokens) == (300, 2)

    def test_non_json_noise_is_skipped_not_fatal(self):
        noisy = 'Shell cwd was reset\n{"type":"turn.completed","usage":{"input_tokens":5}}\n'
        assert parse_events(noisy)[0] == 5

    def test_actions_are_counted_in_the_shape_codex_actually_emits(self):
        """Captured from a real `codex exec --json` run, not invented.

        The first version of this test asserted a top-level type of
        `item.command_execution`. Codex emits `item.completed` and carries the
        kind in `item.item_type`, so the parser and the test agreed with each
        other and with nothing else: a real run that executed commands and
        wrote files reported zero actions.
        """
        lines = "\n".join(
            [
                json.dumps(
                    {"type": "item.started", "item": {"item_type": "command_execution"}}
                ),
                json.dumps(
                    {"type": "item.completed", "item": {"item_type": "command_execution"}}
                ),
                json.dumps(
                    {"type": "item.completed", "item": {"item_type": "agent_message"}}
                ),
                json.dumps({"type": "turn.completed", "usage": {}}),
            ]
        )
        # item.started is not counted twice; a message is not an action.
        assert parse_events(lines)[3] == 1

    def test_talking_is_not_an_action(self):
        line = json.dumps(
            {"type": "item.completed", "item": {"item_type": "agent_message"}}
        )
        assert parse_events(line)[3] == 0

    def test_an_unknown_item_type_counts_as_an_action(self):
        """Under-counting actions makes the deliverable check more lenient."""
        line = json.dumps(
            {"type": "item.completed", "item": {"item_type": "web_search"}}
        )
        assert parse_events(line)[3] == 1


class TestContractBlock:
    def test_it_names_the_exact_report_path(self, tmp_path):
        block = build_contract_block(tmp_path, is_data_agent=False)
        assert str(tmp_path / "report.md") in block

    def test_it_rules_out_the_hollow_report_that_passed_before(self, tmp_path):
        """A 3B model satisfied the old contract with exactly this shape."""
        block = build_contract_block(tmp_path, is_data_agent=False)
        assert "[Latest value]" in block
        assert "failed task" in block

    def test_a_data_agent_is_pointed_at_the_repository_data_layer(self, tmp_path):
        block = build_contract_block(tmp_path, is_data_agent=True)
        assert "vndata" in block


class _Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def task_bits():
    from src.swarm.presets import build_run_from_preset

    run = build_run_from_preset(
        "equity_research_team", {"market": "Vietnam / HOSE", "goal": "test"}
    )
    task = next(t for t in run.tasks if t.id == "task-macro")
    agent = {a.id: a for a in run.agents}[task.agent_id]
    return agent, task


class TestRunSubprocessWorker:
    def _invoke(self, monkeypatch, tmp_path, task_bits, completed, write_report=None):
        agent, task = task_bits
        artifact_dir = tmp_path / "artifacts" / agent.id

        def fake_run(cmd, **kwargs):
            if write_report is not None:
                artifact_dir.mkdir(parents=True, exist_ok=True)
                (artifact_dir / "report.md").write_text(write_report, encoding="utf-8")
            return completed

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setenv(EXECUTOR_ENV, "codex")
        return run_subprocess_worker(
            agent_spec=agent,
            task=task,
            upstream_summaries={},
            user_vars={"market": "Vietnam / HOSE", "goal": "test"},
            run_dir=tmp_path,
        )

    def test_a_nonzero_exit_is_a_failure_carrying_the_stderr(
        self, monkeypatch, tmp_path, task_bits
    ):
        result = self._invoke(
            monkeypatch,
            tmp_path,
            task_bits,
            _Completed(returncode=1, stderr="codex blew up"),
        )
        assert result.status == "failed"
        assert "codex blew up" in result.error

    @pytest.mark.xfail(
        reason=(
            "KNOWN GAP, not a bug in this module: _classify_deliverable checks "
            "that a report exists and that actions were taken, never that the "
            "report contains anything. A 3B model passed it on 2026-09-04 with "
            "a skeleton of [Latest value] placeholders. Closing this means "
            "changing the grading shared with the in-process worker, which is "
            "a decision the operator has not taken. Kept executable so the gap "
            "is a failing expectation rather than a paragraph nobody reads."
        ),
        strict=True,
    )
    def test_a_hollow_report_should_fail_the_contract(
        self, monkeypatch, tmp_path, task_bits
    ):
        """The whole point: a better worker, not an easier contract."""
        usage = json.dumps(
            {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 2}}
        )
        result = self._invoke(
            monkeypatch,
            tmp_path,
            task_bits,
            _Completed(stdout=usage),
            write_report="# Report\n- GDP: [Latest value]\n",
        )
        assert result.status != "completed"

    def test_a_blocked_claude_run_is_not_graded_complete(
        self, monkeypatch, tmp_path, task_bits
    ):
        """The live failure on 2026-09-04, and the misattribution behind it.

        claude headless with no permission mode had every Write and Bash call
        denied, wrote no report, and was still returned as completed. The cause
        was passing ``num_turns`` where the contract expects a tool-call count:
        a data agent passes on tool calls OR a report, and one conversation turn
        satisfied the first clause for free.
        """
        agent, task = task_bits
        payload = json.dumps(
            {
                "type": "result",
                "result": "I could not deliver the file; every write was denied.",
                "num_turns": 1,
                "total_cost_usd": 0.1,
                "usage": {"input_tokens": 2, "output_tokens": 4},
            }
        )
        monkeypatch.setattr(
            subprocess, "run", lambda cmd, **kw: _Completed(stdout=payload)
        )
        monkeypatch.setenv(EXECUTOR_ENV, "claude")
        result = run_subprocess_worker(
            agent_spec=agent,
            task=task,
            upstream_summaries={},
            user_vars={"market": "Vietnam / HOSE", "goal": "test"},
            run_dir=tmp_path,
        )
        assert result.status != "completed"
        assert "report.md" in (result.error or "")

    def test_the_prompt_is_kept_on_disk_for_after_the_fact(
        self, monkeypatch, tmp_path, task_bits
    ):
        """The subprocess transcript is not in events.jsonl; this is."""
        agent, _ = task_bits
        self._invoke(monkeypatch, tmp_path, task_bits, _Completed(stdout=""))
        assert (tmp_path / "artifacts" / agent.id / "prompt.txt").exists()

    def test_a_timeout_is_reported_as_a_timeout(
        self, monkeypatch, tmp_path, task_bits
    ):
        agent, task = task_bits

        def boom(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 1)

        monkeypatch.setattr(subprocess, "run", boom)
        monkeypatch.setenv(EXECUTOR_ENV, "codex")
        result = run_subprocess_worker(
            agent_spec=agent,
            task=task,
            upstream_summaries={},
            user_vars={"market": "VN", "goal": "t"},
            run_dir=tmp_path,
        )
        assert result.status == "timeout"

    def test_a_missing_executable_is_a_result_not_a_crash(
        self, monkeypatch, tmp_path, task_bits
    ):
        agent, task = task_bits

        def missing(cmd, **kwargs):
            raise FileNotFoundError("codex")

        monkeypatch.setattr(subprocess, "run", missing)
        monkeypatch.setenv(EXECUTOR_ENV, "codex")
        result = run_subprocess_worker(
            agent_spec=agent,
            task=task,
            upstream_summaries={},
            user_vars={"market": "VN", "goal": "t"},
            run_dir=tmp_path,
        )
        assert result.status == "failed"
        assert "could not be started" in result.error


class TestRuntimeDispatch:
    def test_the_runtime_picks_the_subprocess_worker_when_configured(self):
        """Guards the seam: the runtime must consult configured_executor().

        The path is resolved from the module rather than the working directory.
        Reading "src/swarm/runtime.py" relative to CWD passes under `pytest`
        run inside agent/ and fails from the repository root -- a test whose
        result depends on where it was started tells you about your shell.
        """
        import src.swarm.runtime as runtime_module

        source = Path(runtime_module.__file__).read_text(encoding="utf-8")
        assert "configured_executor()" in source
        assert "run_subprocess_worker" in source
