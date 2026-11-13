"""Technical analysis — computed locally on DataPro prices.

``vnstock_ta`` was retired on 13/11/2026 together with the rest of the vnstock
subscription. Indicator maths has no vendor dependency, so it is computed here
with pandas on DataPro bars — the same prices the rest of the stack treats as
authoritative. Computing an indicator on one price series and quoting a level
from another is how a signal ends up disagreeing with the chart it describes.

The call shape of the old ``Indicator`` object is kept so existing skills read
the same::

    ind = vndata.ta.indicator("HPG.VN", "2026-01-01", "2026-11-13")
    ind.momentum.rsi(length=14)
    ind.trend.macd()

All averages use Wilder smoothing where the textbook definition does (RSI,
ATR); everything else is a plain rolling window. Every method returns a
``Series`` or ``DataFrame`` indexed like the input bars.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from vndata import price as _price
from vndata.errors import SourceUnavailable

#: Indicator families exposed by :func:`indicator`.
FAMILIES = ("trend", "momentum", "volatility", "volume", "statistics")


def to_ta_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape a :mod:`vndata.price` frame into a ``time`` + OHLCV frame."""
    out = df.reset_index().rename(columns={"trade_date": "time"})
    needed = ["time", "open", "high", "low", "close", "volume"]
    missing = [c for c in needed if c not in out.columns]
    if missing:
        raise ValueError(f"price frame is missing columns required for TA: {missing}")
    return out[needed]


def _wilder(s: pd.Series, length: int) -> pd.Series:
    """Wilder smoothing, seeded with the simple mean of the first *length* values.

    An EWM seeded with the first value drifts from the textbook figure for
    dozens of bars; seeding with the SMA reproduces Wilder's worked example.
    """
    out = pd.Series(np.nan, index=s.index, dtype=float)
    valid = s.dropna().astype(float)
    if len(valid) < length:
        return out
    vals = valid.to_numpy()
    avg = vals[:length].mean()
    smoothed = [avg]
    for x in vals[length:]:
        avg = (avg * (length - 1) + x) / length
        smoothed.append(avg)
    out.loc[valid.index[length - 1:]] = smoothed
    return out


def _families(bars: pd.DataFrame) -> SimpleNamespace:
    o, h, l, c, v = (bars[k].astype(float) for k in ("open", "high", "low", "close", "volume"))

    def sma(length: int = 20) -> pd.Series:
        return c.rolling(length).mean().rename(f"SMA_{length}")

    def ema(length: int = 20) -> pd.Series:
        return c.ewm(span=length, adjust=False, min_periods=length).mean().rename(f"EMA_{length}")

    def macd(fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        line = c.ewm(span=fast, adjust=False).mean() - c.ewm(span=slow, adjust=False).mean()
        sig = line.ewm(span=signal, adjust=False).mean()
        return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})

    def rsi(length: int = 14) -> pd.Series:
        d = c.diff()
        gain = _wilder(d.clip(lower=0), length)
        loss = _wilder(-d.clip(upper=0), length)
        rs = gain / loss.replace(0, np.nan)
        out = 100 - 100 / (1 + rs)
        out = out.where(loss != 0, 100.0)  # no losses in the window -> RSI 100
        return out.where(gain.notna()).rename(f"RSI_{length}")

    def stoch(k: int = 14, d: int = 3) -> pd.DataFrame:
        lo, hi = l.rolling(k).min(), h.rolling(k).max()
        pct_k = 100 * (c - lo) / (hi - lo).replace(0, np.nan)
        return pd.DataFrame({"k": pct_k, "d": pct_k.rolling(d).mean()})

    def roc(length: int = 10) -> pd.Series:
        return (100 * c.pct_change(length)).rename(f"ROC_{length}")

    def atr(length: int = 14) -> pd.Series:
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return _wilder(tr, length).rename(f"ATR_{length}")

    def bbands(length: int = 20, std: float = 2.0) -> pd.DataFrame:
        mid = c.rolling(length).mean()
        dev = c.rolling(length).std(ddof=0)
        return pd.DataFrame({"lower": mid - std * dev, "mid": mid, "upper": mid + std * dev})

    def obv() -> pd.Series:
        return (np.sign(c.diff()).fillna(0) * v).cumsum().rename("OBV")

    def vwma(length: int = 20) -> pd.Series:
        return ((c * v).rolling(length).sum() / v.rolling(length).sum()).rename(f"VWMA_{length}")

    def stdev(length: int = 20) -> pd.Series:
        return c.rolling(length).std().rename(f"STDEV_{length}")

    def zscore(length: int = 20) -> pd.Series:
        m, s = c.rolling(length).mean(), c.rolling(length).std()
        return ((c - m) / s).rename(f"Z_{length}")

    return SimpleNamespace(
        trend=SimpleNamespace(sma=sma, ema=ema, macd=macd),
        momentum=SimpleNamespace(rsi=rsi, stoch=stoch, roc=roc),
        volatility=SimpleNamespace(atr=atr, bbands=bbands),
        volume=SimpleNamespace(obv=obv, vwma=vwma),
        statistics=SimpleNamespace(stdev=stdev, zscore=zscore),
    )


def from_frame(bars: pd.DataFrame) -> SimpleNamespace:
    """Bind the indicator families to an existing OHLCV frame."""
    missing = [k for k in ("open", "high", "low", "close", "volume") if k not in bars.columns]
    if missing:
        raise ValueError(f"price frame is missing columns required for TA: {missing}")
    ind = _families(bars)
    ind.source = bars.attrs.get("source", "unknown")
    return ind


def indicator(symbol: str, start: str, end: str, *, interval: str = "1D") -> SimpleNamespace:
    """Return indicator families bound to DataPro bars for *symbol*.

    Raises:
        SourceUnavailable: DataPro is down or returned no bars.
    """
    bars = _price.ohlcv(symbol, start, end, interval=interval)
    if bars.empty:
        raise SourceUnavailable(f"no price bars for {symbol} between {start} and {end}.")
    return from_frame(bars)
