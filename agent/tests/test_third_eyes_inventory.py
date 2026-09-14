from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from src.third_eyes.api import router
from src.third_eyes.collectors import collect, latest_completed_session, session_freshness, SourceSchemaError
from src.third_eyes.inventory import inventory
from src.third_eyes.models import Observation, Rule, Settings, SourceSpec
from src.third_eyes.service import Service


NOW = datetime(2026, 9, 14, 9, tzinfo=timezone.utc)


def setup_service(tmp_path):
    source = SourceSpec(id="test", kind="macro", domain="macro", indicator="cpi",
                        entity="VN", unit="percent", group="inflation")
    service = Service(Settings(state_dir=str(tmp_path), sources=[source],
                               rules=[Rule(id="r", indicator="cpi", window=10)]))
    return service, source


def test_readiness_counts_closed_history_and_recomputes_staleness(tmp_path):
    service, source = setup_service(tmp_path)
    rows = [Observation(indicator="cpi", entity="VN", source="test", unit="percent", value=i,
                        observed_at=NOW-timedelta(days=16-i), published_at=NOW-timedelta(days=16-i),
                        received_at=NOW-timedelta(days=16-i)) for i in range(16)]
    service.store.ingest(rows)
    service.store.set("coverage:test", {"status": "available", "checked_at": NOW.isoformat()})
    report = inventory(service.settings, service.store, NOW)
    assert report["items"][0]["ready_for_detection"]
    assert report["items"][0]["series"][0]["rules"][0]["observations_available"] == 16
    # Another source's later revision must not hide this source's history.
    service.store.ingest([rows[-1].model_copy(update={"source": "other", "received_at": NOW})])
    assert inventory(service.settings, service.store, NOW)["items"][0]["ready_for_detection"]
    stale = inventory(service.settings, service.store, NOW+timedelta(days=10))["items"][0]
    assert stale["status"] == "stale"
    assert not stale["ready_for_detection"]
    rows[-1].closed = False
    rows[-1].received_at = NOW
    service.store.ingest([rows[-1]])
    assert "insufficient_history" in inventory(service.settings, service.store, NOW)["items"][0]["gaps"]


def test_disabled_missing_and_orphan_rules(tmp_path):
    service, source = setup_service(tmp_path)
    source.kind = "csv"
    source.path = str(tmp_path / "missing.csv")
    service.settings.rules.append(Rule(id="orphan", indicator="absent"))
    report = inventory(service.settings, service.store, NOW)
    assert report["items"][0]["status"] == "missing"
    assert report["orphan_rules"] == ["orphan"]
    source.enabled = False
    assert inventory(service.settings, service.store, NOW)["items"][0]["status"] == "disabled"


def test_schema_failure_is_visible_and_does_not_block_next_source(tmp_path, monkeypatch):
    service, source = setup_service(tmp_path)
    source.entity_column = "symbol"
    monkeypatch.setattr("src.third_eyes.collectors.source_frame",
                        lambda *_: pd.DataFrame({"time": [NOW], "value": [1]}))
    with pytest.raises(SourceSchemaError) as error:
        collect(source, NOW)
    assert error.value.missing == ["symbol"]
    service.scan(source, NOW)
    assert service.store.get("coverage:test")["status"] == "schema_mismatch"
    assert service.store.get("coverage:test")["columns"] == ["time", "value"]
    source.entity_column = None
    service.scan(source, NOW)
    assert service.store.get("coverage:test")["status"] == "available"


def test_inventory_requires_auth_and_never_collects(tmp_path):
    service, _ = setup_service(tmp_path)
    def forbidden(*args):
        raise AssertionError("Inventory must not query vendors")
    service.collector = forbidden
    async def auth(authorization: str | None = Header(None)):
        if authorization != "Bearer test":
            raise HTTPException(401)
    app = FastAPI()
    app.include_router(router(service, auth))
    with TestClient(app) as client:
        assert client.get("/third-eyes/v1/inventory").status_code == 401
        response = client.get("/third-eyes/v1/inventory", headers={"Authorization": "Bearer test"})
        assert response.status_code == 200
        assert response.json()["live_query_performed"] is False
        assert response.json()["items"][0]["ready_for_detection"] is False


def test_eod_freshness_uses_completed_sessions_and_configured_holidays():
    holidays = ["2026-09-02"]
    before_open = datetime(2026, 9, 3, 1, tzinfo=timezone.utc)  # 08:00 Vietnam
    expected = latest_completed_session(before_open, holidays)
    assert expected.astimezone().date().isoformat() <= "2026-09-01"
    source = SourceSpec(id="index", kind="price", domain="market", indicator="index",
                        entity="VNINDEX", unit="points", group="price")
    assert session_freshness(source, expected, before_open, holidays)["session_fresh"] is True
    after_close = datetime(2026, 9, 3, 9, tzinfo=timezone.utc)  # 16:00 Vietnam
    assert session_freshness(source, expected, after_close, holidays)["session_fresh"] is False
