import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(REPO_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from ai_news_feed.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
