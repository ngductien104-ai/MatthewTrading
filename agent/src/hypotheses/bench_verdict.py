"""Carry a strict-bench verdict onto the hypothesis it was testing.

``bench_runner_strict`` is the most carefully built evaluator in this
repository. It holds the day-wise distribution when it permutes, so a control
cannot be beaten by accident of cross-sectional structure; it separates
out-of-sample from training; and it applies the Harvey-Liu-Zhu threshold for
multiple testing across a 455-alpha zoo. It then returns four labels --
``confirmed_alive``, ``train_only``, ``reversed_strict``, ``noise`` -- and,
until this module, nothing consumed them. The result went to a model, was read
once, and was gone.

Meanwhile ``Hypothesis.status`` could be set to ``validated`` by typing it.

So the mapping here is deliberately blunt, and only one label graduates:

* ``confirmed_alive`` beats its random control in the full sample *and* out of
  sample, which is the only one of the four that is evidence *for* anything.
* ``train_only`` beat the control in training and failed after it. That is not
  an incomplete result, it is a specific and damning one -- the shape of an
  overfit -- so it is a rejection, not a return to ``testing``.
* ``reversed_strict`` ran significantly *below* its control. The signal may
  well be real inverted, but the hypothesis as written said the opposite.
* ``noise`` is inside the null.

The verdict is written onto the hypothesis as a run card before the status
moves, so the status always has the thing that justified it sitting next to it,
and re-running a bench leaves the earlier verdict in place rather than
replacing it.
"""

from __future__ import annotations

from typing import Any, Mapping

from src.hypotheses.registry import Hypothesis, HypothesisRegistry

#: Bench label to the lifecycle status it justifies. Only one graduates.
BENCH_STATUS = {
    "confirmed_alive": "validated",
    "train_only": "rejected",
    "reversed_strict": "rejected",
    "noise": "rejected",
}

#: Why each label lands where it does, recorded on the run card so a reader is
#: not left to reconstruct the reasoning from the status alone.
BENCH_REASON = {
    "confirmed_alive": "beat its random control in the full sample and out of sample",
    "train_only": "beat the control in training and failed out of sample -- the shape of an overfit",
    "reversed_strict": "ran significantly below its random control; the stated direction is wrong",
    "noise": "inside the null; indistinguishable from a random control",
}


class BenchVerdictError(ValueError):
    """The bench result cannot settle this hypothesis."""


def verdict_for(bench_result: Mapping[str, Any], alpha_id: str) -> dict[str, Any]:
    """Extract one alpha's verdict from a strict-bench result.

    Args:
        bench_result: The dict returned by ``run_bench_strict``.
        alpha_id: The alpha the hypothesis is about.

    Returns:
        The verdict: ``alpha_id``, ``bench_category``, the mapped ``status``,
        the ``reason``, and the t-statistics the label was derived from.

    Raises:
        BenchVerdictError: The bench errored, did not score this alpha, or
            returned a label this module does not recognise. Each of those is
            refused rather than defaulted, because every available default
            would be a claim about a measurement that was not made.
    """
    if bench_result.get("status") == "error":
        raise BenchVerdictError(
            f"bench run failed, so it settles nothing: {bench_result.get('error')!r}"
        )

    rows = bench_result.get("rows") or []
    match = next((row for row in rows if str(row.get("id")) == str(alpha_id)), None)
    if match is None:
        skipped = {str(item.get("id")): item.get("reason") for item in bench_result.get("skipped", [])}
        if str(alpha_id) in skipped:
            raise BenchVerdictError(
                f"alpha {alpha_id!r} was skipped by the bench ({skipped[str(alpha_id)]}), "
                "so it has no verdict"
            )
        raise BenchVerdictError(
            f"alpha {alpha_id!r} is not in this bench result ({len(rows)} alpha(s) scored)"
        )

    category = str(match.get("_category") or match.get("category") or "")
    if category not in BENCH_STATUS:
        raise BenchVerdictError(
            f"alpha {alpha_id!r} carries an unrecognised bench category {category!r}. "
            f"Known: {', '.join(BENCH_STATUS)}"
        )

    return {
        "alpha_id": str(alpha_id),
        "bench_category": category,
        "status": BENCH_STATUS[category],
        "reason": BENCH_REASON[category],
        "zoo": bench_result.get("zoo", ""),
        "universe": bench_result.get("universe", ""),
        "period": bench_result.get("period", ""),
        "oos_split": bench_result.get("oos_split"),
        "alpha_t_threshold": bench_result.get("alpha_t_threshold"),
        "random_control": bench_result.get("random_control"),
        "n_random_seeds": bench_result.get("n_random_seeds"),
        "alpha_t_full": match.get("alpha_t_full"),
        "alpha_t_train": match.get("alpha_t_train"),
        "alpha_t_test": match.get("alpha_t_test"),
        "ic_mean": match.get("ic_mean"),
        "random_ic_mean": match.get("random_ic_mean"),
    }


def apply_bench_verdict(
    registry: HypothesisRegistry,
    hypothesis_id: str,
    bench_result: Mapping[str, Any],
    alpha_id: str,
    *,
    run_dir: str = "",
) -> Hypothesis:
    """Attach the verdict to a hypothesis and move its status to match.

    Args:
        registry: The hypothesis registry.
        hypothesis_id: The hypothesis the alpha belongs to.
        bench_result: The dict returned by ``run_bench_strict``.
        alpha_id: The alpha the hypothesis is about.
        run_dir: Optional directory holding the bench artifacts.

    Returns:
        The updated hypothesis.

    Raises:
        BenchVerdictError: Propagated from :func:`verdict_for`.
        KeyError: The hypothesis does not exist.
    """
    verdict = verdict_for(bench_result, alpha_id)
    registry.link_backtest(
        hypothesis_id,
        run_card_path=f"bench:{verdict['zoo']}/{verdict['universe']}/{verdict['period']}",
        backtest_run_dir=run_dir,
        metrics=verdict,
        notes=f"strict bench: {verdict['bench_category']} -- {verdict['reason']}",
    )
    # The status moves only after the verdict is on the record, so a run that
    # dies between the two leaves a hypothesis with unread evidence rather than
    # a status with nothing behind it.
    return registry.update(hypothesis_id, status=verdict["status"])
