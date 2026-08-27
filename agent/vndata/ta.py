"""Technical analysis — ``vnstock_ta`` computed on DataPro prices.

``vnstock_ta`` is the truth source for indicator *maths*; it is not a data
source. It runs on whatever bars it is handed, so this module hands it DataPro
bars — the same prices the rest of the stack treats as authoritative. Computing
an indicator on one price series and quoting a level from another is how a
signal ends up disagreeing with the chart it is supposed to describe.

``Indicator`` expects a frame with a ``time`` column plus ``open``, ``high``,
``low``, ``close`` and ``volume``; :func:`indicator` performs that reshape from
the date-indexed frame :mod:`vndata.price` returns.
"""

from __future__ import annotations

import pandas as pd

from vndata import price as _price
from vndata.errors import SourceUnavailable

#: Indicator families exposed by ``vnstock_ta``.
FAMILIES = ("trend", "momentum", "volatility", "volume", "statistics")


def to_ta_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape a :mod:`vndata.price` frame into what ``Indicator`` expects."""
    out = df.reset_index().rename(columns={"trade_date": "time"})
    needed = ["time", "open", "high", "low", "close", "volume"]
    missing = [c for c in needed if c not in out.columns]
    if missing:
        raise ValueError(f"price frame is missing columns required for TA: {missing}")
    return out[needed]


def indicator(symbol: str, start: str, end: str, *, interval: str = "1D"):
    """Return a ``vnstock_ta.Indicator`` bound to DataPro bars for *symbol*.

    Args:
        symbol: Ticker, bare or ``.VN``-suffixed.
        start: Inclusive start date, ``YYYY-MM-DD``.
        end: Inclusive end date, ``YYYY-MM-DD``.
        interval: Bar size passed to :func:`vndata.price.ohlcv`.

    Returns:
        An ``Indicator`` whose ``.trend`` / ``.momentum`` / ``.volatility`` /
        ``.volume`` / ``.statistics`` families are ready to call.

    Raises:
        SourceUnavailable: If ``vnstock_ta`` is missing or no bars came back.
    """
    try:
        from vnstock_ta import Indicator
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable("vnstock_ta is not installed.") from exc

    bars = _price.ohlcv(symbol, start, end, interval=interval)
    if bars.empty:
        raise SourceUnavailable(f"no price bars for {symbol} between {start} and {end}.")

    ind = Indicator(data=to_ta_frame(bars))
    ind.source = bars.attrs.get("source", "datapro")
    ind.degraded = bars.attrs.get("degraded", False)
    return ind
