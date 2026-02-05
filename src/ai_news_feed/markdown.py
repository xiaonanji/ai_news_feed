import json
from datetime import datetime
from typing import Any, Dict, List

from .utils import now_local, to_local


def _frontmatter(title: str, date_str: str) -> str:
    return (
        "---\n"
        f"title: {title}\n"
        "description:\n"
        f"date: {date_str}\n"
        f"scheduled: {date_str}\n"
        "tags:\n"
        "  - AI\n"
        "  - Jeremy\n"
        "layout: layouts/post.njk\n"
        "---\n\n"
    )


def _format_datetime(value: str) -> str:
    if not value:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(value)
        local = to_local(dt)
        return local.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value


def _parse_dt(value: str) -> float:
    if not value:
        return 0.0
    try:
        dt = datetime.fromisoformat(value)
        return dt.timestamp()
    except Exception:
        return 0.0


def sort_items(items: List[Dict[str, Any]], append_order: str) -> List[Dict[str, Any]]:
    impact_rank = {"High": 0, "Medium": 1, "Low": 2}
    reverse_time = append_order == "newest_first"

    def key(item):
        impact = impact_rank.get(item.get("impact"), 3)
        dt = item.get("published_at") or item.get("collected_at") or ""
        ts = _parse_dt(dt)
        if reverse_time:
            ts = -ts
        return (impact, ts)

    return sorted(items, key=key)


def _render_item(lines: List[str], item: Dict[str, Any]) -> None:
    title = item.get("title") or "(Untitled)"
    lines.append(f"### {title}")
    lines.append(f"- 来源：{item.get('source')}")
    lines.append(f"- 发布：{_format_datetime(item.get('published_at'))}")
    lines.append(f"- 收录：{_format_datetime(item.get('collected_at'))}")
    lines.append(f"- 链接：{item.get('url')}")
    lines.append("")
    lines.append("**摘要**")
    bullets = item.get("summary_bullets", [])
    for bullet in bullets:
        lines.append(f"- {bullet}")
    lines.append("")
    lines.append("**意义**")
    lines.append(item.get("so_what", ""))
    lines.append("")
    tags = item.get("tags", [])
    tag_str = " / ".join(tags)
    lines.append(f"**标签**：{tag_str}")
    lines.append("")
    lines.append("---")
    lines.append("")


def render_weekly(items: List[Dict[str, Any]], cfg: Dict[str, Any]) -> str:
    now = now_local()
    year, week, _ = now.isocalendar()
    title = f"AI Weekly Digest — {year}-W{week:02d}"
    lines = [f"# {title}", f"生成时间：{now.strftime('%Y-%m-%d %H:%M')} (Australia/Melbourne)", ""]

    taxonomy = cfg.get("taxonomy", {})
    categories = taxonomy.get("categories", [])
    grouping = cfg["output"].get("grouping", "by_category")

    if grouping == "flat":
        sorted_items = sort_items(items, cfg["output"].get("append_order", "newest_first"))
        for item in sorted_items:
            _render_item(lines, item)
        body = "\n".join(lines)
        if cfg["output"].get("include_frontmatter", False):
            return _frontmatter(title, now.strftime("%Y-%m-%d")) + body
        return body

    grouped: Dict[str, List[Dict[str, Any]]] = {c["id"]: [] for c in categories}
    for item in items:
        grouped.setdefault(item.get("primary_category"), []).append(item)

    for cat in categories:
        cat_id = cat["id"]
        cat_name = cat.get("name_zh", cat_id)
        lines.append(f"## {cat_name}")

        cat_items = sort_items(grouped.get(cat_id, []), cfg["output"].get("append_order", "newest_first"))
        for item in cat_items:
            _render_item(lines, item)

    body = "\n".join(lines)
    if cfg["output"].get("include_frontmatter", False):
        return _frontmatter(title, now.strftime("%Y-%m-%d")) + body
    return body


def output_filename(cfg: Dict[str, Any]) -> str:
    mode = cfg["output"].get("mode", "weekly_file")
    if mode == "single_file":
        return "ai_news.md"
    now = now_local()
    year, week, _ = now.isocalendar()
    template = cfg["output"]["filename_template"]
    return template.format(year=year, week=f"{week:02d}")
