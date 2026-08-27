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
    """The vnstock licence tier does not cover the requested library."""


class WrongSource(VnDataError):
    """Caller asked a source for a data class it is not the truth source for."""
