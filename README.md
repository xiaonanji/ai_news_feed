# AI News Feed

Local CLI that ingests RSS feeds, deduplicates, summarizes/classifies with LLM, and writes weekly Markdown digests.

## Quick Start

1. Create and activate venv.
2. Install deps: `pip install -r requirements.txt`
3. Create `.env` with `OPENAI_API_KEY=...`.
4. Edit `config.yaml` (feeds, web_sources, schedule, output, blog).
5. Run: `python main.py run --config config.yaml`

## Notes
- Default timezone: Australia/Melbourne
- SQLite used for dedup and status tracking
- `web_sources` lets you scrape listing pages without RSS. Use CSS selectors for best reliability.
- Weekly blog summary can be generated to a `_summary.md` file via `output.include_weekly_blog`.
- You can generate a blog from an existing weekly md file: `python main.py blog --config config.yaml --week-file path/to/week.md`.
