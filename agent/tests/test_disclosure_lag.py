"""The point-in-time disclosure policy, and what a VN fundamentals backtest does now."""

from __future__ import annotations

import pytest

from backtest.engines.base import _fundamental_provider
from vndata import fundamental
from vndata.errors import SourceUnavailable


def test_disclosure_lag_policy_is_fixed_and_read_only() -> None:
    assert fundamental.DISCLOSURE_LAG_DAYS == {"year": 90, "quarter": 45}
    with pytest.raises(TypeError):
        fundamental.DISCLOSURE_LAG_DAYS["year"] = 0


@pytest.mark.parametrize("config", [
    {"source": "datapro", "codes": ["VCB.VN"]},
    {"source": "auto", "codes": ["HPG.VN"]},
])
def test_vn_fundamental_fields_fail_loudly_instead_of_running_price_only(config) -> None:
    """VN statements live on VNDIRECT MCP since 13/11/2026; Python has no source."""
    with pytest.raises(SourceUnavailable, match="VNDIRECT MCP"):
        _fundamental_provider(config)
