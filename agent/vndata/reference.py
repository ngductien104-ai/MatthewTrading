"""Reference data — DataPro for the symbol list, snapshots for ICB and baskets.

``vnstock_data.Reference`` served all of this until the vnstock subscription
was cancelled (its authentication stopped on 10/11/2026, which is what took
the 13/11 morning brief down). The split now:

=============================  ====================================  ==========================
Data                           Source                                Entry point
=============================  ====================================  ==========================
Listed symbols, exchange,      DataPro ``/api/symbols`` (live)       :func:`symbols`,
type, shares outstanding                                             :func:`equities`, :func:`etfs`
ICB industry classification    snapshot from VNDIRECT MCP            :func:`classification`
Index baskets (VN30, ...)      snapshot from VNDIRECT MCP            :func:`symbols_by_group`
Company profile, holders,      VNDIRECT MCP only (raises here)       —
officers, events, funds
=============================  ====================================  ==========================

Why snapshots. VNDIRECT MCP is OAuth-protected and only an MCP client can call
it, but ICB codes and index baskets change a few times a year while the daily
brief, the backtest runner and the learning loop need them every run. So an
MCP client (Claude) fetches them and writes a CSV / JSON under
:data:`SNAPSHOT_DIR` with :func:`save_classification` /
:func:`save_index_members`; Python reads that file and stamps ``as_of`` on
every frame it returns. A missing snapshot raises — it never degrades to an
unlabelled or invented classification.
"""

from __future__ import annotations

import io
import json
import time
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

from vndata import price as _price
from vndata.errors import SourceUnavailable, moved_to_vndirect

#: Where the MCP-sourced snapshots live.
SNAPSHOT_DIR = Path(__file__).resolve().parents[1] / "data" / "vn_reference"
CLASSIFICATION_FILE = SNAPSHOT_DIR / "icb_classification.csv"
INDEX_MEMBERS_FILE = SNAPSHOT_DIR / "index_members.json"

#: DataPro writes HOSE as ``HSX``; everything downstream says ``HOSE``.
_EXCHANGE = {"HSX": "HOSE", "HOSE": "HOSE", "HNX": "HNX", "UPCOM": "UPCOM"}

_CLASSIFICATION_COLUMNS = ("symbol", "icb_code_lv2", "icb_name_lv2")


def _ticker(symbol: str) -> str:
    return symbol.strip().upper().replace(".VN", "")


# --------------------------------------------------------------------------
# DataPro — live
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _symbols_csv() -> str:
    """Fetch DataPro's symbol table once per process (it is ~2,200 rows and
    DataPro answers back-to-back requests for it with 503)."""
    last: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(f"{_price._base_url()}/api/symbols", headers=_price._headers(), timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise SourceUnavailable(f"DataPro /api/symbols is not answering: {last}") from last


def symbols() -> pd.DataFrame:
    """Return every instrument DataPro knows, one row per symbol.

    Columns: ``symbol``, ``organ_name``, ``organ_name_en``, ``exchange``
    (``HOSE``/``HNX``/``UPCOM`` for listed boards, DataPro's own label
    otherwise), ``type`` (``STOCK``, ``ETF``, ``CW``, ``IDX``, ``DRV`` ...) and
    ``shares_out``.

    Raises:
        SourceUnavailable: DataPro is not answering.
    """
    raw = pd.read_csv(io.StringIO(_symbols_csv()), dtype={"SYMBOL": str})
    out = pd.DataFrame({
        "symbol": raw["SYMBOL"].astype(str).str.strip().str.upper(),
        "organ_name": raw.get("NAME"),
        "organ_name_en": raw.get("NAME_EN"),
        "exchange": raw["EXCHANGE"].map(lambda e: _EXCHANGE.get(str(e).strip(), str(e).strip())),
        "type": raw["TYPE"].astype(str).str.strip(),
        "shares_out": pd.to_numeric(raw.get("SHARES_OUT"), errors="coerce"),
    })
    out.attrs["source"] = "datapro"
    return out


def equities() -> pd.DataFrame:
    """Return listed common stocks on HOSE / HNX / UPCOM."""
    df = symbols()
    return df[(df["type"] == "STOCK") & df["exchange"].isin(("HOSE", "HNX", "UPCOM"))].reset_index(drop=True)


def etfs() -> pd.DataFrame:
    """Return the listed ETF universe."""
    df = symbols()
    return df[df["type"] == "ETF"].reset_index(drop=True)


# --------------------------------------------------------------------------
# Snapshots refreshed from VNDIRECT MCP
# --------------------------------------------------------------------------

def classification() -> pd.DataFrame:
    """Return the ICB level-2 classification snapshot.

    Columns: ``symbol``, ``icb_code_lv2`` (4-digit string), ``icb_name_lv2``.
    ``df.attrs`` carries ``as_of`` and ``source`` from the snapshot.

    Raises:
        SourceUnavailable: no snapshot has been written yet.
    """
    if not CLASSIFICATION_FILE.exists():
        raise moved_to_vndirect(
            f"ICB classification (chưa có snapshot {CLASSIFICATION_FILE.name}; "
            "lấy phân ngành từ VNDIRECT MCP rồi ghi bằng vndata.reference.save_classification)"
        )
    meta_path = CLASSIFICATION_FILE.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    df = pd.read_csv(CLASSIFICATION_FILE, dtype=str)
    df["icb_code_lv2"] = df["icb_code_lv2"].str.zfill(4)
    df.attrs.update(meta)
    return df


def save_classification(df: pd.DataFrame, *, source: str, as_of: str | None = None) -> Path:
    """Write the ICB snapshot fetched from VNDIRECT MCP.

    Args:
        df: Frame with at least ``symbol``, ``icb_code_lv2``, ``icb_name_lv2``.
        source: Which MCP tool produced it, e.g. ``"vndirect:<tool>"``.
        as_of: Date the classification was read; defaults to today.
    """
    missing = [c for c in _CLASSIFICATION_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"classification snapshot is missing columns {missing}")
    out = df[list(_CLASSIFICATION_COLUMNS)].copy()
    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    out["icb_code_lv2"] = out["icb_code_lv2"].astype(str).str.strip().str.zfill(4)
    if out["symbol"].duplicated().any():
        raise ValueError("classification snapshot has duplicate symbols")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out.sort_values("symbol").to_csv(CLASSIFICATION_FILE, index=False, encoding="utf-8")
    CLASSIFICATION_FILE.with_suffix(".meta.json").write_text(
        json.dumps({"as_of": as_of or date.today().isoformat(), "source": source, "rows": len(out)},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return CLASSIFICATION_FILE


def _load_members() -> dict:
    if not INDEX_MEMBERS_FILE.exists():
        return {}
    return json.loads(INDEX_MEMBERS_FILE.read_text(encoding="utf-8"))


def symbols_by_group(group: str) -> pd.Series:
    """Return the current members of an index basket, e.g. ``VN30``.

    **Current**, not point-in-time: the snapshot records one basket per
    ``as_of`` date. ``attrs`` carries ``as_of`` and ``source``.

    Raises:
        SourceUnavailable: the basket is not in the snapshot.
    """
    key = group.strip().upper()
    entry = _load_members().get(key)
    if not entry:
        raise moved_to_vndirect(
            f"thành phần rổ {key} (chưa có trong {INDEX_MEMBERS_FILE.name}; "
            "lấy từ VNDIRECT MCP rồi ghi bằng vndata.reference.save_index_members)"
        )
    out = pd.Series([_ticker(s) for s in entry["symbols"]], name="symbol")
    out.attrs.update({"as_of": entry.get("as_of"), "source": entry.get("source"), "group": key})
    return out


def save_index_members(group: str, members: list[str], *, source: str, as_of: str | None = None) -> Path:
    """Write one index basket fetched from VNDIRECT MCP into the snapshot."""
    clean = sorted({_ticker(s) for s in members if str(s).strip()})
    if not clean:
        raise ValueError(f"empty member list for {group}")
    data = _load_members()
    data[group.strip().upper()] = {
        "as_of": as_of or date.today().isoformat(), "source": source, "symbols": clean,
    }
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_MEMBERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return INDEX_MEMBERS_FILE


# --------------------------------------------------------------------------
# VNDIRECT MCP only — no Python path
# --------------------------------------------------------------------------

def company(symbol: str) -> pd.DataFrame:
    """Company profile — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"company profile ({symbol})")


def shareholders(symbol: str, mode: str = "detailed") -> pd.DataFrame:
    """Shareholder register — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"shareholders ({symbol})")


def officers(symbol: str, filter_by: str = "working") -> pd.DataFrame:
    """Officer list — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"officers ({symbol})")


def subsidiaries(symbol: str, filter_by: str = "all") -> pd.DataFrame:
    """Subsidiaries and affiliates — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"subsidiaries ({symbol})")


def events(symbol: str | None = None, **kwargs) -> pd.DataFrame:
    """Corporate events calendar — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"corporate events ({symbol or 'calendar'})")


def funds() -> pd.DataFrame:
    """Open-ended fund universe — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect("open-ended fund list")


def fund_nav(symbol: str) -> pd.DataFrame:
    """Open-ended fund NAV history — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"fund NAV ({symbol})")


def fund_top_holding(symbol: str) -> pd.DataFrame:
    """Fund top holdings — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"fund top holdings ({symbol})")


def fund_industry_holding(symbol: str) -> pd.DataFrame:
    """Fund industry allocation — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"fund industry allocation ({symbol})")


def fund_asset_holding(symbol: str) -> pd.DataFrame:
    """Fund asset allocation — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"fund asset allocation ({symbol})")
