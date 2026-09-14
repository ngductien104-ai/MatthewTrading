"""Transactional event outbox and immutable, content-addressed Parquet evidence."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pandas as pd

from .models import FeatureSpec, Observation, Rule, RuleRegistration, Signal, Validation, digest, utcnow


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, default=str)


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "third-eyes.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY, indicator TEXT, entity TEXT, observed TEXT, published TEXT,
                    received TEXT, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS obs_series ON observations(indicator, entity, observed);
                CREATE TABLE IF NOT EXISTS signals (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, payload TEXT, created TEXT);
                CREATE TABLE IF NOT EXISTS feature_registry (
                    id TEXT, version TEXT, payload TEXT NOT NULL, created TEXT,
                    PRIMARY KEY(id, version));
                CREATE TABLE IF NOT EXISTS research_reports (
                    id TEXT PRIMARY KEY, rule_version TEXT, dataset_hash TEXT,
                    synthetic INTEGER NOT NULL, payload TEXT NOT NULL, created TEXT);
                CREATE INDEX IF NOT EXISTS research_rule ON research_reports(rule_version, created);
                CREATE TABLE IF NOT EXISTS rule_registry (
                    rule_id TEXT, rule_version TEXT, status TEXT, payload TEXT NOT NULL,
                    certificate_id TEXT, reason TEXT, updated TEXT,
                    PRIMARY KEY(rule_id, rule_version));
                CREATE TABLE IF NOT EXISTS rule_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, rule_id TEXT, rule_version TEXT,
                    from_status TEXT, to_status TEXT, certificate_id TEXT, reason TEXT, created TEXT);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def set(self, key, value):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, encode(value)))

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def coverage(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute(
                "SELECT payload FROM kv WHERE key LIKE 'coverage:%' ORDER BY key")]

    def prefix_values(self, prefix):
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM kv WHERE key LIKE ? ORDER BY key", (prefix + "%",)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def register_feature(self, feature: FeatureSpec) -> bool:
        payload = feature.model_dump(mode="json")
        with self.connect() as db:
            result = db.execute(
                "INSERT OR IGNORE INTO feature_registry VALUES (?,?,?,?)",
                (feature.id, feature.version, encode(payload), utcnow().isoformat()),
            )
        return bool(result.rowcount)

    def features(self):
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM feature_registry ORDER BY id, version").fetchall()
        return [json.loads(row[0]) for row in rows]

    def register_rule(self, rule: Rule, reason="Configured rule") -> RuleRegistration:
        now = utcnow().isoformat()
        payload = rule.model_dump(mode="json", exclude={"validation"})
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT payload FROM rule_registry WHERE rule_id=? AND rule_version=?",
                (rule.id, rule.fingerprint),
            ).fetchone()
            if row:
                return RuleRegistration.model_validate_json(row[0])
            record = RuleRegistration(rule_id=rule.id, rule_version=rule.fingerprint,
                                      rule=payload, reason=reason, updated_at=now)
            encoded = record.model_dump_json()
            db.execute("INSERT INTO rule_registry VALUES (?,?,?,?,?,?,?)",
                       (rule.id, rule.fingerprint, "candidate", encoded, None, reason, now))
            db.execute("INSERT INTO rule_transitions(rule_id,rule_version,from_status,to_status,certificate_id,reason,created) "
                       "VALUES (?,?,?,?,?,?,?)",
                       (rule.id, rule.fingerprint, None, "candidate", None, reason, now))
        return record

    def rule_registration(self, rule_id, rule_version=None):
        query = "SELECT payload FROM rule_registry WHERE rule_id=?"
        params = [rule_id]
        if rule_version:
            query += " AND rule_version=?"
            params.append(rule_version)
        query += " ORDER BY updated DESC LIMIT 1"
        with self.connect() as db:
            row = db.execute(query, params).fetchone()
        return RuleRegistration.model_validate_json(row[0]) if row else None

    def rules(self):
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM rule_registry ORDER BY rule_id, updated DESC").fetchall()
        return [RuleRegistration.model_validate_json(row[0]) for row in rows]

    def save_research_report(self, rule: Rule, report: dict) -> str:
        validation = report.get("validation", {})
        report_id = digest(report)
        created = utcnow().isoformat()
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO research_reports VALUES (?,?,?,?,?,?)",
                       (report_id, rule.fingerprint, validation.get("dataset_hash", ""),
                        int(bool(validation.get("synthetic"))), encode(report), created))
        self.set("research:" + rule.fingerprint, report)
        return report_id

    def research_report(self, rule_version, *, include_synthetic=True):
        query = "SELECT id,payload FROM research_reports WHERE rule_version=?"
        params = [rule_version]
        if not include_synthetic:
            query += " AND synthetic=0"
        query += " ORDER BY created DESC LIMIT 1"
        with self.connect() as db:
            row = db.execute(query, params).fetchone()
        if row:
            return {"id": row[0], "report": json.loads(row[1])}
        legacy = self.get("research:" + rule_version)
        return {"id": digest(legacy), "report": legacy} if legacy else None

    def transition_rule(self, rule_id, rule_version, to_status, reason, certificate_id=None):
        allowed = {"candidate": {"shadow", "retired"},
                   "shadow": {"validated", "retired"},
                   "validated": {"retired"}, "retired": set()}
        if not reason.strip():
            raise ValueError("Rule transition requires a reason")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM rule_registry WHERE rule_id=? AND rule_version=?",
                             (rule_id, rule_version)).fetchone()
            if not row:
                raise KeyError("Unknown rule version")
            record = RuleRegistration.model_validate_json(row[0])
            if to_status not in allowed[record.status]:
                raise ValueError(f"Invalid rule transition: {record.status} -> {to_status}")
            if to_status == "validated":
                if not certificate_id:
                    raise ValueError("Validation requires an explicit certificate_id")
                cert = db.execute("SELECT payload,synthetic FROM research_reports WHERE id=? AND rule_version=?",
                                  (certificate_id, rule_version)).fetchone()
                if not cert:
                    raise ValueError("Certificate does not match this rule version")
                report = json.loads(cert[0])
                validation = Validation.model_validate(report.get("validation", {}))
                if (cert[1] or not report.get("eligible") or not validation.eligible
                        or validation.rule_version != rule_version):
                    raise ValueError("Synthetic or ineligible certificate cannot validate a rule")
            now = utcnow().isoformat()
            updated = record.model_copy(update={"status": to_status, "certificate_id": certificate_id,
                                                "reason": reason, "updated_at": now})
            db.execute("UPDATE rule_registry SET status=?,payload=?,certificate_id=?,reason=?,updated=? "
                       "WHERE rule_id=? AND rule_version=?",
                       (to_status, updated.model_dump_json(), certificate_id, reason, now,
                        rule_id, rule_version))
            db.execute("INSERT INTO rule_transitions(rule_id,rule_version,from_status,to_status,certificate_id,reason,created) "
                       "VALUES (?,?,?,?,?,?,?)", (rule_id, rule_version, record.status, to_status,
                                                  certificate_id, reason, now))
        self.event("rule_transition", updated.model_dump(mode="json"))
        return updated

    def rule_transitions(self, rule_id, rule_version):
        with self.connect() as db:
            rows = db.execute("SELECT from_status,to_status,certificate_id,reason,created "
                              "FROM rule_transitions WHERE rule_id=? AND rule_version=? ORDER BY id",
                              (rule_id, rule_version)).fetchall()
        return [{"from": r[0], "to": r[1], "certificate_id": r[2],
                 "reason": r[3], "created": r[4]} for r in rows]

    def ingest(self, observations: list[Observation]) -> str:
        if not observations:
            raise ValueError("empty observation batch")
        rows = [o.model_dump(mode="json") for o in observations]
        changed = []
        with self.connect() as db:
            for row in rows:
                identity = digest({k: v for k, v in row.items() if k != "received_at"})
                result = db.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?,?)",
                                    (identity, row["indicator"], row["entity"], row["observed_at"],
                                     row["published_at"], row["received_at"], encode(row)))
                if result.rowcount:
                    changed.append(row)
        # Archive deltas, not a full ten-year download on every polling tick.
        return self.snapshot_rows(changed) if changed else ""

    def snapshot_rows(self, rows):
        snapshot = digest(rows)
        target = self.root / "snapshots" / f"{snapshot}.parquet"
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            temp = target.with_suffix(f".{uuid.uuid4().hex}.tmp")
            with duckdb.connect() as conn:
                conn.register("evidence", pd.DataFrame(rows))
                conn.execute("COPY evidence TO ? (FORMAT PARQUET)", [str(temp)])
            os.replace(temp, target)
        return snapshot

    def document(self, value):
        key = digest(value)
        directory = self.root / "snapshots"
        directory.mkdir(exist_ok=True)
        target = directory / f"{key}.json"
        if not target.exists():
            temp = target.with_suffix(f".{uuid.uuid4().hex}.tmp")
            temp.write_text(encode(value), encoding="utf-8")
            os.replace(temp, target)
        return key

    def evidence(self, key):
        import re
        if not re.fullmatch(r"[a-f0-9]{64}", key):
            return None
        doc = self.root / "snapshots" / f"{key}.json"
        if doc.exists():
            return json.loads(doc.read_text(encoding="utf-8"))
        parquet = doc.with_suffix(".parquet")
        if parquet.exists():
            with duckdb.connect() as db:
                frame = db.execute("SELECT * FROM read_parquet(?)", [str(parquet)]).df()
                return json.loads(frame.to_json(orient="records", date_format="iso"))
        return None

    def history(self, indicator, entity, as_of=None, *, source=None) -> list[Observation]:
        as_of = as_of or utcnow()
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM observations WHERE indicator=? AND entity=?",
                              (indicator, entity)).fetchall()
        latest = {}
        for row in rows:
            obs = Observation.model_validate_json(row[0])
            if source is not None and obs.source != source:
                continue
            if obs.published_at > as_of or obs.received_at > as_of:
                continue
            previous = latest.get(obs.observed_at)
            if previous is None or (obs.published_at, obs.received_at) > (previous.published_at, previous.received_at):
                latest[obs.observed_at] = obs
        return [latest[t] for t in sorted(latest)]

    def entities(self, indicator):
        with self.connect() as db:
            return [row[0] for row in db.execute("SELECT DISTINCT entity FROM observations WHERE indicator=?", (indicator,))]

    def signals(self) -> list[Signal]:
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM signals ORDER BY rowid DESC").fetchall()
        return [Signal.model_validate_json(row[0]) for row in rows]

    def signal(self, signal_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM signals WHERE id=?", (signal_id,)).fetchone()
        return Signal.model_validate_json(row[0]) if row else None

    def publish(self, signal: Signal, *, preserve_ai=True) -> bool:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM signals WHERE id=?", (signal.id,)).fetchone()
            if row:
                previous = Signal.model_validate_json(row[0])
                signal.acknowledged_at = previous.acknowledged_at
                # Quantitative polling must not reset completed/in-flight narration.
                if preserve_ai and signal.ai_status == "pending" and previous.snapshot == signal.snapshot:
                    signal.ai_status, signal.analysis = previous.ai_status, previous.analysis
                    signal.ai_error = previous.ai_error
                old = previous.model_dump(exclude={"detected_at", "state"})
                new = signal.model_dump(exclude={"detected_at", "state"})
                if old == new and (previous.state == "expired") == (signal.state == "expired"):
                    return False
                signal.state = "expired" if signal.state == "expired" else "updated"
            payload = signal.model_dump(mode="json")
            db.execute("INSERT OR REPLACE INTO signals VALUES (?,?)", (signal.id, encode(payload)))
            db.execute("INSERT INTO events(kind,payload,created) VALUES (?,?,?)",
                       ("signal", encode(payload), utcnow().isoformat()))
        return True

    def acknowledge(self, signal_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM signals WHERE id=?", (signal_id,)).fetchone()
            if not row:
                return None
            payload = json.loads(row[0])
            if not payload["acknowledged_at"]:
                payload["acknowledged_at"] = utcnow().isoformat()
                db.execute("UPDATE signals SET payload=? WHERE id=?", (encode(payload), signal_id))
                db.execute("INSERT INTO events(kind,payload,created) VALUES (?,?,?)",
                           ("ack", encode(payload), utcnow().isoformat()))
            return payload

    def events(self, after=0, limit=200):
        with self.connect() as db:
            rows = db.execute("SELECT id,kind,payload,created FROM events WHERE id>? ORDER BY id LIMIT ?",
                              (after, limit)).fetchall()
        return [{"id": row[0], "event": row[1], "data": json.loads(row[2]), "created": row[3]} for row in rows]

    def event(self, kind, data):
        with self.connect() as db:
            db.execute("INSERT INTO events(kind,payload,created) VALUES (?,?,?)",
                       (kind, encode(data), utcnow().isoformat()))
