import re
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
from readability import Document
import trafilatura

from .utils import normalize_whitespace


def clean_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = soup.get_text(" ")
    return normalize_whitespace(text)


def extract_with_readability(html: str) -> Optional[str]:
    try:
        doc = Document(html)
        summary_html = doc.summary()
        return clean_html_to_text(summary_html)
    except Exception:
        return None


def extract_with_trafilatura(html: str, url: str) -> Optional[str]:
    try:
        extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
        if not extracted:
            return None
        return normalize_whitespace(extracted)
    except Exception:
        return None


def fetch_and_extract(url: str, rss_summary: Optional[str], timeout: int, max_chars: int) -> Tuple[str, str]:
    if not url:
        return (normalize_whitespace(rss_summary or ""), "rss_only")

    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "ai-news-feed/1.0"})
        resp.raise_for_status()
        html = resp.text
    except Exception:
        return (normalize_whitespace(rss_summary or ""), "rss_only")

    text = extract_with_readability(html)
    if not text:
        text = extract_with_trafilatura(html, url)

    if not text:
        return (normalize_whitespace(rss_summary or ""), "rss_only")

    text = text[:max_chars]
    return (text, "full")
