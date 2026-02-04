import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


@contextmanager
def get_connection(db_path: str):
    ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY,
                name TEXT,
                url TEXT UNIQUE,
                enabled INTEGER,
                last_fetch_at TEXT,
                fail_count INTEGER,
                last_error TEXT
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                feed_id INTEGER,
                guid TEXT NULL,
                url TEXT,
                dedup_key TEXT UNIQUE,
                title TEXT,
                author TEXT NULL,
                published_at TEXT NULL,
                collected_at TEXT,
                source TEXT,
                content_status TEXT,
                summary_zh TEXT,
                primary_category TEXT,
                tags_json TEXT,
                impact TEXT NULL,
                category_confidence REAL NULL,
                category_reason TEXT NULL,
                status TEXT,
                error TEXT NULL,
                FOREIGN KEY(feed_id) REFERENCES feeds(id)
            );
            """
        )


def upsert_feed(conn: sqlite3.Connection, feed: Dict[str, Any]) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO feeds (name, url, enabled, fail_count) VALUES (?, ?, ?, 0)",
        (feed["name"], feed["url"], 1 if feed.get("enabled", True) else 0),
    )
    conn.execute(
        "UPDATE feeds SET name = ?, enabled = ? WHERE url = ?",
        (feed["name"], 1 if feed.get("enabled", True) else 0, feed["url"]),
    )
    row = conn.execute("SELECT id FROM feeds WHERE url = ?", (feed["url"],)).fetchone()
    return int(row["id"]) if row else 0


def mark_feed_success(conn: sqlite3.Connection, feed_id: int, fetched_at: str) -> None:
    conn.execute(
        "UPDATE feeds SET last_fetch_at = ?, last_error = NULL WHERE id = ?",
        (fetched_at, feed_id),
    )


def mark_feed_failure(conn: sqlite3.Connection, feed_id: int, error: str) -> None:
    conn.execute(
        "UPDATE feeds SET fail_count = COALESCE(fail_count, 0) + 1, last_error = ? WHERE id = ?",
        (error, feed_id),
    )


def item_exists(conn: sqlite3.Connection, dedup_key: str) -> bool:
    row = conn.execute("SELECT 1 FROM items WHERE dedup_key = ?", (dedup_key,)).fetchone()
    return row is not None


def insert_item(conn: sqlite3.Connection, item: Dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO items (
            feed_id, guid, url, dedup_key, title, author, published_at, collected_at,
            source, content_status, summary_zh, primary_category, tags_json, impact,
            category_confidence, category_reason, status, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.get("feed_id"),
            item.get("guid"),
            item.get("url"),
            item.get("dedup_key"),
            item.get("title"),
            item.get("author"),
            item.get("published_at"),
            item.get("collected_at"),
            item.get("source"),
            item.get("content_status"),
            item.get("summary_zh"),
            item.get("primary_category"),
            item.get("tags_json"),
            item.get("impact"),
            item.get("category_confidence"),
            item.get("category_reason"),
            item.get("status"),
            item.get("error"),
        ),
    )


def list_items_between(conn: sqlite3.Connection, start_iso: str, end_iso: str):
    return conn.execute(
        """
        SELECT * FROM items
        WHERE collected_at >= ? AND collected_at < ? AND status = 'processed'
        """,
        (start_iso, end_iso),
    ).fetchall()
