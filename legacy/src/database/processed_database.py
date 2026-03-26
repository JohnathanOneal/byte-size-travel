import json
import os
import sqlite3
from pathlib import Path

from models.schemas import ProcessedArticle


class ProcessedDatabase:
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
            CREATE TABLE IF NOT EXISTS processed_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetched_article_id INTEGER NOT NULL,
                content_type TEXT NOT NULL,
                deal_data JSON,
                locations JSON NOT NULL,
                audience JSON NOT NULL,
                key_themes JSON NOT NULL,
                seasonality JSON NOT NULL,
                processed_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used DATETIME DEFAULT NULL,
                used_count INTEGER DEFAULT 0,
                FOREIGN KEY (fetched_article_id)
                    REFERENCES articles (id),
                UNIQUE(fetched_article_id)
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

    def save_article(self, article: ProcessedArticle) -> int | None:
        try:
            values = (
                article.fetched_article_id,
                json.dumps(article.content_type),
                article.deal_data.model_dump_json() if article.deal_data else None,
                article.locations.model_dump_json(),
                json.dumps(article.audience),
                json.dumps(article.key_themes),
                json.dumps(article.seasonality),
                article.processed_date.isoformat(),
            )

            cursor = self.conn.execute(
                "INSERT OR REPLACE INTO processed_articles"
                " (fetched_article_id, content_type,"
                "  deal_data, locations, audience,"
                "  key_themes, seasonality, processed_date)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                values,
            )
            self.conn.commit()
        except sqlite3.Error:
            return None
        else:
            return cursor.lastrowid

    def get_unprocessed_articles(self) -> list[dict]:
        try:
            cursor = self.conn.execute(
                "SELECT a.* FROM articles a"
                " LEFT JOIN processed_articles p"
                "   ON a.id = p.fetched_article_id"
                " WHERE p.id IS NULL"
                "   AND a.is_full_content_fetched = 1"
            )
        except sqlite3.Error:
            return []
        else:
            return [dict(row) for row in cursor.fetchall()]

    def get_high_value_deals(self, min_score: int = 8) -> dict | None:
        try:
            cursor = self.conn.execute(
                "SELECT a.*, p.*"
                " FROM articles a"
                " JOIN processed_articles p"
                "   ON a.id = p.fetched_article_id"
                " WHERE p.content_type = 'deal'"
                "   AND json_extract("
                "     p.deal_data, '$.value_score') >= ?"
                "   AND date(json_extract("
                "     p.deal_data, '$.booking_deadline'))"
                "     > date('now')"
                " ORDER BY json_extract("
                "   p.deal_data, '$.value_score') DESC"
                " LIMIT 1",
                [min_score],
            )
            result = cursor.fetchone()
        except sqlite3.Error:
            return None
        else:
            return dict(result) if result else None

    def get_matching_guides(self, location: str, limit: int = 2) -> list[dict]:
        try:
            cursor = self.conn.execute(
                "SELECT a.*, p.*"
                " FROM articles a"
                " JOIN processed_articles p"
                "   ON a.id = p.fetched_article_id"
                " WHERE p.content_type"
                "   IN ('guide', 'experience')"
                "   AND json_extract("
                "     p.locations, '$.primary') = ?"
                " LIMIT ?",
                [location, limit],
            )
        except sqlite3.Error:
            return []
        else:
            return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None
