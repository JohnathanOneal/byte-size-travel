from pathlib import Path
import sqlite3
from datetime import datetime
from typing import Dict, Optional


class FetchDatabase:
    def __init__(self, db_path: str = ":memory:"):
        # in memory database used for testing
        if db_path == ":memory:":
            self.db_path = db_path
        elif db_path == "main":
            # Create data/db directory if it doesn't exist
            db_dir = Path("data/db")
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "travel_news.db")
        else:
            raise ValueError("Invalid database path")
        
        self.conn = None
        self.setup_database()

    def setup_database(self):
        """Initialize database connection and create tables"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Create articles table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content TEXT,
                published_date DATETIME,
                fetched_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL
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

    def store_article(self, article: Dict) -> Optional[int]:
        """Store an article, handle duplicates via UNIQUE constraint"""
        try:
            # First check if article exists by URL
            cursor = self.conn.execute(
                "SELECT id FROM articles WHERE url = ?",
                (article["url"],)
            )
            existing = cursor.fetchone()

            if existing:
                return existing[0]  # Return existing ID

            # If not exists, insert new
            cursor = self.conn.execute("""
                INSERT INTO articles 
                (title, url, content, published_date, source_name, source_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                article["title"],
                article["url"],
                article["content"],
                article["published_date"].isoformat(),
                article["source_name"],
                article["source_url"]
            ))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error storing article: {e}")
            return None

    def get_article(self, article_id: int) -> Optional[Dict]:
        """Retrieve an article by its ID"""
        try:
            result = self.conn.execute(
                """
                SELECT id, title, url, content, published_date, 
                       source_name, source_url, fetched_date
                FROM articles 
                WHERE id = ?
                """,
                (article_id,)
            ).fetchone()

            if result:
                return dict(result)  # Convert Row to dict
            return None

        except sqlite3.Error as e:
            print(f"Error retrieving article: {e}")
            return None
