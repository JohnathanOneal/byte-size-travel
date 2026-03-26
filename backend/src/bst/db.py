import sqlite3
from pathlib import Path

import structlog

from bst.settings import settings

logger = structlog.get_logger(__name__)

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('rss', 'email')),
    url TEXT NOT NULL,
    category TEXT NOT NULL,
    quality_score INTEGER NOT NULL CHECK (quality_score BETWEEN 1 AND 10),
    active INTEGER NOT NULL DEFAULT 1,
    last_checked TEXT,
    last_error TEXT,
    config_json TEXT,
    created_date TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    content TEXT,
    published_date TEXT,
    fetched_date TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    source_id INTEGER NOT NULL REFERENCES sources(id),
    is_full_content_fetched INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS enriched_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id),
    daily_drop_category TEXT NOT NULL,
    summary TEXT NOT NULL,
    headline_angle TEXT NOT NULL,
    urgency TEXT NOT NULL CHECK (urgency IN ('breaking', 'timely', 'evergreen')),
    locations TEXT NOT NULL DEFAULT '[]',
    programs_mentioned TEXT NOT NULL DEFAULT '[]',
    cards_mentioned TEXT NOT NULL DEFAULT '[]',
    key_facts TEXT NOT NULL DEFAULT '[]',
    relevance_score INTEGER NOT NULL CHECK (relevance_score BETWEEN 1 AND 10),
    why_relevant TEXT NOT NULL,
    enriched_date TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS article_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id),
    is_saved INTEGER NOT NULL DEFAULT 0,
    tags TEXT DEFAULT '[]',
    notes TEXT,
    used_count INTEGER NOT NULL DEFAULT 0,
    last_used_date TEXT,
    created_date TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_date TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS editions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'ready', 'sent')),
    edition_date TEXT,
    notes TEXT,
    created_date TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_date TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS edition_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id INTEGER NOT NULL REFERENCES editions(id) ON DELETE CASCADE,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    section TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    UNIQUE(edition_id, article_id)
);
"""

FTS_SQL = """\
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    title,
    content,
    content=articles,
    content_rowid=id
);
"""


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or settings.database_path
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.executescript(FTS_SQL)
    conn.commit()
    logger.info("database_schema_created")
