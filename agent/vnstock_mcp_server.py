#!/usr/bin/env python3
"""MCP server exposing the Vietnamese truth-source layer (``vndata``).

Why this exists alongside the DataPro MCP
-----------------------------------------
DataPro already speaks MCP, so a Claude Code session can ask it for bars
directly. Nothing speaks for ``vnstock_data`` / ``vnstock_ta`` /
``vnstock_news``, which means fundamentals, macro, reference data, indicators
and news all require hand-written Python in the right virtualenv — and every
one of those scripts is a fresh chance to read ``RT_PRT_ROE`` as 0.13 instead
of 13%.

This server is a thin wrapper over :mod:`vndata`. It adds no logic of its own:
the routing table, the unit corrections and the loud failures all live in the
layer, so an MCP caller and a Python caller cannot drift apart.

Run it with the project virtualenv, which carries both ``fastmcp`` and the
sponsored packages::

    .venv/Scripts/python.exe agent/vnstock_mcp_server.py

Register it for Claude Code in ``.mcp.json``::

    {
      "mcpServers": {
        "vnstock": {
          "command": ".venv/Scripts/python.exe",
          "args": ["agent/vnstock_mcp_server.py"]
        }
      }
    }

Frames come back as markdown tables, truncated to ``max_rows``, because an MCP
result is read by a model and a 2,000-row CSV is worse than useless.
"""

from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
from pathlib import Path

# The layer lives next to this file, under agent/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastmcp import FastMCP  # noqa: E402

import vndata  # noqa: E402
from vndata.errors import VnDataError  # noqa: E402
from vndata_render import table as _table  # noqa: E402

mcp = FastMCP("vnstock")

#: The sponsored packages hang, and sometimes kill this process, when they run
#: inside the server's long-lived asyncio loop. They run in a child process
#: instead, on a deadline. :mod:`vndata_worker` records the measurements.
_WORKER = Path(__file__).resolve().parent / "vndata_worker.py"

#: Seconds a sponsored call may take before the child is killed. The slowest
#: healthy call measured was 35s and the MCP client backgrounds a tool at 120s,
#: so the default sits between the two: a stuck call comes back as a timeout
#: message rather than disappearing into a background task.
CALL_TIMEOUT = float(os.getenv("VNDATA_CALL_TIMEOUT", "90"))


def _isolated(op: str, timeout: float | None = None, **kwargs) -> str:
    """Run one sponsored ``vndata`` call in a child process and render its reply.

    A hang now costs this one tool a timeout message. It no longer costs the
    session every other ``vn_*`` tool.
    """
    deadline = CALL_TIMEOUT if timeout is None else timeout
    try:
        proc = subprocess.run(
            [sys.executable, str(_WORKER)],
            input=json.dumps({"op": op, "kwargs": kwargs}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=deadline,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired:
        return (
            f"TIMED OUT after {deadline:.0f}s — the sponsored source did not answer, and the "
            "call was killed rather than left to wedge the server. Retry once; if it times "
            "out again, run this against the vndata layer in Python instead of through MCP."
        )

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip().splitlines()
        detail = stderr_tail[-1] if stderr_tail else f"exit code {proc.returncode}"
        return (
            f"WORKER DIED ({detail}) — the call was isolated, so every other vn_* tool is "
            "still available."
        )

    try:
        response = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return f"WORKER RETURNED MALFORMED OUTPUT: {proc.stdout[:400]!r}"

    if response.get("ok"):
        return response["text"]
    if response.get("kind") == "source_unavailable":
        return (
            "SOURCE UNAVAILABLE — do not substitute another source silently.\n\n"
            f"{response.get('message', '')}"
        )
    return f"ERROR ({response.get('kind', 'Error')}): {response.get('message', '')}"


def _guard(fn):
    """Turn a :class:`VnDataError` into a readable MCP result, not a stack trace.

    ``functools.wraps`` sets ``__wrapped__``, which is what lets FastMCP read
    the real signature through the wrapper — without it the tool registers as
    taking ``*args`` and FastMCP rejects it.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except VnDataError as exc:
            return f"SOURCE UNAVAILABLE — do not substitute another source silently.\n\n{exc}"
        except Exception as exc:  # noqa: BLE001 - surface the message, not a trace
            return f"ERROR ({type(exc).__name__}): {exc}"

    return wrapper


@mcp.tool
@_guard
def vn_health() -> str:
    """Report which Vietnamese data sources are live: DataPro, licence tier, packages.

    Call this first when anything returns unexpectedly empty.
    """
    return _isolated("health")


@mcp.tool
@_guard
def vn_source_map() -> str:
    """Return the authoritative data-class -> source mapping for Vietnam.

    One data class, one source. Use it to check where a number should come from
    before fetching it.
    """
    return json.dumps(vndata.SOURCE_MAP, ensure_ascii=False, indent=2)


@mcp.tool
@_guard
def vn_ohlcv(symbol: str, start: str, end: str, interval: str = "1D", max_rows: int = 30) -> str:
    """Daily or intraday bars for a Vietnamese symbol, from DataPro.

    Args:
        symbol: Ticker, bare (``VCB``) or suffixed (``VCB.VN``). Indices
            (``VNINDEX``) and futures (``VN30F1M``) work too.
        start: Inclusive start date, ``YYYY-MM-DD``.
        end: Inclusive end date, ``YYYY-MM-DD``.
        interval: ``1D`` for daily, or a minute bar such as ``5m``.
        max_rows: Rows to render (most recent first cut off at the tail).

    Prices and turnover are in **thousand VND**; volumes are in shares.
    """
    df = vndata.price.ohlcv(symbol, start, end, interval=interval)
    keep = [c for c in ("open", "high", "low", "close", "ref_price", "volume", "value") if c in df.columns]
    return _table(df[keep] if keep else df, max_rows)


@mcp.tool
@_guard
def vn_flow(symbol: str, start: str, end: str, desk: str = "foreign", max_rows: int = 30) -> str:
    """Net foreign or proprietary (tự doanh) buying for a symbol, from DataPro.

    Args:
        symbol: Ticker, bare or ``.VN``-suffixed.
        start: Inclusive start date, ``YYYY-MM-DD``.
        end: Inclusive end date, ``YYYY-MM-DD``.
        desk: ``foreign`` or ``proprietary``.
        max_rows: Rows to render.

    Values are in **thousand VND**, volumes in shares. Requires the DataPro
    desktop — no other source in this stack carries proprietary flow.
    """
    if desk not in {"foreign", "proprietary"}:
        return "desk must be 'foreign' or 'proprietary'"
    fn = vndata.price.foreign_flow if desk == "foreign" else vndata.price.proprietary_flow
    return _table(fn(symbol, start, end), max_rows)


@mcp.tool
@_guard
def vn_financials(symbol: str, statement: str = "income_statement", period: str = "year",
                  max_rows: int = 12) -> str:
    """Financial statements from vnstock_data, pivoted to period x line-item.

    Args:
        symbol: Ticker, bare or ``.VN``-suffixed.
        statement: ``income_statement``, ``balance_sheet`` or ``cash_flow``.
        period: ``year`` or ``quarter``.
        max_rows: Periods to render.

    Values are plain VND. Sponsored depth is 8 annual and 34 quarterly periods.
    """
    return _isolated("financials", symbol=symbol, statement=statement,
                     period=period, max_rows=max_rows)


@mcp.tool
@_guard
def vn_ratios(symbol: str, period: str = "year", max_rows: int = 12) -> str:
    """Financial ratios from vnstock_data, with every unit trap corrected.

    Profitability and bank ratios come back **in percent** (ROE 15.85, not
    0.1585). Money fields are plain VND. Fields that are broken upstream
    (``RT_VALUE_EQUITY``, ``RT_BANK_NOII``) come back ``NaN`` — read equity from
    ``vn_financials`` balance sheet instead. A stored ``0.0`` means "not
    applicable to this company type" and is returned as ``NaN``.
    """
    return _isolated("ratios", symbol=symbol, period=period, max_rows=max_rows)


@mcp.tool
@_guard
def vn_derived(symbol: str, period: str = "year", max_rows: int = 12) -> str:
    """The three fields vnstock_data cannot be trusted on, reconstructed.

    ``minority_interest`` keeps its sign when it is a loss (upstream drops it),
    ``operating_expenses`` is derived for banks (upstream returns NaN), and
    ``equity`` is read from the balance sheet (upstream's ratio field is
    corrupt). All in plain VND.
    """
    return _isolated("derived", symbol=symbol, period=period, max_rows=max_rows)


@mcp.tool
@_guard
def vn_indicator(symbol: str, start: str, end: str, family: str, name: str,
                 length: int = 14, max_rows: int = 20) -> str:
    """Compute a vnstock_ta indicator on DataPro prices.

    Args:
        symbol: Ticker, bare or ``.VN``-suffixed.
        start: Inclusive start date, ``YYYY-MM-DD``.
        end: Inclusive end date, ``YYYY-MM-DD``.
        family: ``trend``, ``momentum``, ``volatility``, ``volume`` or ``statistics``.
        name: Indicator name within the family, e.g. ``rsi``, ``sma``, ``macd``.
        length: Lookback passed to the indicator when it accepts one.
        max_rows: Rows to render.
    """
    return _isolated("indicator", symbol=symbol, start=start, end=end, family=family,
                     name=name, length=length, max_rows=max_rows)


@mcp.tool
@_guard
def vn_company(symbol: str, what: str = "info", max_rows: int = 30) -> str:
    """Company reference data from vnstock_data.

    Args:
        symbol: Ticker, bare or ``.VN``-suffixed.
        what: ``info``, ``shareholders``, ``officers``, ``subsidiaries``,
            ``events``, or one of the free-tier carve-outs
            ``capital_history`` / ``insider_trading`` / ``ownership``.
        max_rows: Rows to render.
    """
    return _isolated("company", symbol=symbol, what=what, max_rows=max_rows)


@mcp.tool
@_guard
def vn_universe(group: str = "", max_rows: int = 60) -> str:
    """List the tradable universe, or the members of one index or board.

    Args:
        group: An index or board such as ``VN30`` or ``HOSE``. Empty returns
            the full ICB classification (one row per symbol per ICB level).
        max_rows: Rows to render.
    """
    return _isolated("universe", group=group, max_rows=max_rows)


@mcp.tool
@_guard
def vn_news(symbol: str = "", sites: str = "", max_articles: int = 10,
            time_frame: str = "1d", max_rows: int = 20) -> str:
    """News from vnstock_news.

    Args:
        symbol: Ticker for ticker-tagged headlines. Leave empty to crawl sites.
        sites: Comma-separated outlet names (``cafef,vietstock``) for full
            article text. Ignored when *symbol* is given.
        max_articles: Cap per outlet when crawling.
        time_frame: Lookback window when crawling, e.g. ``1d``, ``7d``.
        max_rows: Rows to render.
    """
    # Crawling several outlets for full article text is legitimately slow.
    return _isolated("news", timeout=max(CALL_TIMEOUT, 240.0), symbol=symbol, sites=sites,
                     max_articles=max_articles, time_frame=time_frame, max_rows=max_rows)


@mcp.tool
@_guard
def vn_macro(domain: str, name: str, max_rows: int = 24) -> str:
    """Macro, rates or commodity series from vnstock_data.

    Args:
        domain: ``economy``, ``currency`` or ``commodity``.
        name: Series name — call with an unknown name to list the options.
        max_rows: Rows to render.

    Most series are served by an upstream backend that may be blocked on this
    network; the error says so explicitly rather than returning a guess.
    """
    return _isolated("macro", domain=domain, name=name, max_rows=max_rows)


def main() -> None:
    """Serve over stdio, or SSE when ``--transport sse`` is passed."""
    transport = "sse" if "--transport" in sys.argv and "sse" in sys.argv else "stdio"
    if transport == "sse":
        mcp.run(transport="sse", host=os.getenv("MCP_HOST", "127.0.0.1"),
                port=int(os.getenv("MCP_PORT", "8931")))
    else:
        mcp.run()


if __name__ == "__main__":
    main()
