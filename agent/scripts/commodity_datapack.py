#!/usr/bin/env python3
"""Data pack cho swarm hang hoa - keo so that truoc khi agent bat dau suy luan.

Vi sao file nay ton tai
-----------------------
``src/swarm/grounding.py`` chi nhan dien ma co dang ``.VN`` / ``.US`` / ``.HK`` /
``-USDT``. Bien ``{commodity}`` cua preset hang hoa ("dau tho", "dong") khong khop
mau nao, nen swarm chay **khong co mot dong gia that nao** trong prompt - va
docstring cua chinh module grounding da canh bao ket qua: worker se trich gia tu
tri nho mo hinh. File nay bit lo do: keo gia that, kiem cheo, roi ghi ra mot khoi
markdown de ``_run_commodity.py`` tiem vao moi worker qua ``private_context``.

Bon nguon, moi nguon mot vai tro:

* **Yahoo** (``yfinance``) - hop dong toan cau, USD. Nguon chinh cho hau het.
* **vndata.macro.commodity** - cung feed voi Yahoo cho dau/vang/khi, nhung la
  nguon **duy nhat** cho gia VN noi dia (thep VN, vang SJC, xang ban le, heo hoi).
* **akshare futures_main_sina** - hop dong lien tuc Trung Quoc, CNY, ~20 nam.
  Nguon **duy nhat** cho cao su (RU0), quang sat (I0), than coc (J0).
* **DataPro** (``vndata.price``) - gia + khoi ngoai cac ma VN an theo hang hoa.

Bay da kiem chung (xem COMMODITY_DATA_SOURCE.md):

* ``vndata.macro.commodity(name)`` khong truyen ``start=`` chi tra ~6 thang.
* ``iron_ore`` va ``coke`` cua vndata **tra 0 dong ma khong raise** - chuoi chet
  tu 07/03/2025. Script nay danh dau STALE thay vi im lang.
* ``gas`` mac dinh ``market='VN'`` la **gia xang ban le**, khong phai Henry Hub.
* DataPro **khong co forex** du ``SOURCE_MAP`` noi co.

Chay (tu goc repo)::

    .venv/Scripts/python.exe agent/scripts/commodity_datapack.py oil_crude
    .venv/Scripts/python.exe agent/scripts/commodity_datapack.py --list

Exit 0 khi co it nhat mot chuoi gia con song; exit 1 khi khong con nguon nao.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Bar cuoi cach hom nay qua nguong nay thi chuoi bi coi la chet, khong phai
# "cuoi tuan". 10 ngay du cho nghi le dai nhat cua moi san trong bang.
STALE_DAYS = 10
# Hai nguon USD cho cung mot mat hang lech qua nguong nay o bar cuoi thi khong
# duoc tu chon - ghi ca hai va bao dong.
CROSSCHECK_TOL = 0.01
DEFAULT_YEARS = 6


@dataclass(frozen=True)
class Route:
    """Duong lay du lieu cho mot mat hang."""

    label: str
    unit: str
    yahoo: str | None = None
    vndata: str | None = None
    vndata_kwargs: dict = field(default_factory=dict)
    akshare: str | None = None
    akshare_unit: str = "CNY"
    # Chi kiem cheo Yahoo vs vndata khi hai ben la CUNG hop dong, CUNG don vi.
    # Dat False khi hai nguon co chu dich la hai chuan khac nhau - neu khong,
    # kiem cheo bao dong gia moi lan chay (vd sugar: cent/lb vs USD/tan).
    crosscheck: bool = True
    vn_proxies: tuple[str, ...] = ()
    crawl_urls: tuple[str, ...] = ()
    notes: str = ""


# Moi dong duoi day da duoc goi that mot lan truoc khi viet vao day.
ROUTES: dict[str, Route] = {
    "oil_crude": Route(
        label="Dau tho WTI",
        unit="USD/thung",
        yahoo="CL=F",
        vndata="oil_crude",
        akshare="SC0",
        vn_proxies=("BSR", "PLX", "GAS", "PVD", "PVS", "PVT"),
        notes="vndata oil_crude == Yahoo CL=F tuyet doi (cung feed). SC0 la dau INE Thuong Hai, CNY/thung.",
    ),
    "oil_brent": Route(
        label="Dau tho Brent",
        unit="USD/thung",
        yahoo="BZ=F",
        vn_proxies=("BSR", "PLX", "GAS", "PVD", "PVS", "PVT"),
        notes="vndata chi co Brent trong 'listing' (snapshot, khong lich su).",
    ),
    "gas": Route(
        label="Khi tu nhien Henry Hub",
        unit="USD/MMBtu",
        yahoo="NG=F",
        vndata="gas",
        vndata_kwargs={"market": "GLOBAL"},
        vn_proxies=("GAS", "CNG", "PGD", "PGS"),
        notes="BAT BUOC market='GLOBAL'. Mac dinh market='VN' tra GIA XANG BAN LE (ron95/ron92/dau DO), khong phai khi.",
    ),
    "gas_vn": Route(
        label="Gia xang dau ban le VN",
        unit="nghin VND/lit",
        vndata="gas",
        vndata_kwargs={"market": "VN"},
        vn_proxies=("PLX", "OIL", "COM"),
        notes="Chuoi dieu hanh Bo Cong Thuong. Cot: ron95 / ron92 / oil_do.",
    ),
    "copper": Route(
        label="Dong",
        unit="USD/lb",
        yahoo="HG=F",
        akshare="CU0",
        notes="vndata chi co snapshot trong 'listing'. CU0 = SHFE, CNY/tan - dung de doc ton kho/backwardation TQ, khong so sanh thang voi HG=F.",
    ),
    "aluminium": Route(
        label="Nhom",
        unit="USD/tan",
        yahoo="ALI=F",
        akshare="AL0",
    ),
    "gold": Route(
        label="Vang the gioi",
        unit="USD/oz",
        yahoo="GC=F",
        vndata="gold",
        vndata_kwargs={"market": "GLOBAL"},
        akshare="AU0",
        vn_proxies=("PNJ",),
    ),
    "gold_vn": Route(
        label="Vang SJC trong nuoc",
        unit="nghin VND/luong",
        vndata="gold",
        vndata_kwargs={"market": "VN"},
        vn_proxies=("PNJ",),
        notes="Cot buy/sell chu khong phai OHLCV. Chenh voi gia the gioi = premium noi dia.",
    ),
    "steel": Route(
        label="Thep HRC",
        unit="USD/tan ngan",
        yahoo="HRC=F",
        vndata="steel",
        vndata_kwargs={"market": "GLOBAL"},
        akshare="RB0",
        vn_proxies=("HPG", "HSG", "NKG", "GDA"),
        notes="RB0 = thep thanh van SHFE (CNY/tan), khac chuan HRC.",
    ),
    "steel_vn": Route(
        label="Thep xay dung noi dia VN",
        unit="nghin VND/kg",
        vndata="steel",
        vndata_kwargs={"market": "VN"},
        vn_proxies=("HPG", "HSG", "NKG", "GDA", "VGS"),
        notes="Chi vndata co chuoi nay.",
    ),
    "iron_ore": Route(
        label="Quang sat 62% Fe",
        unit="USD/tan",
        yahoo="TIO=F",
        akshare="I0",
        vn_proxies=("HPG",),
        notes="KHONG dung vndata iron_ore - chuoi chet tu 07/03/2025 va tra 0 dong ma khong bao loi.",
    ),
    "coke": Route(
        label="Than coc",
        unit="CNY/tan",
        akshare="J0",
        vn_proxies=("HPG",),
        notes="KHONG dung vndata coke - chet tu 07/03/2025. Chi con DCE J0.",
    ),
    "rubber": Route(
        label="Cao su",
        unit="CNY/tan",
        akshare="RU0",
        vn_proxies=("PHR", "DPR", "GVR", "DRC", "CSM"),
        crawl_urls=(
            "https://www.investing.com/commodities/rubber-usd",
            "https://tradingeconomics.com/commodity/rubber",
        ),
        notes="Khong co ma Yahoo, khong co trong vndata. RU0 = SHFE. TSR20 Singapore phai crawl. .firecrawl/phr_*.json da co san.",
    ),
    "sugar": Route(
        label="Duong tho #11",
        unit="US cent/lb",
        yahoo="SB=F",
        vndata="sugar",
        akshare="SR0",
        vn_proxies=("SBT", "LSS", "QNS"),
        crosscheck=False,
        notes="BA hop dong KHAC NHAU: Yahoo SB=F = duong tho #11 (cent/lb); vndata sugar = duong trang London (USD/tan); SR0 = CZCE (CNY/tan). Khong duoc tron. Chenh trang-tho la 'white premium', khong phai loi du lieu.",
    ),
    "corn": Route(
        label="Ngo",
        unit="US cent/bushel",
        yahoo="ZC=F",
        vndata="corn",
        vn_proxies=("DBC", "BAF", "MML"),
    ),
    "soybean": Route(
        label="Dau tuong",
        unit="US cent/bushel",
        yahoo="ZS=F",
        vndata="soybean",
        vn_proxies=("DBC", "BAF", "MML"),
    ),
    "coffee": Route(
        label="Ca phe Arabica",
        unit="US cent/lb",
        yahoo="KC=F",
        vn_proxies=("PAN", "LTG"),
        notes="Robusta (sat voi VN hon) chi co gia moi nhat trong vndata 'listing'.",
    ),
    "pork": Route(
        label="Heo hoi VN",
        unit="VND/kg",
        vndata="pork",
        vn_proxies=("DBC", "BAF", "HAG", "MML"),
        notes="Tan suat tuan, khong phai ngay.",
    ),
    "urea": Route(
        label="Phan ure",
        unit="USD/tan",
        vndata="fertilizer_ure",
        vn_proxies=("DPM", "DCM", "LAS", "BFC"),
        crawl_urls=("https://tradingeconomics.com/commodity/urea",),
        notes="Chuoi cap nhat cham (~5 tuan tre). Kiem STALE truoc khi dung.",
    ),
}

# Boi canh vi mo tiem kem moi pack - cung mot bo cho moi mat hang.
MACRO_CONTEXT = {
    "DX-Y.NYB": "Chi so dollar DXY",
    "^TNX": "Loi suat TPCP My 10 nam (%)",
    "USDVND=X": "Ty gia USD/VND",
    "^GSPC": "S&P 500",
    "000001.SS": "Shanghai Composite",
}


def _today() -> date:
    return datetime.now().date()


def _series_from_yahoo(symbol: str, start: str) -> tuple[list[dict], str | None]:
    """Tra ve (rows, error). rows la [{'time','close'}...] tang dan theo thoi gian."""
    try:
        import yfinance as yf
    except ImportError:
        return [], "yfinance chua cai - dang chay nham venv? Phai la .venv cua project."
    try:
        df = yf.download(symbol, start=start, progress=False, auto_adjust=False)
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"
    if df is None or df.empty:
        return [], "khong co du lieu tra ve"
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    rows = [
        {"time": idx.date().isoformat(), "close": float(val)}
        for idx, val in close.items()
        if val == val  # loai NaN
    ]
    return rows, None


def _series_from_vndata(name: str, start: str, kwargs: dict) -> tuple[list[dict], str | None]:
    try:
        from vndata import macro
    except Exception as exc:
        return [], f"import vndata that bai: {exc}"
    try:
        df = macro.commodity(name, start=start, **kwargs)
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"
    if df is None or len(df) == 0:
        return [], "tra 0 dong (chuoi nay co the da chet - xem ghi chu route)"
    value_cols = [c for c in df.columns if c != "time"]
    rows = []
    for _, r in df.iterrows():
        row: dict = {"time": str(r["time"])[:10]}
        for c in value_cols:
            try:
                row[c] = float(r[c])
            except (TypeError, ValueError):
                row[c] = None
        if "close" not in row:
            # gold VN dung buy/sell; gas VN dung ron95/... - lay cot dau lam close
            row["close"] = row.get(value_cols[0])
        rows.append(row)
    return rows, None


def _series_from_akshare(symbol: str) -> tuple[list[dict], str | None]:
    try:
        import akshare as ak
    except ImportError:
        return [], "akshare chua cai - dang chay nham venv?"
    try:
        df = ak.futures_main_sina(symbol=symbol)
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"
    if df is None or df.empty:
        return [], "khong co du lieu tra ve"
    rows = [
        {"time": str(r.iloc[0])[:10], "close": float(r.iloc[4])}
        for _, r in df.iterrows()
    ]
    return rows, None


def _staleness(rows: list[dict]) -> tuple[str, int | None]:
    if not rows:
        return "EMPTY", None
    last = date.fromisoformat(rows[-1]["time"])
    age = (_today() - last).days
    return ("STALE" if age > STALE_DAYS else "LIVE"), age


def _fetch_vn_proxies(symbols: tuple[str, ...], start: str, end: str) -> dict:
    """Gia + khoi ngoai cac ma VN an theo hang hoa, qua DataPro."""
    out: dict = {}
    if not symbols:
        return out
    try:
        from vndata import price
    except Exception as exc:
        return {"_error": f"import vndata.price that bai: {exc}"}
    for sym in symbols:
        entry: dict = {}
        try:
            tail = price.ohlcv(sym, start, end).tail(10)
            entry["ohlcv"] = [
                {
                    "time": str(idx)[:10],
                    "close": float(r["close"]),
                    "volume": float(r["volume"]),
                    "value": float(r["value"]),
                }
                for idx, r in tail.iterrows()
            ]
        except Exception as exc:
            entry["ohlcv_error"] = f"{type(exc).__name__}: {exc}"
        try:
            ff = price.foreign_flow(sym, start, end).tail(10)
            entry["foreign_net_value"] = [
                {"time": str(idx)[:10], "net_value": float(r["net_value"])}
                for idx, r in ff.iterrows()
            ]
        except Exception as exc:
            entry["foreign_error"] = f"{type(exc).__name__}: {exc}"
        out[sym] = entry
    return out


def build(key: str, years: int = DEFAULT_YEARS) -> dict:
    """Keo moi nguon cho mot mat hang. Tra ve dict de ghi JSON + render markdown."""
    route = ROUTES[key]
    start = (_today() - timedelta(days=365 * years)).isoformat()
    end = _today().isoformat()

    pack: dict = {
        "key": key,
        "label": route.label,
        "unit": route.unit,
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "history_start": start,
        "notes": route.notes,
        "crawl_urls": list(route.crawl_urls),
        "sources": {},
        "warnings": [],
    }

    if route.yahoo:
        rows, err = _series_from_yahoo(route.yahoo, start)
        status, age = _staleness(rows)
        pack["sources"]["yahoo"] = {
            "symbol": route.yahoo, "unit": route.unit, "status": status,
            "age_days": age, "error": err, "rows": len(rows), "series": rows,
        }
    if route.vndata:
        rows, err = _series_from_vndata(route.vndata, start, route.vndata_kwargs)
        status, age = _staleness(rows)
        pack["sources"]["vndata"] = {
            "symbol": route.vndata, "kwargs": route.vndata_kwargs, "unit": route.unit,
            "status": status, "age_days": age, "error": err, "rows": len(rows), "series": rows,
        }
    if route.akshare:
        rows, err = _series_from_akshare(route.akshare)
        rows = [r for r in rows if r["time"] >= start]
        status, age = _staleness(rows)
        pack["sources"]["akshare"] = {
            "symbol": route.akshare, "unit": route.akshare_unit, "status": status,
            "age_days": age, "error": err, "rows": len(rows), "series": rows,
        }

    for name, src in pack["sources"].items():
        if src["status"] != "LIVE":
            pack["warnings"].append(
                f"{name}:{src['symbol']} = {src['status']}"
                + (f" (bar cuoi cach {src['age_days']} ngay)" if src["age_days"] is not None else "")
                + (f" - {src['error']}" if src.get("error") else "")
            )

    # Kiem cheo hai nguon USD (Yahoo vs vndata). akshare la CNY, khong so sanh.
    y, v = pack["sources"].get("yahoo"), pack["sources"].get("vndata")
    if not route.crosscheck:
        pack["crosscheck"] = {
            "skipped": "hai nguon la hai chuan hop dong khac nhau - xem notes",
        }
    elif y and v and y["status"] == "LIVE" and v["status"] == "LIVE":
        # So o NGAY CHUNG cuoi cung va phai la NGAY TRONG TUAN. Yahoo dan mot
        # bar cuoi tuan bang cach lap lai gia dong cua thu Sau, trong khi vndata
        # co phien dien tu that - so thang bar cuoi voi bar cuoi bien cai do
        # thanh "lech nguon" gia. Vi du 06/09/2026 la Chu nhat: Yahoo 91,48 (lap
        # lai thu Sau) vs vndata 91,96 -> bao lech 0,52%, trong khi moi phien
        # giao dich that hai ben khop den tung cent (0,000%).
        vmap = {r["time"]: r for r in v["series"]}
        common = [
            r for r in y["series"]
            if r["time"] in vmap and date.fromisoformat(r["time"]).weekday() < 5
        ]
        ly = common[-1] if common else None
        lv = vmap[ly["time"]] if ly else None
        if ly and lv and ly["close"] and lv["close"]:
            diff = abs(ly["close"] - lv["close"]) / ly["close"]
            pack["crosscheck"] = {
                "yahoo": ly, "vndata": lv, "rel_diff": round(diff, 6),
                "ok": diff <= CROSSCHECK_TOL,
            }
            if diff > CROSSCHECK_TOL:
                pack["warnings"].append(
                    f"LECH NGUON {diff:.2%}: Yahoo {ly['close']} ({ly['time']}) vs "
                    f"vndata {lv['close']} ({lv['time']}) - KHONG tu chon, phai kiem tay"
                )

    macro_ctx: dict = {}
    for sym, label in MACRO_CONTEXT.items():
        rows, err = _series_from_yahoo(sym, (_today() - timedelta(days=180)).isoformat())
        macro_ctx[sym] = {
            "label": label, "error": err,
            "series": rows[-20:], "latest": rows[-1] if rows else None,
        }
    pack["macro_context"] = macro_ctx

    pack["vn_proxies"] = list(route.vn_proxies)
    pack["vn_proxy_data"] = _fetch_vn_proxies(
        route.vn_proxies, (_today() - timedelta(days=30)).isoformat(), end
    )
    pack["live_sources"] = [n for n, s in pack["sources"].items() if s["status"] == "LIVE"]
    return pack


def _fmt_tail(series: list[dict], n: int = 12) -> str:
    if not series:
        return "  (khong co du lieu)"
    keys = [k for k in series[-1].keys() if k != "time"]
    head = "  | ngay       | " + " | ".join(f"{k:>12}" for k in keys) + " |"
    sep = "  |------------|" + "|".join(["-" * 14] * len(keys)) + "|"
    lines = [head, sep]
    for r in series[-n:]:
        vals = " | ".join(
            f"{r[k]:>12,.4f}" if isinstance(r.get(k), float) else f"{str(r.get(k)):>12}"
            for k in keys
        )
        lines.append(f"  | {r['time']} | {vals} |")
    return "\n".join(lines)


def render_markdown(pack: dict, horizon: str) -> str:
    """Khoi se duoc tiem vao MOI worker qua private_context."""
    L: list[str] = []
    A = L.append
    A("## DATA PACK - GIA THAT, BAT BUOC DUNG")
    A("")
    A(f"**Mat hang:** {pack['label']} (`{pack['key']}`) - **Don vi:** {pack['unit']} - "
      f"**Tam nhin:** {horizon}")
    A(f"**Keo luc:** {pack['built_at']} - **Lich su tu:** {pack['history_start']}")
    A("")
    A("> Day la **nguon gia duy nhat** ban duoc trich. Moi con so gia/khoi luong trong")
    A("> bao cao phai truy nguoc ve khoi nay, hoac ve mot URL ban vua doc bang `read_url`")
    A("> va co dan link. Khong duoc dung gia tu tri nho mo hinh - no sai theo dinh nghia.")
    A("")

    if pack["warnings"]:
        A("### CANH BAO NGUON")
        for w in pack["warnings"]:
            A(f"- {w}")
        A("")

    if pack.get("notes"):
        A(f"**Ghi chu dinh tuyen:** {pack['notes']}")
        A("")

    cc = pack.get("crosscheck")
    if cc and cc.get("skipped"):
        A(f"**Kiem cheo Yahoo vs vndata:** BO QUA - {cc['skipped']}. Hai chuoi duoi day do "
          "hai chuan hop dong khac nhau, chenh lech giua chung KHONG phai loi du lieu; "
          "trich so nao thi phai noi ro chuan nao.")
        A("")
    elif cc:
        verdict = "KHOP" if cc["ok"] else "LECH - PHAI KIEM TAY"
        A(f"**Kiem cheo Yahoo vs vndata:** {cc['yahoo']['close']} vs {cc['vndata']['close']} "
          f"-> lech {cc['rel_diff']:.4%} - {verdict}")
        A("")

    A("### Chuoi gia")
    for name, src in pack["sources"].items():
        A("")
        A(f"**{name} - `{src['symbol']}` - {src['unit']} - {src['status']} - "
          f"{src['rows']} bar**" + (f" - LOI: {src['error']}" if src.get("error") else ""))
        A(_fmt_tail(src["series"]))
    A("")

    A("### Boi canh vi mo")
    A("")
    A("  | ma         | y nghia                              | ngay       | gia |")
    A("  |------------|--------------------------------------|------------|-----|")
    for sym, m in pack["macro_context"].items():
        if m["latest"]:
            A(f"  | {sym:<10} | {m['label']:<36} | {m['latest']['time']} | "
              f"{m['latest']['close']:,.4f} |")
        else:
            A(f"  | {sym:<10} | {m['label']:<36} | - | LOI: {m['error']} |")
    A("")

    if pack["vn_proxies"]:
        A("### Co phieu VN an theo mat hang nay (DataPro, 10 phien gan nhat)")
        A("")
        for sym in pack["vn_proxies"]:
            d = pack["vn_proxy_data"].get(sym, {})
            oh = d.get("ohlcv") or []
            ff = d.get("foreign_net_value") or []
            if not oh:
                A(f"- **{sym}**: khong lay duoc - {d.get('ohlcv_error', 'khong ro')}")
                continue
            first, last = oh[0], oh[-1]
            chg = (last["close"] / first["close"] - 1) * 100 if first["close"] else 0.0
            netsum = sum(r["net_value"] for r in ff) if ff else None
            netstr = (f", khoi ngoai rong 10 phien {netsum:,.0f} (nghin VND)"
                      if netsum is not None else "")
            A(f"- **{sym}**: {last['close']:,.2f} ({last['time']}), 10 phien {chg:+.2f}%{netstr}")
        A("")
        A(f"Backtest chi duoc chay tren cac ma nay voi `\"source\": \"datapro\"` va ma dang "
          f"`{pack['vn_proxies'][0]}.VN`. Hop dong hang hoa toan cau KHONG backtest duoc "
          f"tren may nay - dung co thu.")
        A("")

    if pack["crawl_urls"]:
        A("### Can doc them bang read_url (nguon so chua phu)")
        for u in pack["crawl_urls"]:
            A(f"- {u}")
        A("")
    return "\n".join(L)


def main() -> int:
    p = argparse.ArgumentParser(description="Dung data pack hang hoa cho swarm.")
    p.add_argument("commodity", nargs="?", help="ma mat hang, vd oil_crude")
    p.add_argument("--horizon", default="6 thang")
    p.add_argument("--years", type=int, default=DEFAULT_YEARS)
    p.add_argument("--outdir", default=None)
    p.add_argument("--list", action="store_true", help="liet ke mat hang co san")
    args = p.parse_args()

    if args.list or not args.commodity:
        print(f"{'ma':<12} {'ten':<32} {'nguon':<30} proxy VN")
        print("-" * 100)
        for k, r in ROUTES.items():
            srcs = ",".join(
                s for s in (
                    f"yahoo:{r.yahoo}" if r.yahoo else "",
                    f"vndata:{r.vndata}" if r.vndata else "",
                    f"ak:{r.akshare}" if r.akshare else "",
                ) if s
            )
            print(f"{k:<12} {r.label:<32} {srcs:<30} {','.join(r.vn_proxies)}")
        return 0

    if args.commodity not in ROUTES:
        print(f"[LOI] khong biet mat hang '{args.commodity}'. Chay --list de xem danh sach.")
        return 1

    print(f"Dang keo du lieu cho {args.commodity} ...", flush=True)
    pack = build(args.commodity, years=args.years)

    outdir = Path(args.outdir) if args.outdir else (
        Path(__file__).resolve().parents[2]
        / f"_commodity_{args.commodity}_{_today().strftime('%Y%m%d')}"
    )
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "datapack.md").write_text(render_markdown(pack, args.horizon), encoding="utf-8")
    (outdir / "datapack.json").write_text(
        json.dumps(pack, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )

    print()
    for name, src in pack["sources"].items():
        flag = "[OK]  " if src["status"] == "LIVE" else "[CHET]"
        print(f"{flag} {name:<8} {src['symbol']:<10} {src['status']:<6} "
              f"{src['rows']:>5} bar" + (f"  {src['error']}" if src.get("error") else ""))
    for w in pack["warnings"]:
        print(f"[CANH BAO] {w}")
    print()
    print(f"datapack.md   -> {outdir / 'datapack.md'}")
    print(f"datapack.json -> {outdir / 'datapack.json'}")

    if not pack["live_sources"]:
        print()
        print("[LOI] KHONG con nguon gia nao song cho mat hang nay.")
        if pack["crawl_urls"]:
            print("      Phai crawl tay truoc khi chay swarm:")
            for u in pack["crawl_urls"]:
                print(f"        {u}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
