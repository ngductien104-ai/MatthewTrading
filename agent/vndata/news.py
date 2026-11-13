"""News — publishers' own RSS feeds, parsed here; tagged news on VNDIRECT MCP.

``vnstock_news`` and the ``vnstock_data`` news endpoint were retired with the
vnstock subscription on 13/11/2026. What is left:

* :func:`rss` — headline, link, timestamp and summary straight from a
  publisher's own feed (CafeF, VnEconomy, Vietstock, TinnhanhCK, VnExpress).
  No vendor in between, so nothing to cancel. Measured 09/09/2026: every feed
  in :data:`VN_FEEDS` serves 20+ well-formed items.
* :func:`company_news` / :func:`crawl` — ticker-tagged headlines and full
  article text. Python has no source for these any more: ask VNDIRECT MCP for
  ticker news, or open the article URL from :func:`rss` with ``read_url`` /
  crawl4ai when the body matters.
"""

from __future__ import annotations

import email.utils
import html as _html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import pandas as pd

from vndata.errors import SourceUnavailable, moved_to_vndirect


def company_news(symbol: str, **kwargs) -> pd.DataFrame:
    """Ticker-tagged headlines — fetch via VNDIRECT MCP."""
    raise moved_to_vndirect(f"company news ({symbol})")


def crawl(sources: Sequence[str], **kwargs: Any) -> Any:
    """Full article text — no Python source since vnstock_news was retired.

    Use :func:`rss` for headlines and links, then read the article body with
    the ``read_url`` tool or crawl4ai.
    """
    raise SourceUnavailable(
        "crawl(): vnstock_news đã huỷ 13/11/2026. Dùng vndata.news.rss() lấy tiêu đề + link, "
        "rồi đọc thân bài bằng read_url / crawl4ai; tin gắn mã thì hỏi VNDIRECT MCP."
    )


# Feed dan huong cho TTCK VN. Moi URL da do 09/09/2026: tra >=20 <item>.
# ``kind`` la goi y phan loai ban dau (vi mo / nganh / doanh nghiep); no la
# PRIOR, khong phai ket luan - nguoi doc tin van phai doc tieu de de xep tab.
VN_FEEDS: dict[str, dict[str, str]] = {
    "cafef-ck":      {"site": "CafeF",      "kind": "nganh",       "url": "https://cafef.vn/thi-truong-chung-khoan.rss"},
    "cafef-dn":      {"site": "CafeF",      "kind": "doanh_nghiep","url": "https://cafef.vn/doanh-nghiep.rss"},
    "cafef-vm":      {"site": "CafeF",      "kind": "vi_mo",       "url": "https://cafef.vn/vi-mo-dau-tu.rss"},
    "vneconomy-ck":  {"site": "VnEconomy",  "kind": "nganh",       "url": "https://vneconomy.vn/chung-khoan.rss"},
    "vneconomy-tc":  {"site": "VnEconomy",  "kind": "vi_mo",       "url": "https://vneconomy.vn/tai-chinh.rss"},
    "vietstock-cp":  {"site": "Vietstock",  "kind": "doanh_nghiep","url": "https://vietstock.vn/145/chung-khoan/co-phieu.rss"},
    "vietstock-moi": {"site": "Vietstock",  "kind": "nganh",       "url": "https://vietstock.vn/0/tin-moi.rss"},
    "tnck-home":     {"site": "TinnhanhCK", "kind": "nganh",       "url": "https://www.tinnhanhchungkhoan.vn/rss/home.rss"},
    "vnexpress-kd":  {"site": "VnExpress",  "kind": "vi_mo",       "url": "https://vnexpress.net/rss/kinh-doanh.rss"},
}

_TAG_RE = re.compile(r"<[^>]+>")
_UA = {"User-Agent": "Mozilla/5.0 (compatible; vndata-news/1.0)"}


def _text(node) -> str:
    """Plain text of an RSS node: strip CDATA leftovers, tags and entities."""
    if node is None or node.text is None:
        return ""
    return _html.unescape(_TAG_RE.sub(" ", node.text)).strip()


def _published(node) -> datetime | None:
    for tag in ("pubDate", "{http://purl.org/dc/elements/1.1/}date", "updated", "published"):
        el = node.find(tag)
        if el is None or not (el.text or "").strip():
            continue
        raw = el.text.strip()
        try:
            # TinnhanhCK ghi offset co dau hai cham ("+07:00"); email.utils bo
            # qua dang nay, tra datetime naive, roi bi gan UTC ben duoi -> lech
            # 7 gio (do 12/10/2026). Bo dau hai cham truoc khi parse.
            dt = email.utils.parsedate_to_datetime(
                re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", raw))
        except (TypeError, ValueError):
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                continue
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def rss(
    sources: Sequence[str] | None = None,
    *,
    hours: float | None = 24,
    limit: int = 40,
    timeout: float = 20,
) -> pd.DataFrame:
    """Read publisher RSS feeds directly and return one row per article.

    Args:
        sources: Feed ids from :data:`VN_FEEDS`, or raw feed URLs. ``None``
            reads every curated Vietnamese feed.
        hours: Keep only items published within this many hours. ``None``
            keeps everything. Items with no parseable date are ALWAYS kept
            and marked ``published_at = NaT`` rather than silently dropped.
        limit: Cap per feed.
        timeout: Per-request timeout in seconds.

    Returns:
        DataFrame with ``title``, ``link``, ``published_at``, ``summary``,
        ``site``, ``feed``, ``kind``, sorted newest first. ``df.attrs["failed"]``
        maps feed id to the error string for any feed that did not answer —
        read it and report dead sources instead of presenting a short wire as
        a quiet news day.

    Raises:
        SourceUnavailable: Every requested feed failed.
    """
    import requests

    ids = list(sources) if sources else list(VN_FEEDS)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)) if hours else None

    rows: list[dict[str, Any]] = []
    failed: dict[str, str] = {}
    for ident in ids:
        meta = VN_FEEDS.get(str(ident), {})
        url = meta.get("url", str(ident))
        try:
            resp = requests.get(url, timeout=timeout, headers=_UA)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as exc:
            failed[str(ident)] = f"{type(exc).__name__}: {exc}"
            continue

        items = root.iter("item")
        for item in list(items)[:limit]:
            when = _published(item)
            if cutoff and when and when < cutoff:
                continue
            title = _text(item.find("title"))
            if not title:
                continue
            rows.append({
                "title": title,
                "link": _text(item.find("link")),
                "published_at": when,
                "summary": _text(item.find("description"))[:400],
                "site": meta.get("site", url.split("/")[2] if "//" in url else url),
                "feed": str(ident),
                "kind": meta.get("kind", ""),
            })

    if not rows and failed and len(failed) == len(ids):
        raise SourceUnavailable(
            "Khong feed nao tra loi: "
            + "; ".join(f"{k} -> {v}" for k, v in failed.items())
        )

    df = pd.DataFrame(rows, columns=[
        "title", "link", "published_at", "summary", "site", "feed", "kind"])
    if not df.empty:
        df = (df.drop_duplicates(subset="link")
                .sort_values("published_at", ascending=False, na_position="last")
                .reset_index(drop=True))
    df.attrs["failed"] = failed
    df.attrs["source"] = "rss"
    return df
