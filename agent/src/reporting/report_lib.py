# -*- coding: utf-8 -*-
"""report_lib — thư viện dựng báo cáo PDF tái dùng cho output swarm (TTCK VN).

Dùng lại cho bất kỳ preset nào: build chart (matplotlib→PNG base64) + lắp HTML
(band/section/table/box/chart) + render PDF bằng Playwright/Chromium.

Yêu cầu (đã cài trong $HOME\.venv): matplotlib, playwright (+ chromium).
Chạy bằng: $HOME/.venv/Scripts/python.exe
"""
from __future__ import annotations
import base64, io, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from playwright.sync_api import sync_playwright

# DejaVu Sans phủ đủ dấu tiếng Việt cho nhãn biểu đồ.
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.unicode_minus": False})

ACCENT = "#0b2545"

# ---- Thương hiệu Xsigma Capital (xsigma.lovable.app) ----
BRAND_NAME = "Xsigma Capital"
BRAND_TAGLINE = "The Right Stock, At The Right Time · Tín hiệu giao dịch chứng khoán Việt Nam"
BRAND_URL = "xsigma.lovable.app"
BRAND_INDIGO = "#575ECF"

CSS = """
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; color: #1a2332; font-size: 10.5pt; line-height: 1.5; margin: 0; }
h1 { font-size: 19pt; margin: 0 0 2px 0; color: #0b2545; }
h2 { font-size: 13pt; color: #0b2545; border-bottom: 2px solid #0b2545; padding-bottom: 3px; margin: 20px 0 9px; }
h3 { font-size: 11pt; color: #13315c; margin: 13px 0 5px; }
.sub { color: #5a6b85; font-size: 9.5pt; margin: 1px 0; }
.band { background: linear-gradient(90deg,#0b2545,#13315c); color: #fff; padding: 18px 22px; border-radius: 6px; }
.band h1 { color: #fff; } .band .sub { color: #c7d6ee; }
table { width: 100%; border-collapse: collapse; margin: 8px 0 4px; font-size: 9.6pt; }
th, td { border: 1px solid #cdd7e5; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #eef3f9; color: #0b2545; font-weight: 600; }
tr:nth-child(even) td { background: #f7f9fc; }
.num { text-align: right; white-space: nowrap; }
.box { border-radius: 6px; padding: 12px 16px; margin: 12px 0; }
.box-key { background: #fff4e5; border-left: 5px solid #e8851a; }
.box-act { background: #eaf4ff; border-left: 5px solid #1f6fd6; }
.box-warn { background: #fdecec; border-left: 5px solid #d23b3b; }
.badge { display: inline-block; padding: 2px 9px; border-radius: 12px; font-weight: 700; font-size: 9.5pt; color: #fff; }
.b-fear { background: #d23b3b; } .b-amber { background: #e8851a; } .b-neutral { background: #6b7a90; }
.big { font-size: 15pt; font-weight: 800; }
.neg { color: #c0392b; font-weight: 700; } .pos { color: #1e8449; font-weight: 700; }
ul { margin: 4px 0; padding-left: 20px; } li { margin: 2px 0; }
.small { font-size: 8.7pt; color: #5a6b85; }
.src a { color: #1f6fd6; text-decoration: none; word-break: break-all; }
.disc { font-size: 8.4pt; color: #6b7a90; font-style: italic; }
.pagebreak { page-break-before: always; }
.chartcap { font-size: 8.6pt; color: #5a6b85; margin: 2px 0 6px; }
img.chart { width: 100%; border: 1px solid #dde5ef; border-radius: 4px; }
.brandbar { display: flex; justify-content: space-between; align-items: flex-end;
  padding: 4px 2px 7px; margin-bottom: 10px;
  border-bottom: 3px solid; border-image: linear-gradient(90deg,#FE7B02,#F858BC,#575ECF) 1; }
.bwordmark { font-size: 14pt; font-weight: 800; letter-spacing: 1.2px; color: #1b1b1b; }
.bwordmark .x { color: #575ECF; }
.bwordmark .cap { color: #575ECF; font-weight: 700; letter-spacing: 2px; }
.btag { font-size: 8.3pt; color: #6b7a90; font-style: italic; text-align: right; max-width: 56%; line-height: 1.35; }
"""


# ---------- charts ----------
def _fig_uri(fig, dpi=135):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def chart_price_liquidity(labels, close, gtgd_ty, title, hlines=None):
    """Đường giá (trục trái) + cột GTGD nghìn tỷ (trục phải). hlines=[(y,label,color)]."""
    fig, ax = plt.subplots(figsize=(8.6, 3.1))
    ax2 = ax.twinx()
    x = range(len(labels))
    ax2.bar(x, gtgd_ty, color="#cdd9ea", width=0.62, zorder=1, label="GTGD (nghìn tỷ)")
    ax.plot(x, close, color=ACCENT, lw=2.0, marker="o", ms=2.6, zorder=3, label="VN-Index")
    for y, lab, col in (hlines or []):
        ax.axhline(y, color=col, ls="--", lw=1.1, zorder=2)
        ax.text(len(labels) - 1, y, f" {lab}", color=col, fontsize=7.5, va="center", ha="left")
    ax.set_title(title, fontsize=10.5, color=ACCENT, fontweight="bold", loc="left")
    ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
    step = max(1, len(labels) // 9)
    ax.set_xticks(list(x)[::step]); ax.set_xticklabels(labels[::step], rotation=45, fontsize=7, ha="right")
    ax.tick_params(axis="y", labelsize=7.5); ax2.tick_params(axis="y", labelsize=7.5, colors="#6b7a90")
    ax.set_ylabel("Điểm", fontsize=8); ax2.set_ylabel("GTGD (nghìn tỷ)", fontsize=8, color="#6b7a90")
    ax.grid(axis="y", ls=":", alpha=.4)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper right", framealpha=.9)
    return _fig_uri(fig)


def chart_net_bars(labels, vals, title, ylabel):
    """Cột ròng (đỏ âm / xanh dương)."""
    fig, ax = plt.subplots(figsize=(8.6, 2.7))
    x = range(len(labels))
    colors = ["#1e8449" if v >= 0 else "#c0392b" for v in vals]
    ax.bar(x, vals, color=colors, width=0.66)
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_title(title, fontsize=10.5, color=ACCENT, fontweight="bold", loc="left")
    step = max(1, len(labels) // 9)
    ax.set_xticks(list(x)[::step]); ax.set_xticklabels(labels[::step], rotation=45, fontsize=7, ha="right")
    ax.tick_params(axis="y", labelsize=7.5); ax.set_ylabel(ylabel, fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}"))
    ax.grid(axis="y", ls=":", alpha=.4)
    return _fig_uri(fig)


# ---------- html / pdf ----------
def chart_block(uri, caption):
    return f'<img class="chart" src="{uri}"><div class="chartcap">{caption}</div>'


def brand_bar():
    """Dải thương hiệu Xsigma Capital ở đầu mỗi báo cáo (gắn 'Thực hiện bởi Xsigma')."""
    return (
        '<div class="brandbar">'
        '<div class="bwordmark"><span class="x">X</span>SIGMA <span class="cap">CAPITAL</span></div>'
        f'<div class="btag">Báo cáo thực hiện bởi {BRAND_NAME}<br>{BRAND_TAGLINE}</div>'
        '</div>'
    )


def build_html(band_html, sections_html, brand=True):
    head = brand_bar() if brand else ""
    return (f'<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body>{head}{band_html}{sections_html}</body></html>')


def render_pdf(html, pdf_path, footer_left="Báo cáo swarm · TTCK VN", html_path=None):
    if html_path:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
    src = html_path or os.path.join(os.path.dirname(os.path.abspath(pdf_path)), "_tmp_report.html")
    if not html_path:
        with open(src, "w", encoding="utf-8") as f:
            f.write(html)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto("file:///" + src.replace("\\", "/"))
        pg.pdf(path=pdf_path, format="A4", print_background=True,
               margin={"top": "14mm", "bottom": "16mm", "left": "13mm", "right": "13mm"},
               display_header_footer=True, header_template="<div></div>",
               footer_template=(
                   '<div style="font-size:8px;color:#6b7a90;width:100%;padding:0 13mm;'
                   'display:flex;justify-content:space-between;">'
                   f'<span>{footer_left}</span>'
                   f'<span>{BRAND_NAME} · {BRAND_URL} · Trang '
                   '<span class="pageNumber"></span>/<span class="totalPages"></span></span></div>'))
        b.close()
    if not html_path and os.path.exists(src):
        os.remove(src)
    return pdf_path
