"""Run one isolated Third Eyes Swarm UAT against the configured local model."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from src.third_eyes.models import Signal, digest, utcnow
from src.third_eyes.service import Service, load_settings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="../third-eyes.json")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--domain", choices=("macro", "market", "sector", "company"),
                        default="company")
    parser.add_argument("--entity", default="FPT")
    args = parser.parse_args()

    configured = load_settings(Path(args.config))
    state_dir = Path(args.state_dir).resolve()
    forbidden = {
        Path(configured.state_dir).resolve(),
        (Path(args.config).resolve().parent / ".third-eyes-shadow").resolve(),
    }
    if state_dir in forbidden:
        parser.error("P3 UAT state must be isolated from production and shadow state")
    if state_dir.exists() and any(state_dir.iterdir()):
        parser.error("P3 UAT state directory must be new or empty")

    settings = configured.model_copy(update={
        "state_dir": str(state_dir),
        "sources": [],
        "rules": [],
        "excel_directory": None,
        "ai_enabled": True,
    })
    service = Service(settings)
    now = utcnow()
    evidence = {
        "contract": "third-eyes-p3-uat-v1",
        "uat": True,
        "production": False,
        "entity": args.entity,
        "domain": args.domain,
        "indicator": "uat_evidence_integrity",
        "observed_at": now.isoformat(),
        "value": 100.0,
        "threshold": 95.0,
        "threshold_unit": "uat_points",
        "fact": "Đây là tín hiệu giả lập để nghiệm thu luồng giải thích, không phải tín hiệu đầu tư.",
        "limitations": ["Dữ liệu UAT giả lập", "Không được dùng để ra quyết định đầu tư"],
    }
    snapshot = service.store.document(evidence)
    candidate = Signal(
        id=digest({"contract": evidence["contract"], "snapshot": snapshot}),
        indicator="uat_evidence_integrity",
        entity=args.entity,
        domain=args.domain,
        group="uat",
        observed_at=now,
        detected_at=now,
        value=100.0,
        threshold=95.0,
        feature_value=100.0,
        threshold_unit="uat_points",
        trend="uat_only",
        pattern="evidence_contract",
        rule_id="p3_uat_only",
        rule_version="uat-v1",
        rule_status="candidate",
        snapshot=snapshot,
        source="local_uat_fixture",
        unit="uat_points",
        source_detail={"production": False, "synthetic": True},
        tier="radar",
        severity="watch",
        direction="mixed",
        limitations=evidence["limitations"],
    )
    service.store.publish(candidate)
    result = asyncio.run(service.narrate_once())
    persisted = service.store.signal(candidate.id)
    output = {
        "mode": "p3_swarm_uat",
        "production": False,
        "fincept": False,
        "state_dir": str(state_dir),
        "signal_id": candidate.id,
        "snapshot": snapshot,
        "signal_preserved": persisted is not None and persisted.state != "expired",
        "ai_status": persisted.ai_status if persisted else "missing",
        "ai_error": persisted.ai_error if persisted else "missing",
        "result": result,
    }
    target = state_dir / "uat-report.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if result and result.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
