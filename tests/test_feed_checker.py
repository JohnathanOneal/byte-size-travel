import pytest
from config.source_manager import SourceManager

def test_can_load_sources_file():
    checker = SourceManager("tests/fixtures/test_sources.yaml")
    sources = checker.load_sources()

    assert len(sources) > 0
    assert all(["name" in s and "url" in s for s in sources])

def test_can_validate_feed_url():
    checker = SourceManager()
    # Test with known good RSS feed
    result = checker.check_feed("https://www.travelzoo.com/feed/")

    assert result["is_valid"] == True
    assert "title" in result

def test_handles_invalid_feed_url():
    checker = SourceManager()
    result = checker.check_feed("https://notarealwebsite.com/feed")
    
    assert result["is_valid"] == False
