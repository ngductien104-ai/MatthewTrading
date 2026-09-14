"""Authenticated versioned REST API and replayable SSE for Fincept clients."""
import asyncio
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.responses import HTMLResponse
from pathlib import Path
from .models import Contract, Indicator, Signal


class SignalPage(Contract):
    items: list[Signal]
    total: int


def router(service, auth, event_auth=None):
    api = APIRouter(prefix="/third-eyes/v1")
    secure = [Depends(auth)]

    @api.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    def dashboard():
        # Static shell only; every data request still requires bearer authentication.
        return (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")

    @api.get("/health", dependencies=secure)
    def health():
        return service.health()

    @api.get("/coverage", dependencies=secure)
    def coverage():
        return service.store.coverage()

    @api.get("/inventory", dependencies=secure)
    def inventory():
        from .inventory import inventory as build_inventory
        return build_inventory(service.settings, service.store)

    @api.get("/indicators", dependencies=secure, response_model=list[Indicator])
    def indicators():
        return service.indicators()

    @api.get("/portfolio", dependencies=secure)
    def portfolio():
        return service.store.get("portfolio", {"status": "not_configured", "positions": []})

    @api.get("/evidence/{snapshot}", dependencies=secure)
    def evidence(snapshot: str):
        value = service.store.evidence(snapshot)
        if value is None:
            raise HTTPException(404, "Evidence not found")
        return value

    @api.get("/signals", dependencies=secure, response_model=SignalPage)
    def signals(tier: str | None = None, domain: str | None = None, entity: str | None = None,
                active: bool = True, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        values = [s.model_dump(mode="json") for s in service.store.signals()
                  if (not tier or s.tier == tier) and (not domain or s.domain == domain)
                  and (not entity or s.entity == entity) and (not active or s.state != "expired")]
        return {"items": values[offset:offset+limit], "total": len(values)}

    @api.get("/signals/{signal_id}", dependencies=secure, response_model=Signal)
    def detail(signal_id: str):
        signal = service.store.signal(signal_id)
        if not signal:
            raise HTTPException(404, "Signal not found")
        return signal.model_dump(mode="json")

    @api.post("/signals/{signal_id}/ack", dependencies=secure, response_model=Signal)
    def acknowledge(signal_id: str):
        result = service.store.acknowledge(signal_id)
        if result is None:
            raise HTTPException(404, "Signal not found")
        return result

    @api.get("/events", dependencies=[Depends(event_auth or auth)])
    async def events(request: Request, after: int = Query(0, ge=0),
                     last_event_id: str | None = Header(None)):
        try:
            cursor = max(after, int(last_event_id or 0))
            if cursor < 0:
                raise ValueError()
        except ValueError:
            raise HTTPException(400, "Invalid Last-Event-ID") from None

        async def stream():
            nonlocal cursor
            idle = 0
            while not await request.is_disconnected():
                batch = await asyncio.to_thread(service.store.events, cursor)
                for item in batch:
                    cursor = item["id"]
                    yield f'id: {cursor}\nevent: {item["event"]}\ndata: {json.dumps(item["data"], ensure_ascii=False)}\n\n'
                if batch:
                    idle = 0
                    continue
                idle += 1
                if idle >= 15:
                    yield ": heartbeat\n\n"
                    idle = 0
                await asyncio.sleep(1)
        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    return api


def register(app, auth, event_auth=None):
    """Read existing monitor storage without starting a duplicate scheduler."""
    import os
    from .service import Service, load_settings
    config = os.getenv("THIRD_EYES_CONFIG")
    if config:
        app.include_router(router(Service(load_settings(config)), auth, event_auth))
