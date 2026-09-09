#!/usr/bin/env python3
"""Data pack cho ban tin thi truong VN hang ngay - keo so that truoc khi agent viet.

Vi sao file nay ton tai
-----------------------
Do rong thi truong, GTGD dan dat va luy ke 30 phien la SO THUAN. De agent tu
tinh la mo duong cho no trich tu tri nho mo hinh - dung bai hoc cua
``commodity_datapack.py``. Script nay tinh het, ghi ra CSV, agent chi doc va
dien giai.

Nguon: DataPro cho toan bo gia + dong tien (mot bar chua ca OHLCV, ref_price,
foreign_*, prop_*, put_through_*, active_*, listed_shares) va vnstock_data cho
anh xa san + nganh ICB cap 2.

Bay da kiem chung (do 09/09/2026)
---------------------------------
* ``prop_*`` (tu doanh) ve TRE hon ca gio dong cua - do 09/09/2026 luc 15:11,
  sau ATC, moi ma van tra 0 trong khi 07/09 va 08/09 co so that. Vi vay script
  KHONG tin vao co ``--session`` ma hoi chinh du lieu: khong ma nao co
  ``prop_net`` khac 0 thi ca cot ghi ``N/A``, khong ghi 0.
* ``foreign_*`` NGUOC LAI - song trong phien, dung duoc o ban 11h30.
* Thang ``value`` KHAC NHAU: co phieu = nghin VND, chi so = trieu VND. Quy het
  ve ty VND o mot cho duy nhat (``_to_ty``).
* ``Reference().equity.by_exchange()`` tra ca san lan ICB cap 2 trong 1 call 8s;
  ``vndata.reference.symbols_by_industry()`` mat 26s cho cung viec - dung cai dau.
* Nhom DELISTED (229 ma) van nam trong danh sach - phai loc, khong la do rong sai.

Chay (tu goc repo)::

    $HOME/.venv/Scripts/python.exe agent/scripts/market_datapack.py --session close
    $HOME/.venv/Scripts/python.exe agent/scripts/market_datapack.py --session morning

Exit 0 khi dung duoc; exit 1 khi DataPro chet hoac khong du ma co giao dich.
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import vndata  # noqa: E402
from vndata.errors import SourceUnavailable  # noqa: E402

# Bien do dao dong theo san. Khong co bang nay thi khong dem duoc tran/san.
BAND = {"HOSE": 0.07, "HNX": 0.10, "UPCOM": 0.15}
# Lam tron buoc gia keo gia tran xuong duoi band mot chut - noi long mot buoc.
BAND_TOL = 0.005
# Can lich su du cho MA200 (200 phien ~ 290 ngay lich); lay du 420 cho an toan.
HISTORY_DAYS = 420
# So phien luy ke, dung chung cho flow_30d va A/D line.
LOOKBACK = 30
# Chi so theo doi. Ma DataPro cua ro VN30 la "VN30INDEX" - "VN30" tra 0 dong.
INDICES = ["VNINDEX", "VN30INDEX", "HNXINDEX", "UPCOMINDEX"]
# ETF thanh khoan - phai tach khoi dong ngoai CHU DONG.
ETF_SYMBOLS = {"E1VFVN30", "FUEVFVND", "FUESSVFL", "FUEVN100", "FUEMAV30", "FUEDCMID"}


def _to_ty(value: float, instrument: str) -> float:
    """Quy GTGD ve ty VND. Co phieu tinh bang nghin VND, chi so bang trieu VND."""
    if value is None or pd.isna(value):
        return float("nan")
    return value / 1e6 if instrument == "equity" else value / 1e3


def _fetch(symbol: str, start: str, end: str):
    try:
        df = vndata.price.ohlcv(symbol, start, end, allow_fallback=False)
        return symbol, (None if df.empty else df)
    except Exception as exc:  # mot ma chet khong duoc keo sap ca phien quet
        return symbol, exc


def load_universe():
    """Tra (DataFrame ma x san x icb_lv2, dict icb_code -> ten nganh)."""
    from vnstock_data import Reference

    ref = Reference().equity.by_exchange()
    ref = ref[ref["exchange"].isin(BAND)].copy()
    ref["icb_code_lv2"] = ref["icb_code_lv2"].astype(str).str.zfill(4)

    tax = vndata.reference.industry_taxonomy()
    tax = tax[tax["icb_level"] == 2]
    names = dict(zip(tax["icb_code"].astype(str).str.zfill(4), tax["icb_name"]))
    ref["icb_name"] = ref["icb_code_lv2"].map(names).fillna("Chua phan nganh")
    return ref, names


def scan(symbols, start, end, workers=8):
    """Keo song song tu DataPro. Local API nen thread an toan va nhanh gap 6."""
    out, failed = {}, {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for sym, res in pool.map(lambda s: _fetch(s, start, end), symbols):
            if isinstance(res, Exception):
                failed[sym] = f"{type(res).__name__}: {res}"
            elif res is not None:
                out[sym] = res
    return out, failed


def per_symbol_metrics(sym, df, exchange, icb_code, icb_name, today):
    """Rut mot dong so lieu phien cho mot ma. Tra None neu ma khong co bar hom nay."""
    if today not in df.index:
        return None
    row = df.loc[today]
    ref_px = row.get("ref_price")
    close = row.get("close")
    if pd.isna(close) or pd.isna(ref_px) or ref_px == 0:
        return None

    pct = close / ref_px - 1.0
    band = BAND[exchange]
    vol = row.get("volume", 0) or 0
    val_ty = _to_ty(row.get("value", 0) or 0, "equity")
    listed = row.get("listed_shares", 0) or 0
    # close da back-adjust; adj_rate hom nay = 1 nen gia giao dich = close.
    cap_ty = listed * close * 1000 / 1e9 if listed else float("nan")

    closes = df["close"].dropna()
    def _ma(n):
        return closes.rolling(n).mean().iloc[-1] if len(closes) >= n else float("nan")

    frn_net = ((row.get("foreign_buy_value", 0) or 0)
               - (row.get("foreign_sell_value", 0) or 0))
    prop_net = ((row.get("prop_buy_value", 0) or 0)
                - (row.get("prop_sell_value", 0) or 0))

    hist = df.tail(LOOKBACK)
    frn_30 = ((hist.get("foreign_buy_value", pd.Series(dtype=float)).fillna(0)
               - hist.get("foreign_sell_value", pd.Series(dtype=float)).fillna(0)).sum())
    prop_30 = ((hist.get("prop_buy_value", pd.Series(dtype=float)).fillna(0)
                - hist.get("prop_sell_value", pd.Series(dtype=float)).fillna(0)).sum())
    val20 = _to_ty(df["value"].tail(20).mean(), "equity") if "value" in df else float("nan")

    return {
        "symbol": sym,
        "exchange": exchange,
        "icb_code": icb_code,
        "icb_name": icb_name,
        "close": round(float(close), 3),
        "ref_price": round(float(ref_px), 3),
        "pct_change": round(float(pct) * 100, 2),
        "volume": int(vol),
        "value_ty": round(val_ty, 3),
        "value_avg20_ty": round(val20, 3) if pd.notna(val20) else "",
        "market_cap_ty": round(cap_ty, 1) if pd.notna(cap_ty) else "",
        "at_ceiling": int(pct >= band - BAND_TOL),
        "at_floor": int(pct <= -(band - BAND_TOL)),
        "above_ma20": int(pd.notna(_ma(20)) and close > _ma(20)),
        "above_ma50": int(pd.notna(_ma(50)) and close > _ma(50)),
        "above_ma200": int(pd.notna(_ma(200)) and close > _ma(200)),
        "has_ma200": int(len(closes) >= 200),
        "foreign_net_ty": round(_to_ty(frn_net, "equity"), 4),
        "foreign_net_30d_ty": round(_to_ty(frn_30, "equity"), 4),
        "prop_net_ty": round(_to_ty(prop_net, "equity"), 4),
        "prop_net_30d_ty": round(_to_ty(prop_30, "equity"), 4),
        "put_through_ty": round(_to_ty(row.get("put_through_value", 0) or 0, "equity"), 4),
        "active_buy_ty": round(_to_ty(row.get("active_buy_value", 0) or 0, "equity"), 4),
        "active_sell_ty": round(_to_ty(row.get("active_sell_value", 0) or 0, "equity"), 4),
        "is_etf": int(sym in ETF_SYMBOLS),
    }


def index_rows(frames, today):
    rows = []
    for sym in INDICES:
        df = frames.get(sym)
        if df is None or today not in df.index:
            rows.append({"index": sym, "status": "N/A - khong co bar hom nay"})
            continue
        r = df.loc[today]
        ref_px, close = r.get("ref_price"), r.get("close")
        prev = df["close"].shift(1).loc[today]
        base = ref_px if pd.notna(ref_px) and ref_px else prev
        # Trong phien, DataPro cap nhat `close` cua bar chi so KHONG dong bo voi
        # `high`/`low` - do 09/09/2026 14:33: VN30INDEX close 1958.21 nam duoi
        # low 1966.06, vai phut sau thi nhat quan tro lai. Kep lai de ban tin
        # khong bao gio in ra mot khoang tu mau thuan.
        hi, lo = r.get("high"), r.get("low")
        clamped = 0
        if pd.notna(hi) and pd.notna(lo) and pd.notna(close):
            if close > hi or close < lo:
                clamped = 1
                hi, lo = max(hi, close), min(lo, close)
        hist_val = df["value"].tail(20).map(lambda v: _to_ty(v, "index"))
        rows.append({
            "index": sym,
            "close": round(float(close), 2),
            "ref_price": round(float(base), 2) if pd.notna(base) else "",
            "change": round(float(close - base), 2) if pd.notna(base) else "",
            "pct_change": round(float(close / base - 1) * 100, 2) if pd.notna(base) and base else "",
            "high": round(float(hi), 2) if pd.notna(hi) else "",
            "low": round(float(lo), 2) if pd.notna(lo) else "",
            "range_clamped": clamped,
            "value_ty": round(_to_ty(r.get("value", 0) or 0, "index"), 1),
            "value_avg20_ty": round(float(hist_val.mean()), 1),
            "value_vs_avg20_pct": round(
                _to_ty(r.get("value", 0) or 0, "index") / hist_val.mean() * 100 - 100, 1
            ) if hist_val.mean() else "",
            "status": "OK",
        })
    return rows


def breadth_rows(stocks, frames, today, universe):
    """Do rong: hom nay theo san + duong A/D 30 phien cho toan thi truong."""
    df = pd.DataFrame(stocks)
    out = []
    for scope in ["TOAN_TT", "HOSE", "HNX", "UPCOM"]:
        sub = df if scope == "TOAN_TT" else df[df["exchange"] == scope]
        traded = sub[sub["volume"] > 0]
        ma200 = traded[traded["has_ma200"] == 1]
        out.append({
            "scope": scope,
            "total_listed": len(sub),
            "traded": len(traded),
            "no_trade": len(sub) - len(traded),
            "advancers": int((traded["pct_change"] > 0).sum()),
            "decliners": int((traded["pct_change"] < 0).sum()),
            "unchanged": int((traded["pct_change"] == 0).sum()),
            "ceiling": int(traded["at_ceiling"].sum()),
            "floor": int(traded["at_floor"].sum()),
            "ad_ratio": round(
                (traded["pct_change"] > 0).sum() / max((traded["pct_change"] < 0).sum(), 1), 2
            ),
            "pct_above_ma20": round(traded["above_ma20"].mean() * 100, 1) if len(traded) else "",
            "pct_above_ma50": round(traded["above_ma50"].mean() * 100, 1) if len(traded) else "",
            "pct_above_ma200": round(ma200["above_ma200"].mean() * 100, 1) if len(ma200) else "",
            "ma200_sample": len(ma200),
        })
    return out


def ad_line_rows(frames, universe, sessions):
    """A/D line 30 phien: moi phien dem ma tang tru ma giam, cong don."""
    codes = set(universe["symbol"])
    rows, cum = [], 0
    for day in sessions:
        adv = dec = 0
        for sym in codes:
            df = frames.get(sym)
            if df is None or day not in df.index:
                continue
            r = df.loc[day]
            ref_px, close = r.get("ref_price"), r.get("close")
            if pd.isna(close) or pd.isna(ref_px) or not ref_px or not (r.get("volume") or 0):
                continue
            if close > ref_px:
                adv += 1
            elif close < ref_px:
                dec += 1
        cum += adv - dec
        rows.append({
            "date": day.strftime("%Y-%m-%d"),
            "advancers": adv, "decliners": dec,
            "net": adv - dec, "ad_line": cum,
        })
    return rows


def sector_rows(stocks, prop_available):
    df = pd.DataFrame(stocks)
    df = df[(df["volume"] > 0) & (df["is_etf"] == 0)]
    total_val = df["value_ty"].sum()
    out = []
    for (code, name), g in df.groupby(["icb_code", "icb_name"]):
        cap = pd.to_numeric(g["market_cap_ty"], errors="coerce")
        w = cap / cap.sum() if cap.sum() and pd.notna(cap.sum()) else None
        wpct = float((g["pct_change"] * w).sum()) if w is not None else float(g["pct_change"].mean())
        out.append({
            "icb_code": code,
            "icb_name": name,
            "n_symbols": len(g),
            "pct_change_wavg": round(wpct, 2),
            "pct_change_median": round(float(g["pct_change"].median()), 2),
            "advancers": int((g["pct_change"] > 0).sum()),
            "decliners": int((g["pct_change"] < 0).sum()),
            "breadth_in_sector": round((g["pct_change"] > 0).sum() / len(g) * 100, 1),
            "value_ty": round(float(g["value_ty"].sum()), 2),
            "pct_of_market_value": round(float(g["value_ty"].sum()) / total_val * 100, 2)
            if total_val else "",
            "market_cap_ty": round(float(cap.sum()), 1) if pd.notna(cap.sum()) else "",
            "foreign_net_ty": round(float(g["foreign_net_ty"].sum()), 3),
            "foreign_net_30d_ty": round(float(g["foreign_net_30d_ty"].sum()), 3),
            "prop_net_ty": round(float(g["prop_net_ty"].sum()), 3) if prop_available else "N/A",
            "prop_net_30d_ty": round(float(g["prop_net_30d_ty"].sum()), 3),
            "put_through_ty": round(float(g["put_through_ty"].sum()), 3),
        })
    return sorted(out, key=lambda r: -r["value_ty"])


def leader_rows(stocks, index_level, top=25):
    """Top GTGD + dong gop diem so uoc luong vao VN-Index.

    CANH BAO: VN-Index tinh theo von hoa DIEU CHINH FREE-FLOAT; DataPro chi co
    ``listed_shares``. Cot dong gop la UOC LUONG, khong phai so cua HOSE. Agent
    duoc phep xep hang bang cot nay nhung KHONG duoc trich nhu so chinh thuc.
    """
    df = pd.DataFrame(stocks)
    hose = df[(df["exchange"] == "HOSE") & (df["volume"] > 0) & (df["is_etf"] == 0)].copy()
    cap = pd.to_numeric(hose["market_cap_ty"], errors="coerce")
    hose["cap"] = cap
    total_cap = cap.sum()
    if total_cap and index_level:
        hose["idx_points_est"] = (
            hose["pct_change"] / 100 * hose["cap"] / total_cap * index_level
        ).round(3)
    else:
        hose["idx_points_est"] = float("nan")

    by_val = df[df["volume"] > 0].nlargest(top, "value_ty")
    rows = []
    for _, r in by_val.iterrows():
        pts = hose.loc[hose["symbol"] == r["symbol"], "idx_points_est"]
        rows.append({
            "rank_by_value": len(rows) + 1,
            "symbol": r["symbol"], "exchange": r["exchange"], "icb_name": r["icb_name"],
            "close": r["close"], "pct_change": r["pct_change"],
            "value_ty": r["value_ty"], "value_avg20_ty": r["value_avg20_ty"],
            "market_cap_ty": r["market_cap_ty"],
            "foreign_net_ty": r["foreign_net_ty"],
            "idx_points_est": float(pts.iloc[0]) if len(pts) else "",
            "is_etf": r["is_etf"],
        })
    movers = {
        "top_up": hose.nlargest(10, "idx_points_est")[
            ["symbol", "pct_change", "idx_points_est", "value_ty"]].to_dict("records"),
        "top_down": hose.nsmallest(10, "idx_points_est")[
            ["symbol", "pct_change", "idx_points_est", "value_ty"]].to_dict("records"),
    }
    return rows, movers


def flow_rows(stocks, prop_available, top=30):
    df = pd.DataFrame(stocks)
    df = df[df["volume"] > 0]
    sess, cum = [], []
    for _, r in pd.concat([df.nlargest(top, "foreign_net_ty"),
                           df.nsmallest(top, "foreign_net_ty")]).iterrows():
        sess.append({
            "symbol": r["symbol"], "icb_name": r["icb_name"], "exchange": r["exchange"],
            "pct_change": r["pct_change"], "value_ty": r["value_ty"],
            "foreign_net_ty": r["foreign_net_ty"],
            "foreign_net_pct_of_value": round(
                r["foreign_net_ty"] / r["value_ty"] * 100, 1) if r["value_ty"] else "",
            "prop_net_ty": r["prop_net_ty"] if prop_available else "N/A",
            "put_through_ty": r["put_through_ty"],
            "active_buy_ty": r["active_buy_ty"], "active_sell_ty": r["active_sell_ty"],
            "is_etf": r["is_etf"],
        })
    for _, r in pd.concat([df.nlargest(top, "foreign_net_30d_ty"),
                           df.nsmallest(top, "foreign_net_30d_ty")]).iterrows():
        flip = ""
        if r["foreign_net_30d_ty"] and r["foreign_net_ty"]:
            if (r["foreign_net_30d_ty"] > 0) != (r["foreign_net_ty"] > 0):
                flip = "DOI CHIEU"
        cum.append({
            "symbol": r["symbol"], "icb_name": r["icb_name"],
            "foreign_net_30d_ty": r["foreign_net_30d_ty"],
            "foreign_net_ty": r["foreign_net_ty"],
            "prop_net_30d_ty": r["prop_net_30d_ty"],
            "flip": flip, "is_etf": r["is_etf"],
        })
    return sess, cum


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


MANIFEST_TEMPLATE = """# Data pack thi truong VN - {end}

| Truong | Gia tri |
|---|---|
| Phien | `{session}` ({session_note}) |
| Gio chot so | {stamp} |
| Ma niem yet quet | {n_universe} (da loai DELISTED) |
| Ma co bar hom nay | {n_equity} co phieu + {n_etf} ETF |
| Ma co giao dich | {n_traded} |
| Ma loi khi keo | {n_failed} |
| Ngoai rong phien | {frn_total} ty VND |
| Ngoai rong 30 phien | {frn_30} ty VND |
| Tu doanh rong phien | {prop_total} |

## Quy tac bat buoc voi agent

1. **Chi duoc dung so trong cac file CSV nay.** Thieu thi ghi `N/A` kem ly do,
   khong uoc, khong lay tu tri nho mo hinh.
2. **`prop_net_ty = N/A` la du lieu CHUA VE, khong phai 0.** DataPro cong bo
   tu doanh tre hon ca gio dong cua (do 09/09/2026 15:11: van 0). Cam dien giai
   N/A thanh "tu doanh dung ngoai" hay "tu doanh can bang". Cot
   `prop_net_30d_ty` VAN co so that (luy ke cac phien da chot) - dung duoc.
3. **`idx_points_est` la UOC LUONG** theo von hoa niem yet, khong phai so
   free-float cua HOSE. Dung de xep hang, khong trich nhu so chinh thuc.
4. GTGD da quy ve **ty VND** o tang script (co phieu nghin VND, chi so trieu VND).
5. `put_through_ty` la **thoa thuan** - sang tay, khong phai quan diem chon ma.
   Tru ra truoc khi ket luan ve dong tien chu dong.
6. `range_clamped = 1` trong `index.csv` nghia la trong phien DataPro tra `close`
   nam NGOAI khoang `low`-`high` (cap nhat khong dong bo, da do 09/09/2026 14:33:
   VN30INDEX close 1958.21 duoi low 1966.06). Script da noi rong khoang de no
   khong tu mau thuan; khi co co nay thi bien do trong phien la UOC LUONG.

## File

| File | Noi dung |
|---|---|
| `index.csv` | 4 chi so: diem, +/-, %, bien do, GTGD ty, so voi BQ20 |
| `breadth.csv` | Do rong theo TOAN_TT/HOSE/HNX/UPCOM: tang/giam/TC, tran/san, %MA20/50/200 |
| `ad_line.csv` | Duong A/D {lookback} phien |
| `sector.csv` | ICB cap 2: %thay doi gia quyen von hoa, GTGD, do rong noi nganh, ngoai/tu doanh |
| `leaders.csv` | Top 25 GTGD + dong gop diem uoc luong |
| `index_movers.csv` | Top 10 keo / top 10 dim VN-Index |
| `flow_session.csv` | Ngoai/tu doanh rong theo ma trong phien (top 30 moi chieu) |
| `flow_30d.csv` | Luy ke {lookback} phien + co `DOI CHIEU` |
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Data pack thi truong VN hang ngay")
    ap.add_argument("--session", choices=["morning", "close"], required=True)
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    if not vndata.price.datapro_available():
        print("LOI: DataPro khong tra loi. Bat app DataPro roi chay lai.", file=sys.stderr)
        return 1

    today = pd.Timestamp(args.date)
    start = (today - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")
    outdir = Path(args.outdir or ("_market_" + today.strftime("%Y%m%d")))
    outdir.mkdir(parents=True, exist_ok=True)

    print("[1/5] Nap danh sach ma + nganh ICB...", flush=True)
    universe, _ = load_universe()
    symbols = list(universe["symbol"]) + sorted(ETF_SYMBOLS)

    print("[2/5] Keo %d ma + %d chi so tu DataPro..." % (len(symbols), len(INDICES)), flush=True)
    frames, failed = scan(symbols + INDICES, start, end, args.workers)
    print("      co bar: %d, loi: %d" % (len(frames), len(failed)), flush=True)

    print("[3/5] Tinh chi so, do rong, nganh...", flush=True)
    idx_rows = index_rows(frames, today)
    vni = next((r for r in idx_rows if r["index"] == "VNINDEX" and r["status"] == "OK"), None)

    meta = universe.set_index("symbol")[["exchange", "icb_code_lv2", "icb_name"]].to_dict("index")
    stocks = []
    for sym, df_ in frames.items():
        if sym in INDICES:
            continue
        m = meta.get(sym, {"exchange": "HOSE", "icb_code_lv2": "9999", "icb_name": "ETF"})
        row = per_symbol_metrics(sym, df_, m["exchange"], m["icb_code_lv2"], m["icb_name"], today)
        if row:
            stocks.append(row)
    if len(stocks) < 100:
        print("LOI: chi co %d ma co bar ngay %s - phien nay khong co du lieu "
              "(ngay nghi?) hoac DataPro loi." % (len(stocks), end), file=sys.stderr)
        return 1

    equities = [s for s in stocks if not s["is_etf"]]

    # Tu doanh: hoi CHINH DU LIEU, dung tin vao co --session. DataPro cong bo
    # `prop_*` TRE hon ca gio dong cua - do 09/09/2026 luc 15:11 (sau ATC) moi
    # ma van tra 0 trong khi 07/09 va 08/09 deu co so that. Neu chay `--session
    # close` luc 15h10 va tin vao co phien, ban tin se in "tu doanh 0 ty" - dung
    # loai so gia ma ca lop nay sinh ra de chan. Toan bo thi truong khop lenh
    # ma tu doanh mua va ban deu bang 0 khong phai "tu doanh dung ngoai", do la
    # du lieu chua ve.
    prop_gross = sum((s["prop_net_ty"] != 0) for s in equities)
    prop_available = prop_gross > 0
    vni_df = frames.get("VNINDEX")
    sessions = list(vni_df.index[-LOOKBACK:]) if vni_df is not None else []

    write_csv(outdir / "index.csv", idx_rows)
    write_csv(outdir / "breadth.csv", breadth_rows(equities, frames, today, universe))
    write_csv(outdir / "ad_line.csv", ad_line_rows(frames, universe, sessions))
    write_csv(outdir / "sector.csv", sector_rows(stocks, prop_available))

    print("[4/5] Xep hang dan dat va dong tien...", flush=True)
    leaders, movers = leader_rows(stocks, vni["close"] if vni else None)
    write_csv(outdir / "leaders.csv", leaders)
    write_csv(outdir / "index_movers.csv",
              [dict(side="keo", **r) for r in movers["top_up"]]
              + [dict(side="dim", **r) for r in movers["top_down"]])
    sess_flow, cum_flow = flow_rows(stocks, prop_available)
    write_csv(outdir / "flow_session.csv", sess_flow)
    write_csv(outdir / "flow_30d.csv", cum_flow)

    print("[5/5] Ghi MANIFEST...", flush=True)
    dfe = pd.DataFrame(equities)
    traded = dfe[dfe["volume"] > 0]
    frn_total = round(float(traded["foreign_net_ty"].sum()), 1)
    frn_30 = round(float(traded["foreign_net_30d_ty"].sum()), 1)
    prop_total = (round(float(traded["prop_net_ty"].sum()), 1) if prop_available
                  else "N/A (DataPro chua cong bo tu doanh cho ngay nay)")
    (outdir / "MANIFEST.md").write_text(MANIFEST_TEMPLATE.format(
        end=end, session=args.session,
        session_note=("giua phien, chua dong cua" if args.session == "morning"
                      else "sau dong cua"),
        stamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        n_universe=len(universe), n_equity=len(equities),
        n_etf=len(stocks) - len(equities), n_traded=len(traded),
        n_failed=len(failed), frn_total=frn_total, frn_30=frn_30,
        prop_total=prop_total, lookback=LOOKBACK,
    ), encoding="utf-8")

    if failed:
        (outdir / "fetch_errors.txt").write_text(
            "\n".join("%s\t%s" % (k, v) for k, v in sorted(failed.items())), encoding="utf-8")

    print("\nXONG -> %s" % outdir)
    print("  %d ma giao dich | ngoai rong %s ty | tu doanh %s"
          % (len(traded), frn_total, prop_total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
