# AI News Feed

Local CLI that ingests RSS feeds, deduplicates, summarizes/classifies with LLM, and writes weekly Markdown digests plus a weekly blog post.

## Requirements

- Python 3.10+

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## API Key Setup

Set your OpenAI API key using either an environment variable or a file:

- `.env` (recommended):
  ```bash
  OPENAI_API_KEY=your_key_here
  ```
- Or set `summarizer.api_key_file` in `config.yaml` to a file containing the key.

The CLI loads `.env` automatically via `python-dotenv`.

## Configuration

All settings live in `config.yaml`. Common fields:

- `feeds`: RSS feeds to ingest.
- `web_sources`: list pages to scrape when RSS isn’t available.
- `schedule`: cron-like schedule for external schedulers.
- `storage.db_path`: SQLite database for dedup and tracking.
- `output.path`: output directory for weekly news files.
- `output.blog_path`: output directory for weekly blog files.
- `output.filename_template`: weekly news filename.
- `output.blog_filename_template`: weekly blog filename.
- `output.include_frontmatter`: add YAML frontmatter to weekly news.
- `output.include_weekly_blog`: generate a weekly blog from the news.

## Commands

Run the full pipeline (fetch → summarize → write weekly + blog):

```bash
python main.py run --config config.yaml
```

Initialize the SQLite database:

```bash
python main.py init-db --config config.yaml
```

Generate a blog from an existing weekly markdown file:

```bash
python main.py blog --config config.yaml --week-file path/to/weekly.md
```

## Output

By default, outputs are written to `output.path` and `output.blog_path`:

- Weekly news: `ai_news_{year}-W{week}.md`
- Weekly blog: `ai_news_{year}-W{week}_summary.md`

Both weekly news and blog outputs include the same YAML frontmatter schema and the blog ends with a reference link back to the weekly news file.

## Notes

- Default timezone: Australia/Melbourne
- SQLite is used for deduplication and status tracking
- `web_sources` supports CSS selectors for summary extraction
