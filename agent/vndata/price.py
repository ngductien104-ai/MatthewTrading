"""Price, volume and money-flow — DataPro is the truth source.

DataPro (the desktop app on ``localhost:6789``) is authoritative for every
price-shaped question about the Vietnamese market: OHLCV, turnover, the
official reference price that sets the daily band, foreign flow, proprietary
(tu doanh) flow, put-through deals and active buy/sell pressure. Its daily CSV
carries all of those in one row, which no other source in this stack does.

When DataPro is down the layer falls back to the sponsored
``vnstock_data.Market`` — announced, never silent, and flagged on the returned
frame — because that still carries OHLCV. The free ``vnstock`` package is not
part of this chain.

Unit conventions in the DataPro daily CSV, measured against VCB on 2026-08-01
(4,751,600 shares at ~59,373 VND, roughly 282bn VND of turnover, against a
reported ``VAL`` of 285,499,090):

* ``*_PX`` columns are in **thousand VND** (``59.373`` means 59,373 VND).
* ``VAL`` and every ``*_VAL`` column are in **thousand VND**.
* ``VOL`` columns are in shares.

``to_vnd()`` applies those conversions so callers never multiply by the wrong
power of ten.
"""

from __future__ import annotations

import io
import os
from typing import Iterable

import pandas as pd
import requests

from vndata.errors import SourceUnavailable

#: DataPro daily CSV column -> the name this layer exposes.
COLUMN_MAP: dict[str, str] = {
    "OPEN_PX": "open",
    "HIGH_PX": "high",
    "LOW_PX": "low",
    "CLOSE_PX": "close",
    "REF_PX": "ref_price",          # official band reference, DataPro-only
    "VOL": "volume",
    "VAL": "value",                 # turnover, thousand VND
    "PT_VOL": "put_through_volume",
    "PT_VAL": "put_through_value",
    "BUY_VOL": "active_buy_volume",
    "BUY_VAL": "active_buy_value",
    "SELL_VOL": "active_sell_volume",
    "SELL_VAL": "active_sell_value",
    "PORT_BUY_VOL": "prop_buy_volume",      # tu doanh
    "PORT_BUY_VAL": "prop_buy_value",
    "PORT_SELL_VOL": "prop_sell_volume",
    "PORT_SELL_VAL": "prop_sell_value",
    "FRN_BUY_VOL": "foreign_buy_volume",
    "FRN_BUY_VAL": "foreign_buy_value",
    "FRN_SELL_VOL": "foreign_sell_volume",
    "FRN_SELL_VAL": "foreign_sell_value",
    "OUTSTANDING_VOL": "outstanding_shares",
    "LISTED_VOL": "listed_shares",
    "OI": "open_interest",
    "ADJ_RATE": "adj_rate",
}

#: Columns quoted in thousand VND per share.
PRICE_COLUMNS = ("open", "high", "low", "close", "ref_price")

#: Columns quoted in thousand VND of turnover.
VALUE_COLUMNS = tuple(v for v in COLUMN_MAP.values() if v.endswith("value"))

_DEFAULT_URL = "http://localhost:6789"


def _base_url() -> str:
    return os.getenv("DATAPRO_URL", _DEFAULT_URL).rstrip("/")


def _headers() -> dict[str, str]:
    key = os.getenv("DATAPRO_API_KEY", "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def _ticker(code: str) -> str:
    """Strip the ``.VN`` routing suffix and upper-case."""
    t = code.strip().upper()
    return t[:-3] if t.endswith(".VN") else t


def _epoch(day: str, end_of_day: bool = False) -> int:
    ts = pd.Timestamp(day)
    if end_of_day:
        ts = ts + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return int(ts.timestamp())


def datapro_available(timeout: float = 3.0) -> bool:
    """Return True when the DataPro desktop API answers its ping."""
    try:
        resp = requests.get(f"{_base_url()}/api/ping", headers=_headers(), timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def ohlcv(
    symbol: str,
    start: str,
    end: str,
    *,
    interval: str = "1D",
    columns: Iterable[str] | None = None,
    allow_fallback: bool = True,
) -> pd.DataFrame:
    """Return DataPro bars for *symbol* indexed by trade date.

    Args:
        symbol: Ticker, bare (``VCB``) or suffixed (``VCB.VN``).
        start: Inclusive start date, ``YYYY-MM-DD``.
        end: Inclusive end date, ``YYYY-MM-DD``.
        interval: ``1D`` for daily, or a minute bar such as ``5m``.
        columns: Subset of :data:`COLUMN_MAP` values to keep. ``None`` keeps
            every column DataPro returned.
        allow_fallback: When DataPro is down, serve OHLCV from the sponsored
            ``vnstock_data.Market`` instead of raising. The result carries
            ``df.attrs["source"] == "vnstock_data"`` and ``df.attrs["degraded"]``.

    Returns:
        DataFrame indexed by ``trade_date``. ``df.attrs["source"]`` names the
        source that actually served the request.

    Raises:
        SourceUnavailable: DataPro is unreachable and *allow_fallback* is
            False, or the fallback also failed.
    """
    if not datapro_available():
        if not allow_fallback:
            raise SourceUnavailable(
                "DataPro desktop is not answering on "
                f"{_base_url()}/api/ping — start the app or pass allow_fallback=True."
            )
        return _fallback_ohlcv(symbol, start, end)

    endpoint = "daily" if interval == "1D" else "minute"
    url = (
        f"{_base_url()}/api/data/{endpoint}/{_ticker(symbol)}/"
        f"{_epoch(start)}/{_epoch(end, end_of_day=True)}/1"
    )
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()

    text = resp.text.strip()
    if not text or "\n" not in text:
        return _empty_frame()

    raw = pd.read_csv(io.StringIO(text))
    if raw.empty or "TRADING_TIME" not in raw.columns:
        return _empty_frame()

    raw["trade_date"] = pd.to_datetime(raw["TRADING_TIME"], unit="s")
    df = raw.rename(columns=COLUMN_MAP).set_index("trade_date").sort_index()

    keep = [c for c in COLUMN_MAP.values() if c in df.columns]
    df = df[keep].apply(pd.to_numeric, errors="coerce")
    if columns is not None:
        wanted = [c for c in columns if c in df.columns]
        df = df[wanted]

    df.attrs["source"] = "datapro"
    df.attrs["degraded"] = False
    df.attrs["price_unit"] = "thousand VND"
    df.attrs["value_unit"] = "thousand VND"
    return df


def to_vnd(df: pd.DataFrame) -> pd.DataFrame:
    """Return *df* with prices and turnover converted to plain VND.

    Multiplies :data:`PRICE_COLUMNS` and :data:`VALUE_COLUMNS` by 1,000 and
    updates ``df.attrs`` so a converted frame cannot be converted twice.
    """
    if df.attrs.get("price_unit") == "VND":
        return df
    out = df.copy()
    for col in (*PRICE_COLUMNS, *VALUE_COLUMNS):
        if col in out.columns:
            out[col] = out[col] * 1_000.0
    out.attrs.update(df.attrs)
    out.attrs["price_unit"] = "VND"
    out.attrs["value_unit"] = "VND"
    return out


def foreign_flow(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Return net foreign buying for *symbol*, in shares and thousand VND."""
    df = ohlcv(symbol, start, end, allow_fallback=False)
    if df.empty:
        return df
    out = df[[
        "foreign_buy_volume", "foreign_sell_volume",
        "foreign_buy_value", "foreign_sell_value",
    ]].copy()
    out["net_volume"] = out["foreign_buy_volume"] - out["foreign_sell_volume"]
    out["net_value"] = out["foreign_buy_value"] - out["foreign_sell_value"]
    out.attrs.update(df.attrs)
    return out


def proprietary_flow(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Return net proprietary-desk (tu doanh) buying for *symbol*."""
    df = ohlcv(symbol, start, end, allow_fallback=False)
    if df.empty:
        return df
    out = df[[
        "prop_buy_volume", "prop_sell_volume",
        "prop_buy_value", "prop_sell_value",
    ]].copy()
    out["net_volume"] = out["prop_buy_volume"] - out["prop_sell_volume"]
    out["net_value"] = out["prop_buy_value"] - out["prop_sell_value"]
    out.attrs.update(df.attrs)
    return out


def _empty_frame() -> pd.DataFrame:
    df = pd.DataFrame(columns=list(COLUMN_MAP.values()))
    df.attrs["source"] = "datapro"
    df.attrs["degraded"] = False
    return df


def _fallback_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Serve OHLCV from the sponsored Unified UI when DataPro is unreachable."""
    try:
        from vnstock_data import Market
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable(
            "DataPro is down and vnstock_data is not installed — no price source left."
        ) from exc

    try:
        df = Market().equity(_ticker(symbol)).ohlcv(start=start, end=end)
    except Exception as exc:
        raise SourceUnavailable(
            f"DataPro is down and vnstock_data could not serve {symbol}: {exc}"
        ) from exc

    if df is None or df.empty:
        return _empty_frame()

    df = df.rename(columns={"time": "trade_date"}).set_index("trade_date").sort_index()
    df.attrs["source"] = "vnstock_data"
    df.attrs["degraded"] = True
    df.attrs["degraded_reason"] = (
        "DataPro desktop unreachable; no reference price, foreign/proprietary "
        "flow, put-through or active buy-sell columns in this frame."
    )
    df.attrs["price_unit"] = "thousand VND"
    df.attrs["value_unit"] = "n/a"
    return df
