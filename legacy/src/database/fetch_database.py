import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from config.logging_config import fetch_logger as logger

load_dotenv()


class FetchDatabase:
    def __init__(self, db_path: str = ":memory:") -> None:
        if db_path == ":memory:":
            self.db_path = db_path
        elif db_path == "main":
            db_dir = Path(os.getenv("DATABASE_PATH"))
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "travel_articles.db")
        else:
            msg = "Invalid database path"
            raise ValueError(msg)

        self.conn = None
        self.setup_database()

    def setup_database(self) -> None:
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content TEXT,
                published_date DATETIME,
                fetched_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                is_full_content_fetched BOOLEAN DEFAULT 0
            )
        """)
        self.conn.commit()

    def is_connected(self) -> bool:
        try:
            self.conn.execute("SELECT 1")
        except (sqlite3.Error, AttributeError):
            return False
        else:
            return True

    def store_article(self, article: dict) -> int | None:
        try:
            cursor = self.conn.execute(
                "SELECT id FROM articles WHERE url = ?",
                (article["url"],),
            )
            existing = cursor.fetchone()

            if existing:
                return existing[0]

            cursor = self.conn.execute(
                "INSERT INTO articles"
                " (title, url, content, published_date,"
                "  source_name, source_url,"
                "  is_full_content_fetched)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    article["title"],
                    article["url"],
                    article["content"],
                    article["published_date"].isoformat(),
                    article["source_name"],
                    article["source_url"],
                    article.get("is_full_content_fetched", False),
                ),
            )
            self.conn.commit()
        except sqlite3.Error:
            return None
        else:
            return cursor.lastrowid

    def get_article(self, article_id: int) -> dict | None:
        try:
            result = self.conn.execute(
                "SELECT id, title, url, content,"
                " published_date, source_name, source_url,"
                " fetched_date, is_full_content_fetched"
                " FROM articles WHERE id = ?",
                (article_id,),
            ).fetchone()
        except sqlite3.Error:
            return None
        else:
            if result:
                return dict(result)
            return None

    def get_articles_without_content(self, batch_size: int = 10) -> list[dict]:
        try:
            cursor = self.conn.execute(
                "SELECT id, url FROM articles"
                " WHERE is_full_content_fetched = 0"
                " LIMIT ?",
                (batch_size,),
            )
        except sqlite3.Error:
            logger.exception("Error getting articles")
            return []
        else:
            return [dict(row) for row in cursor.fetchall()]

    def update_article_content(self, article_id: int, content: str) -> bool:
        try:
            logger.debug(
                "DB Connection status: %s",
                self.is_connected(),
            )
            self.conn.execute(
                "UPDATE articles"
                " SET content = ?, is_full_content_fetched = 1"
                " WHERE id = ?",
                (content, article_id),
            )
            self.conn.commit()
        except sqlite3.Error:
            logger.exception("Error updating article %d", article_id)
            return False
        else:
            logger.info(
                "Fetched full content for article %d",
                article_id,
            )
            return True
