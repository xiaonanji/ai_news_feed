import os
import re
from typing import Any, Dict

from .llm import generate_weekly_blog
from .utils import now_local


def blog_output_filename(cfg: Dict[str, Any]) -> str:
    now = now_local()
    year, week, _ = now.isocalendar()
    template = cfg["output"].get("blog_filename_template", "ai_news_{year}-W{week}_summary.md")
    return template.format(year=year, week=f"{week:02d}")


def render_blog_from_week_md(week_md: str, cfg: Dict[str, Any]) -> str:
    return generate_weekly_blog(week_md, cfg)


def write_blog(content: str, out_path: str) -> None:
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, out_path)


def append_reference_section(blog_md: str, title: str, link: str) -> str:
    body = blog_md.rstrip()
    return f"{body}\n\n## 参考\n- [{title}]({link})\n"


def extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            return title or fallback
    return fallback


def ensure_frontmatter(blog_md: str, title: str, date_str: str) -> str:
    if blog_md.lstrip().startswith("---\n"):
        return blog_md
    frontmatter = (
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
    return frontmatter + blog_md
