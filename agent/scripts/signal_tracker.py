#!/usr/bin/env python3
"""Do hieu qua so khuyen nghi bang gia DataPro - dau vao cho the "Tin hieu giao dich".

Vi sao file nay ton tai
-----------------------
Mot bo tracking ngay tho lay gia niem yet luc khuyen nghi chia cho gia hom nay.
Cach do SAI moi khi doanh nghiep thuong co phieu hoac chia tach. Do 09/09/2026
tren PET::

    gia niem yet 18/06/2026        54,80
    close dieu chinh cung ngay     37,80   (adj_rate 1,4496)
    close hom nay                  37,95
    so ngay tho  37,95 / 54,80  ->  -30,7%   SAI - do la pha loang
    so dung      37,95 / 37,80  ->   +0,4%   DUNG

Nen script nay lay CA HAI dau tu chuoi da dieu chinh cua DataPro. Cot
``price_quoted`` trong so chi de doi chieu nguon goc, khong bao gio tham gia
phep tinh.

Chay::

    $HOME/.venv/Scripts/python.exe agent/scripts/signal_tracker.py --outdir _market_YYYYMMDD

Exit 0 khi do duoc it nhat mot ma; exit 1 khi DataPro chet hoac so rong.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import warnings
import logging
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import vndata  # noqa: E402

LEDGER = Path(__file__).resolve().parents[1] / "data" / "signals.yaml"

ACTION_LABEL = {
    "MUA": "MUA", "BAN": "BÁN", "NAM_GIU": "NẮM GIỮ", "TICH_LUY": "TÍCH LUỸ",
    "CHO": "CHỜ", "TRUNG_LAP": "TRUNG LẬP", "SWITCH": "SWITCH",
}


def _num(v):
    return None if v is None or v == "" else float(v)


# Huong cua khuyen nghi. CHO/TRUNG_LAP la khuyen nghi TRANH - gia giam thi
# loi khuyen dung, nen huong cua chung la -1 giong BAN. Do mot lenh ban bang
# thuoc do cua lenh mua se bao TPB -11,6% la "lo", trong khi do la ket qua DUNG.
DIRECTION = {"MUA": 1, "TICH_LUY": 1, "SWITCH": 1, "NAM_GIU": 1,
             "BAN": -1, "CHO": -1, "TRUNG_LAP": -1}


def track(entries, today: str):
    rows = []
    bench = None
    try:
        bench = vndata.price.ohlcv("VNINDEX", "2026-01-01", today, allow_fallback=False)
    except Exception:
        bench = None
    for e in entries:
        sym = str(e["symbol"]).upper()
        when = pd.Timestamp(str(e["date"]))
        start = (when - pd.Timedelta(days=12)).strftime("%Y-%m-%d")
        try:
            df = vndata.price.ohlcv(sym, start, today, allow_fallback=False)
        except Exception as exc:
            rows.append({"symbol": sym, "status": f"LOI: {type(exc).__name__}"})
            continue
        if df.empty:
            rows.append({"symbol": sym, "status": "LOI: khong co bar"})
            continue

        at = df[df.index <= when]
        if at.empty:
            rows.append({"symbol": sym, "status": "LOI: chua niem yet o ngay do"})
            continue

        # Ca hai dau deu la close DA DIEU CHINH -> ty le so sanh dung.
        px0 = float(at["close"].iloc[-1])
        px1 = float(df["close"].iloc[-1])
        adj0 = float(at.get("adj_rate", pd.Series([1.0])).iloc[-1])
        chg = (px1 / px0 - 1) * 100 if px0 else float("nan")

        # Vung mua co cham chua: dung LOW cua chuoi dieu chinh ke tu ngay KN.
        after = df[df.index >= when]
        zone = e.get("buy_zone") or []
        zone_hi = _num(zone[1]) if len(zone) == 2 else None
        zone_hit = ""
        if zone_hi is not None and not after.empty:
            # Nguong vung mua duoc ghi theo gia NIEM YET -> quy ve thang dieu chinh.
            thr = zone_hi / adj0 if adj0 else zone_hi
            zone_hit = "ĐÃ CHẠM" if float(after["low"].min()) <= thr else "CHƯA CHẠM"

        target = _num(e.get("target"))
        stop = _num(e.get("stop"))
        to_target = (target / adj0 / px1 - 1) * 100 if target and px1 and adj0 else None
        to_stop = (stop / adj0 / px1 - 1) * 100 if stop and px1 and adj0 else None

        # Alpha so voi VN-Index tren dung cua so thoi gian cua khuyen nghi.
        bench_pct = None
        if bench is not None and not bench.empty:
            b0 = bench[bench.index <= when]
            if not b0.empty:
                bench_pct = (float(bench["close"].iloc[-1])
                             / float(b0["close"].iloc[-1]) - 1) * 100

        sign = DIRECTION.get(str(e.get("action", "")), 0)
        signed = chg * sign if sign else None
        alpha = (chg - bench_pct) * sign if (sign and bench_pct is not None) else None
        if signed is None:
            verdict = "—"
        elif signed > 1.0:
            verdict = "ĐÚNG"
        elif signed < -1.0:
            verdict = "SAI"
        else:
            verdict = "ĐI NGANG"

        rows.append({
            "symbol": sym,
            "date": str(e["date"]),
            "action": ACTION_LABEL.get(str(e.get("action", "")), str(e.get("action", ""))),
            "price_quoted": e.get("price_quoted") or "",
            "px_at_call_adj": round(px0, 2),
            "px_now_adj": round(px1, 2),
            "adj_rate_at_call": round(adj0, 4),
            "diluted": int(abs(adj0 - 1) > 1e-6),
            "change_pct": round(chg, 2),
            "vnindex_pct": round(bench_pct, 2) if bench_pct is not None else "",
            "signed_pct": round(signed, 2) if signed is not None else "",
            "alpha_pct": round(alpha, 2) if alpha is not None else "",
            "verdict": verdict,
            "sessions": int(len(after)),
            "buy_zone": (f"{zone[0]}–{zone[1]}" if len(zone) == 2 and zone[0]
                         else (f"≤{zone[1]}" if len(zone) == 2 else "")),
            "zone_hit": zone_hit,
            "target": target or "",
            "to_target_pct": round(to_target, 1) if to_target is not None else "",
            "stop": stop or "",
            "to_stop_pct": round(to_stop, 1) if to_stop is not None else "",
            "confidence": e.get("confidence") or "",
            "status": e.get("status", "open"),
            "source": e.get("source", ""),
            "note": " ".join(str(e.get("note", "")).split()),
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Do hieu qua so khuyen nghi")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        print("LOI: thieu pyyaml.", file=sys.stderr)
        return 1

    path = Path(args.ledger)
    if not path.exists():
        print(f"LOI: khong thay so khuyen nghi {path}", file=sys.stderr)
        return 1
    entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if not entries:
        # So rong la trang thai HOP LE - mot ngay khong co khuyen nghi. Ghi file
        # rong roi thoat 0 de batch khong canh bao nham; renderer se hien khoi
        # "chua co tin hieu" thay vi bang trong.
        (outdir / "signals.csv").write_text("", encoding="utf-8")
        (outdir / "signals.json").write_text("[]", encoding="utf-8")
        print(f"So {path.name} dang rong - chua co tin hieu nao cho hom nay.")
        return 0

    if not vndata.price.datapro_available():
        print("LOI: DataPro khong tra loi.", file=sys.stderr)
        return 1

    rows = track(entries, args.date)
    ok = [r for r in rows if "change_pct" in r]
    if not ok:
        print("LOI: khong do duoc ma nao.", file=sys.stderr)
        return 1

    keys = list(max(rows, key=len).keys())
    with (outdir / "signals.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    (outdir / "signals.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    scored = [r for r in ok if r.get("verdict") in ("ĐÚNG", "SAI", "ĐI NGANG")]
    right = sum(1 for r in scored if r["verdict"] == "ĐÚNG")
    alphas = [r["alpha_pct"] for r in scored if r.get("alpha_pct") != ""]
    print(f"XONG -> {outdir / 'signals.csv'}")
    print(f"  {len(ok)} tin hieu | dung {right}/{len(scored)} | "
          f"alpha trung binh {sum(alphas)/len(alphas):+.2f}%" if alphas else "")
    print(f"  {sum(1 for r in ok if r['diluted'])} ma da pha loang "
          f"-> do bang gia dieu chinh ca hai dau")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
