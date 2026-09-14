"""Shared universe scan for breadth and ICB sector strength.

Reuses the market data pack's universe mapping and price normalization. Current
constituents are explicitly NOT historical constituents; this feed cannot
certify a historical backtest. Equal-weight returns use only traded names.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pandas as pd

_lock = threading.Lock()
_cached = None
_cached_at = 0.0
_bars = {}
_universe = None


def frame(now):
    global _cached, _cached_at, _universe
    with _lock:
        if _cached is not None and time.monotonic() - _cached_at < 300:
            return _cached.copy()
        from vndata.price import ohlcv
        if _universe is None:
            from vnstock_data import Reference
            _universe = Reference().equity.list_by_exchange()
            required = {"symbol", "exchange", "icb_code_lv2"}
            if not required <= set(_universe):
                raise ValueError("Universe must include symbol, exchange and icb_code_lv2")
            _universe = _universe[_universe.exchange.isin({"HOSE", "HNX", "UPCOM"})]
        universe = _universe
        def fetch(symbol):
            previous = _bars.get(symbol)
            days = 5 if previous is not None else 420
            try:
                current = ohlcv(symbol, (now-timedelta(days=days)).date().isoformat(),
                                now.date().isoformat(), allow_fallback=False)
                merged = pd.concat([previous, current]) if previous is not None else current
                merged = merged[~merged.index.duplicated(keep="last")].sort_index().tail(300)
                return symbol, merged
            except Exception:
                return symbol, None
        with ThreadPoolExecutor(max_workers=4) as pool:
            fetched = list(pool.map(fetch, universe.symbol.tolist()))
        successful = {symbol: bars for symbol, bars in fetched if bars is not None and not bars.empty}
        if len(successful) < max(100, .8 * len(universe)):
            raise ValueError("Universe coverage below 80%; breadth/sector signal suppressed")
        _bars.update(successful)
        groups = universe.set_index("symbol")["icb_code_lv2"].astype(str).to_dict()
        long = []
        for symbol, bars in successful.items():
            change = bars.close.pct_change(fill_method=None) * 100
            ma50 = bars.close.rolling(50, min_periods=50).mean()
            for dt in bars.index[-120:]:
                if not bars.loc[dt, "volume"] > 0:
                    continue
                long.append({"time": dt, "entity": groups.get(symbol, "unknown"),
                             "return_pct": change.loc[dt],
                             "above_ma50_pct": (100.0 if bars.loc[dt, "close"] > ma50.loc[dt] else 0.0)
                             if pd.notna(ma50.loc[dt]) else float("nan")})
        raw = pd.DataFrame(long)
        sector = raw.groupby(["time", "entity"])[["return_pct", "above_ma50_pct"]].mean().reset_index()
        market = raw.groupby("time")[["return_pct", "above_ma50_pct"]].mean().reset_index()
        market["entity"] = "VN_MARKET"
        baseline = market.set_index("time").return_pct
        sector["relative_strength_pct"] = sector.return_pct - sector.time.map(baseline)
        market["relative_strength_pct"] = 0.0
        _cached = pd.concat([sector, market], ignore_index=True)
        _cached_at = time.monotonic()
        return _cached.copy()
