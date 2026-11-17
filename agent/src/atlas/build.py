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

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2430;--mute:#647084;--line:#dfe3ea;--land:#e3e7ee;--sea:#f0f3f7;
--a1:#cfe0f5;--a2:#9dbfe8;--a3:#5d93d6;--a4:#2c66b8;--hi:#d9480f}
@media (prefers-color-scheme:dark){:root{--bg:#12161c;--card:#1a2029;--ink:#e6eaf0;--mute:#98a3b3;--line:#2c3542;
--land:#2a323e;--sea:#161b22;--a1:#24456f;--a2:#2f5f9c;--a3:#4583cf;--a4:#7fb0ee;--hi:#ff922b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:16px}h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 10px}
h3{font-size:14px;margin:14px 0 6px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}
.sub{color:var(--mute);font-size:13px}.stats{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:150px}
.stat b{display:block;font-size:19px}.stat span{color:var(--mute);font-size:12px}
.vh{position:absolute;opacity:0;pointer-events:none}
.mapbox{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow-x:auto}
.map{position:relative;min-width:760px}.map svg{display:block;width:100%;height:auto;background:var(--sea);border-radius:12px}
.land{fill:var(--land);stroke:var(--card);stroke-width:.4}.n1{fill:var(--a1)}.n2{fill:var(--a2)}.n3{fill:var(--a3)}.n4{fill:var(--a4)}
.pin{position:absolute;transform:translate(-50%,-50%);background:var(--card);border:1.5px solid var(--a4);color:var(--ink);
border-radius:999px;padding:1px 7px;font-size:11px;font-weight:600;cursor:pointer;white-space:nowrap;line-height:1.5}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.chip{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;cursor:pointer}
.chip b{color:var(--a4)}.panel{display:none}
.co{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:6px 0}
.co summary{cursor:pointer;padding:9px 12px;display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline;list-style:none}
.co summary::-webkit-details-marker{display:none}.co summary b{font-size:15px}.co .tag{font-size:11px;color:var(--mute);border:1px solid var(--line);border-radius:6px;padding:0 6px}
.co .rev{margin-left:auto;font-size:13px;color:var(--mute)}.co .in{padding:0 12px 12px;font-size:14px}
.co dl{display:grid;grid-template-columns:130px 1fr;gap:3px 10px;margin:8px 0 0}.co dt{color:var(--mute)}.co dd{margin:0}
.chain{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.link{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.link .no{color:var(--mute);font-size:12px}.link ul{margin:6px 0 0;padding:0;list-style:none}.link li{font-size:13px;padding:2px 0}
.link li i{color:var(--mute);font-style:normal;font-size:11px}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:14px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}th{color:var(--mute);font-weight:600;font-size:12px}
.foot{color:var(--mute);font-size:12px;margin:24px 0 8px}
@media (max-width:600px){.co dl{grid-template-columns:1fr}.co .rev{margin-left:0;width:100%}}
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
        f'<span class="tag">{escape(co.get("cap_do", ""))}</span>'
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
            f'#c-{iso}:checked~.body label[for="c-{iso}"]{{border-color:var(--hi);color:var(--hi)}}'
        )
    rules.append('#c-all:checked~.body .panel[data-c="all"]{display:block}'
                 '#c-all:checked~.body label[for="c-all"]{border-color:var(--hi);color:var(--hi)}')
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
        f'<div class="link"><span class="no">Mắt xích {i}</span><br><b>{escape(chain_labels[link])}</b><ul>'
        + "".join(f"<li>{escape(str(co['ten']))} <i>{co['quoc_gia']}</i></li>"
                  for co in companies if link in (co.get("mat_xich") or []))
        + "</ul></div>"
        for i, link in enumerate(chain, 1)
    )
    size = industry.get("quy_mo_thi_truong")
    stats = [
        (_num(size) + " tr. " + str(industry.get("don_vi_tien", "")) if size else "chưa có",
         f"quy mô thị trường {industry.get('nam_quy_mo') or ''}".strip()),
        (str(len(companies)), "doanh nghiệp trong Atlas"),
        (str(len(by_country)), "quốc gia có trụ sở"),
        (str(len(chain)), "mắt xích chuỗi giá trị"),
    ]
    stats_html = "".join(f'<div class="stat"><b>{escape(v)}</b><span>{escape(k)}</span></div>' for v, k in stats)
    title = escape(str(industry["ten"]))
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Atlas — {title}</title>
<style>{CSS}{''.join(rules)}</style></head><body><div class="wrap">
<h1>{title}</h1><div class="sub">GICS {escape(industry['gics'])} · cấp {escape(str(industry.get('cap_do')))} · cập nhật {escape(str(industry.get('cap_nhat')))} · sinh tự động từ ghi chú Atlas ngày {date.today().isoformat()}</div>
<div class="stats">{stats_html}</div>
{radios}<div class="body">
<h2>Bản đồ — bấm vào một nước</h2>
<div class="mapbox"><div class="map"><svg viewBox="0 0 {MAP_W:.0f} {MAP_H:.0f}" role="img" aria-label="Bản đồ thế giới">{paths}</svg>{''.join(pins)}</div></div>
<div class="sub">Trên điện thoại: kéo ngang bản đồ, hoặc bấm tên nước bên dưới. Màu đậm = nhiều doanh nghiệp đặt trụ sở. Số liệu là nơi đặt <b>trụ sở</b>, không phải nơi đặt nhà máy.</div>
<div class="chips">{''.join(chips)}</div>
{''.join(panels)}
<h2>Chuỗi giá trị — thượng nguồn → hạ nguồn</h2><div class="chain">{chain_html}</div>
<div class="foot">Số tiền theo đơn vị gốc của báo cáo từng doanh nghiệp, chưa quy đổi. Nguồn và nhãn độ tin cậy nằm trong từng ghi chú của Atlas.</div>
</div></div></body></html>"""


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
