"""Macro, rates and commodities — no Python source since 13/11/2026.

``vnstock_data.Macro`` served these until the vnstock subscription was
cancelled. Every function raises :class:`~vndata.errors.SourceUnavailable`.
Where the data lives now:

* VN macro (CPI, GDP, credit, rates, OMO) — VNDIRECT MCP, otherwise the
  primary publisher (GSO, SBV, Ministry of Finance), cited explicitly.
* Global commodities, FX, DXY — Yahoo via ``yfinance`` in the project venv
  (see ``COMMODITY_DATA_SOURCE.md``).
"""

from __future__ import annotations

import pandas as pd

from vndata.errors import moved_to_vndirect

ECONOMY = (
    "cpi", "credit", "fdi", "gdp", "import_export", "industry_prod",
    "money_supply", "population_labor", "retail", "state_budget",
    "total_investment",
)
CURRENCY = (
    "deposit_rate", "exchange_rate", "interbank_rate", "interest_rate",
    "omo", "policy_rate",
)
COMMODITY = (
    "coke", "corn", "fertilizer_ure", "gas", "gold", "iron_ore", "listing",
    "oil_crude", "pork", "soybean", "steel", "sugar",
)
GLOBAL = ("bond_yield", "fed_rate", "index")

_DOMAINS = {"economy": ECONOMY, "currency": CURRENCY, "commodity": COMMODITY,
            "global": GLOBAL}


def series(domain: str, name: str, **kwargs) -> pd.DataFrame:
    """One macro series — fetch via VNDIRECT MCP or the primary publisher."""
    if domain not in _DOMAINS:
        raise ValueError(f"unknown macro domain {domain!r}; expected one of {sorted(_DOMAINS)}")
    raise moved_to_vndirect(f"macro {domain}.{name}")


def economy(name: str, **kwargs) -> pd.DataFrame:
    """Shorthand for ``series("economy", name, ...)``."""
    return series("economy", name, **kwargs)


def currency(name: str, **kwargs) -> pd.DataFrame:
    """Shorthand for ``series("currency", name, ...)``."""
    return series("currency", name, **kwargs)


def commodity(name: str, **kwargs) -> pd.DataFrame:
    """Shorthand for ``series("commodity", name, ...)``."""
    return series("commodity", name, **kwargs)


def index_valuation(index: str = "VNINDEX", duration: str = "5Y") -> pd.DataFrame:
    """Index P/E and P/B history — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"index valuation ({index})")
