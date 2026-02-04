from datetime import datetime
from typing import Any, Dict, List, Optional

import feedparser
from dateutil import parser as date_parser


def parse_datetime(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        dt = date_parser.parse(value)
        return dt.isoformat()
    except Exception:
        return None


def fetch_feed_entries(url: str) -> List[Dict[str, Any]]:
    parsed = feedparser.parse(url)
    entries = []
    for entry in parsed.entries:
        entries.append(
            {
                "guid": entry.get("id") or entry.get("guid"),
                "url": entry.get("link"),
                "title": entry.get("title"),
                "author": entry.get("author"),
                "published_at": parse_datetime(entry.get("published"))
                or parse_datetime(entry.get("updated")),
                "rss_summary": entry.get("summary") or entry.get("description"),
            }
        )
    return entries
