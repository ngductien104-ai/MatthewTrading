"""Run one sponsored ``vndata`` call in a throwaway process and print the result.

Why the work does not happen in the MCP server
----------------------------------------------
Measured on 2026-08-27 against this repo's own server: ``vn_ratios`` for TCB
answered in 35s when called in-process from the project virtualenv, but never
returned through MCP — two attempts were still running at 11m32s and 8m, on
different symbols and with ``max_rows=3``. Issuing ``vn_indicator`` and
``vn_universe`` concurrently killed the server outright (``Connection closed``,
new PID, and every one of the twelve ``vn_*`` tools gone from the session).

Ruled out, with evidence: missing packages (the project venv matches the home
venv at ``vnstock_data`` 3.2.8), stdout corrupting the JSON-RPC stream (0 bytes
captured across a sponsored call), a revoked API key (the server started at
10:42, the key rotated at 09:05), and the computation itself
(``vndata.ta.indicator`` standalone: 26s, clean). What survives is that the
sponsored packages misbehave *inside the server's long-lived asyncio process*,
in a way that the DataPro-only tools — which never touch them — never show.

Root-causing that belongs upstream. Containing it does not: every sponsored
call now gets a fresh process and a deadline, so the worst case is one tool
returning a timeout message instead of every tool disappearing at once.

Protocol: a JSON request on stdin, a JSON response on stdout::

    {"op": "ratios", "kwargs": {"symbol": "TCB", "period": "year",
                                "max_rows": 12}}
    -> {"ok": true, "text": "8 rows total, ..."}
    -> {"ok": false, "kind": "source_unavailable", "message": "..."}

Anything the sponsored libraries print is diverted to stderr while the call
runs, so stdout carries the JSON document and nothing else.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# The layer lives next to this file, under agent/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

import vndata  # noqa: E402
from vndata.errors import VnDataError  # noqa: E402
from vndata_render import table  # noqa: E402


def _health() -> str:
    return json.dumps(vndata.health(), ensure_ascii=False, indent=2, default=str)


def _financials(symbol: str, statement: str = "income_statement",
                period: str = "year", max_rows: int = 12) -> str:
    return table(vndata.fundamental.wide(symbol, statement, period=period), max_rows)


def _ratios(symbol: str, period: str = "year", max_rows: int = 12) -> str:
    return table(vndata.fundamental.ratios_wide(symbol, period=period), max_rows)


def _derived(symbol: str, period: str = "year", max_rows: int = 12) -> str:
    return table(vndata.fundamental.derived(symbol, period=period), max_rows)


def _indicator(symbol: str, start: str, end: str, family: str, name: str,
               length: int = 14, max_rows: int = 20) -> str:
    if family not in vndata.ta.FAMILIES:
        return f"family must be one of {vndata.ta.FAMILIES}"
    ind = vndata.ta.indicator(symbol, start, end)
    group = getattr(ind, family)
    fn = getattr(group, name, None)
    if fn is None:
        available = sorted(n for n in dir(group) if not n.startswith("_") and n != "data")
        return f"unknown {family} indicator {name!r}. Available: {available}"
    try:
        out = fn(length=length)
    except TypeError:
        out = fn()
    frame = out.to_frame() if isinstance(out, pd.Series) else pd.DataFrame(out)
    frame.attrs["source"] = getattr(ind, "source", "datapro")
    return table(frame, max_rows)


def _company(symbol: str, what: str = "info", max_rows: int = 30) -> str:
    sponsored = {
        "info": vndata.reference.company,
        "shareholders": vndata.reference.shareholders,
        "officers": vndata.reference.officers,
        "subsidiaries": vndata.reference.subsidiaries,
        "events": vndata.reference.events,
    }
    carve_out = {
        "capital_history": vndata.corporate.capital_history,
        "insider_trading": vndata.corporate.insider_trading,
        "ownership": vndata.corporate.ownership,
    }
    fn = sponsored.get(what) or carve_out.get(what)
    if fn is None:
        return f"what must be one of {sorted([*sponsored, *carve_out])}"
    return table(fn(symbol), max_rows)


def _universe(group: str = "", max_rows: int = 60) -> str:
    if group:
        return table(vndata.reference.symbols_by_group(group), max_rows)
    return table(vndata.reference.symbols_by_industry(), max_rows)


def _news(symbol: str = "", sites: str = "", max_articles: int = 10,
          time_frame: str = "1d", max_rows: int = 20) -> str:
    if symbol:
        return table(vndata.news.company_news(symbol), max_rows)
    if not sites:
        supported = [s["name"] for s in vndata.news.supported_sites()]
        return f"pass symbol=, or sites= from: {supported}"
    articles = vndata.news.crawl(
        [s.strip() for s in sites.split(",") if s.strip()],
        max_articles=max_articles,
        time_frame=time_frame,
    )
    return table(pd.DataFrame(articles), max_rows)


def _macro(domain: str, name: str, max_rows: int = 24) -> str:
    return table(vndata.macro.series(domain, name), max_rows)


#: Operation name -> implementation. The MCP server's sponsored tools are thin
#: wrappers over these names; the names are the contract between the two.
OPS = {
    "health": _health,
    "financials": _financials,
    "ratios": _ratios,
    "derived": _derived,
    "indicator": _indicator,
    "company": _company,
    "universe": _universe,
    "news": _news,
    "macro": _macro,
}


def run(op: str, kwargs: dict) -> dict:
    """Execute *op* and return the response document, never raising."""
    fn = OPS.get(op)
    if fn is None:
        return {"ok": False, "kind": "bad_request",
                "message": f"unknown op {op!r}; expected one of {sorted(OPS)}"}
    try:
        return {"ok": True, "text": fn(**kwargs)}
    except VnDataError as exc:
        return {"ok": False, "kind": "source_unavailable", "message": str(exc)}
    except TypeError as exc:
        return {"ok": False, "kind": "bad_request", "message": str(exc)}
    except Exception as exc:  # noqa: BLE001 - the server renders this, not a trace
        return {"ok": False, "kind": type(exc).__name__, "message": str(exc)}


def main() -> None:
    request = json.loads(sys.stdin.read() or "{}")

    # Whatever the sponsored libraries decide to print must not land in the
    # JSON document; stdout is reclaimed only once the call is over.
    real_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        response = run(request.get("op", ""), request.get("kwargs") or {})
    finally:
        sys.stdout = real_stdout

    json.dump(response, sys.stdout, ensure_ascii=False)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
