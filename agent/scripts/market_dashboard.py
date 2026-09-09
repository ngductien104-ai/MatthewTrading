#!/usr/bin/env python3
"""Dung dashboard HTML cho ban tin thi truong VN tu data pack + narrative agent.

Phan cong ro rang, va day la ly do file nay ton tai:

* **So** doc thang tu CSV cua ``market_datapack.py``. Khong con so nao di qua
  mo hinh ngon ngu, nen khong co duong cho no bia.
* **Chu** doc tu ``narrative.json`` do agent editor ghi. Agent khong duoc viet
  mot con so nao vao day ngoai cac truong nhan dinh.

Bo cuc muon tu Fincept Terminal (Master Guide, muc "Market Pulse rail" va
"Reading the wire"): mot cot Pulse co dinh ben phai doc trong 5 giay, than trai
la heatmap nganh + ma tran Gia x Tien + hai bang dong tien + news wire.

Chay::

    $HOME/.venv/Scripts/python.exe agent/scripts/market_dashboard.py _market_20260909 \
        --session morning

Khong can matplotlib hay playwright - bieu do la SVG noi tuyen.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from datetime import datetime
from pathlib import Path

GREEN, RED, GREY = "#12a150", "#e5484d", "#8b949e"
INK, MUTED, LINE = "#0b2545", "#5a6b85", "#e3e8ef"
INDIGO = "#575ECF"


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def esc(value):
    return html.escape(str(value if value is not None else ""))


def colour(value):
    v = num(value)
    return GREEN if v > 0 else RED if v < 0 else GREY


def signed(value, digits=2, suffix=""):
    v = num(value)
    return f'<span style="color:{colour(v)}">{v:+,.{digits}f}{suffix}</span>'


# --------------------------------------------------------------------------
# Bieu do SVG noi tuyen - khong phu thuoc thu vien ve
# --------------------------------------------------------------------------

def svg_line(values, width=520, height=110, stroke=INDIGO):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return '<div class="muted">Khong du diem de ve</div>'
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    step = width / (len(vals) - 1)
    pts = " ".join(
        f"{i * step:.1f},{height - (v - lo) / span * (height - 12) - 6:.1f}"
        for i, v in enumerate(vals)
    )
    zero = ""
    if lo < 0 < hi:
        y = height - (0 - lo) / span * (height - 12) - 6
        zero = f'<line x1="0" y1="{y:.1f}" x2="{width}" y2="{y:.1f}" stroke="{LINE}" stroke-dasharray="3 3"/>'
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
            f'preserveAspectRatio="none">{zero}'
            f'<polyline fill="none" stroke="{stroke}" stroke-width="2" points="{pts}"/></svg>')


def svg_bars(labels, values, width=520, height=190):
    if not values:
        return '<div class="muted">Khong co du lieu</div>'
    peak = max(abs(num(v)) for v in values) or 1
    n = len(values)
    bw = width / n * 0.62
    gap = width / n
    mid = height - 34
    body = [f'<line x1="0" y1="{mid}" x2="{width}" y2="{mid}" stroke="{LINE}"/>']
    for i, (lab, val) in enumerate(zip(labels, values)):
        v = num(val)
        h = abs(v) / peak * (mid - 8)
        x = i * gap + (gap - bw) / 2
        y = mid - h if v >= 0 else mid
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                    f'fill="{colour(v)}" opacity="0.85"><title>{esc(lab)}: {v:,.1f}</title></rect>')
        body.append(f'<text x="{x + bw / 2:.1f}" y="{height - 20}" font-size="9" '
                    f'text-anchor="end" fill="{MUTED}" '
                    f'transform="rotate(-40 {x + bw / 2:.1f} {height - 20})">{esc(lab)[:16]}</text>')
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}">'
            + "".join(body) + "</svg>")


# --------------------------------------------------------------------------
# Khoi noi dung
# --------------------------------------------------------------------------

def block_indices(rows):
    cells = []
    for r in rows:
        if r.get("status") != "OK":
            cells.append(f'<div class="idx dead"><b>{esc(r["index"])}</b>'
                         f'<span class="muted">{esc(r.get("status"))}</span></div>')
            continue
        pct = num(r["pct_change"])
        cells.append(
            f'<div class="idx"><b>{esc(r["index"])}</b>'
            f'<span class="big" style="color:{colour(pct)}">{num(r["close"]):,.2f}</span>'
            f'<span style="color:{colour(pct)}">{num(r["change"]):+,.2f} ({pct:+.2f}%)</span>'
            f'<span class="muted">{num(r["low"]):,.2f} - {num(r["high"]):,.2f}</span>'
            f'<span class="muted">GTGD {num(r["value_ty"]):,.0f} ty '
            f'({num(r["value_vs_avg20_pct"]):+.0f}% vs BQ20)</span></div>')
    return '<div class="idxrow">' + "".join(cells) + "</div>"


def block_breadth(rows):
    total = next((r for r in rows if r["scope"] == "TOAN_TT"), None)
    if not total:
        return ""
    adv, dec, unc = (int(num(total[k])) for k in ("advancers", "decliners", "unchanged"))
    tot = max(adv + dec + unc, 1)
    bar = (f'<div class="adbar">'
           f'<div style="width:{adv / tot * 100:.1f}%;background:{GREEN}"></div>'
           f'<div style="width:{unc / tot * 100:.1f}%;background:{GREY}"></div>'
           f'<div style="width:{dec / tot * 100:.1f}%;background:{RED}"></div></div>')
    head = "".join(f"<th>{h}</th>" for h in
                   ["Pham vi", "Tang", "Giam", "TC", "Tran", "San", "A/D",
                    "%>MA20", "%>MA50", "%>MA200"])
    body = "".join(
        f'<tr><td><b>{esc(r["scope"])}</b></td>'
        f'<td style="color:{GREEN}">{r["advancers"]}</td>'
        f'<td style="color:{RED}">{r["decliners"]}</td><td>{r["unchanged"]}</td>'
        f'<td style="color:{GREEN}">{r["ceiling"]}</td>'
        f'<td style="color:{RED}">{r["floor"]}</td><td>{r["ad_ratio"]}</td>'
        f'<td>{r["pct_above_ma20"]}</td><td>{r["pct_above_ma50"]}</td>'
        f'<td>{r["pct_above_ma200"]}</td></tr>' for r in rows)
    return bar + f'<table class="tbl"><tr>{head}</tr>{body}</table>'


def block_sector_heat(rows, top=18):
    tiles = []
    for r in rows[:top]:
        pct = num(r["pct_change_wavg"])
        strength = min(abs(pct) / 2.5, 1.0)
        bg = (f"rgba(18,161,80,{0.10 + strength * 0.55})" if pct > 0
              else f"rgba(229,72,77,{0.10 + strength * 0.55})" if pct < 0
              else "rgba(139,148,158,0.12)")
        tiles.append(
            f'<div class="tile" style="background:{bg}">'
            f'<b>{esc(r["icb_name"])}</b>'
            f'<span class="pct" style="color:{colour(pct)}">{pct:+.2f}%</span>'
            f'<span class="muted">{num(r["value_ty"]):,.0f} ty '
            f'&middot; {num(r["pct_of_market_value"]):.1f}% GTGD</span>'
            f'<span class="muted">do rong {num(r["breadth_in_sector"]):.0f}% '
            f'&middot; ngoai {num(r["foreign_net_ty"]):+,.0f}</span></div>')
    return '<div class="tiles">' + "".join(tiles) + "</div>"


def block_matrix(matrix):
    quads = [("tang_vao", "Gia TANG &middot; Tien VAO", "dan dat that", GREEN),
             ("tang_ra", "Gia TANG &middot; Tien RA", "tang yeu - canh bao", "#c98a00"),
             ("giam_vao", "Gia GIAM &middot; Tien VAO", "tich luy / bat day", INDIGO),
             ("giam_ra", "Gia GIAM &middot; Tien RA", "phan phoi", RED)]
    cells = []
    for key, title, note, col in quads:
        items = matrix.get(key) or []
        lis = "".join(f"<li>{esc(x)}</li>" for x in items) or '<li class="muted">-</li>'
        cells.append(f'<div class="quad" style="border-top:3px solid {col}">'
                     f'<b>{title}</b><span class="muted">{note}</span><ul>{lis}</ul></div>')
    return '<div class="matrix">' + "".join(cells) + "</div>"


def block_flow_table(rows, cols, headers, limit=12):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = []
    for r in rows[:limit]:
        tds = []
        for c in cols:
            v = r.get(c, "")
            if c in ("symbol",):
                tds.append(f"<td><b>{esc(v)}</b></td>")
            elif c == "flip":
                tds.append(f'<td><span class="flip">{esc(v)}</span></td>' if v else "<td></td>")
            elif isinstance(v, str) and v.replace("-", "").replace(".", "").isdigit():
                tds.append(f'<td style="color:{colour(v)}">{num(v):+,.1f}</td>')
            else:
                tds.append(f"<td>{esc(v)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table class="tbl"><tr>{head}</tr>' + "".join(body) + "</table>"


def block_wire(items):
    if not items:
        return '<div class="muted">Khong co tin trong cua so theo doi.</div>'
    rows = []
    for it in items:
        d = str(it.get("dir", "0"))
        arrow = ("&#9650;" if d == "+" else "&#9660;" if d == "-" else "&#9679;")
        col = GREEN if d == "+" else RED if d == "-" else GREY
        pri = esc(it.get("priority", "TB"))
        tickers = " ".join(f'<span class="tick">{esc(t)}</span>'
                           for t in (it.get("tickers") or []))
        src = esc(it.get("source", ""))
        if it.get("n_sources", 1) and int(it.get("n_sources", 1)) > 1:
            src += f' <span class="muted">+{int(it["n_sources"]) - 1} nguon</span>'
        rows.append(
            f'<div class="wire"><span class="age">{esc(it.get("age", ""))}</span>'
            f'<span class="pri p{pri}">{pri}</span>'
            f'<span class="src">{src}</span>'
            f'<span class="ttl">{esc(it.get("title", ""))}</span>'
            f'<span style="color:{col}">{arrow}</span>'
            f'<span class="ticks">{tickers}</span></div>')
    return "".join(rows)


def block_pulse(idx, breadth, sector, flow30, nar, session):
    total = next((r for r in breadth if r["scope"] == "TOAN_TT"), {})
    vni = next((r for r in idx if r["index"] == "VNINDEX" and r.get("status") == "OK"), {})
    sent = nar.get("news_desk", {}).get("sentiment")
    up = sorted(sector, key=lambda r: -num(r["pct_change_wavg"]))[:3]
    down = sorted(sector, key=lambda r: num(r["pct_change_wavg"]))[:3]
    frn = sum(num(r["foreign_net_ty"]) for r in sector)

    def rail(title, inner):
        return f'<div class="prail"><h4>{title}</h4>{inner}</div>'

    sent_html = ('<div class="muted">chua cham</div>' if sent is None else
                 f'<div class="gauge"><div style="left:{(num(sent) + 1) / 2 * 100:.0f}%"></div></div>'
                 f'<div class="big" style="color:{colour(sent)}">{num(sent):+.2f}</div>')
    return "".join([
        rail("VN-INDEX", f'<div class="big" style="color:{colour(vni.get("pct_change"))}">'
                         f'{num(vni.get("close")):,.2f}</div>'
                         f'<div>{signed(vni.get("change"))} ({signed(vni.get("pct_change"), 2, "%")})</div>'),
        rail("DO RONG", f'<div class="kv"><span>Tang</span><b style="color:{GREEN}">'
                        f'{total.get("advancers", "-")}</b></div>'
                        f'<div class="kv"><span>Giam</span><b style="color:{RED}">'
                        f'{total.get("decliners", "-")}</b></div>'
                        f'<div class="kv"><span>Tran / San</span><b>{total.get("ceiling", "-")}'
                        f' / {total.get("floor", "-")}</b></div>'
                        f'<div class="kv"><span>% tren MA50</span><b>'
                        f'{total.get("pct_above_ma50", "-")}%</b></div>'),
        rail("NGANH MANH", "".join(
            f'<div class="kv"><span>{esc(r["icb_name"])[:20]}</span>'
            f'<b style="color:{GREEN}">{num(r["pct_change_wavg"]):+.2f}%</b></div>' for r in up)),
        rail("NGANH YEU", "".join(
            f'<div class="kv"><span>{esc(r["icb_name"])[:20]}</span>'
            f'<b style="color:{RED}">{num(r["pct_change_wavg"]):+.2f}%</b></div>' for r in down)),
        rail("KHOI NGOAI", f'<div class="big" style="color:{colour(frn)}">{frn:+,.0f}</div>'
                           f'<div class="muted">ty VND, rong phien</div>'),
        rail("TU DOANH", '<div class="na">N/A</div><div class="muted">chua cong bo trong phien</div>'
             if session == "morning" else
             f'<div class="big" style="color:{colour(sum(num(r.get("prop_net_ty", 0)) for r in sector))}">'
             f'{sum(num(r.get("prop_net_ty", 0)) for r in sector):+,.0f}</div>'
             '<div class="muted">ty VND, rong phien</div>'),
        rail("TAM LY TIN", sent_html),
    ])


CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI",Arial,sans-serif;color:#0b2545;background:#f5f7fa;font-size:13px}
header{background:#0b2545;color:#fff;padding:14px 22px}
header h1{margin:0;font-size:19px;letter-spacing:.3px}
header .sub{color:#9fb3d1;font-size:12px;margin-top:3px}
.wrap{display:grid;grid-template-columns:1fr 250px;gap:16px;padding:16px 22px;align-items:start}
.card{background:#fff;border:1px solid #e3e8ef;border-radius:7px;padding:13px 15px;margin-bottom:14px}
.card h2{font-size:13px;margin:0 0 10px;color:#0b2545;text-transform:uppercase;letter-spacing:.6px;
  border-bottom:2px solid #0b2545;padding-bottom:5px}
.idxrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.idx{display:flex;flex-direction:column;gap:1px;padding:9px 11px;background:#fbfcfe;border:1px solid #e3e8ef;border-radius:6px}
.idx b{font-size:11px;color:#5a6b85;letter-spacing:.5px}
.idx.dead{opacity:.5}
.big{font-size:21px;font-weight:600;line-height:1.15}
.muted{color:#8b949e;font-size:11px}
.adbar{display:flex;height:16px;border-radius:3px;overflow:hidden;margin-bottom:11px}
.tbl{width:100%;border-collapse:collapse;font-size:12px}
.tbl th{background:#f0f3f8;color:#5a6b85;font-size:10.5px;text-transform:uppercase;
  letter-spacing:.4px;padding:5px 7px;text-align:right;border-bottom:1px solid #e3e8ef}
.tbl th:first-child,.tbl td:first-child{text-align:left}
.tbl td{padding:5px 7px;text-align:right;border-bottom:1px solid #f2f5f9}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:8px}
.tile{padding:8px 10px;border-radius:5px;display:flex;flex-direction:column;gap:1px;border:1px solid rgba(0,0,0,.05)}
.tile b{font-size:11.5px}
.tile .pct{font-size:16px;font-weight:600}
.matrix{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.quad{background:#fbfcfe;border:1px solid #e3e8ef;border-radius:6px;padding:9px 12px}
.quad b{font-size:11.5px}
.quad ul{margin:6px 0 0;padding-left:17px}
.quad li{font-size:12px;margin-bottom:2px}
.wire{display:grid;grid-template-columns:42px 46px 108px 1fr 16px 130px;gap:8px;align-items:baseline;
  padding:6px 0;border-bottom:1px solid #f2f5f9;font-size:12px}
.wire .age{color:#8b949e;font-size:11px}
.wire .src{color:#5a6b85;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pri{font-size:9.5px;padding:1px 4px;border-radius:3px;text-align:center;color:#fff;background:#8b949e}
.pri.pFLASH,.pri.pCAO{background:#e5484d}
.pri.pTB{background:#5a6b85}
.tick{display:inline-block;background:#eef1f7;border-radius:3px;padding:0 4px;margin-right:3px;font-size:10.5px}
.flip{background:#fff3cd;color:#8a6100;padding:1px 5px;border-radius:3px;font-size:10.5px;font-weight:600}
.prail{background:#fff;border:1px solid #e3e8ef;border-radius:7px;padding:10px 12px;margin-bottom:10px}
.prail h4{margin:0 0 6px;font-size:10px;color:#8b949e;letter-spacing:.9px}
.kv{display:flex;justify-content:space-between;font-size:12px;padding:2px 0}
.kv span{color:#5a6b85}
.na{font-size:19px;font-weight:600;color:#c98a00}
.gauge{position:relative;height:7px;border-radius:4px;margin:4px 0 5px;
  background:linear-gradient(90deg,#e5484d,#d9dee7,#12a150)}
.gauge div{position:absolute;top:-3px;width:3px;height:13px;background:#0b2545;border-radius:2px}
.lead{font-size:14px;line-height:1.65}
.lead li{margin-bottom:5px}
.verdict{display:inline-block;padding:3px 10px;border-radius:4px;font-weight:600;font-size:12px}
.warn{background:#fff3cd;border:1px solid #ffe08a;border-radius:6px;padding:9px 12px;margin-top:9px;font-size:12px}
footer{padding:14px 22px;color:#8b949e;font-size:11px;border-top:1px solid #e3e8ef;background:#fff;line-height:1.7}
.narr{font-size:12.5px;line-height:1.65;white-space:pre-wrap}
"""

VERDICT_STYLE = {
    "xac_nhan": (GREEN, "DO RONG XAC NHAN"),
    "phan_ky": ("#c98a00", "DO RONG PHAN KY"),
    "ru_bo": (INDIGO, "RU BO / BREADTH CAI THIEN"),
}


def build(pack: Path, session: str, nar: dict) -> str:
    idx = read_csv(pack / "index.csv")
    breadth = read_csv(pack / "breadth.csv")
    sector = read_csv(pack / "sector.csv")
    leaders = read_csv(pack / "leaders.csv")
    movers = read_csv(pack / "index_movers.csv")
    ad = read_csv(pack / "ad_line.csv")
    fsess = read_csv(pack / "flow_session.csv")
    f30 = read_csv(pack / "flow_30d.csv")

    stamp = nar.get("stamp") or datetime.now().strftime("%Y-%m-%d %H:%M")
    day = nar.get("date") or pack.name.replace("_market_", "")
    label = "PHIEN SANG (11h30)" if session == "morning" else "DONG CUA (15h00)"

    ma = nar.get("market_action", {})
    vcol, vtext = VERDICT_STYLE.get(ma.get("verdict", ""), (GREY, "CHUA CHAM"))

    bullets = "".join(f"<li>{esc(b)}</li>" for b in nar.get("bullets", []))
    contra = nar.get("contradictions") or []
    contra_html = ("".join(f'<div class="warn"><b>Mau thuan giua cac ban:</b> {esc(c)}</div>'
                           for c in contra))

    frn_sess = sorted(fsess, key=lambda r: -num(r["foreign_net_ty"]))
    frn_sell = sorted(fsess, key=lambda r: num(r["foreign_net_ty"]))
    flips = [r for r in f30 if r.get("flip")]

    ad_vals = [num(r["ad_line"]) for r in ad]
    sec_top = sorted(sector, key=lambda r: -abs(num(r["foreign_net_ty"])))[:12]

    left = "".join([
        f'<div class="card"><h2>Tom luoc phien</h2><ul class="lead">{bullets}</ul>'
        f'<span class="verdict" style="background:{vcol}1a;color:{vcol}">{vtext}</span>'
        f'{contra_html}</div>',

        f'<div class="card"><h2>Chi so</h2>{block_indices(idx)}</div>',

        f'<div class="card"><h2>Do rong thi truong</h2>{block_breadth(breadth)}'
        f'<h3 style="font-size:12px;margin:14px 0 4px;color:#5a6b85">Duong A/D 30 phien</h3>'
        f'{svg_line(ad_vals)}'
        f'<div class="narr" style="margin-top:9px">{esc(ma.get("text", ""))}</div></div>',

        f'<div class="card"><h2>Heatmap nganh (ICB cap 2)</h2>{block_sector_heat(sector)}</div>',

        f'<div class="card"><h2>Ma tran Gia x Tien</h2>'
        f'{block_matrix(nar.get("sector_desk", {}).get("matrix", {}))}'
        f'<div class="narr" style="margin-top:10px">'
        f'{esc(nar.get("sector_desk", {}).get("text", ""))}</div></div>',

        f'<div class="card"><h2>Top GTGD &middot; nhom dan dat</h2>'
        f'{block_flow_table(leaders, ["symbol", "icb_name", "close", "pct_change", "value_ty", "foreign_net_ty", "idx_points_est"], ["Ma", "Nganh", "Gia", "%", "GTGD ty", "Ngoai rong", "Diem (uoc)"], 15)}'
        f'<div class="muted" style="margin-top:6px">Cot "Diem (uoc)" tinh theo von hoa niem yet, '
        f'khong phai free-float cua HOSE - dung de xep hang, khong phai so chinh thuc.</div></div>',

        f'<div class="card"><h2>Keo &amp; dim VN-Index</h2>'
        f'{svg_bars([r["symbol"] for r in movers], [num(r["idx_points_est"]) for r in movers])}</div>',

        f'<div class="card"><h2>Khoi ngoai - trong phien</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">'
        f'<div><h3 style="font-size:12px;color:{GREEN};margin:0 0 5px">Gom manh nhat</h3>'
        f'{block_flow_table(frn_sess, ["symbol", "icb_name", "pct_change", "foreign_net_ty"], ["Ma", "Nganh", "%", "Rong ty"], 10)}</div>'
        f'<div><h3 style="font-size:12px;color:{RED};margin:0 0 5px">Xa manh nhat</h3>'
        f'{block_flow_table(frn_sell, ["symbol", "icb_name", "pct_change", "foreign_net_ty"], ["Ma", "Nganh", "%", "Rong ty"], 10)}</div></div>'
        f'<h3 style="font-size:12px;margin:14px 0 4px;color:#5a6b85">Ngoai rong theo nganh (ty VND, phien)</h3>'
        f'{svg_bars([r["icb_name"][:14] for r in sec_top], [num(r["foreign_net_ty"]) for r in sec_top])}'
        f'<div class="narr" style="margin-top:9px">{esc(nar.get("flow_desk", {}).get("text", ""))}</div></div>',

        f'<div class="card"><h2>Luy ke 30 phien &amp; doi chieu</h2>'
        f'{block_flow_table(flips or f30, ["symbol", "icb_name", "foreign_net_30d_ty", "foreign_net_ty", "flip"], ["Ma", "Nganh", "Rong 30 phien", "Rong phien", ""], 14)}'
        f'<div class="muted" style="margin-top:6px">'
        f'{"Cac ma dao chieu so voi 30 phien truoc." if flips else "Khong ma nao doi chieu ro rang."}'
        f'</div></div>',

        f'<div class="card"><h2>Tin tuc &amp; su kien</h2>{block_wire(nar.get("news_desk", {}).get("wire", []))}'
        + (('<div class="warn"><b>Bien dong khong co tin:</b> '
            + esc("; ".join(nar["news_desk"]["unexplained"])) + "</div>")
           if nar.get("news_desk", {}).get("unexplained") else "")
        + (('<h3 style="font-size:12px;margin:14px 0 4px;color:#5a6b85">Lich 5 phien toi</h3><ul class="lead">'
            + "".join(f"<li>{esc(x)}</li>" for x in nar["news_desk"]["calendar"]) + "</ul>")
           if nar.get("news_desk", {}).get("calendar") else "")
        + "</div>",
    ])

    pulse = block_pulse(idx, breadth, sector, f30, nar, session)
    sources = esc(nar.get("sources_note", ""))
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ban tin thi truong VN {day} - {label}</title><style>{CSS}</style></head><body>
<header><h1>BAN TIN THI TRUONG VIET NAM &middot; {day}</h1>
<div class="sub">{label} &middot; so chot luc {stamp} &middot; nguon gia va dong tien: DataPro &middot;
nganh ICB va tin: vnstock_data / vnstock_news</div></header>
<div class="wrap"><div>{left}</div><aside>{pulse}</aside></div>
<footer>
<b>Nguon va gioi han.</b> Moi con so trong trang nay doc truc tiep tu data pack
<code>{esc(pack.name)}</code> do <code>market_datapack.py</code> dung tu DataPro; phan chu do agent viet
va khong duoc chua so nao ngoai pack.<br>
Do rong, tran/san tinh tu <code>ref_price</code> voi bien do HOSE 7% / HNX 10% / UPCoM 15%.
Dong gop diem so la uoc luong theo von hoa niem yet, khong phai so free-float cua HOSE.
{"Tu doanh o ban phien sang la N/A that su - DataPro chi cong bo sau dong cua." if session == "morning" else ""}
{sources}
</footer></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Dung dashboard HTML tu data pack + narrative")
    ap.add_argument("pack", help="Thu muc data pack, vd _market_20260909")
    ap.add_argument("--session", choices=["morning", "close"], required=True)
    ap.add_argument("--narrative", default=None, help="narrative.json (mac dinh trong pack)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pack = Path(args.pack)
    if not (pack / "index.csv").exists():
        print(f"LOI: khong thay index.csv trong {pack} - chay market_datapack.py truoc.",
              file=sys.stderr)
        return 1

    # Hai phien cua cung mot ngay dung chung thu muc, nen narrative phai tach
    # theo phien - neu khong ban 15h10 se de len ban 11h40.
    if args.narrative:
        nar_path = Path(args.narrative)
    else:
        nar_path = pack / f"narrative_{args.session}.json"
        if not nar_path.exists() and (pack / "narrative.json").exists():
            nar_path = pack / "narrative.json"
    nar = json.loads(nar_path.read_text(encoding="utf-8")) if nar_path.exists() else {}
    if not nar:
        print(f"CANH BAO: khong co {nar_path.name} - dung ban chi co so, khong co nhan dinh.",
              file=sys.stderr)

    out = Path(args.out) if args.out else pack / f"BRIEF_{args.session}.html"
    out.write_text(build(pack, args.session, nar), encoding="utf-8")
    print(f"XONG -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
