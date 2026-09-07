"""Chay swarm commodity_research_team_VN voi data pack tiem qua private_context.

Khac cac runner truoc o mot cho duy nhat nhung quyet dinh: no doc datapack.md va
truyen vao ``private_context``. ``runtime.py`` noi khoi do vao khoi grounding cho
**moi** worker — day la duong duy nhat de agent hang hoa co gia that, vi
``grounding.py`` khong nhan dien ten hang hoa (chi nhan .VN/.US/.HK/-USDT).

Chay (tu goc repo)::

    .venv/Scripts/python.exe agent/scripts/commodity_datapack.py oil_crude
    .venv/Scripts/python.exe agent/_run_commodity.py oil_crude --horizon "6 thang"
"""

import argparse
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
except Exception as exc:  # pragma: no cover - chi la tien nghi
    print("dotenv load warn:", exc, flush=True)

from scripts.commodity_datapack import ROUTES  # noqa: E402
from src.config import load_swarm_agent_config  # noqa: E402
from src.swarm.models import RunStatus, TaskStatus  # noqa: E402
from src.swarm.runtime import SwarmRuntime  # noqa: E402
from src.swarm.store import SwarmStore  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("commodity", help="ma mat hang trong ROUTES, vd oil_crude")
    p.add_argument("--horizon", default="6 thang")
    p.add_argument("--datapack", default=None, help="thu muc data pack; mac dinh tim theo ngay hom nay")
    p.add_argument("--timeout", type=int, default=7200)
    args = p.parse_args()

    if args.commodity not in ROUTES:
        print(f"[LOI] khong biet mat hang '{args.commodity}'.")
        return 1
    route = ROUTES[args.commodity]

    if args.datapack:
        pack_dir = Path(args.datapack)
    else:
        repo = HERE.parent
        candidates = sorted(repo.glob(f"_commodity_{args.commodity}_*"))
        if not candidates:
            print(f"[LOI] chua co data pack cho {args.commodity}. Chay truoc:")
            print(f"  .venv/Scripts/python.exe agent/scripts/commodity_datapack.py {args.commodity}")
            return 1
        pack_dir = candidates[-1]

    pack_md = pack_dir / "datapack.md"
    if not pack_md.exists():
        print(f"[LOI] khong thay {pack_md}")
        return 1
    private_context = pack_md.read_text(encoding="utf-8")
    print(f"data pack: {pack_md} ({len(private_context)} ky tu)", flush=True)

    base = HERE / ".swarm" / "runs"
    base.mkdir(parents=True, exist_ok=True)
    store = SwarmStore(base_dir=base)
    rt = SwarmRuntime(
        store=store,
        max_workers=int(os.getenv("SWARM_MAX_WORKERS", "4")),
        agent_config=load_swarm_agent_config(),
    )
    print("provider=", os.getenv("LANGCHAIN_PROVIDER"),
          "model=", os.getenv("LANGCHAIN_MODEL_NAME"), flush=True)

    run = rt.start_run(
        "commodity_research_team_VN",
        {
            "commodity": f"{route.label} ({args.commodity}, don vi {route.unit})",
            "horizon": args.horizon,
            "datapack_path": str(pack_dir),
            "vn_proxies": ", ".join(f"{s}.VN" for s in route.vn_proxies) or "(khong co ma proxy)",
        },
        include_shell_tools=True,
        private_context=private_context,
    )
    rid = run.id
    print("RUN_ID=", rid, flush=True)
    (HERE / f"_commodity_{args.commodity}_runid.txt").write_text(rid)

    seen: dict[str, TaskStatus] = {}
    t0 = time.time()
    while True:
        r = store.load_run(rid)
        if r is None:
            print("run not found yet", flush=True)
            time.sleep(5)
            continue
        for t in r.tasks:
            if seen.get(t.id) != t.status:
                seen[t.id] = t.status
                print(f"[{int(time.time() - t0):5d}s] task {t.id:22s} -> {t.status.value}", flush=True)
                if t.status == TaskStatus.completed and t.summary:
                    print(f"   summary: {t.summary[:300]}", flush=True)
        if r.status in (RunStatus.completed, RunStatus.failed,
                        getattr(RunStatus, "cancelled", RunStatus.failed)):
            print(f"\n=== RUN STATUS: {r.status.value} ===\n", flush=True)
            print("=== FINAL REPORT ===\n", flush=True)
            print(r.final_report or "(no final_report)", flush=True)
            art = base / rid / "artifacts"
            if art.exists():
                print("\n=== ARTIFACTS ===", flush=True)
                for f in sorted(art.iterdir()):
                    print(" ", f.name, f.stat().st_size, "bytes", flush=True)
            break
        if time.time() - t0 > args.timeout:
            print(f"TIMEOUT {args.timeout}s, aborting poll (run van chay nen)", flush=True)
            break
        time.sleep(10)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
