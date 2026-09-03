"""Read the ledger back as a scorecard.

This module runs entirely offline. Everything it needs was written to the
evidence when the outcome was scored, so a scorecard is reproducible from the
ledger alone and cannot quietly disagree with the numbers the resolver stood
behind.

Its job is as much to state what cannot be concluded as what can. At n=8
graded calls the confidence interval on a hit rate spans most of the unit
interval, so the hit rate is printed *with* that interval and never alone. Two
further limits are structural rather than statistical, and are printed every
time:

* **One checkpoint.** No call has reached 63 sessions, so everything here is the
  21-session view of horizons that were never stated as 21 sessions.
* **One market.** All sixteen calls were made between June and August 2026. A
  hit rate over a single regime measures the regime as much as the analyst, and
  nothing here separates the two -- see the ``regime`` note at the foot of the
  report for why the available base-rate file cannot do that separation either.

The calibration section is the part worth reading. Confidence is the one number
on a call that makes a checkable claim about the analyst rather than about the
stock, and the reference Brier score says whether stating it at all beat saying
nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from statistics import fmean, median

from src.learning.records import CallRecord, Outcome
from src.learning.attribution import parse_state
from src.learning.resolve import ACTION_DIRECTION
from src.learning.store import LearningStore

#: Verdicts that put a call into the contest. ``invalidated`` is excluded on
#: purpose: a call stopped out mid-window was not wrong about direction, it was
#: closed, and folding it into a hit rate would grade a position nobody held.
GRADED = ("hit", "miss")


def wilson_interval(hits: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Return the Wilson score interval for *hits* out of *total*.

    Wilson rather than the normal approximation because the normal interval is
    badly wrong exactly where this ledger lives -- small *total*, proportions
    away from a half -- and can hand back bounds outside ``[0, 1]``, which reads
    as precision that is not there.
    """
    if total <= 0:
        return (0.0, 1.0)
    phat = hits / total
    denominator = 1.0 + z * z / total
    centre = (phat + z * z / (2 * total)) / denominator
    spread = z * sqrt(phat * (1 - phat) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def brier_score(pairs: list[tuple[float, int]]) -> float | None:
    """Return the mean squared error of stated probabilities against outcomes.

    Args:
        pairs: ``(stated_confidence, 1 for hit else 0)``.
    """
    if not pairs:
        return None
    return fmean((stated - actual) ** 2 for stated, actual in pairs)


def _numbers(excerpt: str) -> dict[str, float]:
    """Pull the ``key=value`` numbers back out of a price-evidence excerpt."""
    values: dict[str, float] = {}
    for token in excerpt.split():
        key, separator, raw = token.partition("=")
        if not separator:
            continue
        try:
            values[key] = float(raw)
        except ValueError:
            continue
    return values


@dataclass
class Row:
    """One call and its outcome at the reported checkpoint."""

    call: CallRecord
    outcome: Outcome
    prices: dict[str, float] = field(default_factory=dict)

    @property
    def graded(self) -> bool:
        """Whether this row entered the hit rate."""
        return self.outcome.verdict in GRADED

    @property
    def cross_verdict(self) -> str | None:
        """The same verdict, judged against the typical stock instead of the index.

        VN-Index is capitalisation-weighted and a handful of large caps move it,
        so "beat the index" and "beat the median name" are different questions,
        and on this ledger they give different answers. Reported beside the
        index verdict rather than instead of it: switching benchmarks quietly
        would be choosing the flattering one.
        """
        percentile = self.outcome.base_rate_pctile
        if not self.graded or percentile is None:
            return None
        direction = ACTION_DIRECTION[self.call.action]
        beat_the_field = percentile > 0.5
        return "hit" if (beat_the_field == (direction > 0)) else "miss"

    @property
    def entry_printed(self) -> bool | None:
        """Whether the entry a stay-away call named was ever actually reached.

        A ``wait`` says two things -- do not buy here, and a better price is
        coming -- and only the first is what the alpha verdict tests. BSR waited
        at 26.350 for 24.000 and the alpha test scores it on 1,2% of avoided
        underperformance, which badly understates it: 23.350 traded. This asks
        the second question.

        Returns ``None`` when the call named no entry below the reference, which
        is the VRE case: a target *above* the price is a fair-value note, not an
        entry anyone was waiting for.
        """
        target, reference = self.call.target, self.call.ref_price
        if ACTION_DIRECTION[self.call.action] >= 0 or not target or not reference:
            return None
        if target >= reference:
            return None
        rate = self.prices.get("entry_adj_rate")
        low = self.prices.get("adj_low")
        if not rate or low is None:
            return None
        return low <= target / rate


@dataclass
class Scorecard:
    """The ledger read back at one checkpoint."""

    checkpoint_sessions: int
    rows: list[Row]
    counts: dict[str, int]

    @property
    def graded(self) -> list[Row]:
        """Rows that entered the hit rate."""
        return [row for row in self.rows if row.graded]

    def to_dict(self) -> dict[str, object]:
        """Return the scorecard's numbers, for a caller that wants them raw."""
        graded = self.graded
        hits = sum(1 for row in graded if row.outcome.verdict == "hit")
        alphas = [row.outcome.alpha for row in graded if row.outcome.alpha is not None]
        stated = [
            (row.call.confidence, 1 if row.outcome.verdict == "hit" else 0)
            for row in graded
            if row.call.confidence is not None
        ]
        base_rate = fmean(actual for _, actual in stated) if stated else None
        cross = [row for row in graded if row.cross_verdict is not None]
        cross_hits = sum(1 for row in cross if row.cross_verdict == "hit")
        return {
            "checkpoint_sessions": self.checkpoint_sessions,
            "ledger": self.counts,
            "scored": len(self.rows),
            "graded": len(graded),
            "hits": hits,
            "hit_rate": hits / len(graded) if graded else None,
            "hit_rate_ci95": wilson_interval(hits, len(graded)),
            "alpha_mean": fmean(alphas) if alphas else None,
            "alpha_median": median(alphas) if alphas else None,
            "alpha_positive": sum(1 for value in alphas if value > 0),
            "brier": brier_score(stated),
            "brier_reference": base_rate * (1 - base_rate) if base_rate is not None else None,
            "confidence_mean": fmean(value for value, _ in stated) if stated else None,
            "confidence_n": len(stated),
            # Not every graded call stated a confidence, so the calibration
            # section needs the hit rate of *its own* subset. Comparing a mean
            # confidence over seven calls against a hit rate over eight would be
            # the kind of mismatched denominator this report exists to catch.
            "confidence_hit_rate": base_rate,
            "cross_graded": len(cross),
            "cross_hits": cross_hits,
            "cross_hit_rate": cross_hits / len(cross) if cross else None,
            "cross_disagreements": sum(
                1 for row in graded if row.cross_verdict not in (None, row.outcome.verdict)
            ),
        }

    def to_text(self) -> str:
        """Render the scorecard for a terminal."""
        stats = self.to_dict()
        out: list[str] = []
        out.append(f"SCORECARD -- checkpoint {self.checkpoint_sessions} sessions")
        out.append(
            "ledger: "
            + ", ".join(f"{key}={value}" for key, value in sorted(self.counts.items()))
        )
        out.append("")

        out.append("CALLS")
        out.append(
            f"  {'ticker':<6} {'as_of':<11} {'action':<11} {'verdict':<11} "
            f"{'ret':>8} {'vni':>8} {'alpha':>8} {'tgt err':>8} {'pctile':>7} {'conf':>5}"
        )
        for row in self.rows:
            call, outcome = row.call, row.outcome
            target_error = (
                f"{outcome.target_error:+7.2%}" if outcome.target_error is not None else "      --"
            )
            percentile = (
                f"{outcome.base_rate_pctile:.2f}"
                if outcome.base_rate_pctile is not None
                else "--"
            )
            confidence = f"{call.confidence:.2f}" if call.confidence is not None else "   --"
            out.append(
                f"  {call.ticker:<6} {call.as_of:<11} {call.action:<11} {outcome.verdict:<11} "
                f"{outcome.realized_ret:+7.2%} {outcome.vni_ret:+7.2%} {outcome.alpha:+7.2%} "
                f"{target_error} {percentile:>7} {confidence:>5}"
            )
        out.append("")

        graded = self.graded
        low, high = stats["hit_rate_ci95"]
        out.append("DIRECTION")
        if graded:
            out.append(
                f"  hit rate  {stats['hits']}/{stats['graded']} = "
                f"{stats['hit_rate']:.1%}   95% CI [{low:.1%}, {high:.1%}]"
            )
            out.append(
                f"  alpha     mean {stats['alpha_mean']:+.2%}, median "
                f"{stats['alpha_median']:+.2%}, positive in "
                f"{stats['alpha_positive']}/{stats['graded']}"
            )
            out.append(
                f"  the interval spans {high - low:.0%} of the range: at n={stats['graded']} "
                "this separates almost nothing from chance"
            )
            if stats["cross_graded"]:
                out.append("")
                out.append(
                    f"  vs the typical VN30 stock instead of the index: "
                    f"{stats['cross_hits']}/{stats['cross_graded']} = "
                    f"{stats['cross_hit_rate']:.1%}"
                )
                if stats["cross_disagreements"]:
                    flipped = ", ".join(
                        f"{row.call.ticker} ({row.outcome.verdict}->{row.cross_verdict})"
                        for row in graded
                        if row.cross_verdict not in (None, row.outcome.verdict)
                    )
                    out.append(
                        f"  the two benchmarks disagree on {stats['cross_disagreements']} "
                        f"call(s): {flipped}"
                    )
                    out.append(
                        "  VN-Index is cap-weighted, so a few large caps can drag it below "
                        "the median name; both are shown because picking the flattering one "
                        "after the fact is the whole failure this ledger exists to prevent"
                    )
        else:
            out.append("  nothing graded yet")
        out.append("")

        out.append("BY ACTION")
        for action in sorted({row.call.action for row in self.rows}):
            group = [row for row in self.rows if row.call.action == action]
            scored = [row for row in group if row.graded]
            hits = sum(1 for row in scored if row.outcome.verdict == "hit")
            alphas = [row.outcome.alpha for row in group if row.outcome.alpha is not None]
            tally = f"{hits}/{len(scored)}" if scored else "--"
            note = "" if scored else "   (asserts no direction)"
            out.append(
                f"  {action:<11} n={len(group)}  hits {tally:<5} "
                f"mean alpha {fmean(alphas):+7.2%}{note}"
            )
        out.append("")

        out.append(f"CONFIDENCE  (the {stats['confidence_n']} graded calls that stated one)")
        if stats["confidence_n"]:
            realised = stats["confidence_hit_rate"]
            gap = (stats["confidence_mean"] - realised) * 100
            out.append(
                f"  stated mean {stats['confidence_mean']:.1%} vs realised {realised:.1%}"
                f"  ->  overstated by {gap:.1f} points"
            )
            out.append(
                f"  Brier {stats['brier']:.4f} vs {stats['brier_reference']:.4f} for saying "
                f"{realised:.0%} every time"
            )
            verdict = (
                "stating a confidence did NOT beat stating the base rate"
                if stats["brier"] > stats["brier_reference"]
                else "stating a confidence beat stating the base rate"
            )
            out.append(f"  {verdict} -- on n={stats['confidence_n']}, which settles nothing")
        else:
            out.append("  no graded call carried a stated confidence")
        out.append("")

        entries = [(row, row.entry_printed) for row in self.rows]
        entries = [(row, printed) for row, printed in entries if printed is not None]
        if entries:
            out.append("DID THE ENTRY EVER PRINT?")
            out.append("  (a stay-away call also promises a better price; alpha does not test that)")
            for row, printed in entries:
                low_adj = row.prices["adj_low"] * row.prices["entry_adj_rate"]
                out.append(
                    f"  {row.call.ticker:<6} named {row.call.target:>8,.0f}, "
                    f"low {low_adj:>8,.0f}  ->  {'YES' if printed else 'no'}"
                )
            out.append("")

        states = [parse_state(row.outcome.regime) for row in self.rows if row.outcome.regime]
        out.append("MARKET THE CALLS WERE MADE IN")
        if states:
            rising = sum(1 for state in states if state.get("mom63", 0.0) > 0)
            for key, label in (
                ("dd252", "drawdown from the year's high"),
                ("mom63", "63-session momentum"),
                ("rv_pct", "realised vol, percentile of its own year"),
            ):
                values = [state[key] for state in states if key in state]
                if not values:
                    continue
                fmt = ".2f" if key == "rv_pct" else "+.1%"
                out.append(
                    f"  {label:<44} {min(values):{fmt}} to {max(values):{fmt}}"
                )
            out.append(
                f"  {rising} call(s) made into a rising 63-session tape, "
                f"{len(states) - rising} into a falling one -- so these are NOT one market, "
                "and neither half holds enough graded calls to be scored on its own"
            )
        else:
            out.append("  no call carries a regime; the index history did not reach back far enough")
        out.append("")

        out.append("LIMITS")
        out.append(
            f"  n={stats['graded']} graded, at one checkpoint "
            f"({self.checkpoint_sessions} sessions) that none of the calls named."
        )
        out.append(
            "  the peer universe is CURRENT VN30 membership, not point-in-time: names dropped "
            "from the index during a window are absent, and names are dropped for falling, so "
            "every percentile here sits a little low."
        )
        out.append(
            "  the base rate is NOT taken from calibration.json -- that file distributes "
            "VN-Index forward returns, and ranking one stock inside it reads the stock's "
            "roughly doubled volatility as skill."
        )
        return "\n".join(out)


def build_scorecard(store: LearningStore, *, checkpoint: int = 21) -> Scorecard:
    """Read the ledger back at one checkpoint.

    Args:
        store: The ledger.
        checkpoint: Which checkpoint to report, in trading sessions. Mixing
            checkpoints would average horizons of different lengths, so exactly
            one is reported at a time.

    Returns:
        The scorecard, oldest call first.
    """
    rows: list[Row] = []
    for call in store.list_calls():
        for outcome in store.outcomes_for(call.call_id):
            if outcome.checkpoint_sessions != checkpoint:
                continue
            prices: dict[str, float] = {}
            for evidence_id in outcome.evidence_ids:
                evidence = store.get_evidence(evidence_id)
                if evidence and evidence.excerpt.startswith(f"{call.ticker} "):
                    prices = _numbers(evidence.excerpt)
            rows.append(Row(call=call, outcome=outcome, prices=prices))
    return Scorecard(checkpoint_sessions=checkpoint, rows=rows, counts=store.counts())
