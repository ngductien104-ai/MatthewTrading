#!/usr/bin/env python3
"""Preflight check for the Vietnamese data stack — run this before a long analysis.

Answers, in one command, the four questions that actually go wrong:

1. Is the vnstock licence live? (The key gets rotated, and ``auth_state.json`` is
   a 60-minute cache that keeps saying "silver" long after a key is revoked, so
   the tier is read from ``vnai.get_user_tier()``.)
2. Is the DataPro desktop up? Without it there is no reference price and no
   foreign / proprietary flow.
3. Is the macro backend answering? It goes down for stretches on its own.
4. Does swarm grounding actually load real prices for a ``.VN`` symbol? This is
   the check that would have caught VN presets running on training-data prices.

Usage (from the repo root)::

    .venv/Scripts/python.exe agent/scripts/vn_preflight.py

Exit code is 0 when every truth source needed for equity work is live, 1 when
something that blocks analysis is down.
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OK, BAD, WARN = "[OK]  ", "[DOWN]", "[WARN]"


def main() -> int:
    import vndata
    from src.swarm import grounding

    print("=" * 66)
    print("KIEM TRA NGUON DU LIEU VIET NAM")
    print("=" * 66)

    health = vndata.health()
    blocking = []

    tier = health["tier"]
    tier_name = tier.get("tier") if isinstance(tier, dict) else str(tier)
    if tier_name in {"silver", "golden", "diamond", "bronze"}:
        limits = tier.get("limits", {}) if isinstance(tier, dict) else {}
        print(f"{OK} Ban quyen vnstock : {tier_name}  {limits}")
    else:
        print(f"{BAD} Ban quyen vnstock : {tier_name}")
        print("       -> API key co the da bi thu hoi. Ghi key moi vao "
              "$HOME\\.vnstock\\api_key.json roi xoa auth_state.json.")
        blocking.append("licence")

    for pkg, version in health["installed"].items():
        if version:
            print(f"{OK} {pkg:<17} : {version}")
        else:
            print(f"{BAD} {pkg:<17} : chua cai")
            blocking.append(pkg)

    if health["datapro"]:
        print(f"{OK} DataPro desktop   : dang chay")
    else:
        print(f"{BAD} DataPro desktop   : khong tra loi localhost:6789")
        print("       -> Bat app DataPro. Khong co no thi mat gia tham chieu, "
              "khoi ngoai, tu doanh, thoa thuan.")
        blocking.append("datapro")

    if health["asean_macro_backend"]:
        print(f"{OK} Backend macro     : dang chay")
    else:
        print(f"{WARN} Backend macro     : khong tra loi (host nay hay sap tam thoi "
              "roi tu song lai)")
        print("       -> Thu lai sau. Chi anh huong macro/commodity, khong chan "
              "viec phan tich co phieu.")

    print("-" * 66)
    print("GROUNDING SWARM (mã .VN co duoc nap gia that vao prompt khong)")

    probe = {"target": "HPG.VN", "benchmark": "So sanh voi VNINDEX.VN"}
    symbols = grounding.extract_symbols_from_user_vars(probe)
    if not symbols:
        print(f"{BAD} Khong nhan dien duoc ma .VN — worker se trich gia tu du lieu huan luyen.")
        blocking.append("grounding")
    else:
        print(f"{OK} Nhan dien: {symbols}")
        data = grounding.fetch_grounding_data(symbols, window_days=15)
        if not data:
            print(f"{BAD} Nhan dien duoc nhung KHONG lay duoc gia.")
            blocking.append("grounding")
        else:
            for code, rows in data.items():
                last = rows[-1]
                print(f"{OK} {code:<12} {len(rows):>3} phien, moi nhat "
                      f"{last['trade_date'][:10]} close={last['close']:,.2f}")

    print("=" * 66)
    if blocking:
        print(f"CHUA SAN SANG — can xu ly: {', '.join(sorted(set(blocking)))}")
        return 1
    print("SAN SANG. Moi nguon su that deu song.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
