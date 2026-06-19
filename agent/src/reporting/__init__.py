"""Reporting utilities — dựng báo cáo PDF (chart + HTML → Playwright/Chromium) cho output swarm.

Tách khỏi src/tools/ để KHÔNG bị auto-discovery import (report_lib kéo matplotlib +
playwright; chỉ import khi thực sự cần xuất báo cáo).

Yêu cầu runtime: matplotlib + playwright (+ chromium) trong venv đang chạy.
"""
from src.reporting.report_lib import (
    BRAND_NAME,
    BRAND_TAGLINE,
    BRAND_URL,
    CSS,
    brand_bar,
    build_html,
    chart_block,
    chart_net_bars,
    chart_price_liquidity,
    render_pdf,
)

__all__ = [
    "BRAND_NAME",
    "BRAND_TAGLINE",
    "BRAND_URL",
    "CSS",
    "brand_bar",
    "build_html",
    "chart_block",
    "chart_net_bars",
    "chart_price_liquidity",
    "render_pdf",
]
