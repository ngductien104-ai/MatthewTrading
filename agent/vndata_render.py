"""Markdown rendering for ``vndata`` frames, shared by the MCP server and its worker.

This lives apart from both because the frame is rendered in whichever process
fetched it. Sponsored calls run in :mod:`vndata_worker`, DataPro calls run in
the server itself, and both have to produce byte-identical output — an MCP
caller must not be able to tell which side of the process boundary served it.
"""

from __future__ import annotations

import pandas as pd

#: Hard cap so a careless call cannot flood the client's context.
MAX_ROWS_LIMIT = 200


def table(df: pd.DataFrame, max_rows: int = 30) -> str:
    """Render *df* as markdown, tail-truncated, with the source stamp attached."""
    if df is None or len(df) == 0:
        return "(no rows)"
    rows = min(max(int(max_rows), 1), MAX_ROWS_LIMIT)
    shown = df.tail(rows)
    header = f"{len(df)} rows total, showing last {len(shown)}."

    source = df.attrs.get("source")
    if source:
        header += f" source={source}"
    if df.attrs.get("degraded"):
        header += f"  ⚠️ DEGRADED: {df.attrs.get('degraded_reason', 'fallback source in use')}"
    units = [f"{k}={v}" for k, v in df.attrs.items() if k.endswith("_unit")]
    if units:
        header += "  units: " + ", ".join(units)

    return header + "\n\n" + shown.to_markdown()
