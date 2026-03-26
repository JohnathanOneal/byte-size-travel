import pytest

from database.fetch_database import FetchDatabase
from database.populate_db import PopulateDB


def _make_source(
    name: str = "Test Feed",
    url: str = "https://www.reddit.com/r/travel/.rss",
    *,
    active: bool = True,
) -> dict:
    return {
        "name": name,
        "url": url,
        "type": "rss",
        "category": "travel_tips",
        "quality_score": 8,
        "active": active,
    }


@pytest.mark.network
def test_populate_from_single_valid_source() -> None:
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    result = populator.populate_single_source(_make_source())
    assert result["success"]
    assert result["articles_added"] > 0


def test_respects_inactive_source() -> None:
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    sources = [_make_source(active=False)]
    result = populator.populate_all_sources(sources)
    assert result["skipped"] == 1
    assert result["total_articles_added"] == 0


def test_handles_invalid_feed() -> None:
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    source = _make_source(
        name="Bad Feed",
        url="https://notarealwebsite.invalid/feed",
    )
    result = populator.populate_single_source(source)
    assert not result["success"]
    assert "error" in result


@pytest.mark.network
def test_prevents_duplicate_articles() -> None:
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    source = _make_source()
    first_result = populator.populate_single_source(source)
    second_result = populator.populate_single_source(source)

    assert first_result["articles_added"] > 0
    assert second_result["articles_added"] == 0
    assert second_result["articles_existing"] > 0


@pytest.mark.network
def test_populate_from_multiple_sources() -> None:
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    sources = [
        _make_source(name="Feed A"),
        _make_source(
            name="Feed B",
            url="https://www.reddit.com/r/backpacking/.rss",
        ),
    ]

    result = populator.populate_all_sources(sources)
    assert result["total_sources"] == 2
    assert result["successful"] == 2
    assert result["total_articles_added"] > 0


@pytest.mark.network
def test_handles_mixed_valid_and_invalid_sources() -> None:
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    sources = [
        _make_source(name="Valid Feed"),
        _make_source(
            name="Invalid Feed",
            url="https://notarealwebsite.invalid/feed",
        ),
    ]

    result = populator.populate_all_sources(sources)
    assert result["successful"] == 1
    assert result["failed"] == 1


def test_respects_multiple_inactive_sources() -> None:
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    sources = [
        _make_source(name="Inactive 1", active=False),
        _make_source(
            name="Inactive 2",
            url="https://www.reddit.com/r/backpacking/.rss",
            active=False,
        ),
    ]

    result = populator.populate_all_sources(sources)
    assert result["skipped"] == 2
    assert result["total_articles_added"] == 0


@pytest.mark.network
def test_prevent_duplicates_across_multiple_runs() -> None:
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    sources = [_make_source()]

    first_run = populator.populate_all_sources(sources)
    second_run = populator.populate_all_sources(sources)

    assert first_run["total_articles_added"] > 0
    assert second_run["total_articles_added"] == 0
    assert second_run["total_articles_existing"] > 0
