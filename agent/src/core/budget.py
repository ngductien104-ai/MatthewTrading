"""A ceiling on what one run may spend before it is stopped.

Measured on this machine's ledger: 24 runs, 3 of them reached a conclusion, and
**81% of everything generated went to runs that finished nothing**. That is not
a scheduling annoyance, it is four fifths of the budget, and it is the specific
condition the plan says must be fixed before any run is scheduled unattended --
because a scheduler on a runtime like this automates the failing.

A ceiling is the crudest possible control and also the only one that works
without a price list. It does not need to know what a token costs to know that
a run which has spent four times its own expected budget is not about to
recover.

Two decisions worth stating.

**Output tokens, not the sum of every counter.** Cache reads dominate a raw
total by thirty to a hundred times, so a ceiling set against the sum would
either never fire or fire on a run's third turn depending on how much context
it happened to re-read. Generated tokens track the work.

**Off unless configured.** ``VIBE_TRADING_RUN_TOKEN_BUDGET`` is unset by
default, and an unset budget means unlimited. A ceiling with a value invented
here would kill a legitimate long run on this machine tomorrow, and the first
thing anyone does with a limit that fires wrongly is remove it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

#: Environment variable naming the per-run ceiling, in generated tokens.
BUDGET_ENV = "VIBE_TRADING_RUN_TOKEN_BUDGET"


@dataclass(frozen=True)
class BudgetVerdict:
    """Whether a run may continue.

    Attributes:
        exceeded: Whether the ceiling has been passed.
        limit: The ceiling in force, or ``None`` when unlimited.
        spent: Generated tokens so far.
        reason: Sentence naming the ceiling and the spend, empty when fine.
    """

    exceeded: bool
    limit: int | None
    spent: int
    reason: str = ""


def configured_budget(raw: str | None = None) -> int | None:
    """Return the configured ceiling, or ``None`` for unlimited.

    Args:
        raw: Value to read instead of the environment, for testing.

    Returns:
        A positive integer, or ``None`` when unset, unparseable or
        non-positive. An unparseable budget is treated as absent rather than as
        zero: reading ``BUDGET=abc`` as "stop immediately" would halt every run
        on the machine over a typo.
    """
    value = (raw if raw is not None else os.getenv(BUDGET_ENV, "")).strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def check(spent_output_tokens: int, *, limit: int | None = None) -> BudgetVerdict:
    """Return whether a run that has generated *spent_output_tokens* may go on.

    Args:
        spent_output_tokens: Generated tokens so far. Input and cache-read
            tokens are deliberately excluded; see the module docstring.
        limit: Ceiling to apply. Defaults to the configured one.

    Returns:
        The verdict. With no ceiling configured this is always permissive, and
        says so by reporting ``limit=None`` rather than a large number.
    """
    ceiling = limit if limit is not None else configured_budget()
    spent = max(0, int(spent_output_tokens))
    if ceiling is None or spent <= ceiling:
        return BudgetVerdict(exceeded=False, limit=ceiling, spent=spent)
    return BudgetVerdict(
        exceeded=True,
        limit=ceiling,
        spent=spent,
        reason=(
            f"run generated {spent:,} tokens against a ceiling of {ceiling:,} "
            f"({BUDGET_ENV}); stopping before it spends more on a run that is not "
            "converging"
        ),
    )
