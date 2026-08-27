"""vnstock OHLCV price loader for Vietnam equities (internet, no desktop).

Companion to the DataPro loader. DataPro gives the richest VN bars (adjusted
OHLCV + foreign flow + the official ``REF_PX`` reference price) but needs the
DataPro desktop app listening on ``localhost:6789``. vnstock fetches the same
daily/intraday bars straight over the internet with no desktop dependency, so
it serves as the zero-setup fallback in the ``vn_equity`` chain — the system can
still load VN data when DataPro is not running.

Symbols may be bare (``VCB``) or ``.VN``-suffixed (``VCB.VN``); the suffix is
what routes the symbol to the VN engine and is stripped before the API call.

Reference price
---------------
vnstock does not return ``REF_PX``, so we synthesise ``pre_close`` as the prior
session's close — the standard HOSE/HNX reference-price proxy — letting the VN
engine still approximate the ±7/10/15% daily bands.

Config:
    VNSTOCK_PRICE_SOURCE  data sub-source passed to ``Quote`` (default ``vci``;
                          ``kbs`` is the documented alternative). TCBS is
                          deprecated and intentionally not used.
"""

from __future__ import annotations

import contextlib
import io
import os
from typing import Dict, List, Optional

import pandas as pd

from backtest.loaders.base import cached_loader_fetch, validate_date_range
from backtest.loaders.registry import register

# Our interval tokens -> vnstock ``Quote.history`` interval tokens. vnstock
# rejects anything outside this set, so unknown intervals fall back to daily.
_INTERVAL_MAP = {
    "1D": "1D", "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1H",
}


@register
class DataLoader:
    """vnstock-backed OHLCV loader for Vietnamese equities."""

    name = "vnstock"
    markets = {"vn_equity"}
    requires_auth = False  # free; only needs internet

    def __init__(self) -> None:
        """Resolve the price sub-source from the environment (default ``vci``)."""
        self.source = os.getenv("VNSTOCK_PRICE_SOURCE", "vci").strip().lower() or "vci"
        self._quote = None  # lazily imported Quote class

    # -- availability -------------------------------------------------------

    def is_available(self) -> bool:
        """Available when vnstock imports. Network errors surface per-symbol.

        A live request here would slow every fallback resolution, so — like the
        other free loaders — availability is an import check; an actual network
        outage just yields empty frames that the runner falls back from.
        """
        try:
            self._quote_cls()
            return True
        except Exception:
            return False

    # -- fetch --------------------------------------------------------------

    def fetch(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        fields: Optional[List[str]] = None,
        interval: str = "1D",
    ) -> Dict[str, pd.DataFrame]:
        """Fetch Vietnam-equity bars via vnstock ``Quote.history``.

        Args:
            codes: Symbols, bare (``VCB``) or suffixed (``VCB.VN``).
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            fields: Ignored — vnstock ``Quote`` returns OHLCV only (foreign flow
                and turnover require DataPro).
            interval: ``1D`` (daily) or a minute/hour bar (``1m``/``5m``/``1H``).

        Returns:
            Mapping code -> OHLCV DataFrame indexed by ``trade_date``.
        """
        validate_date_range(start_date, end_date)
        vn_interval = _INTERVAL_MAP.get(interval, "1D")
        result: Dict[str, pd.DataFrame] = {}

        for code in codes:
            symbol = self._bare(code)

            def _fetch_one(symbol: str = symbol) -> Optional[pd.DataFrame]:
                try:
                    return self._fetch_frame(symbol, start_date, end_date, vn_interval)
                except Exception as exc:  # noqa: BLE001 - one bad symbol must not abort the run
                    print(f"[WARN] vnstock failed to fetch {symbol}: {exc}")
                    return None

            df = cached_loader_fetch(
                source=self.name,
                symbol=code,
                timeframe=interval,
                start_date=start_date,
                end_date=end_date,
                fields=None,
                fetch=_fetch_one,
            )
            if df is not None and not df.empty:
                result[code] = df

        return result

    # -- internals ----------------------------------------------------------

    def _quote_cls(self):
        """Import vnstock's ``Quote`` once, swallowing its stdout banner.

        The banner would otherwise corrupt the runner's JSON stdout envelope.
        """
        if self._quote is None:
            os.environ.setdefault("PYTHONIOENCODING", "utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                from vnstock import Quote
            self._quote = Quote
        return self._quote

    def _fetch_frame(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        vn_interval: str,
    ) -> Optional[pd.DataFrame]:
        """Fetch and normalise one OHLCV frame from vnstock."""
        Quote = self._quote_cls()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            quote = Quote(source=self.source, symbol=symbol)
            df = quote.history(start=start_date, end=end_date, interval=vn_interval)

        if df is None or df.empty or "time" not in df.columns:
            return None

        df["trade_date"] = pd.to_datetime(df["time"])
        df = df.set_index("trade_date").sort_index()
        keep = ["open", "high", "low", "close", "volume"]
        for col in keep:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        ohlcv = df[keep].dropna(subset=["open", "high", "low", "close"])
        if ohlcv.empty:
            return None

        # Reference price = prior session's close (vnstock omits REF_PX). Compute
        # it before clipping so the first in-range bar still has a valid value,
        # since vnstock often returns a few leading out-of-range bars.
        ohlcv["pre_close"] = ohlcv["close"].shift(1)
        start = pd.Timestamp(start_date)
        end_bound = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        ohlcv = ohlcv.loc[(ohlcv.index >= start) & (ohlcv.index <= end_bound)]
        return ohlcv if not ohlcv.empty else None

    @staticmethod
    def _bare(code: str) -> str:
        """Strip a trailing ``.VN`` market suffix and upper-case the ticker."""
        ticker = code.strip().upper()
        return ticker[:-3] if ticker.endswith(".VN") else ticker
