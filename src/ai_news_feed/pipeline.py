import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from .content import fetch_and_extract
from .db import (
    get_connection,
    init_db,
    insert_item,
    item_exists,
    list_items_between,
    mark_feed_failure,
    mark_feed_success,
    upsert_feed,
)
from .llm import summarize_and_classify
from .blog import (
    append_reference_section,
    blog_output_filename,
    ensure_frontmatter,
    extract_title,
    render_blog_from_week_md,
    write_blog,
)
from .markdown import output_filename, render_weekly
from .rss import fetch_feed_entries
from .utils import now_local
from .web_sources import fetch_web_list_entries


def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    date_str = now_local().strftime("%Y-%m-%d")
    log_path = os.path.join("logs", f"app-{date_str}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def dedup_key(entry: Dict[str, Any], mode: str) -> str:
    if mode == "url":
        return entry.get("url") or ""
    if mode == "guid":
        return entry.get("guid") or entry.get("url") or ""
    return entry.get("guid") or entry.get("url") or ""


def week_bounds(dt: datetime) -> Tuple[datetime, datetime]:
    iso_year, iso_week, iso_weekday = dt.isocalendar()
    start = dt - timedelta(days=iso_weekday - 1)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end


def run_pipeline(cfg: Dict[str, Any]) -> None:
    setup_logging()
    db_path = cfg["storage"]["db_path"]
    init_db(db_path)
    os.makedirs(cfg["output"]["path"], exist_ok=True)

    new_items: List[Dict[str, Any]] = []

    with get_connection(db_path) as conn:
        for feed in cfg["feeds"]:
            if not feed.get("enabled", True):
                continue

            feed_id = upsert_feed(conn, feed)
            try:
                entries = fetch_feed_entries(feed["url"])
                mark_feed_success(conn, feed_id, now_local().isoformat())
                logging.info("Fetched %s entries from %s", len(entries), feed["url"])
            except Exception as exc:
                logging.exception("Feed fetch failed: %s", feed["url"])
                mark_feed_failure(conn, feed_id, str(exc))
                continue

            for entry in entries:
                key = dedup_key(entry, cfg["dedup"]["key"])
                if not key:
                    continue
                if item_exists(conn, key):
                    continue

                collected_at = now_local().isoformat()
                content, content_status = fetch_and_extract(
                    entry.get("url"),
                    entry.get("rss_summary"),
                    timeout=cfg["summarizer"].get("timeout_sec", 60),
                    max_chars=cfg["summarizer"].get("max_chars_input", 12000),
                )

                item = {
                    "feed_id": feed_id,
                    "guid": entry.get("guid"),
                    "url": entry.get("url"),
                    "dedup_key": key,
                    "title": entry.get("title"),
                    "author": entry.get("author"),
                    "published_at": entry.get("published_at"),
                    "collected_at": collected_at,
                    "source": feed.get("name"),
                    "content_status": content_status,
                    "rss_summary": entry.get("rss_summary"),
                }

                try:
                    result = summarize_and_classify(item, content, cfg)
                    item.update(
                        {
                            "summary_zh": json.dumps(
                                {
                                    "bullets": result["summary_bullets_zh"],
                                    "so_what": result["so_what_zh"],
                                },
                                ensure_ascii=False,
                            ),
                            "primary_category": result["primary_category_id"],
                            "tags_json": json.dumps(result["tags"], ensure_ascii=False),
                            "impact": result.get("impact"),
                            "category_confidence": result.get("confidence"),
                            "category_reason": result.get("reason"),
                            "status": "processed",
                            "error": None,
                        }
                    )
                    item["summary_bullets"] = result["summary_bullets_zh"]
                    item["so_what"] = result["so_what_zh"]
                    item["tags"] = result["tags"]
                    new_items.append(item)
                except Exception as exc:
                    item.update(
                        {
                            "status": "failed",
                            "error": str(exc),
                            "summary_zh": None,
                            "primary_category": None,
                            "tags_json": None,
                        }
                    )
                    insert_item(conn, item)
                    logging.exception("Item processing failed: %s", entry.get("url"))

        for src in cfg.get("web_sources", []):
            if not src.get("enabled", True):
                continue

            try:
                entries = fetch_web_list_entries(src)
                logging.info("Fetched %s entries from %s", len(entries), src["list_url"])
            except Exception as exc:
                logging.exception("Web source fetch failed: %s", src.get("list_url"))
                continue

            for entry in entries:
                entry = {
                    "guid": entry.get("url"),
                    "url": entry.get("url"),
                    "title": entry.get("title"),
                    "author": None,
                    "published_at": entry.get("published_at"),
                    "rss_summary": entry.get("rss_summary"),
                }

                key = dedup_key(entry, cfg["dedup"]["key"])
                if not key:
                    continue
                if item_exists(conn, key):
                    continue

                collected_at = now_local().isoformat()
                content, content_status = fetch_and_extract(
                    entry.get("url"),
                    entry.get("rss_summary"),
                    timeout=cfg["summarizer"].get("timeout_sec", 60),
                    max_chars=cfg["summarizer"].get("max_chars_input", 12000),
                )

                item = {
                    "feed_id": None,
                    "guid": entry.get("guid"),
                    "url": entry.get("url"),
                    "dedup_key": key,
                    "title": entry.get("title"),
                    "author": None,
                    "published_at": entry.get("published_at"),
                    "collected_at": collected_at,
                    "source": src.get("name"),
                    "content_status": content_status,
                    "rss_summary": entry.get("rss_summary"),
                }

                try:
                    result = summarize_and_classify(item, content, cfg)
                    item.update(
                        {
                            "summary_zh": json.dumps(
                                {
                                    "bullets": result["summary_bullets_zh"],
                                    "so_what": result["so_what_zh"],
                                },
                                ensure_ascii=False,
                            ),
                            "primary_category": result["primary_category_id"],
                            "tags_json": json.dumps(result["tags"], ensure_ascii=False),
                            "impact": result.get("impact"),
                            "category_confidence": result.get("confidence"),
                            "category_reason": result.get("reason"),
                            "status": "processed",
                            "error": None,
                        }
                    )
                    item["summary_bullets"] = result["summary_bullets_zh"]
                    item["so_what"] = result["so_what_zh"]
                    item["tags"] = result["tags"]
                    new_items.append(item)
                except Exception as exc:
                    item.update(
                        {
                            "status": "failed",
                            "error": str(exc),
                            "summary_zh": None,
                            "primary_category": None,
                            "tags_json": None,
                        }
                    )
                    insert_item(conn, item)
                    logging.exception("Item processing failed: %s", entry.get("url"))

        now = now_local()
        start, end = week_bounds(now)
        existing_rows = list_items_between(conn, start.isoformat(), end.isoformat())
        existing_items = []
        for row in existing_rows:
            existing_items.append(
                {
                    "title": row["title"],
                    "url": row["url"],
                    "source": row["source"],
                    "published_at": row["published_at"],
                    "collected_at": row["collected_at"],
                    "primary_category": row["primary_category"],
                    "impact": row["impact"],
                    "summary_bullets": json.loads(row["summary_zh"]).get("bullets", []) if row["summary_zh"] else [],
                    "so_what": json.loads(row["summary_zh"]).get("so_what", "") if row["summary_zh"] else "",
                    "tags": json.loads(row["tags_json"]) if row["tags_json"] else [],
                }
            )

        all_items = existing_items + [
            {
                "title": i["title"],
                "url": i["url"],
                "source": i["source"],
                "published_at": i["published_at"],
                "collected_at": i["collected_at"],
                "primary_category": i["primary_category"],
                "impact": i.get("impact"),
                "summary_bullets": i.get("summary_bullets", []),
                "so_what": i.get("so_what", ""),
                "tags": i.get("tags", []),
            }
            for i in new_items
        ]

        content_md = render_weekly(all_items, cfg)
        filename = output_filename(cfg)
        out_path = os.path.join(cfg["output"]["path"], filename)
        tmp_path = out_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content_md)
        os.replace(tmp_path, out_path)

        if cfg["output"].get("include_weekly_blog", True):
            blog_md = render_blog_from_week_md(content_md, cfg)
            blog_name = blog_output_filename(cfg)
            blog_dir = cfg["output"].get("blog_path", cfg["output"]["path"])
            blog_path = os.path.join(blog_dir, blog_name)
            os.makedirs(blog_dir, exist_ok=True)
            rel_link = os.path.relpath(out_path, start=blog_dir).replace(os.sep, "/")
            now = now_local()
            year, week, _ = now.isocalendar()
            weekly_title = f"AI Weekly Digest — {year}-W{week:02d}"
            blog_title = extract_title(blog_md, weekly_title)
            blog_md = ensure_frontmatter(blog_md, blog_title, now.strftime("%Y-%m-%d"))
            blog_md = append_reference_section(blog_md, weekly_title, rel_link)
            write_blog(blog_md, blog_path)

        for item in new_items:
            insert_item(conn, item)
