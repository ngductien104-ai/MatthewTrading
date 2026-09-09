"""News — ``vnstock_news`` is the truth source.

Two distinct paths, deliberately kept separate:

* :func:`company_news` — headlines already tagged to a ticker, from the
  sponsored ``vnstock_data`` reference layer. Use it when the question is
  "what happened at this company".
* :func:`crawl` — full article text from the 21 Vietnamese outlets
  ``vnstock_news`` supports. Use it when the question needs the body of the
  article, not just the headline.
* :func:`rss` — headline, link, timestamp and summary straight from a
  publisher's own feed, parsed here. Use it when :func:`crawl` comes back
  blank or the outlet is not one of the 21.

Why :func:`rss` exists. Measured 09/09/2026: ``vnstock_news`` returns three
rows for ``vneconomy.vn/chung-khoan.rss`` with **every field empty** —
``title``, ``publish_time``, ``short_description`` all blank — while the feed
itself serves 50 well-formed items. Its article extractor no longer matches
that site. The feed already carries everything a news wire needs, so this
module reads it directly rather than reporting "no news" for a publisher that
is publishing normally. It also reaches outlets outside the supported 21
(TinnhanhChungKhoan).

The old workaround of scraping headlines through ``Company.news(source="kbs")``
is retired: it returned a different schema per source and carried no article
body.
"""

from __future__ import annotations

import email.utils
import html as _html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import pandas as pd

from vndata.errors import SourceUnavailable


def supported_sites() -> list[dict[str, str]]:
    """Return the outlets ``vnstock_news`` can crawl, as ``{name, domain}``."""
    try:
        import vnstock_news
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable("vnstock_news is not installed.") from exc
    return vnstock_news.list_supported_sites()


def company_news(symbol: str, **kwargs) -> pd.DataFrame:
    """Return ticker-tagged headlines for *symbol* from the reference layer."""
    try:
        from vnstock_data import Reference
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable("vnstock_data is not installed.") from exc
    ticker = symbol.strip().upper().replace(".VN", "")
    try:
        return Reference().company(ticker).news(**kwargs)
    except Exception as exc:
        raise SourceUnavailable(f"vnstock_data could not serve news for {symbol}: {exc}") from exc


def crawl(
    sources: Sequence[str],
    *,
    max_articles: int = 10,
    time_frame: str = "1d",
    clean_content: bool = True,
    **kwargs: Any,
) -> Any:
    """Fetch full article text from Vietnamese outlets.

    Args:
        sources: **Feed or article URLs**, plus ``site_name=`` naming the outlet.
            Bare site names from :func:`supported_sites` are accepted by the
            upstream signature but return an EMPTY frame without raising --
            measured 09/09/2026: ``crawl(["cafef"])`` -> 0 rows, while
            ``crawl(["https://cafef.vn/thi-truong-chung-khoan.rss"],
            site_name="cafef")`` -> 3 rows. Use the URL form.
        max_articles: Cap per source.
        time_frame: Lookback window understood upstream, e.g. ``"1d"``, ``"7d"``.
        clean_content: Strip boilerplate from the article body.
        **kwargs: Passed through to ``EnhancedNewsCrawler.fetch_articles``.

    Returns:
        Whatever the upstream crawler returns — a list of article dicts with
        metadata and markdown body.

    Raises:
        SourceUnavailable: If ``vnstock_news`` is missing or the crawl fails.
    """
    try:
        from vnstock_news import EnhancedNewsCrawler
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SourceUnavailable("vnstock_news is not installed.") from exc

    crawler = EnhancedNewsCrawler()
    try:
        result = crawler.fetch_articles(
            sources=list(sources),
            max_articles=max_articles,
            time_frame=time_frame,
            clean_content=clean_content,
            **kwargs,
        )
    except Exception as exc:
        raise SourceUnavailable(f"vnstock_news crawl failed for {list(sources)}: {exc}") from exc

    # Bare site names return an empty frame instead of raising. Twenty-one
    # outlets producing literally nothing in a day is not a quiet news day, it
    # is the wrong call shape -- say so rather than handing back an empty frame
    # a caller will read as "no news".
    bare = [s for s in sources if "://" not in str(s)]
    if bare and len(result) == 0:
        raise SourceUnavailable(
            "vnstock_news returned 0 articles for bare site name(s) "
            f"{bare}. Pass the feed URL instead, with site_name=, e.g. "
            'crawl(["https://cafef.vn/thi-truong-chung-khoan.rss"], '
            'site_name="cafef").'
        )
    return result


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
            dt = email.utils.parsedate_to_datetime(raw)
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
