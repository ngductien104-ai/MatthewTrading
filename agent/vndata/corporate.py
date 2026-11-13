"""Capital history, insider dealing and ownership — now on VNDIRECT MCP.

These three disclosures used to come from the free ``vnstock`` package as a
documented carve-out. The vnstock subscription was cancelled on 13/11/2026 and
the package is no longer a source for anything, so each function raises
:class:`~vndata.errors.SourceUnavailable` naming where the data lives now.

The authoritative record for all three remains the issuer's own HOSE/HNX
disclosure; cite the filing when a number matters.
"""

from __future__ import annotations

import pandas as pd

from vndata.errors import moved_to_vndirect


def capital_history(symbol: str) -> pd.DataFrame:
    """Share-capital / dilution history — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"capital history ({symbol})")


def insider_trading(symbol: str) -> pd.DataFrame:
    """Insider and related-party dealing — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"insider trading ({symbol})")


def ownership(symbol: str) -> pd.DataFrame:
    """Ownership structure — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"ownership ({symbol})")
