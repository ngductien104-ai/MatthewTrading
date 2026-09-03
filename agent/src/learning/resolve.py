"""Score the calls on the ledger against what prices actually did.

Three questions were left hanging for this module, and the ledger's own
contents answer all three.

**What does a call without a target claim?** The seven ``avoid``/``wait``/
``reduce`` calls make the ledger's shape obvious: VRE 31/07 is ``avoid`` at
24.300 with a target of 26.200 -- *above* the reference. That target is a
fair-value note, not a forecast to trade on; the claim being made is "do not
buy here". So the target never decides a verdict. Every call is graded on the
one thing every action asserts: **which side of the benchmark the ticker lands
on**. Long-side actions are right when alpha is positive, stay-away actions
when it is negative, and ``hold``/``neutral`` assert no direction at all --
they are resolved against real prices and recorded as :data:`NO_CLAIM` rather
than being counted in a hit rate they never entered.

**What about a call with no stated horizon?** Every call on the ledger carries
``horizon_sessions`` 63 because that is the default, not because anyone said
three months. Since the horizon never selected the verdict, nothing needs to be
invented: each call is scored at *every* checkpoint that has elapsed, and the
horizon is left to the report layer to use as a headline. A resolver that
graded only at the horizon would be grading a number the extractor supplied.

**Where does the disclosure lag apply?** Not here. Prices are visible the day
they print, so ``vndata.fundamental.DISCLOSURE_LAG_DAYS`` gates the *fundamental*
invalidation triggers ("gate Q2") -- which this resolver deliberately does not
evaluate, because deciding from free text whether a trigger fired is exactly the
judgement the ledger refuses to let a model make. Only the ``stop`` field, a
machine-readable price level, is checked. Everything else is reported as
unchecked instead of being silently recorded as "did not fire".

The look-ahead trap on the price side is a different one, and it is real. Prices
from DataPro are back-adjusted: BSR's close on 17/06 reads 26.056 today but
traded at 26.350, the 1,1% gap being a dividend paid since. So returns are taken
on the adjusted series -- the only series where a return means anything -- and
the reference price, which is quoted on the same day it is checked against, is
compared on ``vndata.price.traded_price``, the grid a human actually saw.

A **target or a stop is quoted on one day and tested on another**, so neither
lives on a single grid. PET ran a 1,45x corporate action inside its own
21-session window: its traded price "fell" from 54.800 to 37.400 while the stock
lost 1,07%. Comparing the 44.000 target straight against 37.400 records the
outcome as 15% *below* target when it finished 23% *above* it -- the sign
flips. Every quoted level is therefore divided by ``adj_rate`` on the day it was
quoted before it meets a later bar, and both grids are written to the evidence
so the choice stays auditable.

That comparison found something worth saying out loud: ``ref_price`` is
documented as the close on ``as_of``, and on this ledger it frequently is not.
PHR states 62.000 against a 63.000 close, MWG 69.000 against 68.000, VRE 24.300
against 24.800 -- all three are entry levels the committee quoted, not closes.
Scoring from them would fold a 1,5% entry-level gap into every return, so
returns run from the close and the gap is reported as a warning instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping, Sequence

import pandas as pd

from src.learning.attribution import (
    REGIME_LOOKBACK,
    cross_sectional_percentile,
    load_universe,
    market_state,
    peer_returns,
    vn30_symbols,
)
from src.learning.records import (
    CHECKPOINT_SESSIONS,
    CallRecord,
    Evidence,
    Outcome,
    resolve_deadline,
    sha256_text,
)
from src.learning.store import LearningStore

#: The market calendar and the alpha benchmark. Every horizon on this ledger is
#: quoted against the index the committee quotes.
BENCHMARK_SYMBOL = "VNINDEX"

#: Recorded alongside, never decisive. ``VN30`` is not the DataPro name -- it
#: returns an empty frame, which surfaces as an ``IndexError`` several layers
#: down rather than as a missing symbol -- so the working name is pinned here.
VN30_SYMBOL = "VN30INDEX"

#: Which way an action points. ``0`` is not a weak claim, it is no claim.
ACTION_DIRECTION: dict[str, int] = {
    "buy": 1,
    "accumulate": 1,
    "hold": 0,
    "neutral": 0,
    "reduce": -1,
    "sell": -1,
    "avoid": -1,
    "wait": -1,
}

#: Verdict for an action that asserted no direction.
NO_CLAIM = "no_claim"

#: How far the stated ``ref_price`` may sit from the traded close on ``as_of``
#: before the gap is reported. Half a percent is wider than a tick and narrower
#: than the entry levels this ledger actually contains.
REF_PRICE_TOLERANCE = 0.005

#: Signature of a price source: ``(symbol, start, end)`` returning a frame
#: indexed by trade date, priced in VND, carrying ``adj_rate``.
PriceFetcher = Callable[[str, str, str], pd.DataFrame]


def datapro_prices(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Return VND-denominated DataPro bars for *symbol*.

    Fallback is refused on purpose: the sponsored source publishes no
    ``adj_rate``, so a fallback frame cannot say what price actually traded, and
    a resolver that silently scored against an unadjustable series would be the
    quiet degradation ``VN_DATA_SOURCE.md`` exists to prevent.

    Raises:
        SourceUnavailable: DataPro is not answering.
    """
    from vndata import price

    return price.to_vnd(price.ohlcv(symbol, start, end, allow_fallback=False))


def _traded(frame: pd.DataFrame, column: str) -> pd.Series:
    """Return *column* on the traded grid, undoing the back-adjustment."""
    from vndata import price

    return price.traded_price(frame, column)


def _sessions(frame: pd.DataFrame) -> list[str]:
    """Return the frame's trade dates as ascending ISO strings."""
    return [pd.Timestamp(day).date().isoformat() for day in frame.index]


def _snap(day: str, sessions: Sequence[str]) -> str | None:
    """Return the first session on or after *day*, or ``None`` past the end.

    A call written on a Sunday, or during Tet, has no session of its own.
    Snapping forward is the only honest reading: the first price at which the
    call could have been acted on.
    """
    for session in sessions:
        if session >= day:
            return session
    return None


@dataclass
class Pending:
    """A checkpoint that exists but cannot be scored yet."""

    call_id: str
    ticker: str
    checkpoint_sessions: int
    reason: str


@dataclass
class ResolveReport:
    """What one resolver pass did."""

    outcomes: list[Outcome] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    pending: list[Pending] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a one-line summary for the CLI."""
        tally: dict[str, int] = {}
        for outcome in self.outcomes:
            tally[outcome.verdict] = tally.get(outcome.verdict, 0) + 1
        verdicts = ", ".join(f"{name}={count}" for name, count in sorted(tally.items()))
        return (
            f"{len(self.outcomes)} outcome(s) [{verdicts or 'none'}], "
            f"{len(self.pending)} pending, {len(self.warnings)} warning(s)"
        )


def _price_evidence(symbol: str, start: str, end: str, numbers: dict[str, float]) -> Evidence:
    """Build the price-series evidence an outcome is closed against.

    ``observed_at`` is the close of *end*, 15:00 in Ho Chi Minh City, because
    that is the instant the last number quoted here became observable -- not
    whenever the resolver happened to run.
    """
    excerpt = f"{symbol} {start}..{end} " + " ".join(
        f"{key}={value:.6g}" for key, value in sorted(numbers.items())
    )
    year, month, day = (int(part) for part in end.split("-"))
    observed = datetime(year, month, day, 8, 0, 0, tzinfo=timezone.utc)
    return Evidence(
        kind="price_series",
        observed_at=observed.isoformat().replace("+00:00", "Z"),
        source_path=f"datapro://daily/{symbol}",
        locator=f"{start}..{end}",
        sha256=sha256_text(excerpt),
        excerpt=excerpt,
    )


def _window_return(frame: pd.DataFrame, start: str, end: str) -> float | None:
    """Return the adjusted close-to-close return over ``(start, end]``."""
    try:
        first = float(frame.loc[pd.Timestamp(start), "close"])
        last = float(frame.loc[pd.Timestamp(end), "close"])
    except KeyError:
        return None
    if first <= 0:
        return None
    return last / first - 1.0


def _in_window(series: pd.Series, start: str, end: str) -> pd.Series:
    """Return the part of *series* falling in ``(start, end]``."""
    return series[(series.index > pd.Timestamp(start)) & (series.index <= pd.Timestamp(end))]


def _as_adjusted(level: float, entry_rate: float) -> float:
    """Express a price *quoted on the day of the call* on the adjusted grid.

    ``adj_rate`` is the cumulative factor from a bar forward to the present, so
    a level quoted at entry sits at ``level / entry_rate`` on the series every
    later bar is measured on. Dividing is not cosmetic: PET ran a 1,45x
    corporate action inside its own 21-session window, and its traded price
    "fell" from 54.800 to 37.400 while the stock lost 1,07%. A target or a stop
    compared straight against a later traded price is comparing two different
    grids, which is how a target 23% *above* the outcome gets recorded as 15%
    below it.
    """
    return level / entry_rate


def _window_extremes(frame: pd.DataFrame, start: str, end: str) -> dict[str, float]:
    """Return the window's extremes on both grids.

    The adjusted pair is the comparable one -- it is what a quoted level must be
    tested against. The traded pair is what a human would have seen on a screen,
    and the two diverge exactly when a corporate action lands inside the window.
    Both are recorded because the verdict is close-to-close, and the extremes
    answer a sharper question the report layer needs for a ``wait``: whether the
    entry it promised ever actually printed. BSR waiting at 26.350 for 24.000 is
    judged here on alpha, but it did trade 23.350 -- and that is unanswerable
    once these are gone.
    """
    return {
        "adj_low": float(_in_window(frame["low"], start, end).min()),
        "adj_high": float(_in_window(frame["high"], start, end).max()),
        "traded_low": float(_in_window(_traded(frame, "low"), start, end).min()),
        "traded_high": float(_in_window(_traded(frame, "high"), start, end).max()),
    }


def _stop_breach(frame: pd.DataFrame, start: str, end: str, stop_adjusted: float) -> str | None:
    """Return the first session in ``(start, end]`` whose low hit the stop.

    *stop_adjusted* must already be on the adjusted grid, via
    :func:`_as_adjusted`; the comparison is made there because that is the only
    grid on which every bar in the window is measured the same way.

    Only long-side calls are checked. A ``stop`` on a ``wait`` or ``avoid`` call
    is not the same object -- BSR waits at 26.350 for a target of 24.000 with a
    "stop" at 24.900, sitting between the two -- and guessing which side it
    guards would be inventing the analyst's intent.
    """
    hits = _in_window(frame["low"], start, end)
    hits = hits[hits <= stop_adjusted]
    if hits.empty:
        return None
    return pd.Timestamp(hits.index[0]).date().isoformat()


def _superseded_by(
    call: CallRecord, siblings: Sequence[CallRecord], checkpoint_date: str
) -> CallRecord | None:
    """Return the later revision in force by *checkpoint_date*, if any.

    A call the committee revised on session 30 was not still standing at session
    63; scoring it there would grade a view nobody held.
    """
    later = [
        other
        for other in siblings
        if other.revision > call.revision and other.as_of <= checkpoint_date
    ]
    return min(later, key=lambda item: (item.as_of, item.revision)) if later else None


def score_call(
    call: CallRecord,
    *,
    prices: pd.DataFrame,
    benchmark: pd.DataFrame,
    vn30: pd.DataFrame | None = None,
    peers: Mapping[str, pd.DataFrame] | None = None,
    siblings: Sequence[CallRecord] = (),
    checkpoints: Iterable[int] = CHECKPOINT_SESSIONS,
) -> ResolveReport:
    """Score one call at every checkpoint the calendar has reached.

    Args:
        call: The revision to score, on its own clock from its own ``as_of``.
        prices: VND bars for the ticker, covering ``as_of`` onward.
        benchmark: VN-Index bars; also the trading calendar. Carrying
            :data:`~src.learning.attribution.REGIME_LOOKBACK` sessions of
            history before ``as_of`` additionally fills in the regime.
        vn30: VN30 bars, recorded but never used for the verdict.
        peers: Universe frames for the cross-sectional base rate.
        siblings: Other revisions of the same episode, for supersession.
        checkpoints: Checkpoints in trading sessions.

    Returns:
        A report holding the outcomes, their price evidence, and whatever could
        not be scored -- never a verdict the data did not support.
    """
    report = ResolveReport()
    sessions = _sessions(benchmark)
    entry = _snap(call.as_of, sessions)
    if entry is None:
        report.pending.append(
            Pending(call.call_id, call.ticker, 0, f"as_of {call.as_of} is past the calendar")
        )
        return report
    if entry != call.as_of:
        report.warnings.append(
            f"{call.ticker} {call.call_id}: as_of {call.as_of} is not a trading session; "
            f"scored from {entry}"
        )

    direction = ACTION_DIRECTION[call.action]
    traded_close = _traded(prices, "close")
    try:
        entry_rate = float(prices.loc[pd.Timestamp(entry), "adj_rate"])
    except KeyError:
        report.pending.append(
            Pending(call.call_id, call.ticker, 0, f"no bar for {call.ticker} on {entry}")
        )
        return report

    if call.ref_price is not None and pd.Timestamp(entry) in traded_close.index:
        actual = float(traded_close.loc[pd.Timestamp(entry)])
        gap = actual / call.ref_price - 1.0
        if abs(gap) > REF_PRICE_TOLERANCE:
            report.warnings.append(
                f"{call.ticker} {call.call_id}: ref_price {call.ref_price:,.0f} is "
                f"{gap:+.2%} from the {entry} traded close {actual:,.0f} -- an entry "
                "level, not a close; returns are taken from the close"
            )

    for checkpoint in checkpoints:
        landing = resolve_deadline(entry, checkpoint, sessions)
        if landing is None:
            report.pending.append(
                Pending(call.call_id, call.ticker, checkpoint, "checkpoint has not elapsed")
            )
            continue

        realized = _window_return(prices, entry, landing)
        vni_ret = _window_return(benchmark, entry, landing)
        if realized is None or vni_ret is None:
            report.pending.append(
                Pending(call.call_id, call.ticker, checkpoint, "no bar at one endpoint")
            )
            continue

        resolved_price = float(traded_close.loc[pd.Timestamp(landing)])
        exit_adjusted = float(prices.loc[pd.Timestamp(landing), "close"])
        alpha = realized - vni_ret
        vn30_ret = _window_return(vn30, entry, landing) if vn30 is not None else None
        target_error = (
            exit_adjusted / _as_adjusted(call.target, entry_rate) - 1.0
            if call.target
            else None
        )

        notes: list[str] = []
        replacement = _superseded_by(call, siblings, landing)
        breach = (
            _stop_breach(prices, entry, landing, _as_adjusted(call.stop, entry_rate))
            if direction > 0 and call.stop is not None
            else None
        )

        if replacement is not None:
            verdict = "invalidated"
            notes.append(
                f"superseded by revision {replacement.revision} on {replacement.as_of}"
            )
        elif breach is not None:
            verdict = "invalidated"
            notes.append(f"stop {call.stop:,.0f} traded through on {breach}")
        elif direction == 0:
            verdict = NO_CLAIM
            notes.append(f"{call.action} asserts no direction; measured, not graded")
        else:
            verdict = "hit" if alpha * direction > 0 else "miss"

        unchecked = len(call.invalidation_triggers) - (1 if breach is not None else 0)
        if unchecked > 0:
            notes.append(f"{unchecked} free-text trigger(s) not machine-checked")

        regime = market_state(benchmark, entry)
        if not regime:
            notes.append(f"regime needs {REGIME_LOOKBACK} sessions of index history")
        percentile = None
        if peers:
            ranked = peer_returns(peers, entry, landing, exclude=call.ticker)
            percentile = cross_sectional_percentile(realized, ranked)
            if percentile is None:
                notes.append(f"only {len(ranked)} peer(s) priced; no base rate")
            else:
                notes.append(f"base rate vs {len(ranked)} peers (current membership)")
        else:
            notes.append("no peer universe; base rate not attributed")

        evidences = [
            _price_evidence(
                call.ticker,
                entry,
                landing,
                {
                    "entry_close": float(prices.loc[pd.Timestamp(entry), "close"]),
                    "entry_adj_rate": entry_rate,
                    "exit_close": exit_adjusted,
                    "exit_traded": resolved_price,
                    **_window_extremes(prices, entry, landing),
                },
            ),
            _price_evidence(
                BENCHMARK_SYMBOL,
                entry,
                landing,
                {
                    "entry_close": float(benchmark.loc[pd.Timestamp(entry), "close"]),
                    "exit_close": float(benchmark.loc[pd.Timestamp(landing), "close"]),
                },
            ),
        ]
        report.evidence.extend(evidences)
        report.outcomes.append(
            Outcome(
                call_id=call.call_id,
                episode_id=call.episode_id,
                resolved_at=landing,
                checkpoint_sessions=checkpoint,
                verdict=verdict,
                resolved_price=resolved_price,
                realized_ret=realized,
                vni_ret=vni_ret,
                vn30_ret=vn30_ret,
                alpha=alpha,
                target_error=target_error,
                trigger_fired=breach is not None,
                regime=regime,
                base_rate_pctile=percentile,
                evidence_ids=[item.evidence_id for item in evidences],
                notes="; ".join(notes),
            )
        )
    return report


def resolve_ledger(
    store: LearningStore,
    *,
    fetch: PriceFetcher = datapro_prices,
    today: str | None = None,
    ticker: str | None = None,
    checkpoints: Iterable[int] = CHECKPOINT_SESSIONS,
    universe: Sequence[str] | None = None,
    write: bool = True,
) -> ResolveReport:
    """Score every call on the ledger the calendar has caught up with.

    Args:
        store: The ledger.
        fetch: Price source, injectable so a test can hand over a real frame.
        today: Last session to consider; defaults to the current UTC date.
        ticker: Restrict to one symbol.
        checkpoints: Checkpoints in trading sessions.
        universe: Peer symbols for the cross-sectional base rate. Defaults to
            current VN30 membership; pass an empty sequence to skip it.
        write: Append the outcomes. ``False`` makes the pass a dry run.

    Returns:
        The combined report across every call.
    """
    calls = store.list_calls(ticker=ticker)
    report = ResolveReport()
    if not calls:
        return report

    end = today or datetime.now(timezone.utc).date().isoformat()
    start = min(call.as_of for call in calls)
    # The index is fetched from well before the first call so the regime has a
    # trailing year to measure against. Calendar days, generously: 252 sessions
    # is roughly 366 days, and asking for too much history costs one request
    # while asking for too little silently blanks the regime column.
    history_start = (
        pd.Timestamp(start) - pd.Timedelta(days=int(REGIME_LOOKBACK * 1.65))
    ).date().isoformat()
    benchmark = fetch(BENCHMARK_SYMBOL, history_start, end)
    try:
        vn30 = fetch(VN30_SYMBOL, start, end)
    except Exception as exc:  # noqa: BLE001 - VN30 is recorded, never decisive
        report.warnings.append(f"{VN30_SYMBOL} unavailable, vn30_ret left empty: {exc}")
        vn30 = None

    peers: dict[str, pd.DataFrame] = {}
    if universe is None:
        try:
            universe = vn30_symbols()
        except Exception as exc:  # noqa: BLE001 - the base rate is not the verdict
            report.warnings.append(f"VN30 membership unavailable, no base rate: {exc}")
            universe = []
    if universe:
        peers, problems = load_universe(fetch, universe, start, end)
        report.warnings.extend(f"peer {problem}" for problem in problems)

    by_episode: dict[str, list[CallRecord]] = {}
    for call in calls:
        by_episode.setdefault(call.episode_id, []).append(call)

    # The peer frames cover the same span, so a call on a VN30 name is already
    # priced and need not be fetched twice.
    frames: dict[str, pd.DataFrame] = dict(peers)
    for call in calls:
        if call.ticker not in frames:
            try:
                frames[call.ticker] = fetch(call.ticker, start, end)
            except Exception as exc:  # noqa: BLE001 - one dead symbol is not the run
                report.warnings.append(f"{call.ticker}: no price series, not scored: {exc}")
                frames[call.ticker] = pd.DataFrame()
        prices = frames[call.ticker]
        if prices.empty:
            continue
        one = score_call(
            call,
            prices=prices,
            benchmark=benchmark,
            vn30=vn30,
            peers=peers,
            siblings=by_episode[call.episode_id],
            checkpoints=checkpoints,
        )
        report.outcomes.extend(one.outcomes)
        report.evidence.extend(one.evidence)
        report.pending.extend(one.pending)
        report.warnings.extend(one.warnings)

    if write:
        for evidence in report.evidence:
            store.append_evidence(evidence)
        for outcome in report.outcomes:
            store.append_outcome(outcome)
    return report
