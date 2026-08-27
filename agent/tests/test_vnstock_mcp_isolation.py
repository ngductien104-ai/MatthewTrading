"""Tests for the subprocess isolation around sponsored ``vndata`` calls.

The bug these pin down was not a wrong number, it was a dead server: on
2026-08-27 ``vn_ratios`` never returned through MCP, and two sponsored tools
issued together killed the process and took all twelve ``vn_*`` tools with it.
The contract now is narrower and testable — a sponsored call may fail, but it
may not take the server, or any other tool, down with it.

Every test here is offline; ``subprocess.run`` is stubbed.
"""

from __future__ import annotations

import json
import subprocess

import pytest

import vndata_worker
import vnstock_mcp_server as server


class _Completed:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class TestIsolatedCall:
    def test_a_successful_call_returns_the_workers_text(self, monkeypatch):
        payload = json.dumps({"ok": True, "text": "8 rows total, showing last 2."})
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed(stdout=payload))
        assert server._isolated("ratios", symbol="TCB") == "8 rows total, showing last 2."

    def test_a_hang_becomes_a_bounded_timeout_message(self, monkeypatch):
        """The failure that started this: a call that never comes back."""
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="worker", timeout=k.get("timeout", 90))
        monkeypatch.setattr(subprocess, "run", boom)

        out = server._isolated("ratios", symbol="TCB")
        assert out.startswith("TIMED OUT after 90s")
        assert "vndata layer in Python" in out

    def test_the_deadline_is_per_call_overridable(self, monkeypatch):
        seen = {}

        def capture(*a, **k):
            seen["timeout"] = k["timeout"]
            raise subprocess.TimeoutExpired(cmd="worker", timeout=k["timeout"])
        monkeypatch.setattr(subprocess, "run", capture)

        server._isolated("news", timeout=240.0, sites="cafef")
        assert seen["timeout"] == 240.0

    def test_a_worker_crash_is_reported_without_killing_the_server(self, monkeypatch):
        """A child dying is the case that used to end the whole session."""
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **k: _Completed(stderr="Fatal Python error: Segmentation fault",
                                       returncode=-11),
        )
        out = server._isolated("indicator", symbol="HPG")
        assert "WORKER DIED" in out
        assert "every other vn_* tool is still available" in out

    def test_a_source_outage_keeps_its_do_not_substitute_warning(self, monkeypatch):
        """The layer's loud failure must survive the process boundary intact."""
        payload = json.dumps({"ok": False, "kind": "source_unavailable",
                              "message": "DataPro desktop is not answering"})
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed(stdout=payload))

        out = server._isolated("ratios", symbol="TCB")
        assert out.startswith("SOURCE UNAVAILABLE — do not substitute another source silently.")
        assert "DataPro desktop is not answering" in out

    def test_garbage_on_stdout_is_reported_not_parsed(self, monkeypatch):
        """A sponsored library printing over the JSON must not become a fake answer."""
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **k: _Completed(stdout="Welcome to vnstock!\n{\"ok\": true}"),
        )
        assert "MALFORMED OUTPUT" in server._isolated("ratios", symbol="TCB")

    @pytest.mark.parametrize("tool,op", [
        ("vn_ratios", "ratios"),
        ("vn_financials", "financials"),
        ("vn_derived", "derived"),
        ("vn_indicator", "indicator"),
        ("vn_company", "company"),
        ("vn_universe", "universe"),
        ("vn_news", "news"),
        ("vn_macro", "macro"),
        ("vn_health", "health"),
    ])
    def test_every_sponsored_tool_routes_through_isolation(self, monkeypatch, tool, op):
        """DataPro tools stay in-process; sponsored ones must not."""
        seen = {}
        # The stub's first parameter must be named ``op``: vn_indicator and
        # vn_macro both forward a ``name=`` argument of their own.
        monkeypatch.setattr(server, "_isolated",
                            lambda op, **k: seen.setdefault("op", op) or "ok")
        fn = getattr(server, tool)
        args = {"symbol": "TCB", "start": "2026-01-01", "end": "2026-08-27",
                "family": "momentum", "name": "rsi", "domain": "economy"}
        inner = getattr(fn, "__wrapped__", fn)
        params = inner.__code__.co_varnames[:inner.__code__.co_argcount]
        fn(**{k: v for k, v in args.items() if k in params})
        assert seen["op"] == op


class TestWorkerDispatch:
    def test_an_unknown_op_is_refused_by_name(self):
        out = vndata_worker.run("teleport", {})
        assert out["ok"] is False
        assert out["kind"] == "bad_request"
        assert "ratios" in out["message"]

    def test_the_op_table_matches_what_the_server_asks_for(self):
        """Server and worker share one vocabulary; drift here is a silent 404."""
        assert set(vndata_worker.OPS) == {
            "health", "financials", "ratios", "derived",
            "indicator", "company", "universe", "news", "macro",
        }
