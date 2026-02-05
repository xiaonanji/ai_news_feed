import os
from dataclasses import dataclass
from typing import Any, Dict

import yaml


class ConfigError(Exception):
    pass


def load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise ConfigError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    apply_defaults(cfg)
    validate_config(cfg)
    return cfg


def apply_defaults(cfg: Dict[str, Any]) -> None:
    cfg.setdefault("feeds", [])
    cfg.setdefault("web_sources", [])
    cfg.setdefault("schedule", {"mode": "cron", "cron": "0 9 * * MON"})
    cfg.setdefault("storage", {"db_path": "./data/ai_news.db"})
    cfg.setdefault("output", {})
    cfg["output"].setdefault("mode", "weekly_file")
    cfg["output"].setdefault("path", "./output")
    cfg["output"].setdefault("filename_template", "ai_news_{year}-W{week}.md")
    cfg["output"].setdefault("grouping", "by_category")
    cfg["output"].setdefault("append_order", "newest_first")
    cfg["output"].setdefault("include_toc", True)
    cfg["output"].setdefault("include_frontmatter", False)
    cfg["output"].setdefault("include_weekly_blog", True)
    cfg["output"].setdefault("blog_filename_template", "ai_news_{year}-W{week}_summary.md")
    cfg["output"].setdefault("blog_path", cfg["output"].get("path", "./output"))

    cfg.setdefault("dedup", {"key": "url_or_guid"})
    cfg.setdefault("summarizer", {})
    cfg["summarizer"].setdefault("provider", "openai")
    cfg["summarizer"].setdefault("model", "gpt-4.1-mini")
    cfg["summarizer"].setdefault("language", "zh-CN")
    cfg["summarizer"].setdefault("max_chars_input", 12000)
    cfg["summarizer"].setdefault("timeout_sec", 60)
    cfg["summarizer"].setdefault("concurrency", 3)
    cfg["summarizer"].setdefault("retries", 3)
    cfg["summarizer"].setdefault("api_key_env", "OPENAI_API_KEY")
    cfg["summarizer"].setdefault("api_key_file", "")

    cfg.setdefault("blog", {})
    cfg["blog"].setdefault("model", cfg["summarizer"]["model"])
    cfg["blog"].setdefault("max_chars_input", 20000)

    cfg.setdefault("classification", {})
    cfg["classification"].setdefault("mode", "llm_with_keyword_fallback")
    cfg["classification"].setdefault("require_primary_category", True)
    cfg["classification"].setdefault("tag_count_range", [3, 8])
    cfg["classification"].setdefault("include_impact", True)

    cfg.setdefault("taxonomy", {})
    cfg["taxonomy"].setdefault("allow_multi_label", False)
    cfg["taxonomy"].setdefault("default_category", "products_apps")
    cfg["taxonomy"].setdefault("categories", [])


def validate_config(cfg: Dict[str, Any]) -> None:
    if not isinstance(cfg.get("feeds"), list):
        raise ConfigError("feeds must be a list")
    for feed in cfg["feeds"]:
        if "name" not in feed or "url" not in feed:
            raise ConfigError("Each feed requires name and url")
        feed.setdefault("enabled", True)
    if not isinstance(cfg.get("web_sources"), list):
        raise ConfigError("web_sources must be a list")
    for src in cfg["web_sources"]:
        if "name" not in src or "list_url" not in src:
            raise ConfigError("Each web_source requires name and list_url")
        src.setdefault("enabled", True)
        src.setdefault("max_items", 50)
    if not cfg["taxonomy"]["categories"]:
        raise ConfigError("taxonomy.categories cannot be empty")


def taxonomy_id_order(cfg: Dict[str, Any]):
    return [c["id"] for c in cfg["taxonomy"]["categories"]]


def taxonomy_map(cfg: Dict[str, Any]):
    return {c["id"]: c for c in cfg["taxonomy"]["categories"]}
