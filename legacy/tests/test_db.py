from datetime import UTC, datetime

from database.fetch_database import FetchDatabase


def _make_article(url: str = "https://example.com/1") -> dict:
    return {
        "title": "Test Article",
        "url": url,
        "content": "Test content",
        "published_date": datetime.now(tz=UTC),
        "source_name": "Test Feed",
        "source_url": "https://test.com/feed",
    }


def test_can_connect_to_db() -> None:
    db = FetchDatabase(":memory:")
    assert db.is_connected()


def test_can_store_article() -> None:
    db = FetchDatabase(":memory:")
    article_id = db.store_article(_make_article())
    assert article_id is not None


def test_prevents_duplicate_articles() -> None:
    db = FetchDatabase(":memory:")
    article = _make_article()
    first_id = db.store_article(article)
    second_id = db.store_article(article)
    assert first_id == second_id


def test_can_retrieve_stored_article() -> None:
    db = FetchDatabase(":memory:")
    test_article = _make_article()
    article_id = db.store_article(test_article)

    retrieved = db.get_article(article_id)
    assert retrieved is not None
    assert retrieved["title"] == test_article["title"]
    assert retrieved["url"] == test_article["url"]
