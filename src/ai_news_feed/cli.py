import argparse
import os
import sys

from dotenv import load_dotenv

from .config import load_config
from .db import init_db
from .blog import blog_output_filename, render_blog_from_week_md, write_blog
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai_news_feed")
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run", help="Run RSS fetch + summarize + output")
    run_cmd.add_argument("--config", required=True, help="Path to config.yaml")

    init_cmd = sub.add_parser("init-db", help="Initialize SQLite DB")
    init_cmd.add_argument("--config", required=True, help="Path to config.yaml")

    blog_cmd = sub.add_parser("blog", help="Generate weekly blog from a weekly md file")
    blog_cmd.add_argument("--config", required=True, help="Path to config.yaml")
    blog_cmd.add_argument("--week-file", required=True, help="Path to weekly md file")

    return parser


def main(argv=None):
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 2

    cfg = load_config(args.config)

    if args.command == "init-db":
        init_db(cfg["storage"]["db_path"])
        return 0

    if args.command == "run":
        run_pipeline(cfg)
        return 0

    if args.command == "blog":
        with open(args.week_file, "r", encoding="utf-8") as f:
            week_md = f.read()
        blog_md = render_blog_from_week_md(week_md, cfg)
        blog_name = blog_output_filename(cfg)
        out_path = os.path.join(cfg["output"]["path"], blog_name)
        write_blog(blog_md, out_path)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
