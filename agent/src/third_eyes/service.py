"""Monitoring lifecycle, persistent jobs and bounded local narration queue."""
from __future__ import annotations

import asyncio
import logging
import random
import threading
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.live.runtime.jobstore import JobStore
from src.live.runtime.scheduler import Job, Scheduler

from .agents import run_agents
from .collectors import collect, in_session, session_freshness, SourceSchemaError
from .detection import confirm, evaluate
from .models import FeatureSpec, Indicator, ResearchProtocol, Settings, Validation, SourceSpec, Rule, Signal, digest, utcnow
from .portfolio import read_portfolio
from .store import Store
from .lease import MonitorLease

logger = logging.getLogger("third_eyes")


def configure_rotating_log(root: Path, max_bytes: int, backup_count: int):
    target = (root / "third-eyes.log").resolve()
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == target:
            return handler
    handler = RotatingFileHandler(target, maxBytes=max_bytes, backupCount=backup_count,
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return handler


def load_settings(path):
    path = Path(path).resolve()
    settings = Settings.model_validate_json(path.read_text(encoding="utf-8-sig"))
    for source in settings.sources:
        if source.path:
            source.path = str((path.parent / source.path).resolve())
    settings.state_dir = str((path.parent / settings.state_dir).resolve())
    if settings.excel_directory:
        settings.excel_directory = str((path.parent / settings.excel_directory).resolve())
    settings.research_csv = {key: str((path.parent / value).resolve()) for key, value in settings.research_csv.items()}
    return settings


class Service:
    def __init__(self, settings: Settings, collector=collect, *, sleeper=time.sleep, random_fn=random.random):
        self.settings = settings
        self.store = Store(Path(settings.state_dir))
        self.collector = collector
        self.sleeper = sleeper
        self.random_fn = random_fn
        self.scheduler = Scheduler(self.fire, max_recheck_ms=1000)
        self.jobs = JobStore(self.store.root / "jobs.json")
        self.ai_task = None
        self.source_tasks = {}
        self.stopping = False
        self.detect_lock = threading.RLock()
        self.collect_slots = asyncio.Semaphore(2)
        self.lease = MonitorLease(self.store.root / "monitor.lock")
        self.log_handler = None
        for rule in settings.rules:
            self.store.register_rule(rule)
        for source in settings.sources:
            self.store.register_feature(FeatureSpec(id=source.indicator, indicator=source.indicator,
                                        family="threshold", unit=source.unit, description=source.id))

    def indicators(self):
        return [Indicator(id=s.indicator, domain=s.domain, group=s.group, unit=s.unit,
                          description=s.id, cadence_seconds=s.cadence_seconds,
                          max_age_seconds=s.max_age_seconds).model_dump(mode="json") for s in self.settings.sources]

    def refresh_portfolio(self):
        try:
            self.store.set("portfolio", read_portfolio(self.settings))
        except Exception as exc:
            self.store.set("portfolio", {"status": "unavailable", "positions": [],
                                         "error": type(exc).__name__,
                                         "detail": "Check export schema, selected account and file format"})

    def sync_company_sources(self):
        positions = self.store.get("portfolio", {}).get("positions", [])
        symbols = sorted(set(self.settings.watchlist) | {p["symbol"] for p in positions if p.get("symbol")})
        aggregate = next((s for s in self.settings.sources if s.id == "company_disclosures"), None)
        if aggregate is not None and symbols and aggregate.entity == "UNCONFIGURED":
            replacement = aggregate.model_copy(update={
                "kind": "news", "entity": "WATCHLIST", "unit": "event", "enabled": True,
                "entity_column": "symbol", "kwargs": {"symbols": symbols, "coverage_only": True},
            })
            self.settings.sources[self.settings.sources.index(aggregate)] = replacement
            previous = self.store.get("coverage:" + replacement.id, {})
            if previous.get("status") in {None, "disabled"}:
                self.store.set("coverage:" + replacement.id, {
                    "id": replacement.id, "domain": replacement.domain,
                    "indicator": replacement.indicator, "status": "pending",
                })
        existing = {s.id for s in self.settings.sources}
        for symbol in symbols:
            if not symbol.isalnum() or len(symbol) > 12:
                continue
            specs = [
                SourceSpec(id=f"company_{symbol}_price", kind="price", domain="company", indicator=f"company_{symbol}_price",
                           entity=symbol, unit="thousand_VND", group="price", value_column="close",
                           cadence_seconds=60, kwargs={"interval":"1m", "history_days":7,
                           "session_final_bar_close":"14:46"}, max_age_seconds=600),
                SourceSpec(id=f"company_{symbol}_volume", kind="price", domain="company", indicator=f"company_{symbol}_volume",
                           entity=symbol, unit="shares", group="liquidity", value_column="volume",
                           cadence_seconds=60, kwargs={"interval":"1m", "history_days":7,
                           "session_final_bar_close":"14:46"}, max_age_seconds=600),
                SourceSpec(id=f"company_{symbol}_profit", kind="fundamental", domain="company", indicator=f"company_{symbol}_profit",
                           entity=symbol, unit="VND", group="earnings", method="income_statement", date_column="period",
                           filter_column="id", filter_value="IS_NET_PROFIT_AFTER_TAX", kwargs={"period":"quarter"},
                           cadence_seconds=86400, max_age_seconds=86400*150),
                SourceSpec(id=f"company_{symbol}_news", kind="news", domain="company", indicator=f"company_{symbol}_news",
                           entity=symbol, unit="event", group="disclosures", date_column="publish_time", cadence_seconds=300),
            ]
            for source in specs:
                if source.id in existing:
                    continue
                self.settings.sources.append(source)
                if source.kind != "news":
                    window = 10 if source.kind == "fundamental" else 60
                    self.settings.rules.extend([
                        Rule(id=source.id+"_high", indicator=source.indicator, window=window, objective="up"),
                        Rule(id=source.id+"_low", indicator=source.indicator, window=window, side="low")])
                    for rule in self.settings.rules[-2:]:
                        self.store.register_rule(rule, reason="Portfolio/watchlist source")
                self.store.register_feature(FeatureSpec(id=source.indicator, indicator=source.indicator,
                                            family="threshold", unit=source.unit, description=source.id))
                if not self.store.get("coverage:" + source.id):
                    self.store.set("coverage:"+source.id, {"id":source.id,"domain":source.domain,
                                                          "indicator":source.indicator,"status":"pending"})
                self.scheduler.add_job(Job(source.id, int(utcnow().timestamp()*1000), f"interval:{source.cadence_seconds*1000}"))

    def research(self, now):
        import pandas as pd
        from .research import backtest
        for rule in self.settings.rules:
            path = self.settings.research_csv.get(rule.id)
            if not path:
                continue
            try:
                frame = pd.read_csv(path)
                for horizon in self.settings.research_horizons:
                    variant = rule.model_copy(update={"horizon": horizon})
                    self.store.register_rule(variant, reason="Configured research horizon")
                    protocol = ResearchProtocol(hypothesis_id=rule.id, family_id=rule.id,
                                                variant_id=variant.fingerprint)
                    report = backtest(frame, variant, protocol=protocol)
                    certificate = self.store.save_research_report(variant, report)
                    self.store.event("research", {"rule": variant.id, "horizon": horizon,
                                     "certificate_id": certificate, "eligible": report["eligible"],
                                     "as_of": now.isoformat()})
            except Exception as exc:
                self.store.event("research_error", {"rule":rule.id,"error":type(exc).__name__})

    def scan(self, source, now=None):
        now = now or utcnow()
        previous = self.store.get("coverage:" + source.id, {})
        retry_after = previous.get("retry_after")
        if retry_after and datetime.fromisoformat(retry_after) > now:
            return False
        last_error = None
        attempts = self.settings.retry_attempts
        for attempt in range(1, attempts + 1):
            try:
                if source.kind == "news":
                    self.scan_news(source, now)
                    meta = self.store.get("coverage:" + source.id, {})
                else:
                    observations, meta = self.collector(source, now)
                    if observations:
                        self.store.ingest(observations)
                    latest = max((o.observed_at for o in observations if o.closed), default=None)
                    meta.update(session_freshness(source, latest, now, self.settings.holidays))
                    if meta.get("session_fresh") is False:
                        meta["status"] = "stale"
                    elif meta.get("session_fresh") is True and observations:
                        meta["status"] = "available"
                meta.update(consecutive_failures=0, attempts=attempt, retry_after=None,
                            last_success_at=now.isoformat())
                self.store.set("coverage:" + source.id, meta)
                self.detect(now)
                return True
            except (Exception, SystemExit) as exc:
                last_error = exc
                retryable = not isinstance(exc, (SourceSchemaError, ValueError, SystemExit))
                if retryable and attempt < attempts:
                    delay = min(self.settings.retry_max_seconds,
                                self.settings.retry_base_seconds * (2 ** (attempt - 1)))
                    delay += self.settings.retry_jitter_seconds * self.random_fn()
                    logger.warning("source=%s attempt=%s/%s retry_in=%.3fs error=%s",
                                   source.id, attempt, attempts, delay, type(exc).__name__)
                    self.sleeper(delay)
                    continue
                break
        failures = int(previous.get("consecutive_failures", 0)) + 1
        circuit_open = failures >= self.settings.max_consecutive_failures
        retry_at = now + timedelta(seconds=self.settings.failure_cooldown_seconds) if circuit_open else None
        exc = last_error
        self.store.set("coverage:" + source.id, {
            "id": source.id, "domain": source.domain, "indicator": source.indicator,
            "status": "schema_mismatch" if isinstance(exc, SourceSchemaError) else
                      "backoff" if circuit_open else "unavailable",
            "columns": exc.columns if isinstance(exc, SourceSchemaError) else [],
            "missing_columns": exc.missing if isinstance(exc, SourceSchemaError) else [],
            "checked_at": now.isoformat(), "attempts": attempt,
            "consecutive_failures": failures,
            "retry_after": retry_at.isoformat() if retry_at else None,
            "last_success_at": previous.get("last_success_at"),
            "error": type(exc).__name__, "detail": str(exc)[:500]})
        logger.error("source=%s unavailable consecutive_failures=%s error=%s",
                     source.id, failures, type(exc).__name__)
        return False

    def scan_news(self, source, now):
        import pandas as pd
        from .collectors import source_frame, stamp
        frame = source_frame(source, now)
        required = {"id", "title", "publish_time"}
        if not required <= set(frame):
            raise ValueError("Missing company news fields: id/title/publish_time")
        for item in frame.to_dict("records"):
            if pd.isna(item.get("publish_time")) or pd.isna(item.get("id")):
                continue
            published = stamp(item["publish_time"])
            if not 0 <= (now-published).total_seconds() <= source.max_age_seconds:
                continue
            evidence = {key: str(item[key]) if pd.notna(item.get(key)) else None
                        for key in ("id", "title", "summary", "content", "publish_time", "source", "url")}
            if source.kwargs.get("coverage_only"):
                continue
            snapshot = self.store.document(evidence)
            entity = str(item.get(source.entity_column, source.entity)) if source.entity_column else source.entity
            signal = Signal(id=digest([source.id, evidence["id"]]), indicator=source.indicator,
                            entity=entity, domain="company", group="disclosures", observed_at=published,
                            detected_at=now, value=1, threshold=0, trend="new_disclosure", pattern="disclosure",
                            rule_id="new_disclosure", rule_version="1", snapshot=snapshot, source=source.id,
                            unit="event", source_detail=evidence,
                            limitations=["Qualitative disclosure; no statistical significance or direction assigned"])
            self.store.publish(signal)
        self.store.set("coverage:"+source.id, {"id":source.id,"indicator":source.indicator,"domain":"company",
                                               "status":"available","checked_at":now.isoformat(),"rows":len(frame)})

    def detect(self, now=None):
        with self.detect_lock:
            self._detect(now)

    def _detect(self, now=None):
        now = now or utcnow()
        candidates = []
        for source in self.settings.sources:
            coverage = self.store.get("coverage:" + source.id, {})
            if not source.enabled or coverage.get("status") != "available":
                continue
            checked = coverage.get("checked_at")
            if not checked or (now-datetime.fromisoformat(checked)).total_seconds() > max(2*source.cadence_seconds, 86400):
                continue
            entities = self.store.entities(source.indicator) if source.entity_column else [source.entity]
            for entity in entities:
                candidates.extend(self.detect_entity(source, entity, now))
        active_ids = {s.id for s in candidates}
        for previous in self.store.signals():
            if previous.pattern == "disclosure" and (now-previous.observed_at).total_seconds() <= 86400*5:
                active_ids.add(previous.id)
        for signal in confirm(candidates):
            self.store.publish(signal)
        for previous in self.store.signals():
            if previous.id not in active_ids and previous.state != "expired":
                previous.state, previous.tier = "expired", "radar"
                previous.confirmation_ids = []
                self.store.publish(previous)

    def detect_entity(self, source, entity, now):
        candidates = []
        history = self.store.history(source.indicator, entity, now)
        if source.closed_only:
            history = [o for o in history if o.closed]
        if not history:
            return []
        session = session_freshness(source, history[-1].observed_at, now, self.settings.holidays)
        if session["session_fresh"] is False:
            return []
        # Snapshot the exact as-of history, not just the latest fetched delta.
        window = max((r.window for r in self.settings.rules if r.indicator == source.indicator), default=60)
        history = history[-window-6:]
        snapshot = self.store.snapshot_rows([o.model_dump(mode="json") for o in history])
        effective_age = source.max_age_seconds
        if session["session_fresh"] is True:
            effective_age = max(effective_age, int((now-history[-1].published_at).total_seconds()) + 1)
        indicator = Indicator(id=source.indicator, domain=source.domain, group=source.group,
                              unit=source.unit, description=source.id, max_age_seconds=effective_age,
                              closed_only=source.closed_only)
        for original in self.settings.rules:
            if original.indicator != source.indicator:
                continue
            rule = original.model_copy(deep=True)
            registration = self.store.rule_registration(rule.id, rule.fingerprint)
            if registration and registration.status == "retired":
                continue
            # Certificates are informative in every state, but promotion also
            # requires an explicit registry transition to validated.
            certificate = self.store.research_report(rule.fingerprint, include_synthetic=False)
            report = certificate["report"] if certificate else None
            rule.validation = Validation.model_validate(report["validation"]) if report else None
            signal = evaluate(history, rule, indicator, snapshot, now)
            if signal:
                signal.rule_status = registration.status if registration else "candidate"
                positions = self.store.get("portfolio", {}).get("positions", [])
                affected = [p for p in positions if p["symbol"] == signal.entity]
                signal.portfolio = {"positions": affected, "as_of": self.store.get("portfolio", {}).get("as_of"),
                                    "scope": "direct" if affected else "context",
                                    "limitation": "Sector/macro transmission requires cited agent analysis"}
                candidates.append(signal)
        return candidates

    async def fire(self, job):
        now = utcnow()
        queue_age = max(0.0, (now.timestamp() * 1000 - job.next_run_at) / 1000)
        metrics = self.store.get("queue_age", {"latest": {}, "max_seconds": 0.0, "samples": 0})
        metrics["latest"][job.id] = queue_age
        metrics["max_seconds"] = max(float(metrics.get("max_seconds", 0)), queue_age)
        metrics["samples"] = int(metrics.get("samples", 0)) + 1
        metrics["updated_at"] = now.isoformat()
        self.store.set("queue_age", metrics)
        if job.id == "housekeeping":
            previous = self.store.get("heartbeat")
            if previous and (now-datetime.fromisoformat(previous)).total_seconds() > 180:
                self.store.event("gap", {"from": previous, "to": now.isoformat(), "reason": "monitoring interrupted"})
            self.store.set("heartbeat", now.isoformat())
            await asyncio.to_thread(self.refresh_portfolio)
            self.sync_company_sources()
            await asyncio.to_thread(self.detect, now)
            # Scheduler advances after callback; persist its next intended tick explicitly.
            job.next_run_at = int(now.timestamp()*1000) + 60000
            self.jobs.save(self.scheduler.jobs())
            week = f"{now.isocalendar().year}-{now.isocalendar().week}"
            if not in_session(now, self.settings.holidays) and self.store.get("research_week") != week:
                previous = self.source_tasks.get("research")
                if previous is None or previous.done():
                    self.store.set("research_week", week)
                    self.source_tasks["research"] = asyncio.create_task(asyncio.to_thread(self.research, now))
            return
        source = next(s for s in self.settings.sources if s.id == job.id)
        coverage = self.store.get("coverage:" + source.id, {})
        if coverage.get("retry_after") and datetime.fromisoformat(coverage["retry_after"]) > now:
            return
        if source.kind in {"price", "sector"} and not in_session(now, self.settings.holidays):
            # One post-close/weekend recovery read per date also catches late vendor updates.
            day_key = "outside:" + source.id
            slot = now.strftime("%Y-%m-%dT%H")
            if self.store.get(day_key) == slot:
                return
            self.store.set(day_key, slot)
        previous = self.source_tasks.get(source.id)
        if previous and not previous.done():
            return
        async def work():
            async with self.collect_slots:
                await asyncio.to_thread(self.scan, source, utcnow())
        self.source_tasks[source.id] = asyncio.create_task(work())

    async def narrate_once(self):
        """Process one bounded AI batch without affecting quantitative signals."""
        if not self.settings.ai_enabled:
            return None
        pending = [s for s in self.store.signals()
                   if s.ai_status == "pending" and s.state != "expired"][:3]
        if not pending:
            return None
        for signal in pending:
            signal.ai_status = "running"
            self.store.publish(signal)
        try:
            result = await run_agents(self.settings, self.store, pending)
            for old in pending:
                signal = self.store.signal(old.id)
                if signal is None or signal.snapshot != old.snapshot:
                    continue
                signal.ai_status = "completed" if result["status"] == "completed" else "failed"
                signal.analysis = result
                self.store.publish(signal)
            return result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for old in pending:
                signal = self.store.signal(old.id)
                if signal is None or signal.snapshot != old.snapshot:
                    continue
                signal.ai_status, signal.ai_error = "failed", type(exc).__name__
                self.store.publish(signal)
            return {"status": "failed", "error": type(exc).__name__}

    async def narrate(self):
        while not self.stopping:
            await asyncio.sleep(self.settings.ai_batch_seconds)
            await self.narrate_once()

    async def start(self):
        self.lease.acquire()
        try:
            await self._start()
        except BaseException:
            self.lease.release()
            raise

    async def _start(self):
        self.log_handler = configure_rotating_log(self.store.root, self.settings.log_max_bytes,
                                                  self.settings.log_backup_count)
        logger.info("Third Eyes monitor starting in observation-only mode")
        self.refresh_portfolio()
        self.sync_company_sources()
        for signal in self.store.signals():
            if signal.ai_status == "running":
                signal.ai_status, signal.ai_error = "pending", "Recovered interrupted local analysis"
                self.store.publish(signal, preserve_ai=False)
        existing = {j.id: j for j in self.jobs.load()}
        now_ms = int(utcnow().timestamp()*1000)
        for source in self.settings.sources:
            if not self.store.get("coverage:" + source.id):
                self.store.set("coverage:" + source.id, {"id": source.id, "indicator": source.indicator,
                               "domain": source.domain, "status": "pending" if source.enabled else "disabled"})
            if source.enabled:
                job = existing.get(source.id, Job(source.id, now_ms, f"interval:{source.cadence_seconds*1000}"))
                job.schedule = f"interval:{source.cadence_seconds*1000}"
                self.scheduler.add_job(job)
        self.scheduler.add_job(Job("housekeeping", now_ms, "interval:60000"))
        self.jobs.save(self.scheduler.jobs())
        self.scheduler.start()
        self.ai_task = asyncio.create_task(self.narrate())

    async def stop(self):
        self.stopping = True
        await self.scheduler.stop()
        if self.ai_task:
            self.ai_task.cancel()
            await asyncio.gather(self.ai_task, return_exceptions=True)
        await asyncio.gather(*self.source_tasks.values(), return_exceptions=True)
        self.jobs.save(self.scheduler.jobs())
        self.lease.release()
        if self.log_handler:
            logger.info("Third Eyes monitor stopped")
            self.log_handler.flush()
            self.log_handler.close()
            logger.removeHandler(self.log_handler)
            self.log_handler = None

    def health(self):
        heartbeat = self.store.get("heartbeat")
        age = (utcnow()-datetime.fromisoformat(heartbeat)).total_seconds() if heartbeat else None
        return {"status": "running" if age is not None and age < 180 else "offline",
                "heartbeat": heartbeat, "age_seconds": age,
                "model": self.settings.local_model or None, "ai_enabled": self.settings.ai_enabled,
                "coverage": self.store.coverage(), "queue_age": self.store.get("queue_age", {}),
                "observation_only": True}
