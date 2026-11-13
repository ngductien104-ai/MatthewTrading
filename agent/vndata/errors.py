"""Exceptions raised by the ``vndata`` truth-source layer."""

from __future__ import annotations


class VnDataError(RuntimeError):
    """Base class for every ``vndata`` failure."""


class SourceUnavailable(VnDataError):
    """The authoritative source for this data class is not reachable.

    Raised instead of silently degrading to a weaker source. Analysis built
    on an unannounced fallback is worse than analysis that stops and says so.
    """


class NotEntitled(VnDataError):
    """The caller is not entitled to the requested data source."""


class WrongSource(VnDataError):
    """Caller asked a source for a data class it is not the truth source for."""


#: Date the vnstock subscription (vnstock_data / vnstock_ta / vnstock_news and
#: the free vnstock package) was cancelled. Nothing in this layer imports it.
VNSTOCK_RETIRED = "2026-11-13"


def moved_to_vndirect(what: str) -> SourceUnavailable:
    """Build the error raised for a data class that now lives on VNDIRECT MCP.

    VNDIRECT MCP is OAuth-protected and reachable only from an MCP client
    (Claude Code, a Claude subagent in a swarm). Python has no truth source
    for these classes any more, and must not invent one.
    """
    return SourceUnavailable(
        f"{what}: không còn nguồn Python — gói vnstock đã huỷ {VNSTOCK_RETIRED}. "
        "Truy vấn qua VNDIRECT MCP (connector VNDIRECT MCP, tool FINFO_API__*, bảng tool ở skill data-routing) "
        "hoặc đọc BCTC gốc bằng agent/scripts/evidence_pack.py. Không ước tính thay số."
    )
