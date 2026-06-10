"""Vietnam equity (HOSE / HNX / UPCOM) backtest engine.

Market rules:
  - T+2 settlement: shares bought on T are only sellable from T+2 (no day trade)
  - No short selling for retail investors
  - Daily price limits (vs. reference price):
      HOSE  ±7%   |  HNX  ±10%  |  UPCOM ±15%
    (new-listing / ex-right wider bands are not modelled)
  - Round lot: 100 shares (odd lots trade separately — buys rounded to 100)
  - Brokerage commission: ~0.15% bilateral (broker-dependent)
  - Transfer (PIT) tax: 0.1% of proceeds, sell-side only
  - Prices are in thousands of VND as returned by DataPro

The price-limit check uses the ``pre_close`` column (DataPro ``REF_PX``), the
official reference price, which the DataPro loader always attaches.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.engines.base import BaseEngine

# Exchange -> daily price-limit band (fraction of the reference price).
_VN_PRICE_LIMITS = {"HOSE": 0.07, "HSX": 0.07, "HNX": 0.10, "UPCOM": 0.15}


class VNEquityEngine(BaseEngine):
    """Vietnam (HOSE / HNX / UPCOM) cash-equity engine.

    Config keys:
      - commission_rate: default 0.0015 (0.15% per side)
      - sell_tax: default 0.001 (0.1% transfer/PIT tax, sell-only)
      - slippage: default 0.001
      - vn_default_exchange: default "HOSE" (band when a symbol is unmapped)
      - vn_exchange_map: optional {symbol: "HOSE"|"HNX"|"UPCOM"} per-symbol band
    """

    def __init__(self, config: dict):
        config = {**config, "leverage": 1.0}  # VN cash market: no leverage
        super().__init__(config)
        self.commission_rate: float = config.get("commission_rate", 0.0015)
        self.sell_tax: float = config.get("sell_tax", 0.001)
        self.slippage_rate: float = config.get("slippage", 0.001)
        self.default_exchange: str = str(config.get("vn_default_exchange", "HOSE")).upper()
        raw_map = config.get("vn_exchange_map") or {}
        self.exchange_map = {
            self._bare(sym): str(exch).upper() for sym, exch in raw_map.items()
        }

    def can_execute(self, symbol: str, direction: int, bar: pd.Series) -> bool:
        """VN execution rules: no short, T+2 hold, daily price band.

        Args:
            symbol: Ticker (``VCB`` or ``VCB.VN``).
            direction: 1 (buy), -1 (short — always blocked), 0 (sell/close).
            bar: Current bar (uses ``close`` and ``pre_close``).

        Returns:
            True if the trade is allowed.
        """
        # 1. No short selling
        if direction == -1:
            return False

        # 2. T+2: shares bought on T are not sellable until T+2
        if direction == 0:
            pos = self.positions.get(symbol)
            if pos is not None:
                held_sessions = _sessions_held(pos.entry_time, bar)
                if held_sessions is not None and held_sessions < 2:
                    return False

        # 3. Daily price limits (vs. reference price)
        pct_chg = _calc_pct_change(bar)
        if pct_chg is not None:
            limit = self._price_limit(symbol)
            if direction == 1 and pct_chg >= limit - 0.0005:
                return False  # ceiling: cannot buy
            if direction == 0 and pct_chg <= -limit + 0.0005:
                return False  # floor: cannot sell

        return True

    def round_size(self, raw_size: float, price: float) -> float:
        """Round down to 100-share board lots."""
        return max(int(raw_size / 100) * 100, 0)

    def calc_commission(self, size: float, price: float, _direction: int, is_open: bool) -> float:
        """Brokerage commission both sides + transfer/PIT tax on sells."""
        notional = size * price
        comm = notional * self.commission_rate
        if not is_open:  # sell side: add 0.1% transfer tax
            comm += notional * self.sell_tax
        return comm

    def apply_slippage(self, price: float, direction: int) -> float:
        """Apply symmetric slippage to the execution price."""
        return price * (1 + direction * self.slippage_rate)

    # ── helpers ──

    def _price_limit(self, symbol: str) -> float:
        """Daily band for a symbol from its mapped exchange (default HOSE)."""
        exch = self.exchange_map.get(self._bare(symbol), self.default_exchange)
        return _VN_PRICE_LIMITS.get(exch, 0.07)

    @staticmethod
    def _bare(symbol: str) -> str:
        """Upper-case ticker without a trailing ``.VN`` suffix."""
        s = str(symbol).strip().upper()
        return s[:-3] if s.endswith(".VN") else s


# ── module-level helpers ──


def _bar_date(bar: pd.Series):
    """Extract the trade date from a bar (column or index name)."""
    for col in ("trade_date", "date"):
        if col in bar.index:
            try:
                return pd.Timestamp(bar[col]).date()
            except Exception:
                pass
    if hasattr(bar, "name"):
        try:
            return pd.Timestamp(bar.name).date()
        except Exception:
            pass
    return None


def _sessions_held(entry_time, bar: pd.Series):
    """Business-day sessions between entry and the current bar.

    Approximates VN trading sessions with weekdays (public holidays ignored).
    Returns ``None`` when either date cannot be resolved.
    """
    bar_date = _bar_date(bar)
    if bar_date is None or entry_time is None:
        return None
    try:
        entry_date = pd.Timestamp(entry_time).date()
    except Exception:
        return None
    return int(np.busday_count(entry_date, bar_date))


def _calc_pct_change(bar: pd.Series):
    """Move vs. the reference price, using ``pre_close`` (DataPro REF_PX)."""
    close = bar.get("close")
    pre_close = bar.get("pre_close")
    if close is not None and pre_close is not None and float(pre_close) > 0:
        return (float(close) - float(pre_close)) / float(pre_close)
    return None
