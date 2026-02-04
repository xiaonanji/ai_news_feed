import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


def _parse_datetime(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    try:
        dt = date_parser.parse(text, fuzzy=True)
        return dt.isoformat()
    except Exception:
        return None


def _safe_url(list_url: str, href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    if href.startswith("mailto:") or href.startswith("#"):
        return None
    return urljoin(list_url, href)


def _match_regex(value: str, pattern: Optional[str]) -> bool:
    if not pattern:
        return True
    try:
        return re.search(pattern, value) is not None
    except re.error:
        return True


def _within_domain(base_url: str, url: str) -> bool:
    try:
        return urlparse(base_url).netloc == urlparse(url).netloc
    except Exception:
        return False


def _extract_from_items(
    list_url: str,
    soup: BeautifulSoup,
    src: Dict[str, Any],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    item_selector = src.get("item_selector")
    title_selector = src.get("title_selector")
    url_selector = src.get("url_selector")
    date_selector = src.get("date_selector")
    summary_selector = src.get("summary_selector")

    if not item_selector:
        return items

    for node in soup.select(item_selector):
        title = None
        url = None
        published_at = None
        summary = None

        if title_selector:
            tnode = node.select_one(title_selector)
            if tnode:
                title = tnode.get_text(strip=True)
        if url_selector:
            unode = node.select_one(url_selector)
            if unode and unode.get("href"):
                url = _safe_url(list_url, unode.get("href"))
        if date_selector:
            dnode = node.select_one(date_selector)
            if dnode:
                published_at = _parse_datetime(dnode.get_text(strip=True) or dnode.get("datetime"))
        if summary_selector:
            snode = node.select_one(summary_selector)
            if snode:
                summary = snode.get_text(strip=True)

        if title and url:
            items.append(
                {
                    "title": title,
                    "url": url,
                    "published_at": published_at,
                    "rss_summary": summary,
                }
            )

    return items


def _extract_heuristic(list_url: str, soup: BeautifulSoup, src: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen = set()

    include_regex = src.get("include_url_regex")
    exclude_regex = src.get("exclude_url_regex")

    for h2 in soup.find_all("h2"):
        title = h2.get_text(strip=True)
        if not title or len(title) < 8:
            continue

        link = h2.find_parent("a", href=True)
        if not link:
            link = h2.find("a", href=True) or h2.find_parent().find("a", href=True)
        if not link:
            link = h2.find_previous("a", href=True)
        if not link:
            continue

        url = _safe_url(list_url, link.get("href"))
        if not url:
            continue
        if not _within_domain(list_url, url):
            continue
        if not _match_regex(url, include_regex):
            continue
        if exclude_regex and _match_regex(url, exclude_regex):
            continue
        if url in seen:
            continue

        published_at = None
        time_tag = h2.find_parent().find("time") if h2.find_parent() else None
        if time_tag:
            published_at = _parse_datetime(time_tag.get("datetime") or time_tag.get_text(strip=True))

        items.append(
            {
                "title": title,
                "url": url,
                "published_at": published_at,
                "rss_summary": None,
            }
        )
        seen.add(url)

    return items


def fetch_web_list_entries(src: Dict[str, Any]) -> List[Dict[str, Any]]:
    list_url = src["list_url"]
    resp = requests.get(list_url, timeout=30, headers={"User-Agent": "ai-news-feed/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = _extract_from_items(list_url, soup, src)
    if not items:
        items = _extract_heuristic(list_url, soup, src)

    max_items = int(src.get("max_items", 50))
    return items[:max_items]
