"""vnstock_data (sponsor) OHLCV loader for Vietnam equities — Unified UI.

Third VN price source, sitting above the free ``vnstock`` loader in the
``vn_equity`` chain. Same zero-desktop story as ``vnstock`` (plain internet
calls, no DataPro app on ``localhost:6789``) but on the sponsored Unified UI,
which buys two things the free tier cannot give:

* **Foreign flow without DataPro.** ``Market.equity(...).foreign_flow()``
  returns daily foreign buy/sell volume and value, so a backtest can request
  ``foreign_buy`` / ``foreign_sell`` / ``foreign_*_value`` over the internet.
  Free vnstock has no such endpoint — that used to force DataPro.
* **Higher rate limits.** Sponsor tiers lift the quota well above the free
  60 req/min, so multi-symbol runs stop tripping the limiter.

Requires a sponsor API key (silver+); the package itself is only installable
with one. If the sponsorship lapses the calls start failing and the runner
falls through to the free ``vnstock`` loader, which is why that one stays.

Symbols may be bare (``VCB``) or ``.VN``-suffixed (``VCB.VN``); the suffix is
what routes the symbol to the VN engine and is stripped before the API call.

Reference price
---------------
Like free vnstock, the Unified UI does not return ``REF_PX``, so ``pre_close``
is synthesised as the prior session's close — the standard HOSE/HNX
reference-price proxy — letting the VN engine approximate the ±7/10/15% bands.
"""

from __future__ import annotations

import contextlib
import io
import os
from typing import Dict, List, Optional

import pandas as pd

from backtest.loaders.base import cached_loader_fetch, validate_date_range
from backtest.loaders.registry import register

# Our interval tokens -> Unified UI ``ohlcv`` interval tokens. The endpoint also
# accepts ``1W``/``1M``; unknown intervals fall back to daily.
_INTERVAL_MAP = {
    "1D": "1D", "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1H",
}

# Extra (non-OHLCV) columns this loader can attach when requested via ``fields``,
# mapped to the ``foreign_flow`` column that carries them. Names match the
# DataPro loader's ``_EXTRA_FIELD_MAP`` keys so strategies stay source-agnostic.
_FOREIGN_FIELD_MAP = {
    "foreign_buy": "buy_vol",
    "foreign_sell": "sell_vol",
    "foreign_buy_value": "buy_val",
    "foreign_sell_value": "sell_val",
}


@register
class DataLoader:
    """vnstock_data-backed OHLCV loader for Vietnamese equities (sponsor tier)."""

    name = "vnstock_data"
    markets = {"vn_equity"}
    requires_auth = True  # sponsor API key in ~/.vnstock/api_key.json

    def __init__(self) -> None:
        """Prepare lazy handles; nothing is imported until first use."""
        self._market = None  # lazily imported Market class

    # -- availability -------------------------------------------------------

    def is_available(self) -> bool:
        """Available when ``vnstock_data`` imports.

        Import success already implies a sponsor install, so — like the other
        loaders — availability stays an import check rather than a live probe.
        An expired licence just yields empty frames and the runner falls back
        to the free ``vnstock`` loader.
        """
        try:
            self._market_cls()
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
        """Fetch Vietnam-equity bars via the Unified UI ``Market`` layer.

        Args:
            codes: Symbols, bare (``VCB``) or suffixed (``VCB.VN``).
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            fields: Extra columns to attach (see ``_FOREIGN_FIELD_MAP`` keys).
                Only honoured on daily bars — foreign flow is a daily series.
            interval: ``1D`` (daily) or a minute/hour bar (``1m``/``5m``/``1H``).

        Returns:
            Mapping code -> OHLCV DataFrame indexed by ``trade_date``.
        """
        validate_date_range(start_date, end_date)
        vn_interval = _INTERVAL_MAP.get(interval, "1D")
        wanted = [f for f in (fields or []) if f in _FOREIGN_FIELD_MAP]
        if vn_interval != "1D":
            wanted = []  # foreign flow only exists at daily granularity
        result: Dict[str, pd.DataFrame] = {}

        for code in codes:
            symbol = self._bare(code)

            def _fetch_one(symbol: str = symbol) -> Optional[pd.DataFrame]:
                try:
                    return self._fetch_frame(symbol, start_date, end_date, vn_interval, wanted)
                except Exception as exc:  # noqa: BLE001 - one bad symbol must not abort the run
                    print(f"[WARN] vnstock_data failed to fetch {symbol}: {exc}")
                    return None

            df = cached_loader_fetch(
                source=self.name,
                symbol=code,
                timeframe=interval,
                start_date=start_date,
                end_date=end_date,
                fields=wanted or None,
                fetch=_fetch_one,
            )
            if df is not None and not df.empty:
                result[code] = df

        return result

    # -- internals ----------------------------------------------------------

    def _market_cls(self):
        """Import the Unified UI ``Market`` once, swallowing its stdout banner.

        The banner would otherwise corrupt the runner's JSON stdout envelope.
        """
        if self._market is None:
            os.environ.setdefault("PYTHONIOENCODING", "utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                from vnstock_data import Market
            self._market = Market
        return self._market

    def _fetch_frame(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        vn_interval: str,
        extra_fields: List[str],
    ) -> Optional[pd.DataFrame]:
        """Fetch and normalise one OHLCV frame, optionally with foreign flow."""
        Market = self._market_cls()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            equity = Market().equity(symbol)
            df = equity.ohlcv(start=start_date, end=end_date, interval=vn_interval)

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

        # Reference price = prior session's close (the API omits REF_PX). Compute
        # it before clipping so the first in-range bar still has a valid value,
        # since the endpoint often returns a few leading out-of-range bars.
        ohlcv["pre_close"] = ohlcv["close"].shift(1)

        if extra_fields:
            foreign = self._fetch_foreign(equity, start_date, end_date)
            # Daily bars are stamped 07:00 while foreign flow is stamped midnight,
            # so both sides key off the calendar date rather than the raw index.
            bar_dates = ohlcv.index.normalize()
            for field in extra_fields:
                column = _FOREIGN_FIELD_MAP[field]
                # Reindex rather than join: foreign flow publishes a session late,
                # so the newest bar legitimately has no row yet -> NaN, not a drop.
                ohlcv[field] = (
                    foreign[column].reindex(bar_dates).to_numpy()
                    if foreign is not None and column in foreign.columns
                    else pd.NA
                )

        start = pd.Timestamp(start_date)
        end_bound = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        ohlcv = ohlcv.loc[(ohlcv.index >= start) & (ohlcv.index <= end_bound)]
        return ohlcv if not ohlcv.empty else None

    @staticmethod
    def _fetch_foreign(equity, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Daily foreign buy/sell frame indexed like the price frame, or None."""
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                flow = equity.foreign_flow(start=start_date, end=end_date)
        except Exception as exc:  # noqa: BLE001 - missing flow must not lose the bars
            print(f"[WARN] vnstock_data foreign_flow unavailable for {equity.symbol}: {exc}")
            return None

        if flow is None or flow.empty or "time" not in flow.columns:
            return None
        flow = flow.copy()
        flow["trade_date"] = pd.to_datetime(flow["time"]).dt.normalize()
        return flow.set_index("trade_date").sort_index()

    @staticmethod
    def _bare(code: str) -> str:
        """Strip a trailing ``.VN`` market suffix and upper-case the ticker."""
        ticker = code.strip().upper()
        return ticker[:-3] if ticker.endswith(".VN") else ticker
