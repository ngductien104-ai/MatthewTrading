"""Bash tool: execute shell commands under run_dir."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.agent.tools import BaseTool

_OUTPUT_LIMIT = 50_000
_DEFAULT_TIMEOUT = 120


def _child_env() -> dict[str, str]:
    """Return the environment for a child shell, with ``python`` pinned.

    Running a virtualenv's interpreter does not put its ``Scripts``/``bin`` on
    ``PATH`` — activation does that — so a bare ``python`` typed by an agent
    resolves to whatever the OS finds first. On 2026-08-27 that was an
    unrelated runtime carrying neither vnstock_data nor akshare, and the
    quality analyst in a live FPT run concluded the data layer "is not
    available in the runtime" and fell back to Wikipedia for a buy-side
    report. Pinning the directory keeps an agent on the same interpreter the
    swarm itself is running on, which is by construction the one whose
    packages the presets assume.
    """
    env = dict(os.environ)
    bin_dir = str(Path(sys.executable).resolve().parent)
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    return env


class BashTool(BaseTool):
    """Execute shell commands in the working directory."""

    name = "bash"
    description = "Execute a shell command in the working directory. Use for installing packages, running scripts, or inspecting files."
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
        },
        "required": ["command"],
    }
    repeatable = True
    is_readonly = False

    def execute(self, **kwargs: Any) -> str:
        """Execute a shell command.

        Args:
            **kwargs: Must include command. Optional run_dir used as cwd.

        Returns:
            JSON string with stdout, stderr, and exit_code.
        """
        command = kwargs["command"]
        cwd = kwargs.get("run_dir")

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=_DEFAULT_TIMEOUT,
                encoding="utf-8",
                errors="replace",
                env=_child_env(),
            )
            stdout = result.stdout[:_OUTPUT_LIMIT] if len(result.stdout) > _OUTPUT_LIMIT else result.stdout
            stderr = result.stderr[:_OUTPUT_LIMIT] if len(result.stderr) > _OUTPUT_LIMIT else result.stderr
            return json.dumps({
                "status": "ok" if result.returncode == 0 else "error",
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }, ensure_ascii=False)
        except subprocess.TimeoutExpired:
            return json.dumps({
                "status": "error",
                "error": f"Command timed out after {_DEFAULT_TIMEOUT}s",
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({
                "status": "error",
                "error": str(exc),
            }, ensure_ascii=False)
