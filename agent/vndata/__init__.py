"""``vndata`` — the single truth-source router for Vietnamese market data.

One question, one source. Since 13/11/2026 (vnstock subscription cancelled)
there are two truth sources, and only one of them is reachable from Python:

===============================  ==========================  ===================================
Data class                       Truth source                Python entry point
===============================  ==========================  ===================================
OHLCV, volume, turnover          DataPro                     :mod:`vndata.price`
Reference price / daily band     DataPro                     :mod:`vndata.price`
Foreign flow, proprietary flow   DataPro                     :mod:`vndata.price`
Put-through, active buy/sell     DataPro                     :mod:`vndata.price`
Index, futures, ETF bars         DataPro                     :mod:`vndata.price`
Symbol list, exchange, shares    DataPro                     :func:`vndata.reference.symbols`
Technical indicators             local maths on DataPro      :mod:`vndata.ta`
News headlines                   publishers' RSS feeds       :func:`vndata.news.rss`
Financial statements, ratios     VNDIRECT MCP                none — raises SourceUnavailable
Macro, rates                     VNDIRECT MCP / publisher    none — raises SourceUnavailable
Company profile, holders, events VNDIRECT MCP                none — raises SourceUnavailable
ICB classification, VN30 basket  VNDIRECT MCP -> snapshot    :mod:`vndata.reference` snapshot
===============================  ==========================  ===================================

VNDIRECT MCP (``https://mcp.vndirect.com.vn/mcp``) is OAuth-protected and is
called by an MCP client — Claude Code or a Claude subagent running a swarm —
through the connector's ``FINFO_API__*`` tools. See the ``data-routing`` skill.

Rules this layer enforces
-------------------------
* **No vnstock.** Neither the sponsored packages nor the free one are
  imported anywhere in this layer.
* **Failures are loud.** A missing source raises
  :class:`vndata.errors.SourceUnavailable` naming where the data lives now,
  rather than returning something plausible.
* **NaN stays NaN.** A missing number is never filled with zero.

Example
-------
::

    import vndata

    bars = vndata.price.ohlcv("HPG.VN", "2026-01-01", "2026-11-13")
    flow = vndata.price.foreign_flow("HPG.VN", "2026-11-01", "2026-11-13")
    rsi = vndata.ta.indicator("HPG.VN", "2026-01-01", "2026-11-13").momentum.rsi(length=14)
"""

from __future__ import annotations

from vndata import (
    corporate,
    fundamental,
    macro,
    news,
    price,
    reference,
    ta,
)
from vndata.errors import NotEntitled, SourceUnavailable, VnDataError, WrongSource

__all__ = [
    "corporate",
    "fundamental",
    "macro",
    "news",
    "price",
    "reference",
    "ta",
    "SOURCE_MAP",
    "health",
    "NotEntitled",
    "SourceUnavailable",
    "VnDataError",
    "WrongSource",
]

#: Data class -> authoritative source. Referenced by the ``data-routing`` skill;
#: keep the two in step.
SOURCE_MAP: dict[str, str] = {
    "ohlcv": "datapro",
    "volume": "datapro",
    "turnover": "datapro",
    "reference_price": "datapro",
    "foreign_flow": "datapro",
    "proprietary_flow": "datapro",
    "put_through": "datapro",
    "active_flow": "datapro",
    "index": "datapro",
    "futures": "datapro",
    "etf_price": "datapro",
    "symbol_list": "datapro",
    # DataPro's tape carries no FX (USDVND, XAUUSD, DXY return 0 rows,
    # checked 2026-09-07). Live FX comes from Yahoo (USDVND=X, DX-Y.NYB).
    "forex": "yahoo (yfinance)",
    "technical_indicators": "local (pandas on datapro bars)",
    "news": "rss (publisher feeds)",
    "income_statement": "vndirect_mcp",
    "balance_sheet": "vndirect_mcp",
    "cash_flow": "vndirect_mcp",
    "footnotes": "primary filing (evidence_pack.py)",
    "ratios": "vndirect_mcp",
    "valuation_multiples": "vndirect_mcp",
    "macro": "vndirect_mcp",
    "interest_rates": "vndirect_mcp",
    "commodities": "yahoo (yfinance)",
    "industry_classification": "vndirect_mcp (snapshot)",
    "index_membership": "vndirect_mcp (snapshot)",
    "shareholders": "vndirect_mcp",
    "corporate_events": "vndirect_mcp",
    "company_news": "vndirect_mcp",
    "capital_history": "vndirect_mcp",
    "insider_trading": "vndirect_mcp",
    "ownership": "vndirect_mcp",
}


def health() -> dict[str, object]:
    """Report which truth sources Python can reach right now.

    Returns:
        Mapping with a ``datapro`` bool and the ``as_of`` dates of the
        VNDIRECT-sourced snapshots (``None`` when a snapshot is missing).
        VNDIRECT MCP itself is not probed: it is OAuth-only and is checked
        from the MCP client, not from Python.
    """
    import json as _json

    snapshots: dict[str, object] = {}
    for name, path in (
        ("icb_classification", reference.CLASSIFICATION_FILE.with_suffix(".meta.json")),
        ("index_members", reference.INDEX_MEMBERS_FILE),
    ):
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
            snapshots[name] = data.get("as_of") or {k: v.get("as_of") for k, v in data.items()}
        except Exception:
            snapshots[name] = None

    return {
        "datapro": price.datapro_available(),
        "vndirect_mcp": "call via MCP client (connector VNDIRECT MCP, tools FINFO_API__*)",
        "snapshots": snapshots,
    }
