"""Financial statements and ratios — VNDIRECT MCP is the truth source.

``vnstock_data`` served these until the vnstock subscription was cancelled on
13/11/2026. VNDIRECT MCP is OAuth-protected and reachable only from an MCP
client, so the Python entry points below raise
:class:`~vndata.errors.SourceUnavailable` rather than fall back to anything
weaker. Pull statements and ratios through the connector's ``FINFO_API__*`` tools, and
footnotes from the primary PDF (``agent/scripts/evidence_pack.py``).

:data:`DISCLOSURE_LAG_DAYS` stays here: it is a policy constant about *when*
a statement may be used, not about where it comes from.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

import pandas as pd

from vndata.errors import moved_to_vndirect

#: Conservative visibility lag for financial statements, measured in calendar
#: days from the end of the reporting period.  A statement must not be exposed
#: to a resolver or backtest before ``period_end + DISCLOSURE_LAG_DAYS[kind]``;
#: doing so would let it use figures the market could not yet have known.
#:
#: 90 days for annual reports (the audited annual-report publication window)
#: and 45 days for quarterly reports (the 30-day consolidated-report deadline
#: plus a 15-day safety buffer).  These are conservative synthetic dates for
#: feeds without an actual filing timestamp.
DISCLOSURE_LAG_DAYS: Mapping[str, int] = MappingProxyType({"year": 90, "quarter": 45})

STATEMENTS = ("income_statement", "balance_sheet", "cash_flow")


def statement(symbol: str, which: str = "income_statement", period: str = "year") -> pd.DataFrame:
    """Financial statement — fetch via VNDIRECT MCP."""
    if which not in STATEMENTS:
        raise ValueError(f"unknown statement {which!r}; expected one of {STATEMENTS}")
    raise moved_to_vndirect(f"{which} ({symbol}, {period})")


def ratios(symbol: str, period: str = "year") -> pd.DataFrame:
    """Financial ratios — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"ratios ({symbol}, {period})")


def is_bank(symbol: str) -> bool:
    """Bank classification — read the industry from VNDIRECT MCP."""
    raise moved_to_vndirect(f"bank classification ({symbol})")


def derived(symbol: str, period: str = "year") -> pd.DataFrame:
    """Reconstructed fields — fetch statements via VNDIRECT MCP."""
    raise moved_to_vndirect(f"derived fundamentals ({symbol}, {period})")


def wide(symbol: str, which: str = "income_statement", period: str = "year") -> pd.DataFrame:
    """Statement pivoted wide — fetch via VNDIRECT MCP."""
    return statement(symbol, which, period)


def ratios_wide(symbol: str, period: str = "year") -> pd.DataFrame:
    """Ratios pivoted wide — fetch via VNDIRECT MCP."""
    return ratios(symbol, period)
