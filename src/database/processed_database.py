import sqlite3
import json
from pathlib import Path
import os
from typing import Dict, List, Optional
from models.schemas import ProcessedArticle


class ProcessedDatabase:
    def __init__(self, db_path: str = ":memory:"):
        # Use the same database file as FetchDatabase
        if db_path == ":memory:":
            self.db_path = db_path
        elif db_path == "main":
            db_dir = Path(os.getenv('DATABASE_PATH'))
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "travel_articles.db")
        else:
            raise ValueError("Invalid database path")

        self.conn = None
        self.setup_database()

    def setup_database(self):
        """Initialize database connection and create processed_articles table"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Create processed_articles table
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
                FOREIGN KEY (fetched_article_id) REFERENCES articles (id),
                UNIQUE(fetched_article_id)
            )
        """)
        self.conn.commit()

    def is_connected(self) -> bool:
        """Check if database connection is active"""
        try:
            self.conn.execute("SELECT 1")
            return True
        except (sqlite3.Error, AttributeError):
            return False

    def save_article(self, article: ProcessedArticle) -> Optional[int]:
        """Save an enriched article to the database"""
        try:
            query = """
                INSERT OR REPLACE INTO processed_articles (
                    fetched_article_id, content_type, deal_data, locations, audience,
                    key_themes, seasonality, processed_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (
                article.fetched_article_id,
                article.content_type,
                article.deal_data.model_dump_json() if article.deal_data else None,
                article.locations.model_dump_json(),
                json.dumps(article.audience),
                json.dumps(article.key_themes),
                json.dumps(article.seasonality),
                article.processed_date.isoformat()
            )
            
            cursor = self.conn.execute(query, values)
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error saving processed article: {e}")
            return None

    def get_unprocessed_articles(self) -> List[Dict]:
        """Get articles that haven't been processed yet"""
        try:
            query = """
                SELECT a.* FROM articles a
                LEFT JOIN processed_articles p ON a.id = p.fetched_article_id
                WHERE p.id IS NULL AND a.is_full_content_fetched = 1
            """
            cursor = self.conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting unprocessed articles: {e}")
            return []

    def get_high_value_deals(self, min_score: int = 8) -> List[Dict]:
        """Get current high-value deals with full article data"""
        try:
            query = """
                SELECT a.*, p.* 
                FROM articles a
                JOIN processed_articles p ON a.id = p.fetched_article_id
                WHERE p.content_type = 'deal'
                AND json_extract(p.deal_data, '$.value_score') >= ?
                AND date(json_extract(p.deal_data, '$.booking_deadline')) > date('now')
                ORDER BY json_extract(p.deal_data, '$.value_score') DESC
                LIMIT 1
            """
            cursor = self.conn.execute(query, [min_score])
            result = cursor.fetchone()
            return dict(result) if result else None
        except sqlite3.Error as e:
            print(f"Error getting high value deals: {e}")
            return None

    def get_matching_guides(self, location: str, limit: int = 2) -> List[Dict]:
        """Get guides matching a location"""
        try:
            query = """
                SELECT a.*, p.*
                FROM articles a
                JOIN processed_articles p ON a.id = p.fetched_article_id
                WHERE p.content_type IN ('guide', 'experience')
                AND json_extract(p.locations, '$.primary') = ?
                LIMIT ?
            """
            cursor = self.conn.execute(query, [location, limit])
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting matching guides: {e}")
            return []

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
