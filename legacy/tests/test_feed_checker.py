import pytest

from config.source_manager import SourceManager
from content.fetching.parsers import check_rss_feed


def test_can_load_sources_file() -> None:
    manager = SourceManager("tests/fixtures/test_sources.yaml")
    sources = manager.load_sources()

    assert len(sources) > 0
    assert all("name" in s and "url" in s for s in sources)


@pytest.mark.network
def test_can_validate_feed_url() -> None:
    source = {
        "name": "Test Feed",
        "url": "https://www.travelzoo.com/feed/",
        "type": "rss",
        "category": "travel_tips",
        "quality_score": 8,
        "active": True,
    }
    result = check_rss_feed(source)
    assert result["is_valid"]
    assert "title" in result


def test_handles_invalid_feed_url() -> None:
    source = {
        "name": "Bad Feed",
        "url": "https://notarealwebsite.invalid/feed",
        "type": "rss",
        "category": "travel_tips",
        "quality_score": 5,
        "active": True,
    }
    result = check_rss_feed(source)
    assert not result["is_valid"]
