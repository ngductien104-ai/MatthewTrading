"""Where a run came from, so a change in output has something to be blamed on.

A run record that names its provider and model still cannot distinguish two
runs a commit apart. That is not a cosmetic gap: process quality is measured
over time here, and a measurement that improves for an unattributable reason is
a number, not a finding.

Everything in this module reports *unknown* as empty rather than guessing. A
commit hash invented for a directory that is not a repository would be worse
than no hash at all, because it would look like provenance.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: How long to wait for git before giving up. A run must not block on it.
GIT_TIMEOUT_SEC = 5.0


def _git(args: list[str], cwd: Path) -> str:
    """Run one git command, returning its stripped stdout or ``""``."""
    try:
        finished = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SEC,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if finished.returncode != 0:
        return ""
    return finished.stdout.strip()


def current_git_commit(repo: Path | str | None = None) -> str:
    """Return the current commit, marked ``-dirty`` when the tree is modified.

    The dirty marker matters more than it looks. Most work here happens on an
    uncommitted working tree, so a bare hash would claim a run is reproducible
    from that commit when the code it actually ran has never been committed
    anywhere.

    Args:
        repo: Directory inside the repository. Defaults to this file's own
            repository, which is the one whose code is executing.

    Returns:
        ``"<sha>"``, ``"<sha>-dirty"``, or ``""`` when git could not answer --
        not installed, not a repository, or too slow. Empty is a fact about
        what is known, and is preferable to a hash that means nothing.
    """
    root = Path(repo) if repo else Path(__file__).resolve().parent
    if not root.exists():
        return ""
    sha = _git(["rev-parse", "HEAD"], root)
    if not sha:
        return ""
    # `status --porcelain` is empty exactly when the tree is clean; an error
    # from it leaves the commit unmarked rather than falsely marked dirty.
    return f"{sha}-dirty" if _git(["status", "--porcelain"], root) else sha
