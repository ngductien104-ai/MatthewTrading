"""Financial statements and ratios — ``vnstock_data`` is the truth source.

Everything fundamental about a Vietnamese listed company comes from the
sponsored Unified UI: income statement, balance sheet, cash flow, footnotes,
filings and the ratio table. DataPro does not carry these, and the free
``vnstock`` package returns a stale, differently-shaped ratio table that has
produced wrong analysis before — it is not used here.

Raw frames arrive in long format (``period``, ``id``, ``name``, ``unit``,
``value``) and go through :mod:`vndata.normalize` before they reach a caller,
so the documented unit traps cannot leak into analysis.

Three fields are broken or missing upstream and are reconstructed here rather
than reported as-is — see :func:`derived`:

* **Minority interest** loses its sign when it is a loss, so it is recomputed
  as ``net profit after tax - profit attributable to parent shareholders``.
* **Operating expenses** is ``NaN`` for banks, so it is recomputed as
  ``total operating income - pre-provision operating profit``.
* **Equity** is broken in the ratio table and is read from the balance sheet.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

import pandas as pd

from vndata.errors import SourceUnavailable
from vndata.normalize import normalize_ratio, normalize_statement, pivot

#: Conservative visibility lag for financial statements, measured in calendar
#: days from the end of the reporting period.  A statement must not be exposed
#: to a resolver or backtest before ``period_end + DISCLOSURE_LAG_DAYS[kind]``;
#: doing so would let it use figures the market could not yet have known.
#:
#: The existing policy values are 90 days for annual reports (the audited
#: annual-report publication window) and 45 days for quarterly reports (the
#: 30-day consolidated-report deadline plus a 15-day safety buffer).  These are
#: conservative synthetic dates for feeds without an actual filing timestamp,
#: not claims that every issuer filed on exactly that date.
DISCLOSURE_LAG_DAYS: Mapping[str, int] = MappingProxyType({"year": 90, "quarter": 45})

#: Statement name -> the Unified UI method that serves it.
STATEMENTS = ("income_statement", "balance_sheet", "cash_flow")

#: Present only in a credit institution's income statement.
_BANK_MARKER = "IS_NET_INTEREST_INCOME"

_EQUITY_IDS = ("BS_EQUITY", "BS_OWNERS_EQUITY", "BS_TOTAL_EQUITY")


def _fundamental(symbol: str):
    try:
        from vnstock_data import Fundamental
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable(
            "vnstock_data is not installed — fundamentals have no truth source."
        ) from exc
    return Fundamental().equity(symbol.strip().upper().replace(".VN", ""))


def statement(symbol: str, which: str = "income_statement", period: str = "year") -> pd.DataFrame:
    """Return a normalised financial statement in long format.

    Args:
        symbol: Ticker, bare or ``.VN``-suffixed.
        which: One of :data:`STATEMENTS`.
        period: ``year`` or ``quarter``.

    Returns:
        Long frame with a sortable string ``period`` and numeric ``value``
        in plain VND.

    Raises:
        ValueError: If *which* is not a known statement.
        SourceUnavailable: If ``vnstock_data`` cannot serve the request.
    """
    if which not in STATEMENTS:
        raise ValueError(f"unknown statement {which!r}; expected one of {STATEMENTS}")
    api = _fundamental(symbol)
    try:
        raw = getattr(api, which)(period=period)
    except Exception as exc:
        raise SourceUnavailable(f"vnstock_data could not serve {which} for {symbol}: {exc}") from exc
    return normalize_statement(raw)


def ratios(symbol: str, period: str = "year") -> pd.DataFrame:
    """Return the ratio table with every documented unit trap corrected.

    The returned frame keeps ``value_raw`` / ``unit_raw`` alongside the
    corrected ``value`` / ``unit`` and a ``note`` explaining each change, so a
    reviewer can always see what this layer touched.
    """
    api = _fundamental(symbol)
    try:
        raw = api.ratio(period=period)
    except Exception as exc:
        raise SourceUnavailable(f"vnstock_data could not serve ratios for {symbol}: {exc}") from exc
    return normalize_ratio(raw)


def is_bank(symbol: str) -> bool:
    """Return True when *symbol* files a credit-institution income statement."""
    inc = statement(symbol, "income_statement", period="year")
    return bool((inc["id"].astype(str) == _BANK_MARKER).any())


def derived(symbol: str, period: str = "year") -> pd.DataFrame:
    """Return the reconstructed fields that cannot be trusted upstream.

    Args:
        symbol: Ticker, bare or ``.VN``-suffixed.
        period: ``year`` or ``quarter``.

    Returns:
        Frame indexed by period with these columns, all in plain VND:

        ``minority_interest``
            ``net profit after tax - profit attributable to parent``. Carries
            the correct sign when minority interest is a loss.
        ``operating_expenses``
            For banks, ``total operating income - pre-provision profit``.
            ``NaN`` for non-banks, which report the field directly.
        ``equity``
            Read from the balance sheet, because the ratio table's
            ``RT_VALUE_EQUITY`` is broken.
    """
    inc = pivot(statement(symbol, "income_statement", period=period))
    bal = pivot(statement(symbol, "balance_sheet", period=period))

    out = pd.DataFrame(index=inc.index)

    npat = inc.get("IS_NET_PROFIT_AFTER_TAX")
    parent = inc.get("IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_THE_PARENT_COMPANY")
    if parent is None:
        # The id is long and has varied; fall back to a prefix match.
        cols = [c for c in inc.columns if str(c).startswith("IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS")]
        parent = inc[cols[0]] if cols else None
    out["minority_interest"] = (npat - parent) if (npat is not None and parent is not None) else float("nan")

    toi = inc.get("IS_TOTAL_OPERATING_INCOME")
    ppop = inc.get("IS_OPERATING_PROFIT_BEFORE_PROVISION_FOR_CREDIT_LOSSES")
    if ppop is None:
        cols = [c for c in inc.columns if str(c).startswith("IS_OPERATING_PROFIT_BEFORE_PROVISION")]
        ppop = inc[cols[0]] if cols else None
    out["operating_expenses"] = (toi - ppop) if (toi is not None and ppop is not None) else float("nan")

    equity = None
    for candidate in _EQUITY_IDS:
        if candidate in bal.columns:
            equity = bal[candidate]
            break
    out["equity"] = equity if equity is not None else float("nan")

    return out


def wide(symbol: str, which: str = "income_statement", period: str = "year") -> pd.DataFrame:
    """Return a statement pivoted to ``period`` rows x field-id columns."""
    return pivot(statement(symbol, which, period=period))


def ratios_wide(symbol: str, period: str = "year") -> pd.DataFrame:
    """Return the corrected ratio table pivoted to ``period`` rows x id columns."""
    return pivot(ratios(symbol, period=period))
