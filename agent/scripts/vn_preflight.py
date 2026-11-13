#!/usr/bin/env python3
"""Preflight check for the Vietnamese data stack — run this before a long analysis.

Answers, in one command, the questions that actually go wrong:

1. Is the DataPro desktop up? Without it there is no price, reference price,
   foreign / proprietary flow — and since 13/11/2026 no fallback either.
2. Are the VNDIRECT-sourced snapshots (ICB classification, VN30 basket) on
   disk, and how old are they? The daily brief and the learning loop read them.
3. Does swarm grounding actually load real prices for a ``.VN`` symbol? This is
   the check that would have caught VN presets running on training-data prices.

VNDIRECT MCP itself (financials, ratios, macro, company data) is OAuth-only and
is checked from the MCP client, not from here: run ``/mcp`` in Claude Code.

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

    if health["datapro"]:
        print(f"{OK} DataPro desktop   : dang chay")
    else:
        print(f"{BAD} DataPro desktop   : khong tra loi localhost:6789")
        print("       -> Bat app DataPro. Khong co no thi mat gia tham chieu, "
              "khoi ngoai, tu doanh, thoa thuan.")
        blocking.append("datapro")

    for name, as_of in health["snapshots"].items():
        if as_of:
            print(f"{OK} Snapshot {name:<20}: {as_of}")
        else:
            print(f"{WARN} Snapshot {name:<20}: chua co -> lay tu VNDIRECT MCP, ghi bang "
                  "vndata.reference.save_*")

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
