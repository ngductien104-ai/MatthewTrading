#!/usr/bin/env python3
"""Dung dashboard HTML cho ban tin thi truong VN tu data pack + narrative agent.

Phan cong ro rang, va day la ly do file nay ton tai:

* **So** doc thang tu CSV cua ``market_datapack.py`` va ``signal_tracker.py``.
  Khong con so nao di qua mo hinh ngon ngu, nen khong co duong cho no bia.
* **Chu** doc tu ``narrative_<session>.json`` do agent editor ghi. Agent khong
  duoc viet mot con so nao vao day ngoai ``news_desk.sentiment``.

He mau bam ``DESIGN.md`` cua Fincept Terminal - bang mau DONG, khong mot hex
nao ngoai bay mau da dang ky duoc phep xuat hien:

    #000000 nen · #0d0b0a panel · #ede8c8 chu nga · #aaa080 phu
    #302a22 vien · #ff7722 cam tieu diem · #00dd66 xanh song

Quy uoc TTCK VN cua he do: **xanh tang, CAM giam, nga dung gia** -- khong dung
mau do o bat ky dau. Chu IBM Plex Mono, bo goc 0px, vien 1px, luoi 4px.

Chay::

    $HOME/.venv/Scripts/python.exe agent/scripts/market_dashboard.py _market_20260909 \\
        --session close

Khong can matplotlib hay playwright - bieu do la SVG noi tuyen, tuong tac la
JS thuan nhung trong file.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ── bang mau dong ────────────────────────────────────────────────────────
BG, SURFACE, FG = "#000000", "#0d0b0a", "#ede8c8"
MUTED, BORDER, ACCENT, LIVE = "#aaa080", "#302a22", "#ff7722", "#00dd66"


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def esc(v):
    return html.escape(str(v if v is not None else ""))


def vn(v, d=2, plus=False):
    """So kieu Viet: dau phay thap phan, dau cach nhom nghin."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    t = f"{f:,.{d}f}".replace(",", " ").replace(".", ",")
    return ("+" + t) if (plus and f > 0) else t


def cls(v):
    f = num(v)
    return "up" if f > 0 else "down" if f < 0 else "flat"


def ty(v):
    """Doi so ty VND sang nhan gon: 1234.5 -> "1,2 nghin ty"."""
    a = abs(v)
    if not a:
        return "—"
    if a >= 1e6:
        return vn(v / 1e6, 2) + " triệu tỷ"
    if a >= 1e3:
        return vn(v / 1e3, 1) + " nghìn tỷ"
    return vn(v, 1) + " tỷ"


def mix(base, pct, onto):
    """Tron hai mau hex theo ty le phan tram.

    Ban CSS dung color-mix(); o day tron san ra hex de o nhiet hien dung mau
    ngay ca tren trinh duyet chua ho tro color-mix().
    O nhiet phai hien duoc ca khi trinh duyet khong biet color-mix().
    """
    b = [int(base[i:i + 2], 16) for i in (1, 3, 5)]
    o = [int(onto[i:i + 2], 16) for i in (1, 3, 5)]
    k = pct / 100
    return "#%02x%02x%02x" % tuple(round(b[i] * k + o[i] * (1 - k)) for i in range(3))


def bn(v):
    """Feed.fmt.bn cua Fincept: ty -> nghin ty -> trieu ty; 0 hien dau gach."""
    f = num(v, float("nan"))
    if f != f or f == 0:
        return "—"
    if abs(f) >= 1e6:
        return vn(f / 1e6, 2) + " triệu tỷ"
    if abs(f) >= 1e3:
        return vn(f / 1e3, 1) + " nghìn tỷ"
    return vn(f, 1) + " tỷ"


# ── SVG noi tuyen ────────────────────────────────────────────────────────

def svg_area(values, width=920, height=150, stroke=ACCENT):
    vals = [num(v) for v in values]
    if len(vals) < 2:
        return '<div class="empty">Không đủ điểm để vẽ</div>'
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    step = width / (len(vals) - 1)
    pts = [(i * step, height - 14 - (v - lo) / span * (height - 30)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = ("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
            + f" L{pts[-1][0]:.1f} {height} L{pts[0][0]:.1f} {height} Z")
    zero = ""
    if lo < 0 < hi:
        y = height - 14 - (0 - lo) / span * (height - 30)
        zero = (f'<line x1="0" y1="{y:.1f}" x2="{width}" y2="{y:.1f}" '
                f'stroke="{FG}" stroke-width="1" opacity=".45"/>')
    return (f'<svg viewBox="0 0 {width} {height}" style="width:100%;height:{height}px;display:block" '
            f'preserveAspectRatio="none">{zero}'
            f'<path d="{area}" fill="{stroke}" opacity="0.1"/>'
            f'<polyline points="{line}" fill="none" stroke="{stroke}" stroke-width="2"/></svg>')


def bar_rows(items, key, label_key="symbol", limit=8):
    """Bang thanh ngang - dung cho keo/dim chi so."""
    rows = items[:limit]
    if not rows:
        return '<div class="empty">Không có dữ liệu</div>'
    peak = max(abs(num(r[key])) for r in rows) or 1
    out = []
    for r in rows:
        v = num(r[key])
        c = cls(v)
        out.append(
            f'<tr><td class="sym" style="width:44px">{esc(r[label_key])}</td>'
            f'<td class="{c}" style="width:52px">{vn(r.get("pct_change"), 2, True)}</td>'
            f'<td style="padding:0 8px"><div style="height:8px;width:{abs(v)/peak*100:.1f}%;'
            f'background:var(--{c})"></div></td>'
            f'<td class="{c}" style="width:56px">{vn(v, 3, True)}</td></tr>')
    return '<table class="t"><tbody>' + "".join(out) + "</tbody></table>"


def table(cols, rows, limit=None, zebra=True):
    head = "".join(f"<th>{esc(h)}</th>" for _, h, _ in cols)
    body = []
    for r in (rows[:limit] if limit else rows):
        tds = []
        for key, _, kind in cols:
            v = r.get(key, "")
            if kind == "sym":
                tds.append(f'<td class="sym">{esc(v)}</td>')
            elif kind == "name":
                tds.append(f'<td class="name">{esc(v)}</td>')
            elif kind == "signed":
                tds.append(f'<td class="{cls(v)}">{vn(v, 2, True)}</td>')
            elif kind == "num":
                tds.append(f"<td>{vn(v, 2)}</td>")
            elif kind == "num1":
                tds.append(f"<td>{vn(v, 1)}</td>")
            else:
                tds.append(f"<td>{esc(v)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    z = " zebra" if zebra else ""
    # Boc trong .tw de bang tu cuon ngang tren man hinh hep thay vi day ca
    # trang tran ra - cot so deu la white-space:nowrap nen khong the co lai.
    return (f'<div class="tw"><table class="t{z}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def panel(title, note, body, foot=""):
    f = f'<div class="panel-foot">{foot}</div>' if foot else ""
    return (f'<div class="panel"><div class="panel-head"><span>/ {esc(title)}</span>'
            f'<span class="rule"></span><span>{esc(note)}</span></div>'
            f'<div class="panel-body">{body}</div>{f}</div>')


def call(kind, text, muted=False):
    style = ' style="border-color:var(--border);background:transparent"' if muted else ""
    k = ' style="color:var(--muted)"' if muted else ""
    return (f'<div class="call"{style}><div class="k"{k}>{esc(kind)}</div>'
            f"<p>{text}</p></div>")


CSS = """
:root{
  --bg:#000000;--surface:#0d0b0a;--fg:#ede8c8;--muted:#aaa080;
  --border:#302a22;--accent:#ff7722;--live:#00dd66;
  --raised:color-mix(in oklab,var(--surface) 62%,var(--border));
  --hairline:color-mix(in oklab,var(--border) 70%,var(--bg));
  --accent-wash:color-mix(in oklab,var(--accent) 14%,var(--bg));
  --live-wash:color-mix(in oklab,var(--live) 12%,var(--bg));
  --up:var(--live);--down:var(--accent);--flat:var(--muted);
  --font:"IBM Plex Mono","Courier New",monospace;
  --fs-micro:9px;--fs-label:10px;--fs-xs:11px;--fs-sm:12px;--fs-base:13px;
  --fs-md:15px;--fs-lg:19px;--fs-xl:26px;
  --s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:20px;--s6:24px;--bw:1px;
  --pulse-w:268px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--font);
  font-size:var(--fs-base);line-height:1.45;font-variant-numeric:tabular-nums}
a{color:var(--accent);text-decoration:none}a:hover{color:var(--fg)}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--flat)}
.acc{color:var(--accent)}.dim{color:var(--muted)}.right{margin-left:auto}
.row{display:flex;align-items:center;gap:var(--s2);flex-wrap:wrap}
.label{font-size:var(--fs-micro);font-weight:600;letter-spacing:.12em;
  color:var(--muted);text-transform:uppercase}
.empty{padding:var(--s5);text-align:center;color:var(--muted);font-size:var(--fs-xs)}
.top{display:flex;align-items:center;gap:var(--s3);height:40px;padding:0 var(--s4);
  background:var(--surface);border-bottom:var(--bw) solid var(--border)}
.wm{font-size:var(--fs-md);font-weight:700;letter-spacing:.2em}
.wm i{color:var(--accent);font-style:normal}
.ttl{font-size:var(--fs-xs);letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.chip{display:inline-flex;align-items:center;gap:var(--s1);padding:1px var(--s2);
  font-size:var(--fs-micro);font-weight:600;letter-spacing:.1em;text-transform:uppercase;
  border:var(--bw) solid var(--border);color:var(--muted)}
.chip.on{color:var(--live);border-color:var(--live)}
.chip.act{color:var(--accent);border-color:var(--accent)}
.tape{display:grid;grid-template-columns:repeat(4,1fr);gap:var(--bw);
  background:var(--border);border-bottom:var(--bw) solid var(--border)}
.ix{background:var(--surface);padding:var(--s2) var(--s3)}
.ix .px{font-size:var(--fs-xl);font-weight:700;line-height:1.05}
.ix .meta{font-size:var(--fs-micro);color:var(--muted);letter-spacing:.06em;margin-top:2px}
.rng{height:4px;background:var(--hairline);position:relative;margin-top:var(--s2)}
.rng i{position:absolute;top:-2px;width:2px;height:8px;background:var(--fg)}
.wrap{display:grid;grid-template-columns:minmax(0,1fr) var(--pulse-w);gap:var(--s3);
  padding:var(--s3) var(--s4) var(--s6);align-items:start}
.col{display:flex;flex-direction:column;gap:var(--s3);min-width:0}
.panel{border:var(--bw) solid var(--border);background:var(--surface);
  display:flex;flex-direction:column;min-width:0}
.panel-head{display:flex;align-items:center;gap:var(--s2);
  padding:var(--s2) var(--s2) var(--s2) 0;border-bottom:var(--bw) solid var(--border);
  font-size:var(--fs-sm);font-weight:700;letter-spacing:.16em;color:var(--fg);
  text-transform:uppercase}
.panel-head::before{content:"";width:3px;align-self:stretch;background:var(--accent)}
.panel-head .rule{flex:1;height:1px;background:var(--hairline)}
.panel-head>span:last-child{font-size:var(--fs-micro);font-weight:400;
  letter-spacing:.08em;color:var(--muted);text-transform:none}
.panel-body{padding:var(--s3)}
.panel-foot{padding:var(--s1) var(--s2);border-top:var(--bw) solid var(--hairline);
  font-size:var(--fs-micro);color:var(--muted);display:flex;gap:var(--s3)}
table.t{width:100%;border-collapse:collapse;font-size:var(--fs-xs)}
table.t th{text-align:right;padding:var(--s1) var(--s2);color:var(--muted);
  font-size:var(--fs-micro);font-weight:700;letter-spacing:.1em;text-transform:uppercase;
  white-space:nowrap;border-bottom:var(--bw) solid var(--border)}
table.t th:first-child,table.t td:first-child{text-align:left}
table.t td{text-align:right;padding:2px var(--s2);white-space:nowrap;
  border-bottom:var(--bw) solid var(--hairline)}
table.t td.sym{font-weight:700;color:var(--fg)}
table.t td.name{color:var(--muted);text-align:left;max-width:220px;
  overflow:hidden;text-overflow:ellipsis}
table.t.zebra tbody tr:nth-child(even) td{background:color-mix(in oklab,var(--surface) 88%,var(--bg))}
.btn{height:22px;padding:0 var(--s2);font-size:var(--fs-micro);font-weight:600;
  letter-spacing:.1em;color:var(--muted);text-transform:uppercase;background:var(--bg);
  border:var(--bw) solid var(--border);cursor:pointer;font-family:var(--font)}
.btn:hover{color:var(--fg);border-color:var(--muted)}
.btn[data-on="true"]{color:var(--accent);border-color:var(--accent)}
.seg{display:inline-flex;border:var(--bw) solid var(--border)}
.seg .btn{border:0;border-right:var(--bw) solid var(--border);height:20px}
.seg .btn:last-child{border-right:0}
.heat{display:grid;grid-auto-rows:minmax(0,1fr);gap:1px;background:var(--border)}
.heat-cell{display:flex;flex-direction:column;justify-content:center;align-items:center;
  padding:2px;overflow:hidden;background:var(--surface);font-size:var(--fs-micro);
  line-height:1.15;cursor:pointer;text-align:center}
.heat-cell b{font-size:var(--fs-xs);font-weight:700}
.heat-cell:hover{outline:1px solid var(--fg);outline-offset:-1px}
.heat-cell[data-sel="true"]{outline:1px solid var(--accent);outline-offset:-1px}
.breadth{display:flex;height:12px;border:var(--bw) solid var(--border)}
.breadth i{display:block;height:100%}
.grid6{display:grid;grid-template-columns:repeat(6,1fr);gap:var(--bw);
  background:var(--border);border:var(--bw) solid var(--border);margin-top:var(--s3)}
.cellstat{background:var(--surface);padding:var(--s2)}
.cellstat .v{font-size:var(--fs-md);font-weight:700;margin-top:1px}
.mx{display:grid;grid-template-columns:1fr 1fr;gap:var(--bw);background:var(--border);
  border:var(--bw) solid var(--border)}
.q{background:var(--surface);padding:var(--s2) var(--s3);border-top:2px solid var(--border)}
.q.q-lead{border-top-color:var(--live);background:var(--live-wash)}
.q.q-weak{border-top-style:dashed;border-top-color:var(--accent)}
.q.q-accum{border-top-style:dotted;border-top-color:var(--live)}
.q.q-dist{border-top-color:var(--accent);background:var(--accent-wash)}
.q .qh{display:flex;align-items:flex-end;justify-content:space-between;gap:var(--s2);
  padding-bottom:var(--s1);margin-bottom:var(--s2);border-bottom:var(--bw) solid var(--hairline)}
.q .qt{font-size:var(--fs-xs);font-weight:700;letter-spacing:.12em;text-transform:uppercase}
.q .qs{font-size:var(--fs-micro);color:var(--muted);letter-spacing:.06em;text-transform:uppercase}
.q .qw{font-size:var(--fs-lg);font-weight:700;line-height:1;text-align:right}
.q .qwl{font-size:var(--fs-micro);color:var(--muted);text-align:right}
.q ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:3px}
/* Bon cot co be rong co dinh de so thang hang giua cac dong va giua bon o. */
.q li{font-size:var(--fs-xs);display:grid;gap:var(--s2);align-items:baseline;
  grid-template-columns:minmax(0,1fr) 52px 56px 54px}
.q li>b{font-weight:400;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.q li>span{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.q li.mt-h{font-size:var(--fs-micro);letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);padding-bottom:2px;border-bottom:var(--bw) solid var(--hairline)}
.q li.mt-h>b{font-weight:600}
.q li.mt-empty{grid-template-columns:1fr}
.call{border:var(--bw) solid var(--accent);background:var(--accent-wash);
  padding:var(--s2) var(--s3);margin-top:var(--s3);display:flex;gap:var(--s3)}
.call .k{font-size:var(--fs-micro);font-weight:700;letter-spacing:.14em;color:var(--accent);
  text-transform:uppercase;white-space:nowrap;padding-top:2px}
.call p{margin:0;font-size:var(--fs-xs);line-height:1.6}
.lede{counter-reset:l;display:flex;flex-direction:column;gap:var(--s2)}
.lede p{counter-increment:l;margin:0;padding-left:var(--s5);position:relative;
  font-size:var(--fs-sm);line-height:1.62}
.lede p::before{content:"0" counter(l);position:absolute;left:0;top:0;color:var(--accent);
  font-size:var(--fs-micro);font-weight:700;letter-spacing:.1em}
.w2{display:grid;grid-template-columns:44px 92px minmax(0,1fr) 104px;gap:var(--s2);
  align-items:baseline;padding:var(--s1) 0;border-bottom:var(--bw) solid var(--hairline)}
.w2 .ag,.w2 .sr{font-size:var(--fs-micro);color:var(--muted);letter-spacing:.04em}
.w2 .sr{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-transform:uppercase}
.w2 .tt{font-size:var(--fs-xs);line-height:1.5}
.w2 .tk{display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end}
.tag{font-size:var(--fs-micro);padding:0 var(--s1);border:var(--bw) solid var(--border);
  color:var(--muted)}
.rail{display:flex;flex-direction:column;gap:var(--s2);
  border-left:var(--bw) solid var(--border);padding-left:var(--s3)}
.r{border:var(--bw) solid var(--border);background:var(--surface);padding:var(--s2) var(--s3)}
.r .hero{font-size:var(--fs-xl);font-weight:700;line-height:1.05}
.kv{display:flex;justify-content:space-between;align-items:baseline;font-size:var(--fs-xs);
  padding:2px 0;border-bottom:var(--bw) solid var(--hairline)}
.kv:last-child{border-bottom:none}
.kv span{color:var(--muted)}
.na{font-size:var(--fs-lg);font-weight:700;color:var(--accent);letter-spacing:.06em}
.why{font-size:var(--fs-micro);color:var(--muted);line-height:1.55;margin-top:var(--s1)}
.gauge{height:4px;margin:var(--s2) 0 var(--s1);position:relative;
  background:linear-gradient(90deg,var(--down),var(--border),var(--up))}
.gauge i{position:absolute;top:-4px;width:2px;height:12px;background:var(--fg)}
.sf-wrap{position:relative}
.sf-tip{position:absolute;z-index:3;min-width:220px;padding:var(--s2);background:var(--surface);
  border:1px solid var(--accent);color:var(--fg);font-size:var(--fs-xs);line-height:1.65;
  pointer-events:none;top:28px;display:none}
footer{padding:var(--s4);border-top:var(--bw) solid var(--border);color:var(--muted);
  font-size:var(--fs-micro);line-height:1.8}
footer b{color:var(--fg);font-weight:600}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
/* Radio dieu khien tab va o nhiet: an khoi mat nhung van bat duoc ban phim. */
.vh{position:absolute;opacity:0;width:0;height:0;pointer-events:none}
.seg label.btn{display:inline-flex;align-items:center;height:20px;padding:0 var(--s2);
  border:0;border-right:var(--bw) solid var(--border);cursor:pointer}
.seg label.btn:last-child{border-right:0}
.vh:focus-visible ~ .sf-body .seg label,.vh:focus-visible ~ .nw-body .seg label{outline:1px solid var(--fg)}
.split2{display:grid;grid-template-columns:1fr 1fr;gap:var(--s5)}
.grid6.g4{grid-template-columns:repeat(4,1fr)}
.heat-sf{grid-template-columns:repeat(5,minmax(0,1fr));height:190px}
.sf-chart{width:100%;height:260px;display:block}
@media print{body{background:#fff}}

/* ── man hinh hep ────────────────────────────────────────────────────────
   Trang nay dung tren ban lam viec la chinh, nhung doc tren dien thoai thi
   bo cuc hai cot 268px cua .wrap va cac luoi 4-6 cot day noi dung tran ra
   ngoai khung nhin. Hai nguong: 900px dua Market Pulse rail xuong duoi,
   560px xep lai moi luoi thanh mot cot. Khong mot con so nao doi - chi bo cuc. */
@media (max-width:900px){
  .wrap{grid-template-columns:minmax(0,1fr);padding:var(--s3) var(--s3) var(--s5)}
  .rail{border-left:0;border-top:var(--bw) solid var(--border);
    padding-left:0;padding-top:var(--s3)}
  .tape{grid-template-columns:repeat(2,1fr)}
  .grid6{grid-template-columns:repeat(3,1fr)}
  .heat-sf{grid-template-columns:repeat(4,minmax(0,1fr));height:220px}
}
@media (max-width:560px){
  .top{height:auto;flex-wrap:wrap;padding:var(--s2) var(--s3);row-gap:var(--s1)}
  .top .ttl{flex-basis:100%;order:9}
  .ix{padding:var(--s2)}
  .ix .px{font-size:var(--fs-lg)}
  .panel-body{padding:var(--s2)}
  .grid6,.grid6.g4{grid-template-columns:repeat(2,1fr)}
  .mx{grid-template-columns:minmax(0,1fr)}
  .split2{grid-template-columns:minmax(0,1fr);gap:var(--s4)}
  /* Ban do nhiet: 19 o trong luoi trên man hinh rong doc duoc, nhung ep xuong
     360px thi moi o con ~40px va ten nganh dai (Dien, nuoc & xang dau khi dot)
     bi cat cut. Tren dien thoai doi hinh thanh danh sach hang - ten trai, so
     phai - van giu nguyen mau nen nen van la ban do nhiet. */
  .heat-sf{grid-template-columns:minmax(0,1fr);grid-auto-rows:auto;height:auto}
  .heat-sf .heat-cell{flex-direction:row;justify-content:space-between;
    align-items:baseline;gap:var(--s2);text-align:left;padding:var(--s2)}
  .heat-sf .heat-cell b{font-size:var(--fs-xs);overflow:hidden;
    text-overflow:ellipsis;white-space:nowrap}
  .heat-sf .heat-cell span{white-space:nowrap;font-size:var(--fs-xs)}
  .sf-chart{height:200px}
  /* Dong tin: tuoi + nguon mot hang, tieu de va tag xuong hang rieng,
     thay vi bon cot chen nhau con 40px moi cot. */
  .w2{grid-template-columns:44px minmax(0,1fr);gap:var(--s1) var(--s2);
    padding:var(--s2) 0}
  .w2 .tt{grid-column:1/-1}
  .w2 .tk{grid-column:1/-1;justify-content:flex-start}
  .call{flex-direction:column;gap:var(--s1)}
  .q li{flex-wrap:wrap}
  .lede p{padding-left:var(--s4)}
  footer{padding:var(--s3)}
}
"""


# ── du lieu cho widget tuong tac ─────────────────────────────────────────

def sector_payload(pack: Path):
    """Gop chuoi dong tien + ma trong nganh thanh khoi JSON cho Sector Flow."""
    series = defaultdict(list)
    names = {}
    for r in read_csv(pack / "sector_series.csv"):
        series[r["icb_code"]].append([r["date"][5:].replace("-", "/"),
                                      round(num(r["foreign_net_ty"]), 2),
                                      round(num(r["prop_net_ty"]), 2)])
        names[r["icb_code"]] = r["icb_name"]
    members = defaultdict(list)
    for r in read_csv(pack / "sector_members.csv"):
        members[r["icb_code"]].append({
            "s": r["symbol"], "f": round(num(r["foreign_net_30d_ty"]), 1),
            "p": round(num(r["prop_net_30d_ty"]), 1),
            "c": round(num(r["combined_net_30d_ty"]), 1)})
    counts = {r["icb_code"]: int(num(r["n_symbols"])) for r in read_csv(pack / "sector.csv")}
    out = []
    for code, rows in series.items():
        ms = sorted(members.get(code, []), key=lambda m: -abs(m["c"]))[:12]
        out.append({"code": code, "name": names[code], "n": counts.get(code, len(members.get(code, []))),
                    "series": rows[-60:], "members": ms})
    out.sort(key=lambda x: -sum(r[1] + r[2] for r in x["series"][-30:]))
    return out


# WIDGET_JS da bi go bo 11/09/2026: toan bo tuong tac nay gio chay bang
# CSS thuan (radio an + bo chon ~), xem sf_css() va nw_css(). Ly do: app
# dien thoai nguoi dung mo bang khong chay JavaScript, nen moi thu do JS dung
# len deu mat. Bo JS luon thi desktop va mobile chay cung mot duong.



# ── cac khoi trang ───────────────────────────────────────────────────────

def block_tape(rows):
    out = []
    for r in rows:
        if r.get("status") != "OK":
            out.append(f'<div class="ix"><div class="label">{esc(r["index"])}</div>'
                       f'<div class="px flat">—</div>'
                       f'<div class="meta">{esc(r.get("status"))}</div></div>')
            continue
        pct, lo, hi, c = num(r["pct_change"]), num(r["low"]), num(r["high"]), num(r["close"])
        pos = (c - lo) / (hi - lo) * 100 if hi > lo else 0
        clamp = ' · BIÊN ĐỘ ƯỚC' if str(r.get("range_clamped", "0")) == "1" else ""
        out.append(
            f'<div class="ix"><div class="label">{esc(r["index"])}</div>'
            f'<div class="px {cls(pct)}">{vn(c, 2)}</div>'
            f'<div class="{cls(pct)}" style="font-size:var(--fs-xs)">'
            f'{vn(r["change"], 2, True)}  {vn(pct, 2, True)}%</div>'
            f'<div class="meta">GTGD {bn(r["value_ty"]).upper()} · '
            f'{vn(r["value_vs_avg20_pct"], 1, True)}% VS BQ20{clamp}</div>'
            f'<div class="rng"><i style="left:{max(0, min(100, pos)):.1f}%"></i></div>'
            f'<div class="meta">{vn(lo, 2)} — {vn(hi, 2)}</div></div>')
    return '<div class="tape">' + "".join(out) + "</div>"


def block_breadth(rows, ad):
    tot = next((r for r in rows if r["scope"] == "TOAN_TT"), None)
    if not tot:
        return '<div class="empty">Không có dữ liệu độ rộng</div>'
    a, d, u = (int(num(tot[k])) for k in ("advancers", "decliners", "unchanged"))
    n = max(a + d + u, 1)
    bar = (f'<div class="breadth"><i style="width:{a/n*100:.1f}%;background:var(--up)"></i>'
           f'<i style="width:{u/n*100:.1f}%;background:var(--border)"></i>'
           f'<i style="width:{d/n*100:.1f}%;background:var(--down)"></i></div>'
           f'<div class="row" style="margin-top:var(--s1);font-size:var(--fs-micro)">'
           f'<span class="up">{a} TĂNG</span><span class="dim">{u} THAM CHIẾU</span>'
           f'<span class="down right">{d} GIẢM</span></div>')
    stats = "".join(
        f'<div class="cellstat"><div class="label">{k}</div>'
        f'<div class="v {c}">{v}</div></div>'
        for k, v, c in [
            ("A/D ratio", vn(tot["ad_ratio"], 2), cls(num(tot["ad_ratio"]) - 1)),
            ("Trần", tot["ceiling"], "up"), ("Sàn", tot["floor"], "down"),
            ("Trên MA20", vn(tot["pct_above_ma20"], 1) + "%", ""),
            ("Trên MA50", vn(tot["pct_above_ma50"], 1) + "%", ""),
            ("Trên MA200", vn(tot["pct_above_ma200"], 1) + "%", "")])
    chart = ""
    if ad:
        vals = [num(r["ad_line"]) for r in ad]
        peak = max(ad, key=lambda r: num(r["ad_line"]))
        chart = (f'<div class="label" style="margin:var(--s4) 0 var(--s1)">'
                 f'Đường A/D {len(ad)} phiên · {ad[0]["date"][8:10]}/{ad[0]["date"][5:7]} → '
                 f'{ad[-1]["date"][8:10]}/{ad[-1]["date"][5:7]}</div>'
                 + svg_area(vals)
                 + f'<div class="row" style="font-size:var(--fs-micro);color:var(--muted)">'
                   f'<span>ĐẦU KỲ {vn(vals[0], 0, True)}</span>'
                   f'<span>ĐỈNH {peak["date"][8:10]}/{peak["date"][5:7]} '
                   f'<b class="up">{vn(peak["ad_line"], 0, True)}</b></span>'
                   f'<span class="right">HÔM NAY <b class="{cls(vals[-1])}">'
                   f'{vn(vals[-1], 0, True)}</b></span></div>')
    return bar + f'<div class="grid6">{stats}</div>' + chart


def brief_name(pack: Path, session: str) -> str:
    """Ten file ban tin, khong keo duoi.

    Quy uoc nguoi dung chot 11/09/2026: "Tong hop thi truong chung khoan
    cuoi phien" + ngay/thang/nam. Ban giua phien goi la "phien sang" cho dung
    su that - luc do phien chua dong cua.
    """
    d = pack.name.replace("_market_", "")
    day = f"{d[6:8]}-{d[4:6]}-{d[0:4]}" if len(d) == 8 and d.isdigit() else d
    ky = "cuối phiên" if session == "close" else "phiên sáng"
    return f"Tổng hợp thị trường chứng khoán {ky} {day}"


def block_matrix(matrix, sector):
    """Bon o Gia x Tien. Ty trong GTGD tinh tu sector.csv, khong lay tu agent."""
    share = {}
    for key in ("tang_vao", "tang_ra", "giam_vao", "giam_ra"):
        names = [str(x).split("(")[0].strip() for x in (matrix.get(key) or [])]
        share[key] = sum(num(r["pct_of_market_value"]) for r in sector
                         if r["icb_name"] in names)
    meta = [("tang_vao", "q-lead", "up", "Giá tăng · Tiền vào", "dẫn dắt thật"),
            ("tang_ra", "q-weak", "", "Giá tăng · Tiền ra", "tăng yếu — cảnh báo"),
            ("giam_vao", "q-accum", "dim", "Giá giảm · Tiền vào", "tích luỹ / bắt đáy"),
            ("giam_ra", "q-dist", "down", "Giá giảm · Tiền ra", "phân phối")]
    # So trong o lay thang tu sector.csv chu khong boc tach chuoi cua agent.
    # Truoc day moi dong la "ten nganh" + mot cuc chu "(+2,78% · GTGD 892 tỷ ·
    # ngoai +219)" day sang phai, nen cac cot so khong bao gio thang hang. Nay
    # tach thanh bon cot co be rong co dinh; agent chi con quyet dinh nganh nao
    # thuoc o nao, dung voi quy tac chung cua file: agent viet chu, script viet so.
    by_name = {r["icb_name"]: r for r in sector}
    cells = []
    for key, klass, tone, title, sub in meta:
        items = matrix.get(key) or []
        lis = []
        for x in items:
            nm = str(x).split("(")[0].strip()
            r = by_name.get(nm)
            if r:
                nums = (f'<span class="{cls(r["pct_change_wavg"])}">{vn(r["pct_change_wavg"], 2, True)}%</span>'
                        f'<span>{vn(r["value_ty"], 0)}</span>'
                        f'<span class="{cls(r["foreign_net_ty"])}">{vn(r["foreign_net_ty"], 0, True)}</span>')
            else:
                nums = '<span class="dim">—</span><span class="dim">—</span><span class="dim">—</span>'
            lis.append(f'<li><b>{esc(nm)}</b>{nums}</li>')
        body = ("".join(lis) if lis else '<li class="mt-empty dim">—</li>')
        head = ('<li class="mt-h"><b>Ngành</b><span>%</span><span>GTGD</span>'
                '<span>Ngoại</span></li>') if lis else ""
        cells.append(
            f'<div class="q {klass}"><div class="qh">'
            f'<div><div class="qt {tone}">{title}</div>'
            f'<div class="qs">{sub} · {len(items)} ngành</div></div>'
            f'<div><div class="qw {tone}">{vn(share[key], 1)}%</div>'
            f'<div class="qwl">GTGD</div></div></div><ul>{head}{body}</ul></div>')
    return '<div class="mx">' + "".join(cells) + "</div>"


HORIZONS = (1, 5, 10, 20, 30, 60)
HZ_DEFAULT = 30


def chart_svg(series, h):
    """Ve duong luy ke ngoai/tu doanh cho mot nganh o mot chan troi.

    Ban Python cua ham detail() cu ben JS. Ve san o day vi trang phai chay
    duoc trong webview khong co JavaScript (do 11/09/2026 tren dien thoai).
    """
    sl = series[-h:]
    W, HT, L, R, T, B = 920, 260, 62, 18, 18, 38
    pw, ph = W - L - R, HT - T - B
    cf = cp = 0.0
    pts = []
    for t, f, p in sl:
        cf += f
        cp += p
        pts.append((t, cf, cp))
    if not pts:
        return f'<svg class="sf-chart" viewBox="0 0 {W} {HT}" role="img"></svg>'
    vals = [v for _, a, b in pts for v in (a, b)]
    mn, mx = min([0.0] + vals), max([0.0] + vals)
    pad = max((mx - mn) * .12, abs(mx or mn or 1) * .03, 1e-9)
    lo, hi = mn - pad, mx + pad
    span = max(hi - lo, 1e-9)
    n = len(pts)

    def X(i):
        return L + (pw / 2 if n == 1 else i * pw / (n - 1))

    def Y(v):
        return T + (hi - v) / span * ph

    g = []
    for i in range(5):
        v = lo + (hi - lo) * i / 4
        y = Y(v)
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--border)"/>'
                 f'<text x="{L - 7}" y="{y + 3:.1f}" text-anchor="end" fill="var(--muted)" '
                 f'font-size="9">{esc(ty(v))}</text>')
    if lo < 0 < hi:
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="var(--fg)"/>')
    fl = " ".join(f"{X(i):.1f},{Y(p[1]):.1f}" for i, p in enumerate(pts))
    pl = " ".join(f"{X(i):.1f},{Y(p[2]):.1f}" for i, p in enumerate(pts))
    area = ("M" + f"{X(0):.1f} {Y(0):.1f}"
            + "".join(f" L{X(i):.1f} {Y(p[1]):.1f}" for i, p in enumerate(pts))
            + f" L{X(n - 1):.1f} {Y(0):.1f} Z")
    every = max(1, -(-n // 8))
    xl = "".join(f'<text x="{X(i):.1f}" y="{HT - 12}" text-anchor="middle" fill="var(--muted)" '
                 f'font-size="9">{esc(p[0])}</text>'
                 for i, p in enumerate(pts) if i % every == 0 or i == n - 1)
    return (f'<svg class="sf-chart" viewBox="0 0 {W} {HT}" role="img">{"".join(g)}'
            f'<path d="{area}" fill="var(--live)" opacity="0.1"></path>'
            f'<polyline points="{fl}" fill="none" stroke="var(--live)" stroke-width="2"></polyline>'
            f'<polyline points="{pl}" fill="none" stroke="var(--fg)" stroke-width="2" '
            f'stroke-dasharray="6 4"></polyline>{xl}</svg>')


def block_sector_flow(payload):
    """Ban do nhiet dong tien nganh - tuong tac bang CSS thuan, khong JavaScript.

    Hai nhom radio an (chan troi va nganh) dieu khien toan bo widget qua bo
    chon anh em `~`. Truoc day viec nay do JS lam, nhung app dien thoai anh
    dung khong chay script nen o nhiet dung im o nganh dau bang va nut chon ky
    bien mat. Dung san moi to hop 6 chan troi x N nganh thi
    khong con phu thuoc script nao.
    """
    if not payload:
        return '<div class="empty">Không có dữ liệu dòng tiền ngành.</div>'
    ns = len(payload)
    rad = "".join(f'<input type="radio" class="vh" name="sfhz" id="hz-{h}"'
                  f'{" checked" if h == HZ_DEFAULT else ""}>' for h in HORIZONS)
    rad += "".join(f'<input type="radio" class="vh" name="sfsec" id="sc-{i}"'
                   f'{" checked" if i == 0 else ""}>' for i in range(ns))

    hz_btn = "".join(f'<label class="btn" for="hz-{h}">{"1 QUÝ" if h == 60 else str(h) + "P"}</label>'
                     for h in HORIZONS)

    heats, scales = [], []
    for h in HORIZONS:
        nets = [sum(r[1] + r[2] for r in s["series"][-h:]) for s in payload]
        scale = max([1.0] + [abs(v) for v in nets])
        scales.append(f'<span class="sf-scale dim" data-h="{h}">THANG {esc(ty(scale))} · '
                      f'{ns} NGÀNH ICB CẤP 2</span>')
        cells = []
        for i, (s, v) in enumerate(zip(payload, nets)):
            base = "#00dd66" if v > 0 else "#ff7722" if v < 0 else "#302a22"
            mag = min(1.0, abs(v) / scale)
            bgc = mix(base, 8 + mag * (34 if v < 0 else 58), "#0d0b0a")
            cells.append(
                f'<label class="heat-cell" for="sc-{i}" data-i="{i}" '
                f'title="{esc(s["name"])} {esc(ty(v))}" style="background:{bgc}">'
                f'<b>{esc(s["name"])}</b><span class="{cls(v)}">{esc(ty(v))}</span></label>')
        heats.append(f'<div class="heat heat-sf" data-h="{h}">{"".join(cells)}</div>')

    # Ten nganh + bang ma: doi theo nganh, khong doi theo chan troi.
    dets = []
    for i, s in enumerate(payload):
        rows = "".join(
            f'<tr><td class="sym">{esc(m["s"])}</td><td class="{cls(m["f"])}">{esc(ty(m["f"]))}</td>'
            f'<td class="{cls(m["p"])}">{esc(ty(m["p"]))}</td>'
            f'<td class="{cls(m["c"])}">{esc(ty(m["c"]))}</td></tr>' for m in s["members"])
        dets.append(
            f'<div class="sf-det" data-i="{i}">'
            f'<div class="row" style="margin-top:var(--s3)">'
            f'<b style="font-size:var(--fs-md)">{esc(s["name"])}</b>'
            f'<span class="right dim" style="font-size:var(--fs-micro)">{s["n"]} MÃ</span></div>'
            f'<div class="label" style="margin:var(--s3) 0 var(--s1)">Mã trong ngành · '
            f'{len(s["members"])} · luỹ kế 30 phiên</div>'
            f'<div class="tw"><table class="t zebra"><thead><tr><th>Mã</th><th>Khối ngoại</th>'
            f'<th>Tự doanh</th><th>Tổng</th></tr></thead><tbody>{rows}</tbody></table></div></div>')

    # Bieu do + luy ke: doi theo CA hai truc.
    charts = []
    for i, s in enumerate(payload):
        for h in HORIZONS:
            sl = s["series"][-h:]
            cum = sum(r[1] + r[2] for r in sl)
            charts.append(
                f'<div class="sf-ch" data-i="{i}" data-h="{h}">{chart_svg(s["series"], h)}'
                f'<div class="row" style="font-size:var(--fs-xs);margin-top:var(--s2)">'
                f'<span>Luỹ kế {len(sl)} phiên <b class="{cls(cum)}">{esc(ty(cum))}</b></span>'
                f'<span class="right dim" style="font-size:var(--fs-micro)">'
                f'<span style="color:var(--live)">━</span> khối ngoại &nbsp;'
                f'<span style="color:var(--fg)">╌</span> tự doanh</span></div></div>')

    return (f'<div class="sf">{rad}<div class="sf-body">'
            f'<div class="row" style="margin-bottom:var(--s2)">'
            f'<div class="seg">{hz_btn}</div>'
            f'<span class="right" style="font-size:var(--fs-micro)">{"".join(scales)}</span></div>'
            f'{"".join(heats)}{"".join(charts)}{"".join(dets)}</div></div>')


def sf_css(ns):
    """Sinh bo chon CSS cho widget dong tien nganh (phu thuoc so nganh)."""
    out = [".sf-scale,.heat-sf,.sf-det,.sf-ch{display:none}"]
    for h in HORIZONS:
        out.append(f'#hz-{h}:checked ~ .sf-body .sf-scale[data-h="{h}"]{{display:inline}}')
        out.append(f'#hz-{h}:checked ~ .sf-body .heat-sf[data-h="{h}"]{{display:grid}}')
        out.append(f'#hz-{h}:checked ~ .sf-body label[for="hz-{h}"]'
                   '{color:var(--accent);border-color:var(--accent)}')
    for i in range(ns):
        out.append(f'#sc-{i}:checked ~ .sf-body .sf-det[data-i="{i}"]{{display:block}}')
        out.append(f'#sc-{i}:checked ~ .sf-body .heat-cell[data-i="{i}"]'
                   '{outline:1px solid var(--accent);outline-offset:-1px}')
        for h in HORIZONS:
            out.append(f'#hz-{h}:checked ~ #sc-{i}:checked ~ .sf-body '
                       f'.sf-ch[data-i="{i}"][data-h="{h}"]{{display:block}}')
    return "\n".join(out)


def block_signals(rows):
    if not rows:
        return ('<div class="empty" style="text-align:left;padding:var(--s3)">'
                '<div class="label acc" style="margin-bottom:var(--s2)">'
                'Chưa có tín hiệu nào</div>'
                '<div style="font-size:var(--fs-xs);line-height:1.7;color:var(--muted)">'
                'Sổ <b style="color:var(--fg)">agent/data/signals.yaml</b> đang trống. '
                'Đây là trạng thái hợp lệ — một ngày không có khuyến nghị thì thẻ này '
                'trống, không phải bịa ra tín hiệu cho đủ chỗ.<br><br>'
                'Thêm bằng cách nói với Claude trong phiên, hoặc chèn một mục vào sổ với '
                '<b style="color:var(--fg)">mã · hành động · vùng mua · cắt lỗ · chốt lời</b>. '
                'Lịch nhắc 11h25 và 14h55 sẽ hỏi trước mỗi lần bản tin chạy.</div></div>')
    scored = [r for r in rows if r.get("verdict") in ("ĐÚNG", "SAI", "ĐI NGANG")]
    right = sum(1 for r in scored if r["verdict"] == "ĐÚNG")
    alphas = [num(r["alpha_pct"]) for r in scored if r.get("alpha_pct") not in ("", None)]
    zones = [r for r in rows if r.get("buy_zone")]
    hit = sum(1 for r in zones if r.get("zone_hit") == "ĐÃ CHẠM")
    avg = sum(alphas) / len(alphas) if alphas else 0
    stats = "".join(
        f'<div class="cellstat"><div class="label">{k}</div><div class="v {c}">{v}</div></div>'
        for k, v, c in [("Tín hiệu đang mở", str(len(rows)), ""),
                        ("Đúng hướng", f"{right} / {len(scored)}",
                         "up" if right * 2 >= len(scored) else "down"),
                        ("Alpha trung bình", vn(avg, 2, True) + "%", cls(avg)),
                        ("Vùng mua đã chạm", f"{hit} / {len(zones)}", "")])
    VC = {"ĐÚNG": "up", "SAI": "down", "ĐI NGANG": "flat", "—": "flat"}
    body = []
    for r in rows:
        dl = ' <span class="tag">PL</span>' if str(r.get("diluted")) == "1" else ""
        hitc = "up" if r.get("zone_hit") == "ĐÃ CHẠM" else "dim"
        body.append(
            f'<tr><td class="sym">{esc(r["symbol"])}</td>'
            f'<td class="name">{esc(r["date"][8:10])}/{esc(r["date"][5:7])}</td>'
            f'<td class="name">{esc(r["action"])}</td>'
            f'<td>{vn(r["px_at_call_adj"], 2)}{dl}</td>'
            f'<td>{vn(r["px_now_adj"], 2)}</td>'
            f'<td class="{cls(r["change_pct"])}">{vn(r["change_pct"], 2, True)}%</td>'
            f'<td class="dim">{vn(r["vnindex_pct"], 2, True)}%</td>'
            f'<td class="{cls(r["alpha_pct"])}"><b>{vn(r["alpha_pct"], 2, True)}%</b></td>'
            f'<td class="{VC.get(r.get("verdict"), "flat")}">{esc(r.get("verdict"))}</td>'
            f'<td class="name">{esc(r.get("buy_zone") or "—")}</td>'
            f'<td class="{hitc}">{esc(r.get("zone_hit") or "—")}</td></tr>')
    head = ("<tr><th>Mã</th><th>Ngày KN</th><th>Khuyến nghị</th><th>Giá lúc KN</th>"
            "<th>Hôm nay</th><th>Thay đổi</th><th>VN-Index</th><th>Alpha</th>"
            "<th>Kết quả</th><th>Vùng mua</th><th>Chạm?</th></tr>")
    diluted = [r["symbol"] for r in rows if str(r.get("diluted")) == "1"]
    notes = call(
        "Đo bằng giá điều chỉnh",
        "Cột <b>Giá lúc KN</b> là giá <b>đã điều chỉnh</b>, không phải giá hiển thị trên bảng "
        "hôm đó. Mã đã thưởng hoặc chia tách được gắn nhãn PL"
        + (f" ({esc(', '.join(diluted))})" if diluted else "")
        + ". Lấy giá niêm yết cũ chia cho giá hôm nay sẽ tính cả phần pha loãng thành lỗ.")
    notes += call(
        "Chấm theo hướng",
        "Lệnh BÁN và khuyến nghị TRÁNH (CHỜ, TRUNG LẬP) được chấm ngược dấu — giá giảm là "
        "kết quả <b>đúng</b> của lệnh bán, không phải khoản lỗ. Alpha đo trên đúng cửa sổ "
        "thời gian của từng khuyến nghị so với VN-Index.", muted=True)
    return (f'<div class="grid6 g4" style="margin-top:0">{stats}</div>'
            f'<div class="tw"><table class="t zebra" style="margin-top:var(--s3)"><thead>{head}</thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>{notes}')


TAB_LABEL = {"vi_mo": "Vĩ mô", "nganh": "Ngành", "doanh_nghiep": "Doanh nghiệp"}


def block_wire(items):
    """Dong tin chia ba tab - tach hoan toan, dieu khien bang radio CSS.

    Ban truoc dua vao JS de an/hien tung nhom; app dien thoai khong chay
    script nen ca ba nhom do xuong cung mot cho. Radio an + bo chon `~` lam
    dung viec do ma khong can JavaScript.
    """
    if not items:
        return '<div class="empty">Không có tin trong cửa sổ theo dõi.</div>'
    groups = defaultdict(list)
    for it in items:
        groups[str(it.get("tab") or "nganh")].append(it)
    keys = [k for k in ("vi_mo", "nganh", "doanh_nghiep") if groups.get(k)]
    if not keys:
        return '<div class="empty">Không có tin phân loại được.</div>'
    rad, tabs, blocks = [], [], []
    for j, key in enumerate(keys):
        g = groups[key]
        rad.append(f'<input type="radio" class="vh" name="nw" id="nw-{key}"'
                   f'{" checked" if j == 0 else ""}>')
        tabs.append(f'<label class="btn" for="nw-{key}">{TAB_LABEL[key]} · {len(g)}</label>')
        rows = []
        for it in g:
            tk = "".join(f'<span class="tag">{esc(t)}</span>' for t in (it.get("tickers") or []))
            src = esc(it.get("source", ""))
            if int(num(it.get("n_sources"), 1)) > 1:
                src += f' +{int(num(it["n_sources"])) - 1}'
            rows.append(
                f'<div class="w2">'
                f'<span class="ag">{esc(it.get("age", ""))}</span>'
                f'<span class="sr">{src}</span>'
                f'<span class="tt">{esc(it.get("title", ""))}</span>'
                f'<span class="tk">{tk}</span></div>')
        blocks.append(f'<div class="nwg" data-k="{key}">{"".join(rows)}'
                      f'<div class="dim" style="font-size:var(--fs-micro);margin-top:var(--s2)">'
                      f'ĐANG XEM {len(g)} TIN · {TAB_LABEL[key].upper()}</div></div>')
    return (f'<div class="nw">{"".join(rad)}<div class="nw-body">'
            f'<div class="row" style="margin-bottom:var(--s2)">'
            f'<div class="seg">{"".join(tabs)}</div></div>'
            f'{"".join(blocks)}</div></div>')


def nw_css():
    out = [".nwg{display:none}"]
    for key in ("vi_mo", "nganh", "doanh_nghiep"):
        out.append(f'#nw-{key}:checked ~ .nw-body .nwg[data-k="{key}"]{{display:block}}')
        out.append(f'#nw-{key}:checked ~ .nw-body label[for="nw-{key}"]'
                   '{color:var(--accent);border-color:var(--accent)}')
    return "\n".join(out)


def block_rail(idx, breadth, sector, nar, session, signals):
    tot = next((r for r in breadth if r["scope"] == "TOAN_TT"), {})
    vni = next((r for r in idx if r["index"] == "VNINDEX" and r.get("status") == "OK"), {})
    frn = sum(num(r["foreign_net_ty"]) for r in sector)
    prop_na = any(str(r.get("prop_net_ty")) == "N/A" for r in sector)
    up = sorted(sector, key=lambda r: -num(r["pct_change_wavg"]))[:3]
    dn = sorted(sector, key=lambda r: num(r["pct_change_wavg"]))[:3]
    sent = nar.get("news_desk", {}).get("sentiment")

    def R(title, inner, style=""):
        return f'<div class="r"{style}><div class="label">{title}</div>{inner}</div>'

    kv = lambda k, v, c="": f'<div class="kv"><span>{k}</span><b class="{c}">{v}</b></div>'
    parts = [
        R("VN-Index",
          f'<div class="hero {cls(vni.get("pct_change"))}">{vn(vni.get("close"), 2)}</div>'
          f'<div class="{cls(vni.get("pct_change"))}" style="font-size:var(--fs-xs)">'
          f'{vn(vni.get("change"), 2, True)} · {vn(vni.get("pct_change"), 2, True)}%</div>'
          + kv("GTGD", bn(vni.get("value_ty")))
          + kv("So BQ20", vn(vni.get("value_vs_avg20_pct"), 1, True) + "%",
               cls(vni.get("value_vs_avg20_pct")))),
        R("Độ rộng",
          kv("Tăng", tot.get("advancers", "—"), "up") + kv("Giảm", tot.get("decliners", "—"), "down")
          + kv("Trần / Sàn", f'{tot.get("ceiling", "—")} / {tot.get("floor", "—")}')
          + kv("Trên MA50", vn(tot.get("pct_above_ma50"), 1) + "%")),
        R("Ngành mạnh", "".join(kv(esc(r["icb_name"])[:22], vn(r["pct_change_wavg"], 2, True) + "%", "up") for r in up)),
        R("Ngành yếu", "".join(kv(esc(r["icb_name"])[:22], vn(r["pct_change_wavg"], 2, True) + "%", "down") for r in dn)),
        R("Khối ngoại",
          f'<div class="hero {cls(frn)}" style="font-size:var(--fs-lg)">{vn(frn, 1, True)} tỷ</div>'
          f'<div class="why">ròng cả phiên, đã tách thoả thuận và ETF</div>'),
    ]
    if prop_na:
        parts.append(R("Tự doanh",
                       '<div class="na">N/A</div><div class="why">DataPro chưa công bố tự doanh cho '
                       'ngày này. Đây là dữ liệu <b>chưa về</b>, không phải tự doanh cân bằng.</div>',
                       ' style="border-color:var(--accent)"'))
    else:
        pr = sum(num(r.get("prop_net_ty")) for r in sector)
        parts.append(R("Tự doanh",
                       f'<div class="hero {cls(pr)}" style="font-size:var(--fs-lg)">{vn(pr, 1, True)} tỷ</div>'
                       f'<div class="why">ròng cả phiên</div>'))
    if sent is not None:
        parts.append(R("Tâm lý tin",
                       f'<div class="gauge"><i style="left:{(num(sent)+1)/2*100:.0f}%"></i></div>'
                       f'<b class="{cls(sent)}" style="font-size:var(--fs-lg)">{vn(sent, 2, True)}</b>'))
    # Trang thai nguon phai doc tu suc khoe feed THAT. Ban truoc o nay la chu
    # chet: VnEconomy da duoc va o tang du lieu va dang chay, nhung o nay van
    # ghi "Loi parser" vi khong ai cap nhat no. Mot o trang thai khong the tu
    # cap nhat thi khong phai o trang thai.
    srcs = nar.get("news_desk", {}).get("sources") or []
    if srcs:
        parts.append(R("Trạng thái nguồn", "".join(
            kv(esc(x.get("name", "")),
               "OK" if x.get("ok") else esc(x.get("error", "LỖI")),
               "up" if x.get("ok") else "down") for x in srcs)))

    if signals:
        scored = [r for r in signals if r.get("verdict") in ("ĐÚNG", "SAI", "ĐI NGANG")]
        right = sum(1 for r in scored if r["verdict"] == "ĐÚNG")
        al = [num(r["alpha_pct"]) for r in scored if r.get("alpha_pct") not in ("", None)]
        parts.append(R("Sổ khuyến nghị",
                       kv("Đang mở", str(len(signals)))
                       + kv("Đúng hướng", f"{right}/{len(scored)}", "up" if right * 2 >= len(scored) else "down")
                       + kv("Alpha TB", vn(sum(al) / len(al) if al else 0, 2, True) + "%",
                            cls(sum(al) / len(al) if al else 0))))
    return '<div class="rail">' + "".join(parts) + "</div>"


VERDICT = {"xac_nhan": ("up", "Độ rộng xác nhận chỉ số"),
           "phan_ky": ("acc", "Độ rộng phân kỳ với chỉ số"),
           "ru_bo": ("up", "Rũ bỏ — độ rộng cải thiện")}


def build(pack: Path, session: str, nar: dict) -> str:
    idx = read_csv(pack / "index.csv")
    breadth = read_csv(pack / "breadth.csv")
    ad = read_csv(pack / "ad_line.csv")
    sector = read_csv(pack / "sector.csv")
    leaders = read_csv(pack / "leaders.csv")
    movers = read_csv(pack / "index_movers.csv")
    fsess = read_csv(pack / "flow_session.csv")
    f30 = read_csv(pack / "flow_30d.csv")
    signals = read_csv(pack / "signals.csv")

    day = nar.get("date") or pack.name.replace("_market_", "")
    if len(day) == 8:
        day = f"{day[6:8]}/{day[4:6]}/{day[0:4]}"
    stamp = nar.get("stamp") or datetime.now().strftime("%H:%M")
    label = "PHIÊN SÁNG" if session == "morning" else "ĐÓNG CỬA"

    ma = nar.get("market_action", {})
    vcls, vtext = VERDICT.get(ma.get("verdict", ""), ("dim", "Chưa chấm"))

    n_traded = sum(int(num(r["traded"])) for r in breadth if r["scope"] == "TOAN_TT")
    bullets = "".join(f"<p>{esc(b)}</p>" for b in nar.get("bullets", []))
    contra = "".join(call(f"Mâu thuẫn {i}", esc(c))
                     for i, c in enumerate(nar.get("contradictions") or [], 1))

    sectors = sector_payload(pack)
    frn_buy = sorted(fsess, key=lambda r: -num(r["foreign_net_ty"]))
    frn_sell = sorted(fsess, key=lambda r: num(r["foreign_net_ty"]))
    flips = [r for r in f30 if r.get("flip")]
    keo = [r for r in movers if r.get("side") == "keo"]
    dim_ = [r for r in movers if r.get("side") == "dim"]

    unexplained = nar.get("news_desk", {}).get("unexplained") or []
    unexp = call("Không có tin",
                 "Biến động mạnh mà không có tin trong nước giải thích: <b>"
                 + esc(", ".join(unexplained))
                 + "</b>. Bản tin ghi trống thay vì gán nguyên nhân theo trùng hợp thời điểm."
                 ) if unexplained else ""

    left = "".join([
        panel("Tóm lược phiên", f"{n_traded} mã giao dịch",
              f'<div class="lede">{bullets}</div>'
              f'<div class="row" style="margin-top:var(--s3)">'
              f'<span class="chip {"on" if vcls == "up" else "act"}">{vtext}</span></div>'
              + contra),
        panel("Bản đồ nhiệt ngành · Sector Flow",
              "Khối ngoại + tự doanh · lũy kế theo chân trời",
              block_sector_flow(sectors),
              '<span>Nguồn DataPro · lũy kế theo chân trời đang chọn</span>'
              '<span class="right">Ô nhiệt tô theo dòng tiền ròng, không phải %thay đổi giá</span>'),
        panel("Độ rộng thị trường",
              "Trần sàn tính từ giá tham chiếu · HOSE 7% HNX 10% UPCOM 15%",
              block_breadth(breadth, ad)
              + (f'<div class="row" style="margin-top:var(--s2);font-size:var(--fs-xs)">'
                 f'{esc(ma.get("text", ""))}</div>' if ma.get("text") else "")),
        panel("Ma trận Giá × Tiền",
              "Trục giá %thay đổi gia quyền · trục tiền ngoại ròng và GTGD",
              block_matrix(nar.get("sector_desk", {}).get("matrix", {}), sector)
              + (call("Ghi chú", esc(nar["sector_desk"]["text"]))
                 if nar.get("sector_desk", {}).get("text") else "")),
        panel("Dẫn dắt thanh khoản", "Top 15 giá trị giao dịch",
              table([("symbol", "Mã", "sym"), ("icb_name", "Ngành", "name"),
                     ("close", "Giá", "num"), ("pct_change", "%", "signed"),
                     ("value_ty", "GTGD tỷ", "num1"),
                     ("foreign_net_ty", "Ngoại ròng", "signed"),
                     ("idx_points_est", "Điểm ước", "signed")], leaders, 15),
              '<span>Cột "Điểm ước" tính theo vốn hoá niêm yết, không phải free-float của HOSE '
              '— dùng để xếp hạng, không phải số chính thức</span>'),
        panel("Kéo & dìm chỉ số", "Đóng góp điểm ước lượng vào VN-Index",
              '<div class="split2">'
              f'<div><div class="label up" style="margin-bottom:var(--s1)">Kéo lên</div>'
              f'{bar_rows(keo, "idx_points_est")}</div>'
              f'<div><div class="label down" style="margin-bottom:var(--s1)">Dìm xuống</div>'
              f'{bar_rows(dim_, "idx_points_est")}</div></div>'),
        panel("Khối ngoại", "Đã tách thoả thuận và ETF khỏi dòng chủ động",
              '<div class="split2">'
              f'<div><div class="label up" style="margin-bottom:var(--s1)">Gom mạnh nhất</div>'
              + table([("symbol", "Mã", "sym"), ("icb_name", "Ngành", "name"),
                       ("pct_change", "%", "signed"), ("foreign_net_ty", "Ròng tỷ", "signed"),
                       ("foreign_net_pct_of_value", "%GTGD", "num1")], frn_buy, 8)
              + '</div><div><div class="label down" style="margin-bottom:var(--s1)">Xả mạnh nhất</div>'
              + table([("symbol", "Mã", "sym"), ("icb_name", "Ngành", "name"),
                       ("pct_change", "%", "signed"), ("foreign_net_ty", "Ròng tỷ", "signed"),
                       ("foreign_net_pct_of_value", "%GTGD", "num1")], frn_sell, 8)
              + "</div></div>"
              + (f'<div class="row" style="margin-top:var(--s2);font-size:var(--fs-xs)">'
                 f'{esc(nar["flow_desk"]["text"])}</div>'
                 if nar.get("flow_desk", {}).get("text") else "")),
        panel("Đổi chiều so với 30 phiên",
              f"{len(flips)} mã đảo dấu dòng ngoại",
              table([("symbol", "Mã", "sym"), ("icb_name", "Ngành", "name"),
                     ("foreign_net_30d_ty", "Ròng 30 phiên", "signed"),
                     ("foreign_net_ty", "Ròng phiên", "signed"),
                     ("flip", "", "text")], flips or f30, 14)),
        panel("Tín hiệu giao dịch & lịch sử khuyến nghị",
              "Sổ agent/data/signals.yaml · đo bằng giá điều chỉnh DataPro",
              block_signals(signals),
              '<span>Alpha = chênh lệch với VN-Index trên đúng cửa sổ thời gian của từng khuyến nghị</span>'
              '<span class="right">Thêm tín hiệu mới: bổ sung một mục vào signals.yaml</span>'),
        panel("Dòng tin", esc(nar.get("news_desk", {}).get("note", "24 giờ gần nhất")),
              block_wire(nar.get("news_desk", {}).get("wire", [])) + unexp),
    ])

    rail = block_rail(idx, breadth, sector, nar, session, signals)
    srcs = nar.get("news_desk", {}).get("sources") or []
    ok_n = sum(1 for x in srcs if x.get("ok"))
    news_chip = (f'<div class="chip {"on" if ok_n == len(srcs) else "act"}">'
                 f'Tin {ok_n}/{len(srcs)} nguồn</div>') if srcs else ""

    prop_note = ("Tự doanh ghi N/A vì DataPro chưa công bố cho ngày này. "
                 if any(str(r.get("prop_net_ty")) == "N/A" for r in sector) else "")

    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bản tin thị trường VN {day} · {label}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap">
<style>{CSS}
{sf_css(len(sectors))}
{nw_css()}</style></head><body>
<div class="top">
  <div class="wm"><i>X</i>SIGMA</div><div style="color:var(--border)">/</div>
  <div class="ttl">Market Desk · Bản tin thị trường Việt Nam</div>
  <div class="right"></div>
  <div class="chip act">{label} · {day}</div>
  <div class="chip">Chốt {stamp}</div>
  <div class="chip on">DataPro</div>
  {news_chip}
</div>
{block_tape(idx)}
<div class="wrap"><div class="col">{left}</div>{rail}</div>
<footer>
<b>NGUỒN VÀ GIỚI HẠN.</b> Mọi con số trên trang đọc trực tiếp từ data pack
{esc(pack.name)} do market_datapack.py và signal_tracker.py dựng từ DataPro;
phần chữ do agent viết và không chứa số nào ngoài pack.<br>
Độ rộng và trần/sàn tính từ giá tham chiếu với biên độ HOSE 7% · HNX 10% · UPCoM 15%.
Đóng góp điểm số là ước lượng theo vốn hoá niêm yết, không phải vốn hoá điều chỉnh
free-float của HOSE. Hiệu quả khuyến nghị đo trên chuỗi giá đã điều chỉnh ở cả hai đầu.<br>
{prop_note}Bản tin mô tả trạng thái thị trường, không chứa khuyến nghị mua bán.
{esc(nar.get("sources_note", ""))}
</footer>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Dung dashboard HTML tu data pack + narrative")
    ap.add_argument("pack", help="Thu muc data pack, vd _market_20260909")
    ap.add_argument("--session", choices=["morning", "close"], required=True)
    ap.add_argument("--narrative", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pack = Path(args.pack)
    if not (pack / "index.csv").exists():
        print(f"LOI: khong thay index.csv trong {pack} - chay market_datapack.py truoc.",
              file=sys.stderr)
        return 1

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
    if not (pack / "signals.csv").exists():
        print("CANH BAO: khong co signals.csv - the tin hieu se trong. "
              "Chay agent/scripts/signal_tracker.py.", file=sys.stderr)

    out = Path(args.out) if args.out else pack / (brief_name(pack, args.session) + ".html")
    out.write_text(build(pack, args.session, nar), encoding="utf-8")
    print(f"XONG -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
