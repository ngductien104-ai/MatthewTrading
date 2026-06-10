"""DataPro loader for Vietnam-equity daily and intraday bars.

DataPro is a desktop app that exposes a local HTTP API (default
``http://localhost:6789``) over HOSE / HNX / UPCOM / derivatives / index data.
This loader speaks that API and returns adjusted OHLCV bars.

Symbols may be written bare (``VCB``) or with an explicit ``.VN`` suffix
(``VCB.VN``); the suffix is what lets ``_detect_market`` route the symbol to the
Vietnam market rules, and is stripped before hitting the API.

Config:
    DATAPRO_URL      base URL of the running DataPro API (default localhost:6789)
    DATAPRO_API_KEY  bearer token, required only for remote access; localhost
                     usually needs none.

Real-time ticks / order-book depth are out of scope (loaders are point-in-time
historical bars only).
"""

from __future__ import annotations

import io
import os
from typing import Dict, List, Optional

import pandas as pd
import requests

from backtest.loaders.base import cached_loader_fetch, validate_date_range
from backtest.loaders.registry import register

# Extra (non-OHLCV) columns this loader can attach when requested via ``fields``.
# Maps the public field name -> the raw DataPro CSV column name.
_EXTRA_FIELD_MAP = {
    "value": "VAL",            # turnover in VND
    "foreign_buy": "FRN_BUY_VOL",
    "foreign_sell": "FRN_SELL_VOL",
    "foreign_buy_value": "FRN_BUY_VAL",
    "foreign_sell_value": "FRN_SELL_VAL",
}


@register
class DataLoader:
    """DataPro-backed OHLCV loader for Vietnamese equities."""

    name = "datapro"
    markets = {"vn_equity"}
    requires_auth = False  # localhost needs no key; remote sets DATAPRO_API_KEY

    def __init__(self) -> None:
        """Resolve base URL + optional bearer token from the environment."""
        self.base_url = os.getenv("DATAPRO_URL", "http://localhost:6789").rstrip("/")
        api_key = os.getenv("DATAPRO_API_KEY", "").strip()
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    # -- availability -------------------------------------------------------

    def is_available(self) -> bool:
        """Available when the DataPro API answers ``/api/ping``."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/ping", headers=self._headers, timeout=3
            )
            return resp.status_code == 200
        except requests.RequestException:
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
        """Fetch Vietnam-equity bars via the DataPro HTTP API.

        Args:
            codes: Symbols, bare (``VCB``) or suffixed (``VCB.VN``).
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            fields: Extra columns to attach (see ``_EXTRA_FIELD_MAP`` keys).
            interval: ``1D`` (daily) or a minute bar (``1m``/``5m``).

        Returns:
            Mapping code -> OHLCV DataFrame indexed by ``trade_date``.
        """
        validate_date_range(start_date, end_date)

        endpoint = "daily" if interval == "1D" else "minute"
        timeframe = "1D" if interval == "1D" else interval
        from_epoch = self._to_epoch(start_date)
        to_epoch = self._to_epoch(end_date, end_of_day=True)
        wanted = [f for f in (fields or []) if f in _EXTRA_FIELD_MAP]
        result: Dict[str, pd.DataFrame] = {}

        for code in codes:
            symbol = self._normalize_symbol(code)

            def _fetch_one(symbol: str = symbol) -> Optional[pd.DataFrame]:
                try:
                    return self._fetch_frame(symbol, endpoint, from_epoch, to_epoch, wanted)
                except Exception as exc:  # noqa: BLE001 - one bad symbol must not abort the run
                    print(f"[WARN] DataPro failed to fetch {symbol}: {exc}")
                    return None

            df = cached_loader_fetch(
                source=self.name,
                symbol=code,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                fields=wanted,
                fetch=_fetch_one,
            )
            if df is not None and not df.empty:
                result[code] = df

        return result

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _normalize_symbol(code: str) -> str:
        """Strip a trailing ``.VN`` market suffix and upper-case the ticker."""
        ticker = code.strip().upper()
        if ticker.endswith(".VN"):
            ticker = ticker[:-3]
        return ticker

    @staticmethod
    def _to_epoch(date_str: str, end_of_day: bool = False) -> int:
        """Convert a YYYY-MM-DD string to a UTC epoch-second the API expects."""
        if not date_str:
            return 0
        ts = pd.Timestamp(date_str)
        if end_of_day:
            ts = ts + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        return int(ts.timestamp())

    def _fetch_frame(
        self,
        symbol: str,
        endpoint: str,
        from_epoch: int,
        to_epoch: int,
        extra_fields: List[str],
    ) -> Optional[pd.DataFrame]:
        """Fetch and normalize one OHLCV frame from DataPro (adjusted prices)."""
        url = f"{self.base_url}/api/data/{endpoint}/{symbol}/{from_epoch}/{to_epoch}/1"
        resp = requests.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()

        text = resp.text.strip()
        if not text or "\n" not in text:
            return None

        df = pd.read_csv(io.StringIO(text))
        if df.empty or "TRADING_TIME" not in df.columns:
            return None

        df["trade_date"] = pd.to_datetime(df["TRADING_TIME"], unit="s")
        df = df.set_index("trade_date").sort_index()
        df = df.rename(
            columns={
                "OPEN_PX": "open",
                "HIGH_PX": "high",
                "LOW_PX": "low",
                "CLOSE_PX": "close",
                "VOL": "volume",
                "REF_PX": "pre_close",
            }
        )

        # ``pre_close`` (DataPro REF_PX) is the daily price-limit reference, so
        # always carry it: the VN engine needs it to enforce ±7%/±10%/±15% bands.
        keep = ["open", "high", "low", "close", "volume"]
        if "pre_close" in df.columns:
            df["pre_close"] = pd.to_numeric(df["pre_close"], errors="coerce")
            keep.append("pre_close")
        for field in extra_fields:
            raw = _EXTRA_FIELD_MAP[field]
            if raw in df.columns:
                df[field] = pd.to_numeric(df[raw], errors="coerce")
                keep.append(field)

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        ohlcv = df[keep].dropna(subset=["open", "high", "low", "close"])
        return ohlcv if not ohlcv.empty else None
