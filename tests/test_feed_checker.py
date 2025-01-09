import pytest
from src.feed_checker import FeedChecker

def test_can_load_sources_file():
    checker = FeedChecker("tests/fixtures/test_sources.yaml")
    sources = checker.load_sources()
    assert len(sources) > 0
    assert all(["name" in s and "url" in s for s in sources])

def test_can_validate_feed_url():
    checker = FeedChecker()
    # Test with known good RSS feed
    result = checker.check_feed("https://www.nomadicmatt.com/feed/")
     
    assert result["is_valid"] == True
    assert "title" in result

def test_handles_invalid_feed_url():
    checker = FeedChecker()
    result = checker.check_feed("https://notarealwebsite.com/feed")
    assert result["is_valid"] == False
