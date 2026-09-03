---
name: research-memory
description: Load what this desk has already measured about its own work — the derived playbook, the confidence-calibration gap, and the errors that keep recurring — before starting a new analysis. Use at the START of any equity, sector, or macro analysis, and before writing a recommendation that states a confidence or a price target.
category: research
---
# Research Memory

## Purpose

Put the ledger's findings in front of the work that would otherwise repeat
them. Every line it loads was **derived by rule** from scored calls and process
records — arithmetic over measurements, not a model's opinion about what went
well.

## When to load it

- Before starting an analysis of any ticker, sector, or macro question.
- Before writing a recommendation that states a **confidence** or a **target price**.
- Before scheduling or budgeting a swarm run.

## How to load it

```bash
$HOME/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, r'C:\Users\VVVZV\MatthewTrading\agent')
from src.learning.recall import playbook_block
print(playbook_block() or 'no lesson has crossed its evidence threshold yet')
"
```

Or read the rendered files directly, one per domain, with YAML frontmatter so
Dataview can query them:

```
Obsidian/MatthewObsidian/60_Playbook/{calibration,process,nganhang,batdongsan,banle,vimo,kythuat}.md
```

An empty domain file is not an oversight. It says the evidence does not exist
yet, which is the honest state and is preferable to a line invented to fill it.

## How to read what it gives you

Each line carries a **status** and an observation count.

| Status | Meaning |
|---|---|
| `confirmed` | Enough evidence that it does not expire. |
| `provisional` | A prior worth checking. Expires in 90 days unless evidence accumulates. |

**These are to be argued with.** If the work in front of you contradicts a
line, say so explicitly and say why. That contradiction is the signal the
ledger is waiting for — it is how `contradicted_count` moves, and a playbook
that only ever accumulates agreement is a playbook amplifying its own bias.

## What it will not do

- It will not tell you a sector view. Sector domains are empty because eight
  graded calls cannot support per-sector conclusions, and filling them from a
  language model is exactly the failure the ledger exists to prevent.
- It will not grade your analysis. Scoring is `src.learning.process_score`,
  which only ever awards a point for a quote it can find in your document.

## Refreshing it

After new calls are scored (`python -m src.learning.cli resolve`), re-derive:

```bash
$HOME/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, r'C:\Users\VVVZV\MatthewTrading\agent')
from src.learning.store import LearningStore, default_db_path
from src.learning.lessons import derive, curate, write_playbook
s = LearningStore(default_db_path())
print(len(curate(s, derive(s))), 'lesson(s)')
write_playbook(s, r'C:\Users\VVVZV\MatthewTrading\Obsidian\MatthewObsidian\60_Playbook')
"
```

Re-deriving **updates** existing lines rather than rewriting the file, so
nothing is lost and the counts move.

## Related

- `src/learning/recall.py` — the block builder.
- `src/learning/lessons.py` — the rules that derive each line, and their thresholds.
- `python -m src.learning.cli report` — the scorecard the calibration line comes from.
