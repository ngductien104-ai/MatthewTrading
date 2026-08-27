"""Reference data — ``vnstock_data`` is the truth source.

Symbol lists, ICB industry classification, index membership, company profile,
officers, shareholders, subsidiaries, the events calendar, ETF and fund
listings. These replace the free-tier calls that skills used to make
(``Listing(source="VCI").symbols_by_industries()``,
``Company(symbol).overview()``), which return a different schema and a stale
classification.
"""

from __future__ import annotations

import pandas as pd

from vndata.errors import SourceUnavailable


def _reference():
    try:
        from vnstock_data import Reference
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable(
            "vnstock_data is not installed — reference data has no truth source."
        ) from exc
    return Reference()


def _ticker(symbol: str) -> str:
    return symbol.strip().upper().replace(".VN", "")


def symbols() -> pd.DataFrame:
    """Return every listed equity symbol."""
    return _reference().equity.list()


def symbols_by_industry() -> pd.DataFrame:
    """Return the ICB classification of every symbol, one row per ICB level.

    Columns: ``symbol``, ``organ_name``, ``com_type_code``, ``icb_level``,
    ``icb_code``, ``icb_name``. Filter on ``icb_level`` to pick the depth you
    want — level 2 is the usual sector grouping.

    This is the replacement for the free-tier
    ``Listing(source="VCI").symbols_by_industries()``.
    """
    return _reference().industry.sectors()


def industry_taxonomy() -> pd.DataFrame:
    """Return the ICB code table itself (codes and names, no symbols)."""
    return _reference().industry.list()


def symbols_by_group(group: str) -> pd.DataFrame:
    """Return the members of an index or board, e.g. ``VN30``, ``HOSE``."""
    return _reference().equity.list_by_group(group)


def company(symbol: str) -> pd.DataFrame:
    """Return the company profile for *symbol*."""
    return _reference().company(_ticker(symbol)).info()


def shareholders(symbol: str, mode: str = "detailed") -> pd.DataFrame:
    """Return the shareholder register for *symbol*."""
    return _reference().company(_ticker(symbol)).shareholders(mode=mode)


def officers(symbol: str, filter_by: str = "working") -> pd.DataFrame:
    """Return the officer list for *symbol*."""
    return _reference().company(_ticker(symbol)).officers(filter_by=filter_by)


def subsidiaries(symbol: str, filter_by: str = "all") -> pd.DataFrame:
    """Return subsidiaries and affiliates of *symbol*."""
    return _reference().company(_ticker(symbol)).subsidiaries(filter_by=filter_by)


def events(symbol: str | None = None, **kwargs) -> pd.DataFrame:
    """Return corporate events — for one *symbol*, or the whole calendar."""
    ref = _reference()
    if symbol:
        return ref.company(_ticker(symbol)).events(**kwargs)
    return ref.events.calendar(**kwargs)


def etfs() -> pd.DataFrame:
    """Return the listed ETF universe."""
    return _reference().etf.list()


def funds() -> pd.DataFrame:
    """Return the open-ended mutual fund universe (Fmarket).

    Note this covers open-ended funds distributed through Fmarket only — it
    does **not** cover listed ETFs. Use :func:`etfs` for those.
    """
    return _reference().fund().list()


def fund_nav(symbol: str) -> pd.DataFrame:
    """Return the NAV history of an open-ended fund, e.g. ``DCDS``."""
    return _reference().fund().nav_report(symbol)


def fund_top_holding(symbol: str) -> pd.DataFrame:
    """Return the top holdings of an open-ended fund."""
    return _reference().fund().top_holding(symbol)


def fund_industry_holding(symbol: str) -> pd.DataFrame:
    """Return the industry allocation of an open-ended fund."""
    return _reference().fund().industry_holding(symbol)


def fund_asset_holding(symbol: str) -> pd.DataFrame:
    """Return the asset-class allocation of an open-ended fund."""
    return _reference().fund().asset_holding(symbol)


def market_status() -> object:
    """Return the live session status (OPEN, ATO, ATC, CLOSED)."""
    return _reference().market.status()
