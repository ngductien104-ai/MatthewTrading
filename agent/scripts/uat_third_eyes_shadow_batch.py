"""Evaluate a diverse batch of real shadow signals without writing to shadow state."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
from pathlib import Path

import duckdb

from src.third_eyes.models import Signal
from src.third_eyes.service import Service, load_settings


def read_snapshot(root: Path, snapshot: str):
    if not re.fullmatch(r"[a-f0-9]{64}", snapshot):
        return None
    document = root / "snapshots" / f"{snapshot}.json"
    if document.exists():
        return json.loads(document.read_text(encoding="utf-8"))
    parquet = document.with_suffix(".parquet")
    if parquet.exists():
        with duckdb.connect() as db:
            frame = db.execute("SELECT * FROM read_parquet(?)", [str(parquet)]).df()
        return json.loads(frame.to_json(orient="records", date_format="iso"))
    return None


def read_shadow(root: Path):
    database = root / "third-eyes.sqlite3"
    if not database.exists():
        raise FileNotFoundError(f"Shadow database not found: {database}")
    uri = database.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        signals = [Signal.model_validate_json(row[0]) for row in db.execute(
            "SELECT payload FROM signals ORDER BY rowid DESC"
        )]
        coverage = [json.loads(row[0]) for row in db.execute(
            "SELECT payload FROM kv WHERE key LIKE 'coverage:%' ORDER BY key"
        )]
        row = db.execute("SELECT payload FROM kv WHERE key='portfolio'").fetchone()
        portfolio = json.loads(row[0]) if row else {}
    return signals, coverage, portfolio


def diverse_active(signals, limit: int):
    active = [signal for signal in signals if signal.state != "expired"]
    selected, seen_ids, seen_groups = [], set(), set()
    # Prefer different analytical groups before filling with another entity.
    for signal in active:
        if signal.group in seen_groups:
            continue
        selected.append(signal)
        seen_ids.add(signal.id)
        seen_groups.add(signal.group)
        if len(selected) == limit:
            return selected
    seen_entity_groups = {(signal.entity, signal.group) for signal in selected}
    for signal in active:
        key = (signal.entity, signal.group)
        if signal.id in seen_ids or key in seen_entity_groups:
            continue
        selected.append(signal)
        seen_entity_groups.add(key)
        if len(selected) == limit:
            return selected
    return selected


def evidence_projection(value, tail_rows: int = 12):
    """Bound context while retaining the original content hash as provenance."""
    if isinstance(value, list) and len(value) > tail_rows:
        return {
            "projection": "tail_rows",
            "total_rows": len(value),
            "omitted_rows": len(value) - tail_rows,
            "rows": value[-tail_rows:],
        }
    return {"projection": "complete", "value": value}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="../third-eyes.json")
    parser.add_argument("--shadow-state", default="../.third-eyes-shadow")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--limit", type=int, default=3, choices=(2, 3))
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    configured = load_settings(config_path)
    shadow_root = Path(args.shadow_state).resolve()
    state_dir = Path(args.state_dir).resolve()
    forbidden = {Path(configured.state_dir).resolve(), shadow_root}
    if any(state_dir == root or state_dir.is_relative_to(root) for root in forbidden):
        parser.error("Batch UAT state must be isolated from production and shadow state")
    if state_dir.exists() and any(state_dir.iterdir()):
        parser.error("Batch UAT state directory must be new or empty")

    shadow_signals, coverage, portfolio = read_shadow(shadow_root)
    selected = diverse_active(shadow_signals, args.limit)
    if len(selected) < args.limit:
        parser.error(f"Need {args.limit} diverse active shadow signals; found {len(selected)}")
    missing = [signal.snapshot for signal in selected
               if read_snapshot(shadow_root, signal.snapshot) is None]
    if missing:
        parser.error("Missing shadow snapshots: " + ", ".join(missing))

    settings = configured.model_copy(update={
        "state_dir": str(state_dir),
        "sources": [],
        "rules": [],
        "excel_directory": None,
        "ai_enabled": True,
    })
    service = Service(settings)
    for item in coverage:
        if item.get("id"):
            service.store.set("coverage:" + item["id"], item)
    if portfolio:
        service.store.set("portfolio", portfolio)

    imported = []
    for signal in selected:
        original_snapshot = signal.snapshot
        snapshot = service.store.document({
            "contract": "third-eyes-shadow-import-v1",
            "synthetic": False,
            "shadow_snapshot_id": original_snapshot,
            "shadow_signal_id": signal.id,
            "evidence": evidence_projection(read_snapshot(shadow_root, original_snapshot)),
        })
        source_detail = dict(signal.source_detail)
        source_detail.update({"uat_import": True, "shadow_snapshot_id": original_snapshot})
        candidate = signal.model_copy(deep=True, update={
            "snapshot": snapshot,
            "source_detail": source_detail,
            "ai_status": "pending",
            "ai_error": None,
            "analysis": None,
        })
        service.store.publish(candidate)
        imported.append({
            "signal_id": candidate.id,
            "entity": candidate.entity,
            "indicator": candidate.indicator,
            "domain": candidate.domain,
            "original_snapshot": original_snapshot,
            "uat_snapshot": snapshot,
        })

    result = asyncio.run(service.narrate_once())
    persisted = [service.store.signal(item["signal_id"]) for item in imported]
    output = {
        "mode": "p3_shadow_batch_uat",
        "production": False,
        "fincept": False,
        "shadow_open_mode": "sqlite_ro",
        "shadow_state": str(shadow_root),
        "state_dir": str(state_dir),
        "signals": imported,
        "signals_preserved": all(signal is not None and signal.state != "expired"
                                 for signal in persisted),
        "ai_statuses": {signal.id: signal.ai_status for signal in persisted if signal},
        "result": result,
    }
    target = state_dir / "uat-report.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if result and result.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
