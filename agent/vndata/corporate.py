"""The documented exception: three disclosures the sponsored tier does not carry.

``vnstock_data``'s reference layer exposes ``events``, ``info``, ``news``,
``officers``, ``shareholders`` and ``subsidiaries``. It does **not** expose:

* ``capital_history`` — share-capital raises and dilution history
* ``insider_trading`` — insider and related-party dealing
* ``ownership`` — the ownership structure tree

The free ``vnstock`` package does. Rather than scatter ``from vnstock import
Company`` across half a dozen skills — which is exactly the pattern this layer
exists to stop — the carve-out lives here, in one file, narrowed to three
functions and labelled on every return value.

Everything else stays on the sponsored tier. If ``vnstock_data`` ever ships
these endpoints, delete this module and repoint the callers; nothing else has
to change.

The authoritative record for all three is the issuer's own HOSE/HNX disclosure.
Treat what comes back here as a fast index into that record, and cite the
filing when a number matters.
"""

from __future__ import annotations

import pandas as pd

from vndata.errors import SourceUnavailable

#: Stamped onto every frame this module returns.
_TIER = "vnstock (free tier) — no sponsored equivalent exists"


def _company(symbol: str):
    try:
        from vnstock import Company
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable(
            "the free vnstock package is not installed; it is required only for "
            "capital history, insider trading and ownership."
        ) from exc
    return Company(symbol=symbol.strip().upper().replace(".VN", ""))


def _stamp(df: pd.DataFrame, what: str) -> pd.DataFrame:
    df.attrs["source"] = _TIER
    df.attrs["data_class"] = what
    df.attrs["verify_against"] = "HOSE/HNX issuer disclosure"
    return df


def capital_history(symbol: str) -> pd.DataFrame:
    """Return the share-capital / dilution history for *symbol*."""
    try:
        return _stamp(_company(symbol).capital_history(), "capital_history")
    except SourceUnavailable:
        raise
    except Exception as exc:
        raise SourceUnavailable(f"capital history unavailable for {symbol}: {exc}") from exc


def insider_trading(symbol: str) -> pd.DataFrame:
    """Return insider and related-party dealing for *symbol*."""
    try:
        return _stamp(_company(symbol).insider_trading(), "insider_trading")
    except SourceUnavailable:
        raise
    except Exception as exc:
        raise SourceUnavailable(f"insider trading unavailable for {symbol}: {exc}") from exc


def ownership(symbol: str) -> pd.DataFrame:
    """Return the ownership structure tree for *symbol*."""
    try:
        return _stamp(_company(symbol).ownership(), "ownership")
    except SourceUnavailable:
        raise
    except Exception as exc:
        raise SourceUnavailable(f"ownership unavailable for {symbol}: {exc}") from exc
