"""Start real research from a scheduler cycle.

``run_cycle`` takes its launcher as an argument rather than importing one. The
docstring there gives the reason: when the seam was written, no provider on
this machine could complete a request, so a launcher written alongside it could
not have been run even once. This branch keeps finding unexercised code
presented as working, and declining to add another instance was the right call.

A local ollama now completes, so the launcher exists and has been run.

What it does *not* do is decide anything. The cycle has already chosen the
candidates and the token ceiling behind five gates; this turns that decision
into a swarm run and returns its id. Keeping the choice in ``loop.py`` and the
machinery here is what lets the gates be tested without starting research, and
research to be started without going through the gates.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

from src.core.budget import BUDGET_ENV

logger = logging.getLogger(__name__)

#: Preset the unattended cycle runs. It takes a market and a research goal
#: rather than a ticker list, so the candidates are rendered into the goal.
DEFAULT_PRESET = "equity_research_team"

#: Market the cycle researches. The scheduler's universe is Vietnamese.
DEFAULT_MARKET = "Vietnam / HOSE"


def build_goal(candidates: list[str]) -> str:
    """Render the cycle's candidates into the preset's research goal."""
    return (
        "Scheduled unattended review of: "
        + ", ".join(candidates)
        + ". For each name, state the thesis, the evidence behind it, and what "
        "would falsify it."
    )


def swarm_launcher(
    *,
    preset: str = DEFAULT_PRESET,
    market: str = DEFAULT_MARKET,
    max_workers: int | None = None,
) -> Callable[[list[str], int], str]:
    """Return a launcher that starts a real swarm run.

    Args:
        preset: Preset to run.
        market: Market passed to the preset.
        max_workers: Concurrent workers. Defaults to ``SWARM_MAX_WORKERS``.

    Returns:
        A callable matching ``run_cycle``'s ``launcher`` contract: it takes the
        candidates and the cycle's token ceiling and returns a run id.
    """

    def launch(candidates: list[str], ceiling: int) -> str:
        # The ceiling is the cycle's, and it only binds the run if the run can
        # see it. Set before the run starts, because the budget is read as
        # workers spend rather than once at the top.
        os.environ[BUDGET_ENV] = str(ceiling)

        from src.config.loader import load_swarm_agent_config
        from src.swarm.runtime import SwarmRuntime
        from src.swarm.store import SwarmStore

        base_dir = Path(__file__).resolve().parents[2] / ".swarm" / "runs"
        base_dir.mkdir(parents=True, exist_ok=True)
        runtime = SwarmRuntime(
            store=SwarmStore(base_dir=base_dir),
            max_workers=(
                max_workers
                if max_workers is not None
                else int(os.getenv("SWARM_MAX_WORKERS", "4"))
            ),
            agent_config=load_swarm_agent_config(),
        )

        run = runtime.start_run(
            preset,
            {"market": market, "goal": build_goal(candidates)},
        )
        logger.info(
            "Scheduler launched swarm run %s (%s) under a %d-token ceiling",
            run.id,
            preset,
            ceiling,
        )
        return run.id

    return launch


__all__ = ["BUDGET_ENV", "DEFAULT_MARKET", "DEFAULT_PRESET", "build_goal", "swarm_launcher"]
