"""Source/readiness audit from configuration and local evidence; no vendor calls."""
from collections import Counter
from datetime import datetime
from pathlib import Path

from .models import utcnow
from .collectors import session_freshness


def inventory(settings, store, now=None):
    now = now or utcnow()
    items = []
    configured = {source.indicator for source in settings.sources}
    for source in settings.sources:
        coverage = store.get("coverage:" + source.id, {})
        status = coverage.get("status", "pending")
        checked = coverage.get("checked_at")
        check_age = None
        if checked:
            try:
                timestamp = datetime.fromisoformat(checked)
                if timestamp.tzinfo is None:
                    raise ValueError("Naive coverage timestamp")
                check_age = (now - timestamp).total_seconds()
            except (ValueError, TypeError):
                status = "unverified"
        if status == "available" and (check_age is None or check_age < 0):
            status = "unverified"
        elif status == "available" and check_age > max(2 * source.cadence_seconds, 86400):
            status = "stale"
        if not source.enabled:
            status = "disabled"
        elif source.kind == "csv" and (not source.path or not Path(source.path).is_file()):
            status = "missing"
        entities = store.entities(source.indicator) if source.entity_column else [source.entity]
        rules = [rule for rule in settings.rules if rule.indicator == source.indicator]
        series = []
        for entity in entities:
            rows = [row for row in store.history(source.indicator, entity, now, source=source.id)
                    if row.closed or not source.closed_only]
            latest = max((row.published_at for row in rows), default=None)
            age = (now - latest).total_seconds() if latest else None
            session = session_freshness(source, latest, now, settings.holidays)
            checks = []
            for rule in rules:
                # Mirrors the detector's conservative history requirement.
                required = rule.window + 6
                checks.append({"rule_id": rule.id, "family": rule.family,
                               "observations_required": required,
                               "observations_available": len(rows),
                               "history_sufficient": len(rows) >= required})
            series.append({"entity": entity, "observations": len(rows),
                           "first_observed": min((r.observed_at.isoformat() for r in rows), default=None),
                           "last_observed": max((r.observed_at.isoformat() for r in rows), default=None),
                           "publication_age_seconds": age,
                           "fresh": age is not None and 0 <= age <= source.max_age_seconds,
                           **session,
                           "rules": checks})
        reasons = []
        if status != "available":
            reasons.append(status)
        if source.kind != "news":
            if not series or any(not s["observations"] for s in series):
                reasons.append("missing_history")
            if any(s["observations"] and not s["fresh"] for s in series):
                reasons.append("stale_history")
            if any(s["session_fresh"] is False for s in series):
                reasons.append("missing_latest_session")
            if not rules:
                reasons.append("no_rules")
            if any(not r["history_sufficient"] for s in series for r in s["rules"]):
                reasons.append("insufficient_history")
        items.append({"id": source.id, "domain": source.domain, "indicator": source.indicator,
                      "entity": source.entity, "kind": source.kind, "unit": source.unit,
                      "enabled": source.enabled, "status": status, "checked_at": checked,
                      "check_age_seconds": check_age, "cadence_seconds": source.cadence_seconds,
                      "max_age_seconds": source.max_age_seconds,
                      "columns": coverage.get("columns", []),
                      "schema": {"date": source.date_column, "value": source.value_column,
                                 "published": source.published_column, "entity": source.entity_column},
                      "series": series, "ready_for_detection": not reasons,
                      "gaps": list(dict.fromkeys(reasons)),
                      "limitation": "Readiness is not backtest certification; no live query performed"})
    return {"schema_version": "1", "as_of": now.isoformat(), "live_query_performed": False,
            "items": items, "summary": dict(Counter(item["status"] for item in items)),
            "orphan_rules": [r.id for r in settings.rules if r.indicator not in configured]}
