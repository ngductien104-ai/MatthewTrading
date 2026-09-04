"""Tests for the live proposer behind ``learning extract``.

Two properties carry the weight here, and neither is about happy-path plumbing.

The first is that **the proposer gets no tools**. Every quote an extraction
returns has to appear character-for-character in the document it was handed, and
a proposer that could read the disk would be able to satisfy that rule by
quoting a *different* file. So the absence of ``--permission-mode`` in the claude
command, and ``--sandbox read-only`` in the codex one, are asserted the way a
gate is asserted -- not left to a code comment that a later edit can quietly
contradict.

The second is that **a name this module does not know is refused, not defaulted**.
Falling back silently would file one model's extractions under another model's
name in a ledger whose whole purpose is telling those apart afterwards.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from src.learning import propose as propose_module
from src.learning.propose import (
    PROPOSER_ENV,
    ProposerError,
    claude_propose,
    codex_propose,
    configured_proposer,
    proposals_dir,
    save_reply,
)


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Keep every reply this test writes out of the real ``~/.vibe-trading``."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv(PROPOSER_ENV, raising=False)
    monkeypatch.setattr(propose_module.Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def _claude_stdout(result: str) -> str:
    return json.dumps(
        {
            "type": "result",
            "result": result,
            "num_turns": 1,
            "total_cost_usd": 0.01,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        }
    )


def _codex_stdout(result: str) -> str:
    return "\n".join(
        [
            json.dumps({"type": "item.completed", "item": {"text": result}}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}}),
        ]
    )


def _fake_run(monkeypatch, *, stdout: str = "", stderr: str = "", code: int = 0) -> list[list[str]]:
    """Record the command lines a proposer builds, and answer them canned."""
    seen: list[list[str]] = []

    def run(command, **kwargs):
        seen.append(list(command))
        return subprocess.CompletedProcess(command, code, stdout, stderr)

    monkeypatch.setattr(propose_module.subprocess, "run", run)
    return seen


# -- no tools, deliberately ----------------------------------------------------


def test_claude_is_asked_with_every_tool_denied(monkeypatch):
    seen = _fake_run(monkeypatch, stdout=_claude_stdout('{"calls": []}'))
    claude_propose("prompt")
    command = seen[0]
    assert "-p" in command and "--output-format" in command
    assert not [word for word in command if word.startswith("--permission-mode")]
    assert "--dangerously-skip-permissions" not in command


def test_codex_is_asked_read_only(monkeypatch):
    seen = _fake_run(monkeypatch, stdout=_codex_stdout('{"calls": []}'))
    codex_propose("prompt")
    command = seen[0]
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "workspace-write" not in command


def test_the_prompt_goes_on_stdin_not_the_command_line(monkeypatch):
    """cmd.exe stops at 8191 characters and a prompt carries a whole document."""
    captured = {}

    def run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, _claude_stdout("ok"), "")

    monkeypatch.setattr(propose_module.subprocess, "run", run)
    claude_propose("x" * 20000)
    assert captured["input"] == "x" * 20000


# -- refusing rather than defaulting -------------------------------------------


def test_an_unknown_proposer_is_refused(monkeypatch):
    monkeypatch.setenv(PROPOSER_ENV, "deepseek")
    with pytest.raises(ValueError) as error:
        configured_proposer()
    assert PROPOSER_ENV in str(error.value)
    assert "deepseek" in str(error.value)


def test_the_env_var_picks_the_backend(monkeypatch):
    monkeypatch.setenv(PROPOSER_ENV, "codex")
    seen = _fake_run(monkeypatch, stdout=_codex_stdout("from codex"))
    assert configured_proposer()("prompt") == "from codex"
    assert seen[0][1] == "exec"


def test_the_argument_overrides_the_env_var(monkeypatch):
    monkeypatch.setenv(PROPOSER_ENV, "codex")
    seen = _fake_run(monkeypatch, stdout=_claude_stdout("from claude"))
    assert configured_proposer("claude")("prompt") == "from claude"
    assert seen[0][1] == "-p"


def test_claude_is_the_default(monkeypatch):
    seen = _fake_run(monkeypatch, stdout=_claude_stdout("from claude"))
    configured_proposer()("prompt")
    assert seen[0][1] == "-p"


# -- failures that must not be mistaken for empty answers ----------------------


def test_a_nonzero_exit_becomes_a_proposer_error(monkeypatch):
    _fake_run(monkeypatch, stdout="", stderr="usage limit reached", code=1)
    with pytest.raises(ProposerError) as error:
        claude_propose("prompt")
    assert "exited 1" in str(error.value)
    assert "usage limit reached" in str(error.value)


def test_a_reply_with_no_result_text_is_an_error_not_an_empty_extraction(monkeypatch):
    _fake_run(monkeypatch, stdout=_claude_stdout(""))
    with pytest.raises(ProposerError):
        claude_propose("prompt")


def test_codex_with_no_message_is_an_error(monkeypatch):
    _fake_run(monkeypatch, stdout="")
    with pytest.raises(ProposerError):
        codex_propose("prompt")


def test_a_timeout_is_a_proposer_error(monkeypatch):
    def run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs.get("timeout", 1))

    monkeypatch.setattr(propose_module.subprocess, "run", run)
    with pytest.raises(ProposerError) as error:
        claude_propose("prompt", timeout=7)
    assert "7s" in str(error.value)


def test_a_missing_executable_is_a_proposer_error(monkeypatch):
    def run(command, **kwargs):
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(propose_module.subprocess, "run", run)
    with pytest.raises(ProposerError) as error:
        codex_propose("prompt")
    assert "could not be started" in str(error.value)


# -- the reply stays on disk ---------------------------------------------------


def test_every_live_reply_is_written_out(monkeypatch, home):
    _fake_run(monkeypatch, stdout=_claude_stdout('{"calls": [1]}'))
    reply = configured_proposer()("prompt")
    written = list(proposals_dir().glob("*.json"))
    assert len(written) == 1
    assert written[0].read_text(encoding="utf-8") == reply


def test_two_prompts_are_kept_apart_by_digest(home):
    first = save_reply("prompt one", "a")
    second = save_reply("prompt two", "b")
    assert first.name.split("-")[-1] != second.name.split("-")[-1]
    assert first.read_text(encoding="utf-8") == "a"
    assert second.read_text(encoding="utf-8") == "b"
