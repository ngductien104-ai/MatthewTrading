"""Who plays ``propose`` for :mod:`src.learning.extract`.

``extract_document`` takes its proposer as an argument and the CLI has only ever
supplied one from a file on disk -- a reply somebody recorded by hand. That was
the honest thing to do while no provider on this machine could complete a
request, but it left Giai đoạn 1 open: a backfill that needs a human to play the
model is not a loop.

**No tools, deliberately.** The extraction prompt is a text-to-JSON transform.
Every number the model reports is re-parsed from its own quote, and every quote
must appear character-for-character in the document it was given -- that is the
guarantee the whole module rests on. A proposer with filesystem access could
satisfy both rules by quoting a *different* document, so the tools are not
merely unnecessary here, they are the one thing that could break the evidence
chain. ``claude -p`` with no permission mode has every tool denied, which is the
configuration this wants rather than a limitation to work around.

**The reply is kept.** ``extract.py`` says a backfill nobody can re-run against
the same input is a one-off, not a backfill, and reading replies from disk was
how that was honoured. A live proposer that dropped its reply would quietly undo
it, so every reply is written under ``~/.vibe-trading/proposals/`` and the path
is returned to the caller.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

#: Which model proposes. Unset means claude, the configured executor.
PROPOSER_ENV = "VIBE_TRADING_PROPOSER"

SUPPORTED_PROPOSERS = ("claude", "codex")

#: Seconds for one document. Generous because a long research note is a long
#: prompt, and a proposer killed halfway returns nothing usable.
DEFAULT_TIMEOUT_SECONDS = 900


class ProposerError(RuntimeError):
    """The proposer could not be reached, or produced nothing to parse."""


def proposals_dir() -> Path:
    """Where raw replies are kept so an extraction can be re-run."""
    path = Path.home() / ".vibe-trading" / "proposals"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_reply(prompt: str, reply: str) -> Path:
    """Write one reply next to the digest of the prompt that produced it.

    Named by prompt digest rather than by document path: the same document
    re-extracted after an edit is a different question, and should not silently
    overwrite the answer to the old one.
    """
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = proposals_dir() / f"{stamp}-{digest}.json"
    path.write_text(reply, encoding="utf-8")
    return path


def _run(command: list[str], prompt: str, timeout: int) -> subprocess.CompletedProcess:
    """Run a proposer, sending the prompt on stdin.

    On stdin because the npm shims resolve through cmd.exe on Windows, whose
    command line stops at 8191 characters -- and an extraction prompt carries a
    whole research document.
    """
    try:
        return subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        raise ProposerError(f"{command[0]} exceeded {timeout}s") from exc
    except (FileNotFoundError, OSError) as exc:
        raise ProposerError(f"{command[0]} could not be started: {exc}") from exc


def claude_propose(prompt: str, *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Return Claude Code's raw reply to one extraction prompt.

    No ``--permission-mode`` is passed, so every tool is denied. See the module
    docstring: that is the point, not an oversight.
    """
    from src.swarm.subprocess_worker import parse_claude_result

    exe = shutil.which("claude") or "claude"
    completed = _run([exe, "-p", "--output-format", "json"], prompt, timeout)
    if completed.returncode != 0:
        raise ProposerError(
            f"claude exited {completed.returncode}: "
            f"{(completed.stderr or '').strip()[:400]}"
        )
    _input_tokens, _output_tokens, reply, _turns, cost = parse_claude_result(
        completed.stdout
    )
    if not reply:
        raise ProposerError("claude returned no result text")
    logger.info("claude proposed %d chars (cost $%.4f)", len(reply), cost)
    return reply


def codex_propose(prompt: str, *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Return codex's raw reply to one extraction prompt.

    ``--sandbox read-only`` rather than the worker's ``workspace-write``: this
    proposer has nothing to write, and a proposer that could write files could
    write the document it then quotes.
    """
    from src.swarm.subprocess_worker import parse_events

    exe = shutil.which("codex") or "codex"
    completed = _run(
        [
            exe,
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "-",
        ],
        prompt,
        timeout,
    )
    if completed.returncode != 0:
        raise ProposerError(
            f"codex exited {completed.returncode}: "
            f"{(completed.stderr or '').strip()[:400]}"
        )
    _input_tokens, _output_tokens, messages, _actions = parse_events(completed.stdout)
    if not messages:
        raise ProposerError("codex returned no message")
    return messages[-1]


def configured_proposer(name: str = "") -> Callable[[str], str]:
    """Return the proposer to use, saving each reply as it goes.

    Args:
        name: Override the configured proposer.

    Returns:
        A ``Callable[[str], str]`` matching what ``extract_document`` expects.

    Raises:
        ValueError: The name is not one this module knows. Refused rather than
            defaulted, because falling back silently would attribute one
            model's extractions to another in the ledger.
    """
    chosen = (name or os.getenv(PROPOSER_ENV) or "claude").strip().lower()
    if chosen not in SUPPORTED_PROPOSERS:
        raise ValueError(
            f"{PROPOSER_ENV}={chosen!r} is not supported; expected one of "
            f"{', '.join(SUPPORTED_PROPOSERS)}"
        )
    backend = claude_propose if chosen == "claude" else codex_propose

    def propose(prompt: str) -> str:
        reply = backend(prompt)
        path = save_reply(prompt, reply)
        logger.info("proposer=%s reply saved to %s", chosen, path)
        return reply

    return propose


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "PROPOSER_ENV",
    "SUPPORTED_PROPOSERS",
    "ProposerError",
    "claude_propose",
    "codex_propose",
    "configured_proposer",
    "proposals_dir",
    "save_reply",
]
