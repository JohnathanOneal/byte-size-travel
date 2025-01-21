import feedparser
from datetime import datetime
import logging
from typing import Dict
from source_manager import SourceManager
import requests
from parsers import email_feed_parser_gmail, rss_feed_parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PopulateDB:
    def __init__(self, db):
        self.db = db

    # Helper Functions
    def check_feed(self, url: str) -> Dict:
        """Check if a feed URL is valid and accessible"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse the feed using feedparser
            feed = feedparser.parse(response.content)

            # feedparser's flag for malformed feeds
            if feed.bozo:
                return {"is_valid": False, "error": "Invalid feed format"}

            if not feed.entries:
                return {"is_valid": False, "error": "No entries found"}

            return {
                "is_valid": True,
                "title": feed.feed.title if "title" in feed.feed else "Unknown",
                "entry_count": len(feed.entries)
            }

        except requests.exceptions.Timeout:
            return {"is_valid": False, "error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            return {"is_valid": False, "error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"is_valid": False, "error": f"Unexpected error: {str(e)}"}

    # Populate Functions
    def populate_single_source(self, source: Dict) -> Dict:
        """Populate database from a single source."""
        try:
            if source["type"] == "email":
                entries = email_feed_parser_gmail(source)
            elif source["type"] == "rss":
                entries = rss_feed_parser(source)
            else:
                raise ValueError(f"Unsupported source type: {source['type']}")

            articles_added = 0
            articles_existing = 0

            for entry in entries:
                article = {
                    "title": entry["title"],
                    "url": entry["url"],
                    "content": entry["content"],
                    "published_date": entry["published_date"],
                    "source_name": source["name"],
                    "source_url": entry.get("source_url", ""),
                    "is_full_content_fetched": entry.get("is_full_content_fetched", None),
                }

                cursor = self.db.conn.execute("SELECT COUNT(*) FROM articles WHERE url = ?", (article["url"],))
                exists_count = cursor.fetchone()[0]

                article_id = self.db.store_article(article)

                if article_id and exists_count == 0:
                    articles_added += 1
                else:
                    articles_existing += 1

            return {
                "success": True,
                "articles_added": articles_added,
                "articles_existing": articles_existing,
            }

        except Exception as e:
            logger.error(f"Error processing source {source['name']}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def populate_all_sources(self, sources=None) -> Dict:
        """
        Process all sources and return summary stats
        Args:
            sources: Optional list of sources to process. If None, loads from config
        Returns:
            Dict with summary statistics
        """
        source_manager = SourceManager()
        loading_from_config = sources is None
        if loading_from_config:
            sources = source_manager.load_sources()

        results = {
            'total_sources': len(sources),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'total_articles_added': 0,
            'total_articles_existing': 0
        }

        logger.info(f"Starting population of {len(sources)} sources")

        for source in sources:
            # First check if source is active
            if not source.get('active', True):
                results['skipped'] += 1
                continue

            # If source is active check if it is a valid feed, if not update source metadata to deactivate it
            check_result = self.check_feed(source["url"])
            if not check_result.get('is_valid'):
                logger.error(f"Skipping invalid source {source['name']}: {check_result['error']}")
                source['active'] = False
                source['last_checked'] = datetime.now().isoformat()
                source['error'] = check_result['error']
                results['failed'] += 1
                continue

            # If source is active and feed is valid, process the source
            source_result = self.populate_single_source(source)
            if source_result['success']:
                source['last_checked'] = datetime.now().isoformat()
                results['successful'] += 1
                results['total_articles_added'] += source_result['articles_added']
                results['total_articles_existing'] += source_result.get('articles_existing', 0)
                logger.info(f"Processed {source['name']}: {source_result['articles_added']} new articles")
            else:
                results['failed'] += 1
                logger.error(f"Failed to process {source['name']}: {source_result['error']}")

        # Save source metadata back to config file if loaded from config
        if loading_from_config:
            source_manager.save_sources(sources)

        return results
