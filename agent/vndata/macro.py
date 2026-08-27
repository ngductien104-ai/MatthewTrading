"""Macro, rates, FX and commodities — ``vnstock_data`` is the truth source.

This module deliberately wraps only the **sub-domain** API
(``Macro().economy()``, ``Macro().currency()``, ``Macro().commodity()``).

The flat methods on ``Macro()`` itself — ``Macro().gdp()``, ``.cpi()``,
``.interest_rate()`` and friends — are marked ``[DEPRECATED]`` upstream with a
stated removal date of **31/08/2026**. Any skill or script still calling them
breaks on that date, so nothing in this repository should.

The A-share-oriented ``akshare`` / ``tushare`` macro sources that the upstream
project defaults to are not appropriate for Vietnamese macro work and are not
used here.
"""

from __future__ import annotations

import pandas as pd

from vndata.errors import SourceUnavailable

#: ``economy`` series available upstream.
ECONOMY = (
    "cpi", "credit", "fdi", "gdp", "import_export", "industry_prod",
    "money_supply", "population_labor", "retail", "state_budget",
    "total_investment",
)

#: ``currency`` series: rates and FX.
CURRENCY = (
    "deposit_rate", "exchange_rate", "interbank_rate", "interest_rate",
    "omo", "policy_rate",
)

#: ``commodity`` series, local and global.
COMMODITY = (
    "coke", "corn", "fertilizer_ure", "gas", "gold", "iron_ore", "listing",
    "oil_crude", "pork", "soybean", "steel", "sugar",
)

_DOMAINS = {"economy": ECONOMY, "currency": CURRENCY, "commodity": COMMODITY}

#: Host serving most macro series upstream.
ASEAN_HOST = "asean-apigw.aseansc.com.vn"

#: The one series measured to use a different backend, so it keeps working when
#: :data:`ASEAN_HOST` is unreachable. Everything else in ``economy`` /
#: ``commodity`` and most of ``currency`` goes through that host.
NON_ASEAN_SERIES = frozenset({("currency", "interest_rate")})


def _macro():
    try:
        from vnstock_data import Macro
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable(
            "vnstock_data is not installed — macro data has no truth source."
        ) from exc
    return Macro()


def series(domain: str, name: str, **kwargs) -> pd.DataFrame:
    """Return one macro series.

    Args:
        domain: ``economy``, ``currency`` or ``commodity``.
        name: Series name — see :data:`ECONOMY`, :data:`CURRENCY`,
            :data:`COMMODITY`.
        **kwargs: Passed through to the upstream method (``start``, ``end``,
            ``period``, ``market`` and so on).

    Returns:
        The upstream DataFrame, unmodified — macro frames are already in
        sensible units and are not subject to the ratio-table traps.

    Raises:
        ValueError: If *domain* or *name* is not recognised.
        SourceUnavailable: If ``vnstock_data`` cannot serve the request.
    """
    if domain not in _DOMAINS:
        raise ValueError(f"unknown macro domain {domain!r}; expected one of {sorted(_DOMAINS)}")
    if name not in _DOMAINS[domain]:
        raise ValueError(f"unknown {domain} series {name!r}; expected one of {_DOMAINS[domain]}")

    node = getattr(_macro(), domain)()
    try:
        return getattr(node, name)(**kwargs)
    except Exception as exc:
        hint = ""
        if ASEAN_HOST in str(exc) and (domain, name) not in NON_ASEAN_SERIES:
            hint = (
                f"\n{ASEAN_HOST} is the upstream backend for this series and it is not "
                "answering right now. This host has gone down for a stretch and come "
                "back on its own before (observed 2026-08-27), so retry before "
                "concluding anything is broken locally — DNS resolving while TCP fails "
                "is what its outage looks like, and it is not a local network problem. "
                "If it stays down, macro has no second truth source: crawl the primary "
                "publisher (GSO, SBV, Ministry of Finance) and cite it explicitly, "
                "rather than estimating. 'currency.interest_rate' uses a different "
                "backend and keeps working through these outages."
            )
        raise SourceUnavailable(f"vnstock_data could not serve {domain}.{name}: {exc}{hint}") from exc


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
    """Return historical P/E and P/B for a market index.

    Sourced from ``Analytics().valuation()``, the only place in the stack that
    carries index-level multiples.
    """
    try:
        from vnstock_data import Analytics
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable("vnstock_data is not installed.") from exc
    try:
        return Analytics().valuation(index=index).evaluation(duration=duration)
    except Exception as exc:
        raise SourceUnavailable(f"vnstock_data could not serve valuation for {index}: {exc}") from exc
