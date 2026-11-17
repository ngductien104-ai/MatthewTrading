"""Generate the Atlas views from note frontmatter: atlas.json, a world-map HTML
page and an Obsidian canvas per industry.

Run from ``agent/``:  python -m src.atlas.build

The HTML is rendered here and works with JavaScript disabled: picking a country
is a hidden radio input plus CSS sibling selectors, details are <details>.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from html import escape
from pathlib import Path

from src.atlas import world
from src.atlas.schema import ATLAS_DIR, load_notes

VAULT_DIR = ATLAS_DIR.parent
MAP_W, LAT_TOP, LAT_BOTTOM = 1000.0, 84.0, -58.0
MAP_H = MAP_W * (LAT_TOP - LAT_BOTTOM) / 360.0
COUNTRY_VN = {
    "US": "Mỹ", "TW": "Đài Loan", "KR": "Hàn Quốc", "JP": "Nhật Bản", "CN": "Trung Quốc",
    "NL": "Hà Lan", "DE": "Đức", "GB": "Anh", "CH": "Thuỵ Sĩ", "FR": "Pháp", "VN": "Việt Nam",
    "IN": "Ấn Độ", "SG": "Singapore", "MY": "Malaysia", "IL": "Israel", "IT": "Ý", "ES": "Tây Ban Nha",
    "SE": "Thuỵ Điển", "DK": "Đan Mạch", "CA": "Canada", "BR": "Brazil", "AU": "Úc", "SA": "Ả Rập Xê Út",
    "TH": "Thái Lan", "ID": "Indonesia", "HK": "Hồng Kông", "RU": "Nga", "MX": "Mexico",
}
LEVEL_LABEL = {"dai_chung": "đại chúng", "tu_nhan": "tư nhân", "nha_nuoc": "nhà nước"}


# ── data ────────────────────────────────────────────────────────────────────

def _plain(value):
    return value.isoformat() if isinstance(value, date) else value


def _one_liner(path: Path) -> str:
    """First blockquote line of a note body — the one-sentence description."""
    for line in path.read_text(encoding="utf-8").split("---", 2)[-1].splitlines():
        if line.startswith("> "):
            return line[2:].strip()
    return ""


def collect(atlas_dir: Path = ATLAS_DIR) -> dict:
    """Industries with their companies, straight from frontmatter."""
    notes = load_notes(atlas_dir)
    industries = {}
    for path, fm in notes:
        if fm["loai_ghi_chu"] == "nganh":
            industries[str(fm["gics"])] = {
                **{k: _plain(v) for k, v in fm.items()},
                "gics": str(fm["gics"]),
                "slug": path.stem.removesuffix("_MOC"),
                "folder": path.parent.relative_to(atlas_dir).as_posix(),
                "companies": [],
            }
    for path, fm in notes:
        if fm["loai_ghi_chu"] != "doanh_nghiep":
            continue
        industry = industries.get(str(fm.get("nganh_gics")))
        if industry is None:
            continue
        industry["companies"].append({
            **{k: _plain(v) for k, v in fm.items()},
            "file": path.stem,
            "mo_ta": _one_liner(path),
        })
    return {"generated": date.today().isoformat(), "industries": industries}


# ── formatting ──────────────────────────────────────────────────────────────

def _num(value) -> str:
    return f"{value:,.0f}".replace(",", ".")


def _money(value, unit) -> str:
    return "chưa có" if value in (None, "") else f"{_num(value)} triệu {unit or ''}".strip()


def _country(iso: str, shapes: dict) -> str:
    return COUNTRY_VN.get(iso) or shapes.get(iso, {}).get("name") or iso


def _xy(lon: float, lat: float) -> tuple[float, float]:
    return (lon + 180.0) / 360.0 * MAP_W, (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * MAP_H


def _path(rings) -> str:
    parts = []
    for ring in rings:
        pts = [_xy(lon, lat) for lon, lat in ring]
        parts.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
    return "".join(parts)


# ── HTML ────────────────────────────────────────────────────────────────────

# Terminal look modelled on Fincept Terminal's "Obsidian" theme: near-black panels,
# hairline borders, amber accent, monospace type. Deliberately dark-only.
CSS = """
:root{color-scheme:dark;--bg:#080808;--panel:#0a0a0a;--raised:#111;--hover:#161616;--line:#1f1f1f;--line2:#2c2c2c;
--ink:#e5e5e5;--mute:#8a8a8a;--dim:#5a5a5a;--amber:#d97706;--amber-hi:#f59e0b;--amber-bg:#1a1000;--cyan:#22b8cf;--green:#22c55e;
--land:#141414;--sea:#0b0b0b;--a1:#3b2205;--a2:#6b3a06;--a3:#a85a07;--a4:#f59e0b;
--mono:"JetBrains Mono",Consolas,"Cascadia Mono",Menlo,"Courier New",monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.55 var(--mono);font-variant-numeric:tabular-nums}
a{color:var(--amber-hi);text-decoration:none}a:hover{text-decoration:underline}
.top{background:var(--raised);border-bottom:1px solid var(--line2);padding-block:8px;
padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.brand{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 14px}
.brand b{color:var(--amber);letter-spacing:.12em;font-size:14px}.brand span{color:var(--mute);font-size:11px;letter-spacing:.08em}
.live{color:var(--green)}.tabs{display:flex;flex-wrap:wrap;gap:2px;margin-top:8px}
.tabs a{color:var(--mute);font-size:11px;letter-spacing:.1em;padding:4px 10px;border:1px solid var(--line2);background:var(--panel)}
.tabs a:first-child{background:var(--amber);color:#0a0a0a;border-color:var(--amber);font-weight:700}
.tabs a:hover{color:var(--ink);text-decoration:none;border-color:var(--amber)}
.tape{display:flex;gap:22px;overflow-x:auto;white-space:nowrap;background:var(--panel);border-bottom:1px solid var(--line);
font-size:12px;padding-block:6px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.tape b{color:var(--ink)}.tape i{font-style:normal;color:var(--amber-hi)}.tape u{text-decoration:none;color:var(--dim)}
.wrap{max-width:1280px;margin:0 auto;padding-block:14px 0;display:grid;gap:12px;
padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.box{background:var(--panel);border:1px solid var(--line);min-width:0}
.hd{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;background:var(--raised);border-bottom:1px solid var(--line);padding:6px 10px}
.hd h2{margin:0;font-size:11px;letter-spacing:.12em;color:var(--amber);font-weight:700;text-transform:uppercase;border-left:2px solid var(--amber);padding-left:8px}
.hd span{color:var(--dim);font-size:11px;margin-left:auto}
.bd{padding:10px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--line)}
.kpi div{background:var(--panel);padding:10px 12px}.kpi b{display:block;font-size:20px;color:var(--amber-hi);font-weight:600}
.kpi span{color:var(--mute);font-size:10px;letter-spacing:.1em;text-transform:uppercase}
.vh{position:absolute;opacity:0;pointer-events:none}
.mapbox{overflow-x:auto}.map{position:relative;min-width:760px}
.map svg{display:block;width:100%;height:auto;background:var(--sea)}
.land{fill:var(--land);stroke:#262626;stroke-width:.35}.n1{fill:var(--a1)}.n2{fill:var(--a2)}.n3{fill:var(--a3)}.n4{fill:var(--a4)}
.pin{position:absolute;transform:translate(-50%,-50%);background:#000;border:1px solid var(--amber);color:var(--amber-hi);
padding:0 5px;font-size:10px;font-weight:700;cursor:pointer;white-space:nowrap;line-height:1.6;letter-spacing:.04em}
.pin:hover{background:var(--amber);color:#000}
.note{color:var(--dim);font-size:11px;padding:8px 10px;border-top:1px solid var(--line)}
.chips{display:flex;flex-wrap:wrap;gap:4px;padding:10px;border-top:1px solid var(--line)}
.chip{border:1px solid var(--line2);background:var(--bg);padding:3px 9px;font-size:11px;cursor:pointer;color:var(--mute);letter-spacing:.04em}
.chip b{color:var(--amber-hi);font-weight:600}.chip:hover{border-color:var(--amber);color:var(--ink)}
.panel{display:none}.panel>h2{margin:0 0 8px;font-size:12px;color:var(--ink);letter-spacing:.06em;text-transform:uppercase}
#c-all:checked~.body .chip[for="c-all"] b,.chip:hover b{color:inherit}.panel h3{margin:12px 0 4px;font-size:10px;letter-spacing:.14em;color:var(--cyan);text-transform:uppercase}
.panel h3:first-of-type{margin-top:0}
.co{border-bottom:1px solid var(--line)}.co:nth-of-type(even){background:#0c0c0c}
.co summary{cursor:pointer;padding:6px 8px;display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:4px 10px;align-items:baseline;list-style:none}
.co summary::-webkit-details-marker{display:none}.co summary:hover{background:var(--hover)}
.co summary b{font-weight:600;color:var(--ink);overflow-wrap:anywhere}.co summary b::before{content:"▸ ";color:var(--dim)}
.co[open] summary b::before{content:"▾ ";color:var(--amber)}
.tag{font-size:10px;color:var(--mute);border:1px solid var(--line2);padding:0 5px;letter-spacing:.06em;justify-self:start}
.tag.l3{background:var(--amber-bg);color:var(--amber-hi);border-color:var(--amber)}
.rev{font-size:12px;color:var(--ink);text-align:right}
.co .in{padding:4px 10px 12px 22px;color:var(--mute);font-size:12px}
.co dl{display:grid;grid-template-columns:120px minmax(0,1fr);gap:2px 12px;margin:8px 0 0}
.co dt{color:var(--dim);text-transform:uppercase;font-size:10px;letter-spacing:.08em;padding-top:2px}.co dd{margin:0;color:var(--ink);overflow-wrap:anywhere}
.chain{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1px;background:var(--line)}
.link{background:var(--panel);padding:10px}.link .no{color:var(--amber);font-size:10px;letter-spacing:.12em}
.link b{display:block;margin:2px 0 6px;font-size:12px}.link ul{margin:0;padding:0;list-style:none}
.link li{font-size:12px;padding:1px 0;display:flex;justify-content:space-between;gap:8px;color:var(--mute)}.link li i{font-style:normal;color:var(--dim)}
.tbl{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{text-align:left;padding:5px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:10px;letter-spacing:.1em;text-transform:uppercase;background:var(--raised)}
tr:nth-child(even) td{background:#0c0c0c}td.n{text-align:right;color:var(--amber-hi)}
.arrow{color:var(--amber)}
.status{display:flex;flex-wrap:wrap;gap:4px 18px;margin-top:12px;background:var(--raised);border-top:1px solid var(--line2);
color:var(--dim);font-size:10px;letter-spacing:.08em;padding-block:6px;
padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.status b{color:var(--mute);font-weight:400}.status .ok{color:var(--green)}
:focus-visible{outline:1px solid var(--amber-hi);outline-offset:1px}
@media (max-width:600px){.co summary{grid-template-columns:minmax(0,1fr) auto}.co .rev{grid-column:1/-1;text-align:left}
.co dl{grid-template-columns:1fr}.co dt{padding-top:6px}}
"""


def _company_html(co: dict, chain_labels: dict, shapes: dict) -> str:
    links = ", ".join(chain_labels.get(link, link) for link in co.get("mat_xich") or [])
    rows = [
        ("Mắt xích", links),
        ("Trụ sở", ", ".join(x for x in (co.get("tru_so"), _country(co["quoc_gia"], shapes)) if x)),
        ("Mã / sàn", " · ".join(str(x) for x in (co.get("ma"), co.get("san")) if x) or "không niêm yết"),
        ("Doanh thu", _money(co.get("doanh_thu"), co.get("don_vi_tien"))
         + (f" (năm tài chính {co['nam_tai_chinh']})" if co.get("nam_tai_chinh") else "")),
        ("Vốn hoá", _money(co.get("von_hoa"), co.get("don_vi_von_hoa") or co.get("don_vi_tien"))),
        ("Chủ sở hữu", co.get("chu_so_huu") or ""),
        ("Cùng bậc", ", ".join(co.get("doi_thu_cung") or [])),
        ("Bậc trên", ", ".join(co.get("doi_thu_tren") or [])),
        ("Bậc dưới", ", ".join(co.get("doi_thu_duoi") or [])),
        ("Mua từ", ", ".join(co.get("mua_tu") or [])),
        ("Bán cho", ", ".join(co.get("ban_cho") or [])),
        ("Liên hệ VN", ", ".join(co.get("lien_ket_VN") or [])),
        ("Nguồn", ", ".join(co.get("nguon") or [])),
    ]
    body = "".join(f"<dt>{escape(k)}</dt><dd>{escape(str(v)).replace('_', ' ')}</dd>" for k, v in rows if v)
    return (
        f'<details class="co"><summary><b>{escape(str(co["ten"]))}</b>'
        f'<span class="tag{" l3" if co.get("cap_do") == "L3" else ""}">{escape(co.get("cap_do", ""))}</span>'
        f'<span class="tag">{escape(LEVEL_LABEL.get(co.get("loai"), ""))}</span>'
        f'<span class="rev">{escape(_money(co.get("doanh_thu"), co.get("don_vi_tien")))}</span></summary>'
        f'<div class="in">{escape(co.get("mo_ta", ""))}<dl>{body}</dl></div></details>'
    )


def _spread(spots: dict, dx: float = 46.0, dy: float = 17.0) -> dict:
    """Nudge country pins apart vertically so neighbours (Europe, East Asia) stay readable."""
    spots = {iso: list(xy) for iso, xy in spots.items()}
    for _ in range(40):
        moved = False
        for a in spots:
            for b in spots:
                if a < b and abs(spots[a][0] - spots[b][0]) < dx and abs(spots[a][1] - spots[b][1]) < dy:
                    upper, lower = (a, b) if spots[a][1] <= spots[b][1] else (b, a)
                    spots[upper][1] -= 2.0
                    spots[lower][1] += 2.0
                    moved = True
        if not moved:
            break
    return {iso: (x, y) for iso, (x, y) in spots.items()}


def render_html(industry: dict, shapes: dict) -> str:
    """One self-contained page for an industry."""
    companies = sorted(industry["companies"], key=lambda c: str(c["ten"]).lower())
    chain = industry.get("mat_xich") or []
    chain_labels = {**{link: link.replace("_", " ") for link in chain}, **(industry.get("ten_mat_xich") or {})}
    by_country: dict[str, list] = {}
    for co in companies:
        by_country.setdefault(co["quoc_gia"], []).append(co)
    order = sorted(by_country, key=lambda iso: (-len(by_country[iso]), iso))
    top = max((len(v) for v in by_country.values()), default=1)

    def shade(iso: str) -> str:
        n = len(by_country.get(iso, []))
        return "" if not n else f" n{min(4, 1 + (4 * n - 1) // top)}"

    paths = "".join(
        f'<path class="land{shade(iso)}" d="{_path(shape["rings"])}"><title>{escape(_country(iso, shapes))}</title></path>'
        for iso, shape in shapes.items() if shape["label"][1] > LAT_BOTTOM
    )
    spots = _spread({iso: _xy(*shapes[iso]["label"]) for iso in order if iso in shapes})
    pins, chips, panels, rules = [], [], [], []
    for iso in order:
        n = len(by_country[iso])
        name = escape(_country(iso, shapes))
        if iso in spots:
            x, y = spots[iso]
            pins.append(f'<label class="pin" for="c-{iso}" style="left:{x / MAP_W * 100:.2f}%;top:{y / MAP_H * 100:.2f}%">{iso} {n}</label>')
        chips.append(f'<label class="chip" for="c-{iso}">{name} <b>{n}</b></label>')
        groups = []
        for link in chain:
            members = [co for co in by_country[iso] if link in (co.get("mat_xich") or [])]
            if members:
                groups.append(f"<h3>{escape(chain_labels[link])}</h3>" + "".join(_company_html(co, chain_labels, shapes) for co in members))
        panels.append(f'<div class="panel" data-c="{iso}"><h2>{name} — {n} doanh nghiệp</h2>{"".join(groups)}</div>')
        rules.append(
            f'#c-{iso}:checked~.body .panel[data-c="{iso}"]{{display:block}}'
            f'#c-{iso}:checked~.body label[for="c-{iso}"]{{border-color:var(--amber);background:var(--amber);color:#000}}'
        )
    rules.append('#c-all:checked~.body .panel[data-c="all"]{display:block}'
                 '#c-all:checked~.body label[for="c-all"]{border-color:var(--amber);background:var(--amber);color:#000}')
    overview = "".join(
        f"<tr><td>{escape(_country(iso, shapes))}</td><td>{len(by_country[iso])}</td>"
        f"<td>{escape(', '.join(str(co['ten']) for co in by_country[iso]))}</td></tr>" for iso in order
    )
    panels.insert(0, '<div class="panel" data-c="all"><h2>Tất cả quốc gia</h2><table><tr><th>Quốc gia</th><th>Số DN</th>'
                     f'<th>Doanh nghiệp</th></tr>{overview}</table></div>')
    chips.insert(0, '<label class="chip" for="c-all">Tất cả</label>')
    radios = '<input class="vh" type="radio" name="c" id="c-all" checked>' + "".join(
        f'<input class="vh" type="radio" name="c" id="c-{iso}">' for iso in order)

    chain_html = "".join(
        f'<div class="link"><span class="no">{i:02d} · {"THƯỢNG NGUỒN" if i == 1 else "HẠ NGUỒN" if i == len(chain) else "MẮT XÍCH"}</span>'
        f'<b>{escape(chain_labels[link])}</b><ul>'
        + "".join(f"<li><span>{escape(str(co['ten']))}</span><i>{co['quoc_gia']}</i></li>"
                  for co in companies if link in (co.get("mat_xich") or []))
        + "</ul></div>"
        for i, link in enumerate(chain, 1)
    )
    names = {co["file"]: str(co["ten"]) for co in companies}
    flows = [(co, buyer) for co in companies for buyer in co.get("ban_cho") or [] if buyer in names]
    flow_rows = "".join(
        f"<tr><td>{escape(str(co['ten']))} <span class=\"tag\">{co['quoc_gia']}</span></td><td class=\"arrow\">→</td>"
        f"<td>{escape(names[buyer])}</td></tr>" for co, buyer in flows
    ) or '<tr><td colspan="3">Chưa có quan hệ nào có nguồn.</td></tr>'
    deep = [co for co in companies if co.get("cap_do") == "L3"]
    tape = "".join(
        f"<span><b>{escape(str(co.get('ma') or co['ten']))}</b> <u>{co['quoc_gia']}</u> "
        f"<i>{escape(_money(co.get('doanh_thu'), co.get('don_vi_tien')))}</i></span>" for co in deep
    ) or "<span>Chưa có hồ sơ L3.</span>"
    size = industry.get("quy_mo_thi_truong")
    stats = [
        (_num(size) + " tr. " + str(industry.get("don_vi_tien", "")) if size else "chưa có",
         f"quy mô thị trường {industry.get('nam_quy_mo') or ''}".strip()),
        (str(len(companies)), "doanh nghiệp"),
        (str(len(deep)), "hồ sơ sâu L3"),
        (str(len(by_country)), "quốc gia có trụ sở"),
        (str(len(chain)), "mắt xích chuỗi"),
        (str(len(flows)), "quan hệ mua-bán có nguồn"),
    ]
    stats_html = "".join(f'<div><b>{escape(v)}</b><span>{escape(k)}</span></div>' for v, k in stats)
    title = escape(str(industry["ten"]))
    today = date.today().isoformat()
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Atlas {title}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&amp;display=swap">
<style>{CSS}{''.join(rules)}</style></head><body>
<header class="top"><div class="brand"><b>ATLAS TERMINAL</b><span>BỘ NÃO NGÀNH &amp; DOANH NGHIỆP</span>
<span class="live">● DỮ LIỆU TỪ VAULT</span><span>{today}</span></div>
<nav class="tabs"><a href="#tong-quan">TỔNG QUAN</a><a href="#ban-do">BẢN ĐỒ</a><a href="#chuoi">CHUỖI GIÁ TRỊ</a><a href="#mua-ban">MUA-BÁN</a></nav></header>
<div class="tape" aria-label="Hồ sơ sâu L3, doanh thu năm gần nhất">{tape}</div>
<main class="wrap">
<section class="box" id="tong-quan"><div class="hd"><h2>{title}</h2><span>GICS {escape(industry['gics'])} · CẤP {escape(str(industry.get('cap_do')))} · CẬP NHẬT {escape(str(industry.get('cap_nhat')))}</span></div>
<div class="kpi">{stats_html}</div></section>
{radios}<div class="body" style="display:grid;gap:12px">
<section class="box" id="ban-do"><div class="hd"><h2>Bản đồ trụ sở</h2><span>BẤM VÀO MỘT NƯỚC</span></div>
<div class="mapbox"><div class="map"><svg viewBox="0 0 {MAP_W:.0f} {MAP_H:.0f}" role="img" aria-label="Bản đồ thế giới">{paths}</svg>{''.join(pins)}</div></div>
<div class="chips">{''.join(chips)}</div>
<div class="note">Màu đậm = nhiều doanh nghiệp đặt trụ sở. Bản đồ theo nơi đặt trụ sở, chưa theo nhà máy. Trên điện thoại kéo ngang bản đồ hoặc bấm tên nước.</div></section>
<section class="box"><div class="hd"><h2>Doanh nghiệp theo nước</h2><span>DOANH THU NĂM GẦN NHẤT · ĐƠN VỊ GỐC</span></div>
<div class="bd">{''.join(panels)}</div></section>
</div>
<section class="box" id="chuoi"><div class="hd"><h2>Chuỗi giá trị</h2><span>THƯỢNG NGUỒN → HẠ NGUỒN</span></div><div class="chain">{chain_html}</div></section>
<section class="box" id="mua-ban"><div class="hd"><h2>Quan hệ mua-bán có nguồn</h2><span>NGƯỜI BÁN → NGƯỜI MUA</span></div>
<div class="tbl"><table><tr><th>Bên bán</th><th></th><th>Bên mua</th></tr>{flow_rows}</table></div>
<div class="note">Chỉ ghi quan hệ có báo cáo gốc nêu tên. Phần lớn hãng không nêu tên khách, nên bảng này chưa kín.</div></section>
</main>
<footer class="status"><span class="ok">● SẴN SÀNG</span><span>NGUỒN <b>GHI CHÚ ATLAS</b></span><span>SINH LÚC <b>{today}</b></span>
<span>TIỀN <b>THEO ĐƠN VỊ GỐC, CHƯA QUY ĐỔI</b></span><span>NHÃN TIN CẬY <b>TRONG TỪNG GHI CHÚ</b></span></footer>
</body></html>"""


# ── canvas ──────────────────────────────────────────────────────────────────

def render_canvas(industry: dict, atlas_dir: Path = ATLAS_DIR) -> dict:
    """Obsidian canvas: one column per chain link, company notes inside, flows between."""
    chain = industry.get("mat_xich") or []
    labels = {**{link: link.replace("_", " ") for link in chain}, **(industry.get("ten_mat_xich") or {})}
    rel = atlas_dir.relative_to(VAULT_DIR).as_posix()
    nodes, edges, placed = [], [], {}
    col_w, card_w, card_h, gap = 340, 280, 60, 12
    for col, link in enumerate(chain):
        members = [co for co in sorted(industry["companies"], key=lambda c: str(c["ten"]).lower())
                   if link in (co.get("mat_xich") or [])]
        x = col * (col_w + 60)
        nodes.append({"id": f"g-{link}", "type": "group", "label": f"{col + 1}. {labels[link]}",
                      "x": x, "y": 0, "width": col_w, "height": 70 + max(1, len(members)) * (card_h + gap)})
        for row, co in enumerate(members):
            node_id = f"{link}-{co['file']}"
            placed.setdefault(co["file"], node_id)
            nodes.append({"id": node_id, "type": "file", "file": f"{rel}/DoanhNghiep/{co['file']}.md",
                          "x": x + 30, "y": 50 + row * (card_h + gap), "width": card_w, "height": card_h})
    for src, dst in industry.get("dong_chay") or []:
        if src in chain and dst in chain:
            edges.append({"id": f"f-{src}-{dst}", "fromNode": f"g-{src}", "fromSide": "right",
                          "toNode": f"g-{dst}", "toSide": "left"})
    for co in industry["companies"]:
        for buyer in co.get("ban_cho") or []:
            if co["file"] in placed and buyer in placed:
                edges.append({"id": f"s-{co['file']}-{buyer}", "fromNode": placed[co["file"]], "fromSide": "right",
                              "toNode": placed[buyer], "toSide": "left", "label": "bán cho"})
    return {"nodes": nodes, "edges": edges}


# ── entry point ─────────────────────────────────────────────────────────────

def build(atlas_dir: Path = ATLAS_DIR, shapes: dict | None = None) -> list[Path]:
    shapes = world.load() if shapes is None else shapes
    data = collect(atlas_dir)
    written = [atlas_dir / "_HeThong" / "atlas.json"]
    written[0].write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for industry in data["industries"].values():
        if not industry["companies"]:
            continue
        folder = atlas_dir / industry["folder"]
        page = folder / f"BanDo_{industry['slug']}.html"
        page.write_text(render_html(industry, shapes), encoding="utf-8")
        canvas = folder / "ChuoiGiaTri.canvas"
        canvas.write_text(json.dumps(render_canvas(industry, atlas_dir), ensure_ascii=False, indent=1), encoding="utf-8")
        written += [page, canvas]
    return written


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    for path in build():
        print(path.relative_to(ATLAS_DIR).as_posix(), f"{path.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
