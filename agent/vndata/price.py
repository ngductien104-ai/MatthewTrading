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

Unit conventions differ by instrument type — the 1,000x trap
------------------------------------------------------------
``VAL`` does **not** carry the same scale for every symbol, and reading it
uniformly is a three-orders-of-magnitude error. Measured on 2026-08-25/27:

===============  ==========  ==================  =====================
Instrument       LISTED_VOL  ``*_PX`` means      ``VAL`` scale
===============  ==========  ==================  =====================
Equity / ETF     > 0         price, thousand VND thousand VND
Index            0, OI = 0   **index level**     **million VND**
Futures          0, OI > 0   index points        unverified
===============  ==========  ==================  =====================

Evidence: HPG 68,320,100 shares x 23,163 VND = 1.58e12 VND against ``VAL``
1,793,446,015 (a 1,000x gap); E1VFVN30 845,000 x 31,750 = 2.68e10 against
26,915,697 (same 1,000x). HNXINDEX ``VAL`` 2,621,503 only reconciles as 2,621bn
VND — 117,880,078 shares at an implied 22,240 VND — a 1,000,000x scale.
VN30F1M reconciles against neither, so this module refuses to convert futures
turnover rather than publish a number it cannot stand behind.

An index's ``close`` is a level, not a price: converting it to VND is
meaningless, so :func:`to_vnd` leaves index price columns alone.

:func:`to_vnd` applies the right conversion per instrument, and
``df.attrs["instrument"]`` records which rule was used.
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

    # Classify before honouring ``columns``: the signal lives in listed_shares
    # and open_interest, which a caller asking only for close/volume drops.
    instrument = classify_instrument(df)

    if columns is not None:
        wanted = [c for c in columns if c in df.columns]
        df = df[wanted]
    df.attrs["source"] = "datapro"
    df.attrs["degraded"] = False
    df.attrs["instrument"] = instrument
    if instrument == "equity":
        df.attrs["price_unit"] = "thousand VND"
        df.attrs["value_unit"] = "thousand VND"
    elif instrument == "index":
        df.attrs["price_unit"] = "index level"
        df.attrs["value_unit"] = "million VND"
    else:
        df.attrs["price_unit"] = "index points"
        df.attrs["value_unit"] = "unverified — do not quote turnover for futures"
    return df


def classify_instrument(df: pd.DataFrame) -> str:
    """Return ``equity``, ``index`` or ``futures`` for a DataPro frame.

    Uses the structural signal the feed itself provides rather than a hardcoded
    symbol list: a listed instrument reports ``LISTED_VOL``; an index reports
    zero listed volume and no open interest; a futures contract reports zero
    listed volume but non-zero open interest.
    """
    listed = df["listed_shares"].max() if "listed_shares" in df.columns else 0
    oi = df["open_interest"].max() if "open_interest" in df.columns else 0
    if pd.notna(listed) and listed > 0:
        return "equity"
    return "futures" if (pd.notna(oi) and oi > 0) else "index"


def to_vnd(df: pd.DataFrame) -> pd.DataFrame:
    """Return *df* with prices and turnover converted to plain VND.

    The conversion depends on the instrument (see the module docstring):

    * **equity / ETF** — prices and turnover both scale by 1,000.
    * **index** — turnover scales by 1,000,000; price columns are left alone
      because an index ``close`` is a level, not a price in VND.
    * **futures** — nothing is scaled. The turnover convention could not be
      reconciled against notional, and inventing a factor here would put a
      wrong number into a report. ``df.attrs["value_unit"]`` says so.

    Idempotent: a frame already carrying ``price_unit == "VND"`` is returned
    unchanged.
    """
    if df.attrs.get("price_unit") == "VND":
        return df

    instrument = df.attrs.get("instrument") or classify_instrument(df)
    out = df.copy()
    out.attrs.update(df.attrs)
    out.attrs["instrument"] = instrument

    if instrument == "equity":
        for col in (*PRICE_COLUMNS, *VALUE_COLUMNS):
            if col in out.columns:
                out[col] = out[col] * 1_000.0
        out.attrs["price_unit"] = "VND"
        out.attrs["value_unit"] = "VND"
    elif instrument == "index":
        for col in VALUE_COLUMNS:
            if col in out.columns:
                out[col] = out[col] * 1_000_000.0
        out.attrs["price_unit"] = "index level"
        out.attrs["value_unit"] = "VND"
    else:  # futures
        out.attrs["price_unit"] = "index points"
        out.attrs["value_unit"] = "unverified — do not quote turnover for futures"

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
