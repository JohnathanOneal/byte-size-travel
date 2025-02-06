import pytest
from datetime import datetime
from src.populate_db import PopulateDB
from src.fetchdatabase import FetchDatabase

def test_populate_from_single_valid_source():
    """Test populating from a single known good source"""
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)
    
    test_source = {
        "name": "Test Feed",
        "url": "https://www.reddit.com/r/travel/.rss",  # Known working feed
        "category": "test",
        "quality_score": 8.5,
        "active": True
    }
    
    result = populator.populate_single_source(test_source)
    assert result['success'] == True
    assert result['articles_added'] > 0

def test_respects_inactive_source():
    """Test that inactive sources are skipped"""
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)
    
    test_source = {
        "name": "Test Feed",
        "url": "https://www.reddit.com/r/travel/.rss",
        "category": "test",
        "quality_score": 8.5,
        "active": False
    }
    
    result = populator.populate_single_source(test_source)
    assert result['skipped'] == True
    assert result['reason'] == 'inactive'

def test_handles_invalid_feed():
    """Test handling of invalid feed URL"""
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)
    
    test_source = {
        "name": "Bad Feed",
        "url": "https://notarealwebsite.com/feed",
        "category": "test",
        "quality_score": 8.5,
        "active": True
    }
    
    result = populator.populate_single_source(test_source)
    assert result['success'] == False
    assert 'error' in result


def test_prevents_duplicate_articles():
    """Test that same articles aren't added twice"""
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    test_source = {
        "name": "Test Feed",
        "url": "https://www.reddit.com/r/travel/.rss",
        "category": "test",
        "quality_score": 8.5,
        "active": True
    }

    # Populate twice
    first_result = populator.populate_single_source(test_source)
    second_result = populator.populate_single_source(test_source)

    assert first_result['articles_added'] > 0
    assert second_result['articles_added'] == 0
    assert second_result['articles_existing'] > 0


def test_populate_from_multiple_sources():
    """Test populating from multiple sources"""
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    test_sources = [
        {
            "name": "Valid Feed",
            "url": "https://www.reddit.com/r/travel/.rss",
            "category": "test",
            "quality_score": 8.5,
            "active": True
        },
        {
            "name": "Another Valid Feed",
            "url": "https://www.reddit.com/r/backpacking/.rss",
            "category": "test",
            "quality_score": 7.5,
            "active": True
        }
    ]

    result = populator.populate_all_sources(test_sources)
    assert result['total_sources'] == 2
    assert result['successful'] == 2
    assert result['total_articles_added'] > 0


def test_handles_mixed_valid_and_invalid_sources():
    """Test processing both valid and invalid sources together"""
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    test_sources = [
        {
            "name": "Valid Feed",
            "url": "https://www.reddit.com/r/travel/.rss",
            "category": "test",
            "quality_score": 8.5,
            "active": True
        },
        {
            "name": "Invalid Feed",
            "url": "https://notarealwebsite.com/feed",
            "category": "test",
            "quality_score": 7.5,
            "active": True
        }
    ]

    result = populator.populate_all_sources(test_sources)
    assert result['successful'] == 1
    assert result['failed'] == 1


def test_respects_multiple_inactive_sources():
    """Test handling of multiple inactive sources"""
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    test_sources = [
        {
            "name": "Inactive Feed 1",
            "url": "https://www.reddit.com/r/travel/.rss",
            "active": False
        },
        {
            "name": "Inactive Feed 2",
            "url": "https://www.reddit.com/r/backpacking/.rss",
            "active": False
        }
    ]

    result = populator.populate_all_sources(test_sources)
    assert result['skipped'] == 2
    assert result['total_articles_added'] == 0


def test_prevent_duplicates_across_multiple_runs():
    """Test that running multiple times doesn't duplicate articles"""
    db = FetchDatabase(":memory:")
    populator = PopulateDB(db)

    test_sources = [
        {
            "name": "Valid Feed",
            "url": "https://www.reddit.com/r/travel/.rss",
            "active": True
        }
    ]

    first_run = populator.populate_all_sources(test_sources)
    second_run = populator.populate_all_sources(test_sources)

    assert first_run['total_articles_added'] > 0
    assert second_run['total_articles_added'] == 0
    assert second_run['total_articles_existing'] > 0
