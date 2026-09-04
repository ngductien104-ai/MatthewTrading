"""Shared fixtures and sys.path setup for all tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure agent/ is on sys.path so imports like `backtest.*` and `src.*` work.
AGENT_DIR = Path(__file__).resolve().parent.parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

# The operator's ``~/.vibe-trading/.env`` is loaded into ``os.environ`` the first
# time ``src.providers.llm`` is imported, and on 2026-09-04 that file gained
# ``VIBE_TRADING_WORKER_EXECUTOR=claude``. From that moment the runtime's worker
# dispatch (``src/swarm/runtime.py``) stopped choosing the in-process loop under
# test and started spawning the real ``claude`` CLI: the full suite sat for 35
# minutes on one live, billable invocation, and spawned another as soon as that
# one was killed.
#
# Presetting the variable to empty is what stops it, rather than deleting it:
# the .env is loaded with ``override=False``, which fills in any name that is
# *absent*, so a name cleared at session start comes back the moment some test
# imports the provider module. An empty value reads as "in-process" and is left
# alone. A test that wants the external executor still sets it with monkeypatch.
os.environ["VIBE_TRADING_WORKER_EXECUTOR"] = ""
