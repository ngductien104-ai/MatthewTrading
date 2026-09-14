"""Small, schema-checked adapters for first-party public data."""
from __future__ import annotations

import calendar
import re
from html.parser import HTMLParser

import pandas as pd
import requests


NSO_API = "https://www.nso.gov.vn/wp-json/wp/v2"
_MONTHS = {
    "một": 1, "hai": 2, "ba": 3, "tư": 4, "bốn": 4, "năm": 5,
    "sáu": 6, "bảy": 7, "tám": 8, "chín": 9, "mười": 10,
    "mười một": 11, "mười hai": 12,
}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data.strip():
            self.parts.append(data.strip())


def _plain(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    return " ".join(parser.parts)


def parse_cpi_post(title: str, html: str, published_at: str, url: str) -> dict:
    """Extract monthly headline CPI YoY from one official NSO release."""
    normalized_title = title.casefold()
    month_match = re.search(r"tháng\s+(mười hai|mười một|[a-zà-ỹ]+)", normalized_title)
    year_match = re.search(r"năm\s+(20\d{2})", normalized_title)
    if not month_match or not year_match or month_match.group(1) not in _MONTHS:
        raise ValueError("NSO CPI title does not contain a recognized month/year")
    text = _plain(html).casefold()
    value_match = re.search(
        r"chỉ số giá tiêu dùng(?:\s*\(cpi\))?\s+tháng\s+.+?"
        r"(?P<direction>tăng|giảm)\s+(?P<value>\d+(?:[,.]\d+)?)%\s+so với cùng kỳ",
        text,
    )
    if not value_match:
        raise ValueError("NSO CPI release is missing headline YoY CPI")
    value = float(value_match.group("value").replace(",", "."))
    if value_match.group("direction") == "giảm":
        value = -value
    year = int(year_match.group(1))
    month = _MONTHS[month_match.group(1)]
    observed = f"{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
    return {"time": observed, "cpi_total": value, "published_at": published_at,
            "title": title, "url": url, "source": "Cục Thống kê (NSO)"}


def nso_cpi(limit: int = 18, timeout: float = 20) -> pd.DataFrame:
    """Fetch recent monthly CPI releases from the official NSO WordPress API."""
    response = requests.get(
        NSO_API + "/search",
        params={"search": "chỉ số giá tiêu dùng", "per_page": min(max(limit, 1), 100)},
        timeout=timeout,
        headers={"User-Agent": "ThirdEyes/1.0 (personal research monitor)"},
    )
    response.raise_for_status()
    rows = []
    failures = []
    for item in response.json():
        try:
            post = requests.get(
                NSO_API + "/posts/" + str(item["id"]),
                params={"_fields": "date,link,title,content"}, timeout=timeout,
                headers={"User-Agent": "ThirdEyes/1.0 (personal research monitor)"},
            )
            post.raise_for_status()
            payload = post.json()
            rows.append(parse_cpi_post(payload["title"]["rendered"],
                                       payload["content"]["rendered"],
                                       payload["date"], payload["link"]))
        except (KeyError, TypeError, ValueError, requests.RequestException) as exc:
            failures.append(f"{item.get('id', 'unknown')}: {type(exc).__name__}")
    if not rows:
        raise ValueError("No valid CPI release returned by NSO: " + ", ".join(failures))
    frame = pd.DataFrame(rows).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    frame.attrs["parse_failures"] = failures
    return frame
