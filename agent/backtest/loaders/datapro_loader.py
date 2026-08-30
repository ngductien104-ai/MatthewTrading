"""Backtest adapter for the canonical :mod:`vndata.price` DataPro client."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from backtest.loaders.base import cached_loader_fetch, validate_date_range
from backtest.loaders.registry import register
from vndata import price
from vndata.errors import SourceUnavailable

_DEFAULT_COLUMNS = ["open", "high", "low", "close", "volume", "ref_price"]
_FIELD_ALIASES = {
    "foreign_buy": "foreign_buy_volume",
    "foreign_sell": "foreign_sell_volume",
    "foreign_buy_value": "foreign_buy_value",
    "foreign_sell_value": "foreign_sell_value",
}
_AVAILABLE_FIELDS = set(price.COLUMN_MAP.values()) | set(_FIELD_ALIASES)


@register
class DataLoader:
    """Expose DataPro bars through the unchanged backtest loader contract."""

    name = "datapro"
    markets = {"vn_equity"}
    requires_auth = False

    def is_available(self) -> bool:
        return price.datapro_available()

    def fetch(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        *,
        interval: str = "1D",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch bars while preserving the loader's historical default schema.

        Prices remain in DataPro's native convention (thousand VND for an
        equity, index points for an index), exactly as the old loader returned
        them. Instrument-aware unit metadata comes from :mod:`vndata.price`.
        """
        validate_date_range(start_date, end_date)
        timeframe = "1D" if interval == "1D" else interval
        requested = [field for field in (fields or []) if field in _AVAILABLE_FIELDS]
        canonical = list(dict.fromkeys(_FIELD_ALIASES.get(field, field) for field in requested))
        columns = list(dict.fromkeys([*_DEFAULT_COLUMNS, *canonical]))
        result: Dict[str, pd.DataFrame] = {}

        for code in codes:
            def _fetch_one(code: str = code) -> Optional[pd.DataFrame]:
                frame = price.ohlcv(
                    code, start_date, end_date, interval=interval, columns=columns
                )

                if frame.attrs.get("degraded"):
                    reason = frame.attrs.get("degraded_reason", "fallback source was used")
                    raise SourceUnavailable(f"DataPro fetch for {code} is degraded: {reason}")

                out = frame.rename(columns={"ref_price": "pre_close"}).copy()
                out.attrs.update(frame.attrs)
                keep = ["open", "high", "low", "close", "volume"]
                if "pre_close" in out.columns:
                    keep.append("pre_close")
                keep.extend(name for name in canonical if name in out.columns and name not in keep)
                out = out[keep]
                for alias, canonical_name in _FIELD_ALIASES.items():
                    if alias in requested and canonical_name in out.columns and alias != canonical_name:
                        out[alias] = out[canonical_name]
                        if canonical_name not in requested:
                            out = out.drop(columns=canonical_name)
                return out

            frame = cached_loader_fetch(
                source=self.name,
                symbol=code,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                fields=requested,
                fetch=_fetch_one,
            )
            if frame is not None and not frame.empty:
                result[code] = frame

        return result
