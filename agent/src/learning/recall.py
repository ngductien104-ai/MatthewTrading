"""Put what the ledger learned in front of the work that would repeat it.

A ledger nothing reads is a diary. This module renders the live lessons as a
prompt block and hands it to the two places research actually starts: a swarm
worker, and a Claude Code session.

Three decisions worth stating.

**It is its own section, not part of ``{upstream_context}``.** The plan asked
for the latter, and the plan also records why that is a trap: a preset that
declares ``input_from:`` without putting ``{upstream_context}`` in its
``system_prompt`` drops the data silently, with no error. Attaching the playbook
to that placeholder would inherit the same silent failure, and a playbook that
sometimes is not there is worse than one that never is, because nobody can tell
which run had it.

**It never enters the cached system prompt.** ``agent/context.py`` keeps
``build_system_prompt`` stable so the prompt cache holds, and learned content
changes every time a lesson is derived. It travels the user-message path
instead, which is where changing context already goes.

**A dead ledger costs nothing.** Every entry point swallows its own failure and
returns an empty string. Research that would have run fine without a playbook
must not fail because of one.
"""

from __future__ import annotations

from typing import Sequence

from src.learning.records import Lesson

#: Most lessons to put in a prompt. The cap is a real constraint, not a
#: formality: past roughly this many lines the block stops being read as
#: guidance and starts being skimmed as boilerplate.
MAX_LESSONS = 12

#: Hard ceiling on the rendered block, in characters.
MAX_CHARS = 4000

_HEADER = """## What this desk has already measured about itself

These lines were derived by rule from a ledger of scored calls and process
records -- not written by a model, and not opinions. Each carries how many
observations stand behind it. A provisional line is one the evidence does not
yet settle; treat it as a prior worth checking, not a conclusion to repeat.

They are here to be argued with. If the work in front of you contradicts one,
say so explicitly and why -- that contradiction is itself the signal the ledger
is waiting for."""


def render_block(lessons: Sequence[Lesson], *, max_lessons: int = MAX_LESSONS) -> str:
    """Render lessons as a prompt section, strongest evidence first.

    Args:
        lessons: Live lessons.
        max_lessons: Cap on lines included.

    Returns:
        The block, or ``""`` when there is nothing evidenced to say. An empty
        string is deliberate: a header announcing an empty playbook spends
        tokens telling the worker that nothing was learned.
    """
    if not lessons:
        return ""
    ranked = sorted(
        lessons,
        key=lambda item: (item.status != "confirmed", -item.support_count, item.domain),
    )[:max_lessons]

    lines = [_HEADER, ""]
    for lesson in ranked:
        weight = f"{lesson.status}, n={lesson.support_count}"
        lines.append(f"- **[{lesson.domain}]** ({weight}) {lesson.statement}")
    block = "\n".join(lines)
    if len(block) > MAX_CHARS:
        block = block[:MAX_CHARS].rsplit("\n", 1)[0] + "\n- _(truncated)_"
    return block


def playbook_block(domain: str | None = None, *, store: object | None = None) -> str:
    """Return the prompt block for the live playbook, or ``""`` on any failure.

    Args:
        domain: Restrict to one playbook domain.
        store: Optional open ledger. When omitted one is opened and closed here.

    Returns:
        The rendered block. Every failure path returns ``""`` rather than
        raising: a swarm run that would have worked without a playbook must not
        die because the ledger is locked, missing, or mid-migration.
    """
    try:
        from src.learning.store import LearningStore, default_db_path

        if store is not None:
            return render_block(store.live_lessons(domain=domain))  # type: ignore[attr-defined]
        with LearningStore(default_db_path()) as ledger:
            return render_block(ledger.live_lessons(domain=domain))
    except Exception:  # noqa: BLE001 - recall is an enhancement, never a dependency
        return ""
