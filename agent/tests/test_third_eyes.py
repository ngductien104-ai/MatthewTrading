from datetime import datetime, timedelta, timezone
import asyncio
import json

import httpx
import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from src.third_eyes.models import (FeatureSpec, Indicator, Observation, ResearchProtocol,
                                   Rule, Settings, SourceSpec, Validation)
from src.third_eyes.store import Store
from src.third_eyes.detection import evaluate, confirm
from src.third_eyes.research import backtest
from src.third_eyes.service import Service
from src.third_eyes.api import router
from src.third_eyes.agents import local_endpoint, run_agents
from src.third_eyes.portfolio import optional_number
from src.third_eyes.datasets import build_dataset
from src.third_eyes.__main__ import main
from src.live.runtime.scheduler import Job
from src.swarm.presets import inspect_preset

NOW = datetime(2026, 9, 14, 9, tzinfo=timezone.utc)


def observations(count=80):
    return [Observation(indicator="x", entity="VCB", observed_at=NOW-timedelta(days=count-i-1),
                        published_at=NOW-timedelta(days=count-i-1), received_at=NOW-timedelta(days=count-i-1),
                        value=float(i if i < count-1 else 1000), source="test", unit="percent",
                        group="price", point_in_time=True) for i in range(count)]


def signal():
    return evaluate(observations(), Rule(id="r", indicator="x"),
                    Indicator(id="x", domain="company", group="price", unit="percent", description="test"),
                    "evidence", NOW)


def test_asof_revisions_and_first_receipt(tmp_path):
    store = Store(tmp_path)
    original = observations()[-2]
    revision = original.model_copy(update={"value": 900, "published_at": NOW, "received_at": NOW, "revision": "2"})
    snapshot = store.ingest([original, revision])
    assert (tmp_path / "snapshots" / f"{snapshot}.parquet").exists()
    assert store.history("x", "VCB", NOW-timedelta(hours=1))[-1].value == original.value
    assert store.history("x", "VCB", NOW)[-1].value == 900
    store.ingest([original.model_copy(update={"received_at": NOW+timedelta(days=1)})])
    assert len(store.history("x", "VCB", NOW-timedelta(hours=1))) == 1


def test_closed_bars_stale_and_future_data():
    rule = Rule(id="r", indicator="x")
    indicator = Indicator(id="x", domain="company", group="price", unit="percent", description="test")
    rows = observations()
    a = evaluate(rows, rule, indicator, "a", NOW)
    assert a.threshold < a.value
    future = rows[-1].model_copy(update={"observed_at": NOW+timedelta(days=1), "value": 1e8,
                                         "published_at": NOW+timedelta(days=1), "received_at": NOW+timedelta(days=1)})
    assert evaluate(rows+[future], rule, indicator, "a", NOW) == a
    assert evaluate(rows, rule, indicator, "a", NOW+timedelta(days=10)) is None
    rows[-1].closed = False
    assert evaluate(rows, rule, indicator, "a", NOW).observed_at != NOW


def test_priority_needs_independent_confirmation_and_matching_certificate():
    a = signal()
    a.validation = Validation(rule_version=a.rule_version, objective="down", horizon=5,
                              independent_events=30, windows=3, improvement_ci_low=.01,
                              point_in_time=True, evidence_hash="hash", dataset_hash="dataset")
    a.rule_status = "validated"
    assert confirm([a])[0].tier == "radar"
    b = a.model_copy(deep=True, update={"id": "b", "group": "liquidity"})
    assert confirm([a,b])[0].tier == "priority"
    a.validation.rule_version = "other"
    assert confirm([a,b])[0].tier == "radar"


def test_transactional_dedup_and_ack_restart(tmp_path):
    store = Store(tmp_path)
    a = signal()
    assert store.publish(a)
    assert not store.publish(a.model_copy(update={"detected_at": NOW+timedelta(seconds=1)}))
    store.acknowledge(a.id)
    reopened = Store(tmp_path)
    assert reopened.signal(a.id).acknowledged_at
    assert len(reopened.events()) == 2
    assert [e["id"] for e in reopened.events(1)] == [2]
    assert reopened.acknowledge("missing") is None


def test_service_replay_is_idempotent_and_expires_on_source_failure(tmp_path):
    spec = SourceSpec(id="test", kind="csv", domain="company", indicator="x", entity="VCB",
                      unit="percent", group="price")
    settings = Settings(state_dir=str(tmp_path), sources=[spec], rules=[Rule(id="r", indicator="x")])
    service = Service(settings)
    service.store.ingest(observations())
    service.store.set("coverage:test", {"status": "available", "checked_at": NOW.isoformat()})
    service.detect(NOW)
    service.detect(NOW)
    assert len(service.store.events()) == 1
    service.store.set("coverage:test", {"status": "unavailable"})
    service.detect(NOW)
    assert service.store.signals()[0].state == "expired"


def research_frame():
    dates = pd.date_range("2020-01-01", periods=1400, tz="UTC")
    rng = np.random.default_rng(42)
    return pd.DataFrame({"time": dates, "published_at": dates, "received_at": dates,
                         "value": rng.normal(size=len(dates)),
                         "target_close": 100*np.exp(np.cumsum(rng.normal(0,.01,len(dates)))),
                         "point_in_time": True, "adjusted_target": True, "historical_universe": True})


def test_walk_forward_purge_reproducible_and_no_lookahead():
    frame = research_frame()
    rule = Rule(id="r", indicator="x", quantile=.8)
    a, b = backtest(frame, rule, bootstrap=100), backtest(frame, rule, bootstrap=100)
    assert a == b
    times = [pd.Timestamp(e["time"]) for e in a["events"]]
    assert all((b-a).days > rule.horizon for a,b in zip(times,times[1:]))
    frame.loc[4, "received_at"] = frame.time.iloc[5]
    with pytest.raises(ValueError, match="Lookahead"):
        backtest(frame, rule)


def test_retro_data_cannot_certify():
    frame = research_frame()
    frame["point_in_time"] = False
    assert not backtest(frame, Rule(id="r", indicator="x"), bootstrap=100)["eligible"]


def test_multiple_testing_is_explicit_and_synthetic_is_never_eligible():
    frame = research_frame()
    protocol = ResearchProtocol(hypothesis_id="h", family_id="family", variant_id="v2",
                                variants_tested=4, holdout_id="holdout-2026",
                                multiple_testing_method="bonferroni", synthetic=True)
    report = backtest(frame, Rule(id="r", indicator="x"), bootstrap=100, protocol=protocol)
    assert report["multiple_testing"]["per_variant_alpha"] == pytest.approx(.0125)
    assert report["validation"]["synthetic"] is True
    assert not report["eligible"]
    with pytest.raises(ValueError, match="Bonferroni"):
        ResearchProtocol(hypothesis_id="h", family_id="f", variant_id="v", variants_tested=2)


def test_point_in_time_dataset_builder_keeps_session_horizons_and_release_events():
    times = pd.date_range("2026-01-05", periods=80, freq="B", tz="UTC")
    releases = []
    for index in (0, 20, 40, 60):
        releases.append(Observation(indicator="macro", entity="VN", observed_at=times[index].to_pydatetime(),
                                    published_at=times[index].to_pydatetime(), received_at=times[index].to_pydatetime(),
                                    value=float(index), source="official", unit="percent", point_in_time=True))
    target = pd.DataFrame({"time": times, "close": np.arange(100, 180, dtype=float)})
    feature = FeatureSpec(id="macro_release", indicator="macro", unit="percent", description="test")
    frame, manifest = build_dataset(releases, target, feature, entity="VN", target_entity="VNINDEX",
                                    adjusted_target=True, historical_universe=True)
    assert frame.event_eligible.sum() == 4
    assert frame.loc[0, "target_return_5"] == pytest.approx(105 / 100 - 1)
    assert manifest.rows == 80 and manifest.point_in_time and manifest.dataset_hash


def test_rule_registry_requires_ordered_lifecycle_and_real_certificate(tmp_path):
    store = Store(tmp_path)
    rule = Rule(id="registered", indicator="x")
    registration = store.register_rule(rule)
    validation = Validation(rule_version=rule.fingerprint, objective="down", horizon=5,
                            independent_events=30, windows=3, improvement_ci_low=.01,
                            point_in_time=True, evidence_hash="evidence", dataset_hash="dataset")
    certificate = store.save_research_report(rule, {"eligible": True,
                                             "validation": validation.model_dump(mode="json")})
    with pytest.raises(ValueError, match="Invalid rule transition"):
        store.transition_rule(rule.id, rule.fingerprint, "validated", "skip shadow", certificate)
    store.transition_rule(rule.id, rule.fingerprint, "shadow", "operator accepted shadow")
    updated = store.transition_rule(rule.id, rule.fingerprint, "validated",
                                    "independent acceptance", certificate)
    assert updated.status == "validated"
    assert [step["to"] for step in store.rule_transitions(rule.id, rule.fingerprint)] == [
        "candidate", "shadow", "validated"]


def test_synthetic_certificate_cannot_validate_rule(tmp_path):
    store = Store(tmp_path)
    rule = Rule(id="synthetic", indicator="x")
    store.register_rule(rule)
    store.transition_rule(rule.id, rule.fingerprint, "shadow", "synthetic dry run")
    validation = Validation(rule_version=rule.fingerprint, objective="down", horizon=5,
                            synthetic=True, evidence_hash="e", dataset_hash="d")
    certificate = store.save_research_report(rule, {"eligible": False,
                                             "validation": validation.model_dump(mode="json")})
    with pytest.raises(ValueError, match="Synthetic or ineligible"):
        store.transition_rule(rule.id, rule.fingerprint, "validated", "must fail", certificate)


def test_retry_backoff_circuit_and_queue_age_survive_restart(tmp_path):
    spec = SourceSpec(id="retry", kind="csv", domain="company", indicator="x", entity="VCB",
                      unit="percent", group="price")
    calls, sleeps = [], []
    def flaky(source, now):
        calls.append(now)
        if len(calls) < 3:
            raise ConnectionError("temporary")
        return observations(), {"id": source.id, "indicator": source.indicator,
                                "domain": source.domain, "status": "available",
                                "checked_at": now.isoformat()}
    settings = Settings(state_dir=str(tmp_path), sources=[spec], retry_attempts=3,
                        retry_base_seconds=1, retry_jitter_seconds=.5)
    service = Service(settings, collector=flaky, sleeper=sleeps.append, random_fn=lambda: .5)
    assert service.scan(spec, NOW)
    assert sleeps == [1.25, 2.25]
    assert service.store.get("coverage:retry")["consecutive_failures"] == 0
    job = Job("housekeeping", int(NOW.timestamp() * 1000) - 5000, "interval:60000")
    asyncio.run(service.fire(job))
    reopened = Service(settings)
    assert reopened.store.get("queue_age")["latest"]["housekeeping"] >= 5
    service.jobs.save([Job("persisted", 1234, "interval:60000")])
    assert Service(settings).jobs.load()[0].id == "persisted"

    broken = SourceSpec(id="broken", kind="csv", domain="company", indicator="broken",
                        entity="VCB", unit="percent", group="price")
    broken_settings = Settings(state_dir=str(tmp_path / "broken"), sources=[broken], retry_attempts=1,
                               max_consecutive_failures=2, failure_cooldown_seconds=60)
    count = {"calls": 0}
    def fail(*_):
        count["calls"] += 1
        raise ConnectionError("offline")
    circuit = Service(broken_settings, collector=fail, sleeper=lambda _: None)
    assert not circuit.scan(broken, NOW)
    assert not circuit.scan(broken, NOW + timedelta(seconds=1))
    assert circuit.store.get("coverage:broken")["status"] == "backoff"
    assert not circuit.scan(broken, NOW + timedelta(seconds=2))
    assert count["calls"] == 2


def test_rotating_log_is_bounded(tmp_path):
    from src.third_eyes.service import configure_rotating_log, logger
    handler = configure_rotating_log(tmp_path, 1024, 2)
    try:
        for _ in range(40):
            logger.info("x" * 100)
        handler.flush()
        assert (tmp_path / "third-eyes.log").stat().st_size <= 1024
        assert (tmp_path / "third-eyes.log.1").exists()
    finally:
        handler.close()
        logger.removeHandler(handler)


def test_api_auth_pagination_ack(tmp_path):
    service = Service(Settings(state_dir=str(tmp_path)))
    service.store.publish(signal())
    def auth(authorization: str | None = Header(None)):
        if authorization != "Bearer test":
            raise HTTPException(401)
    app = FastAPI()
    app.include_router(router(service, auth))
    with TestClient(app) as client:
        assert client.get("/third-eyes/v1/signals").status_code == 401
        headers = {"Authorization": "Bearer test"}
        data = client.get("/third-eyes/v1/signals", headers=headers).json()
        assert data["total"] == 1
        sid = data["items"][0]["id"]
        assert client.post(f"/third-eyes/v1/signals/{sid}/ack", headers=headers).json()["acknowledged_at"]
        assert client.get("/third-eyes/v1/events", params={"after": -1}, headers=headers).status_code == 422
        assert client.get("/third-eyes/v1/events", headers={**headers,"Last-Event-ID":"bad"}).status_code == 400


def test_local_only_and_bad_citations_fail_dag(tmp_path):
    with pytest.raises(ValueError):
        local_endpoint("https://api.openai.com")
    settings = Settings(state_dir=str(tmp_path), local_model="local")
    def handler(request):
        report = {"summary":"bad", "findings":[{"signal_id":"made_up", "explanation":"bad", "evidence_ids":["fake"]}], "gaps":[]}
        return httpx.Response(200, json={"message":{"content":json.dumps(report)}})
    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_agents(settings, Store(tmp_path), [signal()], client=client)
    result = asyncio.run(execute())
    assert result["status"] == "failed"
    assert result["reports"] == {}


def test_presets_valid():
    for preset in ("third_eyes_watch", "third_eyes_research"):
        assert not inspect_preset(preset)["errors"]


def test_sse_replays_after_cursor(tmp_path):
    service = Service(Settings(state_dir=str(tmp_path)))
    service.store.publish(signal())
    service.store.acknowledge(signal().id)
    api = router(service, lambda: None)
    endpoint = next(r.endpoint for r in api.routes if r.path.endswith("/events"))
    class Request:
        async def is_disconnected(self):
            return False
    async def read():
        response = await endpoint(Request(), after=0, last_event_id="1")
        iterator = response.body_iterator
        value = await anext(iterator)
        await iterator.aclose()
        return value
    assert "id: 2\nevent: ack" in asyncio.run(read())


def test_company_sources_added_without_persisting_account(tmp_path):
    service = Service(Settings(state_dir=str(tmp_path), watchlist=["VCB"]))
    service.sync_company_sources()
    service.sync_company_sources()
    assert len(service.settings.sources) == 4
    assert {s.kind for s in service.settings.sources} == {"price", "fundamental", "news"}


def test_cli_inventory_materializes_watchlist_sources_without_vendor_calls(tmp_path, capsys):
    config = tmp_path / "config.json"
    settings = Settings(state_dir="state", watchlist=["FPT"])
    config.write_text(settings.model_dump_json(), encoding="utf-8")
    assert main(["--config", str(config), "inventory"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert {item["id"] for item in report["items"]} == {
        "company_FPT_price", "company_FPT_volume", "company_FPT_profit", "company_FPT_news"
    }
    assert report["live_query_performed"] is False


def test_lease_and_restart_releases(tmp_path):
    from src.third_eyes.lease import MonitorLease
    a, b = MonitorLease(tmp_path / "monitor.lock"), MonitorLease(tmp_path / "monitor.lock")
    a.acquire()
    try:
        with pytest.raises(RuntimeError, match="Another"):
            b.acquire()
    finally:
        a.release()
    b.acquire()
    b.release()


def test_timestamp_and_nonfinite_rejected():
    item = observations()[0].model_dump()
    item["received_at"] = datetime(2026,1,1)
    with pytest.raises(ValueError):
        Observation(**item)
    item = observations()[0].model_dump()
    item["value"] = float("nan")
    with pytest.raises(ValueError):
        Observation(**item)


def test_news_event_is_idempotent_and_not_certified(tmp_path, monkeypatch):
    import src.third_eyes.collectors as collectors
    spec = SourceSpec(id="news", kind="news", domain="company", indicator="news", entity="VCB", unit="event", group="events")
    service = Service(Settings(state_dir=str(tmp_path), sources=[spec]))
    monkeypatch.setattr(collectors, "source_frame", lambda *args: pd.DataFrame([
        {"id":"event1","title":"Test disclosure", "publish_time":NOW.isoformat()}]))
    service.scan(spec,NOW)
    service.scan(spec,NOW)
    assert len(service.store.signals()) == 1
    assert len(service.store.events()) == 1
    assert service.store.signals()[0].tier == "radar"
    service.detect(NOW)
    assert service.store.signals()[0].state != "expired"


@pytest.mark.parametrize("value", [None,"", "N/A", "broken", "NaN", "inf"])
def test_unknown_portfolio_numbers_are_not_zero(value):
    assert optional_number(value) is None
