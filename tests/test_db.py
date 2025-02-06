import pytest
from datetime import datetime
from src.fetchdatabase import FetchDatabase


def test_can_connect_to_db():
    db = FetchDatabase(":memory:")  # SQLite in-memory for testing
    assert db.is_connected()


def test_can_store_article():
    db = FetchDatabase(":memory:")
    article = {
        "title": "Test Article",
        "url": "https://example.com/1",
        "content": "Test content",
        "published_date": datetime.now(),
        "source_name": "Test Feed",
        "source_url": "https://test.com/feed"
    }
    article_id = db.store_article(article)
    assert article_id is not None


def test_prevents_duplicate_articles():
    db = FetchDatabase(":memory:")
    article = {
        "title": "Test Article",
        "url": "https://example.com/1",
        "content": "Test content",
        "published_date": datetime.now(),
        "source_name": "Test Feed",
        "source_url": "https://test.com/feed"
    }
    first_id = db.store_article(article)
    second_id = db.store_article(article)
    assert first_id == second_id


def test_can_retrieve_stored_article():
    db = FetchDatabase(":memory:")
    test_article = {
        "title": "Test Article",
        "url": "https://example.com/1",
        "content": "Test content",
        "published_date": datetime.now(),
        "source_name": "Test Feed",
        "source_url": "https://test.com/feed"
    }
    article_id = db.store_article(test_article)

    retrieved = db.get_article(article_id)
    assert retrieved is not None
    assert retrieved["title"] == test_article["title"]
    assert retrieved["url"] == test_article["url"]
