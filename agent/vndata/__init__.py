"""``vndata`` — the single truth-source router for Vietnamese market data.

One question, one source. The mapping is fixed, and every skill, swarm preset,
backtest loader and analysis script in this repository goes through here rather
than importing a vendor library directly.

===============================  ==================  ==========================
Data class                       Truth source        Entry point
===============================  ==================  ==========================
OHLCV, volume, turnover          DataPro             :mod:`vndata.price`
Reference price / daily band     DataPro             :mod:`vndata.price`
Foreign flow, proprietary flow   DataPro             :mod:`vndata.price`
Put-through, active buy/sell     DataPro             :mod:`vndata.price`
Index, futures, ETF, FX bars     DataPro             :mod:`vndata.price`
Financial statements             vnstock_data        :mod:`vndata.fundamental`
Ratios, valuation multiples      vnstock_data        :mod:`vndata.fundamental`
Macro, rates, FX, commodities    vnstock_data        :mod:`vndata.macro`
Symbol lists, ICB, shareholders  vnstock_data        :mod:`vndata.reference`
Technical indicators             vnstock_ta          :mod:`vndata.ta`
News headlines and article text  vnstock_news        :mod:`vndata.news`
Capital history, insider, owner  vnstock (free)      :mod:`vndata.corporate`
===============================  ==================  ==========================

Rules this layer enforces
-------------------------
* **The free ``vnstock`` package is not a source**, with exactly one
  documented exception: :mod:`vndata.corporate`, which covers three
  disclosures the sponsored tier does not carry at all (capital history,
  insider trading, ownership tree). Nothing else may import it. When DataPro
  is down, price falls back to the sponsored ``vnstock_data`` and marks the
  frame ``degraded``; it never silently drops to free-tier data.
* **Failures are loud.** A missing source raises
  :class:`vndata.errors.SourceUnavailable` rather than returning something
  plausible. Analysis that stops beats analysis built on the wrong number.
* **Units are corrected once, here.** The ``vnstock_data`` ratio table ships
  fields whose declared unit contradicts the stored value; see
  :mod:`vndata.normalize` for the verified list.
* **NaN stays NaN.** A missing number is never filled with zero, and a stored
  ``0.0`` in the ratio table is read as "not applicable", not as a measurement.

Example
-------
::

    import vndata

    bars = vndata.price.ohlcv("HPG.VN", "2026-01-01", "2026-08-27")
    flow = vndata.price.foreign_flow("HPG.VN", "2026-08-01", "2026-08-27")
    rsi = vndata.ta.indicator("HPG.VN", "2026-01-01", "2026-08-27").momentum.rsi(length=14)
    roe = vndata.fundamental.ratios_wide("HPG")["RT_PRT_ROE"]   # already in percent
    cpi = vndata.macro.economy("cpi")
"""

from __future__ import annotations

from vndata import (
    corporate,
    fundamental,
    macro,
    news,
    normalize,
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
    "normalize",
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
    "forex": "datapro",
    "income_statement": "vnstock_data",
    "balance_sheet": "vnstock_data",
    "cash_flow": "vnstock_data",
    "footnotes": "vnstock_data",
    "ratios": "vnstock_data",
    "valuation_multiples": "vnstock_data",
    "macro": "vnstock_data",
    "interest_rates": "vnstock_data",
    "commodities": "vnstock_data",
    "industry_classification": "vnstock_data",
    "index_membership": "vnstock_data",
    "shareholders": "vnstock_data",
    "corporate_events": "vnstock_data",
    "screener": "vnstock_data",
    "technical_indicators": "vnstock_ta",
    "news": "vnstock_news",
    # The documented carve-out — see vndata.corporate.
    "capital_history": "vnstock (free)",
    "insider_trading": "vnstock (free)",
    "ownership": "vnstock (free)",
}


def health() -> dict[str, object]:
    """Report which truth sources are live right now.

    Returns:
        Mapping with a ``datapro`` bool, the vnstock licence ``tier``, and an
        ``installed`` sub-mapping of package name -> version or ``None``.
        Intended for a preflight check before a long analysis run.
    """
    import importlib.metadata as md

    installed: dict[str, str | None] = {}
    for pkg in ("vnstock_data", "vnstock_ta", "vnstock_news"):
        try:
            installed[pkg] = md.version(pkg)
        except Exception:
            installed[pkg] = None

    tier: object = None
    try:
        import vnai

        tier = vnai.get_user_tier()
    except Exception as exc:
        tier = f"unavailable: {exc}"

    asean = False
    try:
        import requests

        requests.head(f"https://{macro.ASEAN_HOST}/", timeout=5)
        asean = True
    except Exception:
        asean = False

    return {
        "datapro": price.datapro_available(),
        "tier": tier,
        "installed": installed,
        "asean_macro_backend": asean,
    }
