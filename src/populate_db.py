from dataclasses import dataclass
import feedparser
from datetime import datetime
import logging
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PopulateDB:
    def __init__(self, db):
        self.db = db

    def populate_single_source(self, source: Dict) -> Dict:
        """
        Populate database from a single source
        Returns dict with results of operation
        """
        if not source.get('active', True):
            return {
                'success': True,
                'skipped': True,
                'reason': 'inactive'
            }

        try:
            feed = feedparser.parse(source['url'])

            if hasattr(feed, 'bozo_exception'):
                return {
                    'success': False,
                    'error': str(feed.bozo_exception)
                }

            articles_added = 0
            articles_existing = 0

            for entry in feed.entries[:10]:
                article = {
                    "title": entry.title,
                    "url": entry.link,
                    "content": entry.get('description', ''),
                    "published_date": datetime(*entry.published_parsed[:6]),
                    "source_name": source['name'],
                    "source_url": source['url']
                }

                # Get existing article count before storing
                cursor = self.db.conn.execute("SELECT COUNT(*) FROM articles WHERE url = ?", (article["url"],))
                exists_count = cursor.fetchone()[0]

                article_id = self.db.store_article(article)

                if article_id and exists_count == 0:
                    articles_added += 1
                else:
                    articles_existing += 1

            return {
                'success': True,
                'articles_added': articles_added,
                'articles_existing': articles_existing
            }

        except Exception as e:
            logger.error(f"Error processing feed {source['name']}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def populate_all_sources(self, sources=None) -> Dict:
        """
        Process all sources and return summary stats
        Args:
            sources: Optional list of sources to process. If None, loads from config
        Returns:
            Dict with summary statistics
        """
        if sources is None:
            from feed_checker import FeedChecker
            checker = FeedChecker()
            sources = checker.load_sources()

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
            source_result = self.populate_single_source(source)

            if source_result.get('skipped'):
                results['skipped'] += 1
                continue

            if source_result['success']:
                results['successful'] += 1
                results['total_articles_added'] += source_result['articles_added']
                results['total_articles_existing'] += source_result.get('articles_existing', 0)
            else:
                results['failed'] += 1

        return results
