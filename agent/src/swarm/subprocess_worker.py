"""Run a swarm task inside an external coding agent instead of the ReAct loop.

The in-process worker asks an LLM for tool calls and executes them itself. That
needs a model emitting native function calls, and the only such provider this
machine can reach is a 3B local one that satisfied the output contract with a
template full of ``[Latest value]``. An external agent -- ``codex exec`` here --
brings its own tools and its own loop, and does work of a different quality.

What that costs, stated plainly because it is why this is off by default:

**The ledger sees less.** The in-process worker records every tool call as an
event. This one records the subprocess's token usage, its exit code and its
final message; what the agent did in between lives in its own transcript, not in
``events.jsonl``. A branch built to make conclusions attributable is giving some
attribution up, and should do it knowingly rather than discover it later.

**The token ceiling binds late.** ``VIBE_TRADING_RUN_TOKEN_BUDGET`` is checked
between tasks, not inside them, so a subprocess overspends within a task and is
stopped at the next boundary. The in-process worker has the same property; the
amounts here are larger.

**Usage is read, not derived.** ``turn.completed`` reports ``input_tokens``,
``cached_input_tokens`` and ``output_tokens``. Only the first and last are
summed: ``cached_input_tokens`` names the cached *portion* of ``input_tokens``,
and adding the two is the double count that already inflated this branch's own
token figures 225x.

Off unless ``VIBE_TRADING_WORKER_EXECUTOR`` is set, and never silent -- the
executor in force is emitted as an event, so a run's provenance says which loop
produced it.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from src.config.loader import AgentConfig
from src.agent.skills import SkillsLoader
from src.swarm.models import SwarmAgentSpec, SwarmEvent, SwarmTask, WorkerResult
from src.swarm.worker import (
    _classify_deliverable,
    _collect_artifacts,
    _emit,
    _filter_skill_descriptions,
    _is_data_agent,
    _report_written,
    _resolve_summary,
    _write_summary,
    build_worker_prompt,
)

logger = logging.getLogger(__name__)

#: Which external agent runs the task. Unset means the in-process ReAct loop.
EXECUTOR_ENV = "VIBE_TRADING_WORKER_EXECUTOR"

#: Sandbox policy passed to codex. ``workspace-write`` lets it write the report
#: and drive the repository's own tooling without handing over the machine.
SANDBOX_ENV = "VIBE_TRADING_CODEX_SANDBOX"
DEFAULT_SANDBOX = "workspace-write"

#: Whether the sandbox may reach the network. Research needs data and data comes
#: over the network, so this defaults on -- but it is named, so switching it off
#: is one variable rather than a code change.
NETWORK_ENV = "VIBE_TRADING_CODEX_NETWORK"

#: Permission mode handed to claude headless. Left unset by default: a worker
#: that may act without asking is the operator's decision, not this module's.
CLAUDE_PERMISSION_ENV = "VIBE_TRADING_CLAUDE_PERMISSION_MODE"

#: Fallback when an agent spec declares no timeout of its own.
DEFAULT_TIMEOUT_SECONDS = 1800

SUPPORTED_EXECUTORS = ("codex", "claude")


def configured_executor() -> str:
    """Return the configured external executor, or ``""`` for in-process.

    An unrecognised name raises rather than falling back. Silently reverting to
    the in-process loop would answer "why was this run cheap and shallow?" with
    nothing, and a typo in a variable name is exactly how that happens.
    """
    name = (os.getenv(EXECUTOR_ENV) or "").strip().lower()
    if not name:
        return ""
    if name not in SUPPORTED_EXECUTORS:
        raise ValueError(
            f"{EXECUTOR_ENV}={name!r} is not supported; expected one of "
            f"{', '.join(SUPPORTED_EXECUTORS)}, or unset for the in-process worker"
        )
    return name


def _repo_root() -> Path:
    """Repository root, so the agent can reach the venv and the data layer."""
    return Path(__file__).resolve().parents[3]


def build_contract_block(artifact_dir: Path, is_data_agent: bool) -> str:
    """State the deliverable in the terms the classifier will grade it on.

    The in-process worker infers the contract from the tools it was given. A
    subprocess arrives with its own tools and would otherwise never be told, so
    the requirement is written out explicitly -- including that a placeholder
    report is a failure, which is the exact way a weak model passed this
    contract while producing nothing.
    """
    report_path = artifact_dir / "report.md"
    lines = [
        "## Deliverable (this is what gets graded)",
        "",
        f"Write your report to exactly this path: {report_path}",
        "",
        "It must contain real figures that you fetched, each with its source.",
        "A skeleton with placeholders such as [Latest value] is a failed task,",
        "not a partial one.",
    ]
    if is_data_agent:
        lines += [
            "",
            "For Vietnamese market data use this repository's own layer rather",
            "than the vendor libraries: run the home venv python against",
            "`agent.vndata`. Never invent a number, and cross-check any figure",
            "that drives a conclusion against a second source.",
        ]
    return "\n".join(lines)


def _codex_command(last_message_file: Path) -> list[str]:
    """Assemble the codex invocation.

    The prompt is *not* an argument. ``shutil.which`` resolves codex to the npm
    ``.cmd`` shim on Windows, so the process is launched through cmd.exe and
    inherits its 8191-character command line limit -- which an 8.4KB worker
    prompt exceeds on the first real task. A trailing ``-`` tells codex to read
    the instructions from stdin instead, where there is no such ceiling.
    """
    exe = shutil.which("codex") or "codex"
    sandbox = (os.getenv(SANDBOX_ENV) or DEFAULT_SANDBOX).strip()
    cmd = [
        exe,
        "exec",
        "--json",
        "--skip-git-repo-check",
        "--sandbox",
        sandbox,
        "-C",
        str(_repo_root()),
        "-o",
        str(last_message_file),
    ]
    network = (os.getenv(NETWORK_ENV) or "true").strip().lower()
    if sandbox == "workspace-write" and network in ("1", "true", "yes"):
        cmd += ["-c", "sandbox_workspace_write.network_access=true"]
    cmd.append("-")
    return cmd


def _claude_command(permission_mode: str = "") -> list[str]:
    """Assemble the claude headless invocation.

    Prompt goes on stdin for the same reason as codex: the npm shim runs
    through cmd.exe, whose command line ceiling an 8KB worker prompt exceeds.
    """
    exe = shutil.which("claude") or "claude"
    cmd = [exe, "-p", "--output-format", "json"]
    mode = (permission_mode or os.getenv(CLAUDE_PERMISSION_ENV) or "").strip()
    if mode:
        cmd += ["--permission-mode", mode]
    return cmd


def parse_claude_result(stdout: str) -> tuple[int, int, str, int, float]:
    """Read claude's JSON into ``(input, output, result, turns, cost_usd)``.

    ``turns`` is ``num_turns`` -- conversation turns, **not** tool calls. It is
    named here because passing it to the deliverable check as a tool-call count
    graded a run complete that had been blocked from writing a single file.

    **The token fields do not mean what codex's mean.** Anthropic reports
    ``input_tokens`` *excluding* what came from cache, with
    ``cache_creation_input_tokens`` and ``cache_read_input_tokens`` as separate
    quantities; codex reports ``input_tokens`` *including* its cached portion.
    Reading either one with the other's convention produces a number that is
    wrong by orders of magnitude in a plausible-looking direction, which is the
    same shape of error as this repository's vnstock unit traps.

    Fresh input here is ``input_tokens + cache_creation_input_tokens``: both had
    to be processed. ``cache_read_input_tokens`` is excluded from the total --
    counting it is what made this branch's own token figures 225x too large --
    but it is returned to the caller through the event, not silently dropped.
    """
    payload: dict[str, Any] = {}
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and candidate.get("type") == "result":
            payload = candidate
    if not payload:
        return 0, 0, "", 0, 0.0
    usage = payload.get("usage") or {}
    fresh_input = int(usage.get("input_tokens") or 0) + int(
        usage.get("cache_creation_input_tokens") or 0
    )
    output_tokens = int(usage.get("output_tokens") or 0)
    result = str(payload.get("result") or "").strip()
    turns = int(payload.get("num_turns") or 0)
    cost = float(payload.get("total_cost_usd") or 0.0)
    return fresh_input, output_tokens, result, turns, cost


#: ``item.item_type`` values that are the agent talking or thinking rather than
#: acting. Everything else counted -- an unknown item type is more likely a new
#: kind of action than a new kind of chatter, and under-counting actions makes
#: the deliverable check more lenient, which is the wrong way to be wrong.
_NON_ACTION_ITEM_TYPES = frozenset({"agent_message", "reasoning", "todo_list", "error"})


def _is_action_item(event: dict[str, Any]) -> bool:
    """Whether one ``item.completed`` event represents the agent doing something.

    Codex nests the kind in ``item.item_type``; the top-level ``type`` is only
    ``item.completed``. An earlier version of this function matched substrings
    against the top-level type, counted zero actions on a run that executed
    commands and wrote files, and was covered by a test asserting an event shape
    that codex never emits.
    """
    item = event.get("item")
    if not isinstance(item, dict):
        return False
    item_type = str(item.get("item_type") or item.get("type") or "").strip()
    return bool(item_type) and item_type not in _NON_ACTION_ITEM_TYPES


def _message_text(event: dict[str, Any]) -> str:
    """Pull assistant text out of one codex event, if it carries any."""
    item = event.get("item") or event.get("msg") or {}
    if isinstance(item, dict):
        for key in ("text", "message", "last_agent_message"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("text", "message", "last_agent_message"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def parse_events(stdout: str) -> tuple[int, int, list[str], int]:
    """Read codex JSONL into ``(input_tokens, output_tokens, messages, actions)``.

    ``cached_input_tokens`` is deliberately excluded from the input total. It is
    the cached *portion* of ``input_tokens``, so summing them double counts --
    the mistake that made this branch's own token figures 225x too large.
    """
    input_tokens = output_tokens = actions = 0
    messages: list[str] = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = str(event.get("type") or "")
        if kind == "turn.completed":
            usage = event.get("usage") or {}
            input_tokens += int(usage.get("input_tokens") or 0)
            output_tokens += int(usage.get("output_tokens") or 0)
        elif kind == "item.completed" and _is_action_item(event):
            actions += 1
        text = _message_text(event)
        if text:
            messages.append(text)
    return input_tokens, output_tokens, messages, actions


def run_subprocess_worker(
    agent_spec: SwarmAgentSpec,
    task: SwarmTask,
    upstream_summaries: dict[str, str],
    user_vars: dict[str, str],
    run_dir: Path,
    event_callback: Callable[[SwarmEvent], None] | None = None,
    include_shell_tools: bool = False,
    grounding_block: str = "",
    agent_config: AgentConfig | None = None,
) -> WorkerResult:
    """Execute one task by handing it to an external coding agent.

    The signature matches :func:`src.swarm.worker.run_worker` so the runtime can
    pick between them without knowing which it holds.

    Returns:
        The result, graded by the same classifier the in-process worker uses. A
        subprocess that writes a hollow report fails here exactly as it would
        there -- the point is a better worker, not an easier contract.
    """
    agent_id = agent_spec.id
    task_id = task.id
    executor = configured_executor() or SUPPORTED_EXECUTORS[0]
    timeout = agent_spec.timeout_seconds or DEFAULT_TIMEOUT_SECONDS

    _emit(event_callback, "worker_started", agent_id, task_id, {"executor": executor})

    artifact_dir = run_dir / "artifacts" / agent_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Best-effort by construction, same as the in-process worker: a run that
    # would have worked without a playbook must not die because the ledger is
    # locked or missing.
    from src.learning.recall import playbook_block as _playbook_block

    skills_loader = SkillsLoader()
    skill_desc = _filter_skill_descriptions(skills_loader, agent_spec.skills)
    system_prompt = build_worker_prompt(
        agent_spec,
        upstream_summaries,
        skill_desc,
        grounding_block=grounding_block,
        playbook_block=_playbook_block(),
    )

    class _FallbackDict(dict):
        """Dict that hints the agent to infer missing template variables."""

        def __missing__(self, key: str) -> str:
            return f"(determine the appropriate {key} based on the objective)"

    try:
        user_prompt = task.prompt_template.format_map(_FallbackDict(user_vars))
    except (KeyError, ValueError) as exc:
        error_msg = f"Failed to render prompt template: {exc}"
        _emit(event_callback, "worker_failed", agent_id, task_id, {"error": error_msg})
        return WorkerResult(status="failed", summary="", iterations=0, error=error_msg)

    prompt = "\n\n".join(
        [
            system_prompt,
            user_prompt,
            build_contract_block(artifact_dir, _is_data_agent(agent_spec)),
        ]
    )
    # Kept on disk because the subprocess transcript is not in events.jsonl:
    # without this, a run's prompt would be unrecoverable after the fact.
    (artifact_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    last_message_file = artifact_dir / "last_message.txt"

    command = (
        _claude_command() if executor == "claude" else _codex_command(last_message_file)
    )

    t0 = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        error_msg = f"{executor} exceeded {timeout}s"
        _emit(event_callback, "worker_failed", agent_id, task_id, {"error": error_msg})
        return WorkerResult(status="timeout", summary="", iterations=1, error=error_msg)
    except (FileNotFoundError, OSError) as exc:
        error_msg = f"{executor} could not be started: {exc}"
        _emit(event_callback, "worker_failed", agent_id, task_id, {"error": error_msg})
        return WorkerResult(status="failed", summary="", iterations=0, error=error_msg)

    elapsed = time.monotonic() - t0
    cost_usd = 0.0
    if executor == "claude":
        input_tokens, output_tokens, summary, turns, cost_usd = parse_claude_result(
            completed.stdout
        )
        # NOT turns. ``--output-format json`` reports how many conversation
        # turns happened, which is not how many tools were used. Feeding one to
        # the other let a run that was blocked from writing anything at all be
        # graded complete: the contract passes a data agent that made tool
        # calls OR wrote a report, and a turn count of 1 satisfied the first
        # clause for free. A quantity that was never observed must not be
        # reported as though it were.
        actions = 0
    else:
        input_tokens, output_tokens, messages, actions = parse_events(completed.stdout)
        summary = ""
        if last_message_file.exists():
            summary = last_message_file.read_text(
                encoding="utf-8", errors="replace"
            ).strip()
        if not summary and messages:
            summary = messages[-1]

    _emit(
        event_callback,
        "worker_subprocess_finished",
        agent_id,
        task_id,
        {
            "executor": executor,
            "exit_code": completed.returncode,
            "elapsed_ms": int(elapsed * 1000),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "actions": actions,
            "cost_usd": cost_usd,
        },
    )

    if completed.returncode != 0:
        error_msg = (
            f"{executor} exited {completed.returncode}: "
            f"{(completed.stderr or '').strip()[:400]}"
        )
        _emit(event_callback, "worker_failed", agent_id, task_id, {"error": error_msg})
        return WorkerResult(
            status="failed",
            summary=summary,
            artifact_paths=_collect_artifacts(artifact_dir),
            iterations=1,
            error=error_msg,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    summary = _resolve_summary(
        artifact_dir, summary or f"{executor} finished without a final message"
    )
    _write_summary(artifact_dir, summary)

    reason = _classify_deliverable(
        summary,
        is_data_agent=_is_data_agent(agent_spec),
        report_written=_report_written(artifact_dir),
        data_tool_calls=actions,
    )
    if reason:
        _emit(
            event_callback,
            "worker_incomplete",
            agent_id,
            task_id,
            {"iterations": 1, "reason": reason, "executor": executor},
        )
        return WorkerResult(
            status="incomplete",
            summary=summary,
            artifact_paths=_collect_artifacts(artifact_dir),
            iterations=1,
            error=f"no valid deliverable: {reason}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    _emit(event_callback, "worker_completed", agent_id, task_id, {"executor": executor})
    return WorkerResult(
        status="completed",
        summary=summary,
        artifact_paths=_collect_artifacts(artifact_dir),
        iterations=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


__all__ = [
    "DEFAULT_SANDBOX",
    "EXECUTOR_ENV",
    "NETWORK_ENV",
    "SANDBOX_ENV",
    "CLAUDE_PERMISSION_ENV",
    "SUPPORTED_EXECUTORS",
    "build_contract_block",
    "configured_executor",
    "parse_claude_result",
    "parse_events",
    "run_subprocess_worker",
]
