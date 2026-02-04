import os
from typing import Dict, Any

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
