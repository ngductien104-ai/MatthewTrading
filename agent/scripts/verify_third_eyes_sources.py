"""One-shot source verification; no scheduler, LLM, portfolio or terminal startup."""
import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.third_eyes.inventory import inventory
from src.third_eyes.models import utcnow
from src.third_eyes.service import Service, load_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source", action="append")
    args = parser.parse_args()
    settings = load_settings(args.config)
    service = Service(settings)
    service.refresh_portfolio()
    service.sync_company_sources()
    selected = set(args.source or [])
    unknown = selected - {s.id for s in settings.sources}
    if unknown:
        parser.error(f"Unknown source IDs: {sorted(unknown)}")
    started = utcnow().isoformat()
    versions = {}
    for package in ("vnstock", "vnstock_data", "vnai"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = None
    results = []
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    for source in settings.sources:
        if not source.enabled or (selected and source.id not in selected):
            continue
        print(f"Checking {source.id} ({source.domain})", flush=True)
        service.scan(source)
        meta = service.store.get("coverage:" + source.id, {})
        results.append(meta)
        print(f"  {meta.get('status')}: {meta.get('rows', 0)} rows; {meta.get('detail', '')[:250]}", flush=True)
        # Checkpoint after every source so a slow later provider does not lose evidence.
        output.write_text(json.dumps({"started_at": started, "updated_at": utcnow().isoformat(),
                                     "mode": "one_shot", "versions": versions, "results": results},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"started_at": started, "completed_at": utcnow().isoformat(),
              "mode": "one_shot", "versions": versions, "results": results,
              "inventory": inventory(settings, service.store)}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {output.resolve()}", flush=True)


if __name__ == "__main__":
    main()
