"""Say what the market was doing, so a hit rate is not read as skill alone.

Two attributions, and one refusal.

**The regime** is a description of the index on the day a call was made --
drawdown from the trailing year's high, two momentum windows, and where the
current realised volatility sits in its own trailing year. It is deliberately a
state descriptor and not a named regime: a name like "chop" is a claim about a
taxonomy nobody here has validated, whereas the four numbers are measurements.
Its job is to let the scorecard say *these calls were all made in one market*,
which at n=8 matters more than the hit rate itself.

**The base rate** is a cross-sectional percentile: where the call's stock landed
among its peers over the identical window. This is not the same control as
alpha. Alpha asks whether the stock beat the index, and a Vietnamese index is a
handful of large caps; the percentile asks whether it beat the *typical stock*,
which is what a stock picker's opportunity set actually looks like. TPB fell
14,1% while the index fell 9,4% -- but whether that was a bad two months for TPB
or a bad two months for everything is a question only the cross-section answers.

**The refusal** is the base-rate file the plan named.
``_risk_committee_202608/out/calibration.json`` distributes *VN-Index* forward
returns conditioned on regime, n=147. Ranking one stock's return inside a
distribution of index returns reads the stock's roughly doubled volatility as
skill: a single name lands in the tails constantly, for reasons that have
nothing to do with the call. It is the right file for the question it was built
for -- what does the index do next -- and the wrong denominator for this one.
"""

from __future__ import annotations

from typing import Callable, Iterable, Mapping

import numpy as np
import pandas as pd

#: Sessions of index history the regime descriptor needs before it will speak.
REGIME_LOOKBACK = 252

#: Momentum windows, in trading sessions.
MOMENTUM_WINDOWS = (21, 63)

#: Realised-volatility window, in trading sessions.
VOL_WINDOW = 21

#: Fewest peers that may stand behind a percentile. Below this the number is
#: noise wearing a decimal point.
MIN_PEERS = 10


def market_state(benchmark: pd.DataFrame, day: str) -> str:
    """Describe the index on *day*, or return ``""`` when history is short.

    Args:
        benchmark: Index bars, indexed by trade date, covering at least
            :data:`REGIME_LOOKBACK` sessions before *day*.
        day: The session to describe.

    Returns:
        A compact descriptor such as
        ``dd252=-6.2% mom63=+8.1% mom21=-1.3% rv_pct=0.42``, or the empty
        string when there is not enough history. Empty is the honest answer:
        a drawdown measured against 40 sessions is not a drawdown against a
        year, and silently relabelling it would make the scorecard's regime
        column mean two different things in the same table.
    """
    closes = benchmark["close"]
    stamp = pd.Timestamp(day)
    if stamp not in closes.index:
        return ""
    position = closes.index.get_loc(stamp)
    if position < REGIME_LOOKBACK:
        return ""

    history = closes.iloc[position - REGIME_LOOKBACK : position + 1]
    spot = float(history.iloc[-1])
    parts = [f"dd252={spot / float(history.max()) - 1.0:+.1%}"]
    for window in sorted(MOMENTUM_WINDOWS, reverse=True):
        past = float(history.iloc[-(window + 1)])
        parts.append(f"mom{window}={spot / past - 1.0:+.1%}")

    returns = np.log(history / history.shift(1)).dropna()
    realised = returns.rolling(VOL_WINDOW).std().dropna()
    if len(realised) >= VOL_WINDOW:
        current = float(realised.iloc[-1])
        parts.append(f"rv_pct={float((realised < current).mean()):.2f}")
    return " ".join(parts)


def peer_returns(
    peers: Mapping[str, pd.DataFrame], start: str, end: str, *, exclude: str = ""
) -> dict[str, float]:
    """Return each peer's close-to-close return over ``(start, end]``.

    A peer that did not trade on both endpoints is dropped rather than filled:
    a suspended stock has no return over the window, and inventing one would
    move the percentile the whole measurement exists to produce.
    """
    out: dict[str, float] = {}
    for symbol, frame in peers.items():
        if symbol == exclude.upper() or frame is None or frame.empty:
            continue
        try:
            first = float(frame.loc[pd.Timestamp(start), "close"])
            last = float(frame.loc[pd.Timestamp(end), "close"])
        except KeyError:
            continue
        if first > 0:
            out[symbol] = last / first - 1.0
    return out


def cross_sectional_percentile(value: float, peers: Mapping[str, float]) -> float | None:
    """Return where *value* sits among *peers*, in ``[0, 1]``.

    Returns ``None`` below :data:`MIN_PEERS`, because a percentile over four
    names is a rounding artefact, not a base rate.
    """
    values = list(peers.values())
    if len(values) < MIN_PEERS:
        return None
    below = sum(1 for item in values if item < value)
    ties = sum(1 for item in values if item == value)
    return (below + 0.5 * ties) / len(values)


def load_universe(
    fetch: Callable[[str, str, str], pd.DataFrame],
    symbols: Iterable[str],
    start: str,
    end: str,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Fetch every peer, keeping the ones that answered.

    Returns:
        The frames that loaded, and a list of complaints about the ones that
        did not. One dead symbol must not cost the whole cross-section, but it
        must not vanish silently either.
    """
    frames: dict[str, pd.DataFrame] = {}
    problems: list[str] = []
    for symbol in symbols:
        name = str(symbol).strip().upper().replace(".VN", "")
        if not name or name in frames:
            continue
        try:
            frame = fetch(name, start, end)
        except Exception as exc:  # noqa: BLE001 - one dead peer is not the universe
            problems.append(f"{name}: {exc}")
            continue
        if frame is not None and not frame.empty:
            frames[name] = frame
    return frames, problems


def parse_state(descriptor: str) -> dict[str, float]:
    """Read a regime descriptor back into numbers.

    The descriptor is written by :func:`market_state` and stored on the outcome,
    so a report can group by market conditions without refetching an index.
    """
    values: dict[str, float] = {}
    for token in descriptor.split():
        key, separator, raw = token.partition("=")
        if not separator:
            continue
        try:
            values[key] = float(raw.rstrip("%")) / (100.0 if raw.endswith("%") else 1.0)
        except ValueError:
            continue
    return values


def vn30_symbols() -> list[str]:
    """Return current VN30 membership.

    **Current**, not point-in-time: the reference endpoint publishes today's
    constituents only. A name dropped from the index during a scoring window is
    therefore absent from the cross-section, and since names are dropped for
    falling, the surviving peer distribution sits a little high and every
    percentile computed against it reads a little low. The bias is small over
    the two-month windows on this ledger and it is real; it is stated on the
    scorecard rather than corrected, because correcting it needs a membership
    history nothing here has.
    """
    from vndata.reference import symbols_by_group

    members = symbols_by_group("VN30")
    column = members["symbol"] if isinstance(members, pd.DataFrame) else members
    return [str(value).strip().upper() for value in column.tolist() if str(value).strip()]
