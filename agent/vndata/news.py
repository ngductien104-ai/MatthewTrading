"""News — ``vnstock_news`` is the truth source.

Two distinct paths, deliberately kept separate:

* :func:`company_news` — headlines already tagged to a ticker, from the
  sponsored ``vnstock_data`` reference layer. Use it when the question is
  "what happened at this company".
* :func:`crawl` — full article text from the 21 Vietnamese outlets
  ``vnstock_news`` supports. Use it when the question needs the body of the
  article, not just the headline.

The old workaround of scraping headlines through ``Company.news(source="kbs")``
is retired: it returned a different schema per source and carried no article
body.
"""

from __future__ import annotations

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
        sources: Site names from :func:`supported_sites` (``"cafef"``,
            ``"vietstock"``, ...) or article URLs.
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
        return crawler.fetch_articles(
            sources=list(sources),
            max_articles=max_articles,
            time_frame=time_frame,
            clean_content=clean_content,
            **kwargs,
        )
    except Exception as exc:
        raise SourceUnavailable(f"vnstock_news crawl failed for {list(sources)}: {exc}") from exc
