"""Benchmark ticker resolution and fetch for backtest comparison.

Provides a lightweight, zero-dependency way to fetch benchmark reference
data given a set of strategy codes and a data source.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from backtest.loaders.registry import resolve_loader
from backtest.loaders.yfinance_loader import DataLoader as YfinanceLoader


# -------------------------------------------------------------------
# Benchmark map: market type → default ticker
# -------------------------------------------------------------------

MARKET_BENCHMARKS: dict[str, Optional[str]] = {
    "us_equity":  "SPY",
    "hk_equity":  "HK.03100",   # Hang Seng China Enterprises ETF
    "a_share":    "000300.SH",  # CSI 300 (China A-share core index)
    "vn_equity":  "VNINDEX.VN",  # broad market; pass explicit "VN30INDEX.VN" for a VN30 mandate
    "crypto":     "BTC-USDT",
    "futures":    "ES.CME",      # E-mini S&P 500 futures
    "forex":      None,         # no universal benchmark
}

# Label written into metrics when no external benchmark was fetched and the
# engine fell back to the equal-weight mean of the strategy's own universe.
# That fallback is *not* a market benchmark, and unlabelled it silently turns
# information_ratio / excess_return into self-comparison.
INTERNAL_FALLBACK_LABEL = "internal_equal_weight_universe"


class BenchmarkUnavailable(RuntimeError):
    """Raised when a benchmark was requested but could not be fetched.

    Deliberately loud, matching the ``SourceUnavailable`` doctrine in
    ``VN_DATA_SOURCE.md``: a dead benchmark source must stop the run rather
    than degrade into comparing the strategy against itself.
    """


@dataclass
class BenchmarkResult:
    ticker:     str
    ret_series: pd.Series       # per-bar returns, index = timestamps
    total_ret: float          # total return over the period


def resolve_benchmark(
    strategy_codes: list[str],
    source:       str,
    start_date:   str,
    end_date:     str,
    interval:     str = "1D",
    explicit:     Optional[str] = None,
) -> Optional[BenchmarkResult]:
    """Resolve the appropriate benchmark ticker and fetch its return series.

    Args:
        strategy_codes: Instruments being backtested (used for market inference).
        source:         Data source name (tushare / yfinance / okx / akshare / ccxt).
        start_date:     Backtest start date.
        end_date:       Backtest end date.
        interval:       Bar interval (1m / 5m / 15m / 30m / 1H / 4H / 1D).
        explicit:       Override ticker (e.g. "SPY" passed via config).

    Returns:
        BenchmarkResult with return series and total return, or None if no
        benchmark applies to this market at all (forex).

    Raises:
        BenchmarkUnavailable: A benchmark applies but could not be fetched.
            Callers must not silently continue — an unfetchable benchmark
            previously degraded into comparing the strategy against its own
            universe, which quietly invalidated information_ratio and
            excess_return.
    """
    market = _infer_market(strategy_codes, source)
    ticker = explicit or MARKET_BENCHMARKS.get(market)
    if ticker is None:
        return None

    try:
        bench_df = _fetch_benchmark(ticker, start_date, end_date, interval, market)
    except Exception as exc:
        raise BenchmarkUnavailable(
            f"benchmark {ticker!r} (market={market}) could not be fetched: {exc}"
        ) from exc

    if bench_df.empty or "close" not in bench_df.columns:
        raise BenchmarkUnavailable(
            f"benchmark {ticker!r} (market={market}) returned no usable close series"
        )

    close = bench_df["close"].dropna()
    if len(close) < 2:
        raise BenchmarkUnavailable(
            f"benchmark {ticker!r} (market={market}) returned fewer than 2 bars"
        )

    ret_series = close.pct_change().fillna(0.0)
    total_ret   = float((1 + ret_series).prod() - 1)

    return BenchmarkResult(ticker=ticker, ret_series=ret_series, total_ret=total_ret)


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------

def _infer_market(codes: list[str], source: str) -> str:
    """Rough market inference from symbol patterns and source."""
    if not codes:
        return "us_equity"

    first = codes[0].upper()

    if source in ("okx", "ccxt") or "-" in first or "/" in first:
        return "crypto"
    if first.endswith(".VN") or source in ("datapro", "vnstock_data", "vnstock"):
        return "vn_equity"
    if first.endswith(".US"):
        return "us_equity"
    if first.endswith(".HK"):
        return "hk_equity"
    if source in ("tushare", "akshare"):
        if first.isdigit() and len(first) == 6:
            return "a_share"
        if first.startswith(("IF", "IC", "IH", "IM", "T", "TF")):
            return "futures"
        return "a_share"

    return "us_equity"


def _fetch_benchmark(
    ticker:    str,
    start_date: str,
    end_date:   str,
    interval:   str,
    market:     str = "us_equity",
) -> pd.DataFrame:
    """Fetch benchmark OHLCV data.

    Vietnam goes through its own loader chain (DataPro, then the sponsored
    Unified UI): VNINDEX / VN30INDEX are not reachable from yfinance at all.
    Every other market keeps the pre-existing yfinance path — which in
    practice only ever worked for us_equity / hk_equity, a limitation left
    untouched here rather than changed blind.
    """
    loader = resolve_loader(market) if market == "vn_equity" else YfinanceLoader()
    result = loader.fetch([ticker], start_date, end_date, interval=interval)

    if isinstance(result, dict):
        df = result.get(ticker)
    elif isinstance(result, pd.DataFrame):
        df = result
    else:
        return pd.DataFrame()

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return pd.DataFrame()

    return df