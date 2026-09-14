"""python -m src.third_eyes --help"""
from __future__ import annotations

import argparse
import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd

from .service import Service, load_settings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Third Eyes local monitoring and replay")
    parser.add_argument("--config", default="third-eyes.json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create explicit source/rule configuration")
    scan = sub.add_parser("scan", help="Collect configured sources once; no LLM calls")
    scan.add_argument("--source", action="append", help="Only collect this source ID; repeatable")
    sub.add_parser("inventory", help="Audit configured sources and local history without vendor calls")
    sub.add_parser("status")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8790)
    research = sub.add_parser("backtest")
    research.add_argument("--rule", required=True)
    research.add_argument("--csv", required=True)
    research.add_argument("--horizons", default="1,5,20")
    research.add_argument("--hypothesis-id")
    research.add_argument("--family-id")
    research.add_argument("--variants-tested", type=int, default=1)
    research.add_argument("--holdout-id", default="")
    research.add_argument("--multiple-testing-method", choices=("single_hypothesis", "bonferroni"),
                          default="single_hypothesis")
    research.add_argument("--synthetic", action="store_true")
    dataset = sub.add_parser("dataset", help="Build a point-in-time research CSV from the local store")
    dataset.add_argument("--indicator", required=True)
    dataset.add_argument("--entity", required=True)
    dataset.add_argument("--target-entity", required=True)
    dataset.add_argument("--target-csv", required=True)
    dataset.add_argument("--output", required=True)
    dataset.add_argument("--target-time", default="time")
    dataset.add_argument("--target-close", default="close")
    dataset.add_argument("--horizons", default="1,5,20")
    dataset.add_argument("--adjusted-target", action="store_true")
    dataset.add_argument("--historical-universe", action="store_true")
    dataset.add_argument("--synthetic", action="store_true")
    sub.add_parser("rules", help="List persistent rule lifecycle state")
    transition = sub.add_parser("rule-transition", help="Advance or retire a registered rule")
    transition.add_argument("--rule", required=True)
    transition.add_argument("--version")
    transition.add_argument("--to", required=True, choices=("shadow", "validated", "retired"))
    transition.add_argument("--reason", required=True)
    transition.add_argument("--certificate-id")
    replay = sub.add_parser("replay")
    replay.add_argument("--jsonl", required=True, help="Canonical Observation records, ordered by received_at")
    replay.add_argument("--output", required=True, help="New isolated replay directory")
    sub.add_parser("openapi")
    args = parser.parse_args(argv)
    path = Path(args.config)
    if args.command == "init":
        from .defaults import default_settings
        with path.open("x", encoding="utf-8") as handle:
            handle.write(default_settings().model_dump_json(indent=2))
        print(str(path.resolve()))
        return 0
    settings = load_settings(path)
    service = Service(settings)
    if args.command == "scan":
        selected = set(args.source or [])
        unknown = selected - {s.id for s in settings.sources}
        if unknown:
            parser.error("Unknown source IDs: " + ", ".join(sorted(unknown)))
        service.refresh_portfolio()
        for source in settings.sources:
            if source.enabled and (not selected or source.id in selected):
                service.scan(source)
        print(json.dumps(service.health(), ensure_ascii=False, indent=2))
    elif args.command == "inventory":
        from .inventory import inventory
        print(json.dumps(inventory(settings, service.store), ensure_ascii=False, indent=2))
    elif args.command == "status":
        print(json.dumps(service.health(), ensure_ascii=False, indent=2))
    elif args.command == "backtest":
        from .models import ResearchProtocol
        from .research import backtest
        rule = next((r for r in settings.rules if r.id == args.rule), None)
        if rule is None:
            parser.error("Unknown rule")
        frame = pd.read_csv(args.csv)
        reports = []
        for horizon in [int(v) for v in args.horizons.split(",")]:
            variant = rule.model_copy(update={"horizon": horizon})
            service.store.register_rule(variant, reason="CLI research horizon")
            protocol = ResearchProtocol(
                hypothesis_id=args.hypothesis_id or rule.id,
                family_id=args.family_id or rule.id,
                variant_id=variant.fingerprint,
                variants_tested=args.variants_tested,
                holdout_id=args.holdout_id,
                multiple_testing_method=args.multiple_testing_method,
                synthetic=args.synthetic,
            )
            report = backtest(frame, variant, protocol=protocol)
            certificate = service.store.save_research_report(variant, report)
            reports.append({"certificate_id": certificate, "rule_version": variant.fingerprint,
                            **report})
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    elif args.command == "dataset":
        from .datasets import build_dataset, write_dataset
        from .models import FeatureSpec
        source = next((s for s in settings.sources if s.indicator == args.indicator), None)
        if source is None:
            parser.error("Unknown indicator")
        feature = FeatureSpec(id=args.indicator, indicator=args.indicator, unit=source.unit,
                              description=source.id)
        service.store.register_feature(feature)
        history = service.store.history(args.indicator, args.entity)
        frame, manifest = build_dataset(
            history, pd.read_csv(args.target_csv), feature, entity=args.entity,
            target_entity=args.target_entity, target_time=args.target_time,
            target_close=args.target_close,
            horizons=[int(v) for v in args.horizons.split(",")],
            adjusted_target=args.adjusted_target,
            historical_universe=args.historical_universe, synthetic=args.synthetic,
        )
        output, manifest_path = write_dataset(frame, manifest, Path(args.output))
        print(json.dumps({"dataset": str(output), "manifest": str(manifest_path),
                          **manifest.model_dump(mode="json")}, ensure_ascii=False, indent=2))
    elif args.command == "rules":
        print(json.dumps([r.model_dump(mode="json") for r in service.store.rules()],
                         ensure_ascii=False, indent=2))
    elif args.command == "rule-transition":
        registration = service.store.rule_registration(args.rule, args.version)
        if registration is None:
            parser.error("Unknown rule/version")
        updated = service.store.transition_rule(
            registration.rule_id, registration.rule_version, args.to, args.reason,
            certificate_id=args.certificate_id,
        )
        print(updated.model_dump_json(indent=2))
    elif args.command == "replay":
        from .models import Observation
        output = Path(args.output)
        if output.exists():
            parser.error("Replay output must be a new directory")
        replay_service = Service(settings.model_copy(update={"state_dir": str(output.resolve()), "ai_enabled": False}))
        records = [Observation.model_validate_json(line) for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]
        ordered = sorted(records, key=lambda o: o.received_at)
        if records != ordered:
            parser.error("Replay records must be ordered by received_at")
        from itertools import groupby
        for when, batch in groupby(records, key=lambda o: o.received_at):
            rows = list(batch)
            replay_service.store.ingest(rows)
            for source in settings.sources:
                if any(o.indicator == source.indicator and o.entity == source.entity for o in rows):
                    replay_service.store.set("coverage:" + source.id,
                                             {"status": "available", "checked_at": when.isoformat()})
            replay_service.detect(when)
        print(json.dumps({"signals": len(replay_service.store.signals()), "output": str(output.resolve())}))
    else:
        from fastapi import FastAPI, Header, HTTPException
        from .api import router

        async def auth(authorization: str | None = Header(None)):
            token = os.getenv("THIRD_EYES_TOKEN", "")
            if not token or not secrets.compare_digest(authorization or "", "Bearer " + token):
                raise HTTPException(401, "Invalid monitor token")

        @asynccontextmanager
        async def lifespan(app):
            await service.start()
            try:
                yield
            finally:
                await service.stop()

        app = FastAPI(title="Third Eyes", version="1.0.0", lifespan=lifespan)
        app.include_router(router(service, auth))
        if args.command == "openapi":
            print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))
        else:
            if not os.getenv("THIRD_EYES_TOKEN"):
                parser.error("Set THIRD_EYES_TOKEN before starting the API")
            import uvicorn
            uvicorn.run(app, host="127.0.0.1", port=args.port, workers=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
