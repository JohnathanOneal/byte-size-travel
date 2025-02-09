import feedparser
from datetime import datetime
from config.logging_config import fetch_logger as logger
from typing import Dict, List, Optional
from src.source_manager import SourceManager, RSSSource, EmailSource
import requests
from src.parsers import email_feed_parser_gmail, rss_feed_parser, check_rss_feed, check_email_feed


class PopulateDB:
    def __init__(self, db):
        self.db = db
        self.source_manager = SourceManager()

    def populate_single_source(self, source: Dict) -> Dict:
        """Populate database from a single source."""
        logger.info(f"Starting to process source: {source['name']} ({source['type']})")
        start_time = datetime.now()

        try:
            # Get entries based on source type
            if source["type"] == "email":
                entries = email_feed_parser_gmail(source)
                logger.debug(f"Retrieved {len(entries)} entries from email source {source['name']}")
            elif source["type"] == "rss":
                entries = rss_feed_parser(source)
                logger.debug(f"Retrieved {len(entries)} entries from RSS source {source['name']}")
            else:
                raise ValueError(f"Unsupported source type: {source['type']}")

            articles_added = 0
            articles_existing = 0

            # Process entries
            for entry in entries:
                article = {
                    "title": entry["title"],
                    "url": entry["url"],
                    "content": entry["content"],
                    "published_date": entry["published_date"],
                    "source_name": source["name"],
                    "source_url": source["url"],
                    "is_full_content_fetched": entry.get("is_full_content_fetched", False),
                }

                cursor = self.db.conn.execute(
                    "SELECT COUNT(*) FROM articles WHERE url = ?",
                    (article["url"],)
                )
                exists_count = cursor.fetchone()[0]

                article_id = self.db.store_article(article)
                if article_id and exists_count == 0:
                    articles_added += 1
                    logger.debug(f"Added new article: {article['title'][:50]}...")
                else:
                    articles_existing += 1

            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Completed processing {source['name']}: "
                f"Added {articles_added} new, {articles_existing} existing "
                f"(took {processing_time:.2f}s)"
            )

            return {
                "success": True,
                "articles_added": articles_added,
                "articles_existing": articles_existing,
                "processing_time": processing_time
            }

        except Exception as e:
            logger.error(
                f"Error processing source {source['name']}: {str(e)}",
                exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

    def populate_all_sources(self, sources: Optional[List[Dict]] = None) -> Dict:
        """Process all sources and return summary stats."""
        start_time = datetime.now()
        loading_from_config = sources is None

        if loading_from_config:
            # Use the new source manager to load and validate sources
            sources = self.source_manager.load_sources()
            logger.info(f"Loaded {len(sources)} sources from config")

        results = {
            'total_sources': len(sources),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'total_articles_added': 0,
            'total_articles_existing': 0,
            'total_processing_time': 0
        }

        logger.info(f"Starting population of {len(sources)} sources")

        for idx, source in enumerate(sources, 1):
            logger.info(f"Processing source {idx}/{len(sources)}: {source['name']}")

            if not source.get('active', True):
                logger.info(f"Skipping inactive source: {source['name']}")
                results['skipped'] += 1
                continue

            try:
                # Validate feed
                if source["type"] == "rss":
                    check_result = check_rss_feed(source)
                elif source["type"] == "email":
                    check_result = check_email_feed(source)
                else:
                    raise ValueError(f"Unsupported source type: {source['type']}")

                if not check_result.get('is_valid'):
                    logger.error(f"Invalid source {source['name']}: {check_result['error']}")
                    # Update source using source manager
                    self.source_manager.update_source(source['name'], {
                        'active': False,
                        'last_checked': datetime.now().isoformat(),
                        'error': check_result['error']
                    })
                    results['failed'] += 1
                    continue

            except Exception as e:
                logger.error(f"Error checking source {source['name']}: {str(e)}")
                results['failed'] += 1
                continue

            # Process valid source
            source_result = self.populate_single_source(source)

            # Update source using source manager
            self.source_manager.update_source(source['name'], {
                'last_checked': datetime.now().isoformat(),
                'error': source_result.get('error') if not source_result['success'] else None
            })

            if source_result['success']:
                results['successful'] += 1
                results['total_articles_added'] += source_result['articles_added']
                results['total_articles_existing'] += source_result.get('articles_existing', 0)
                results['total_processing_time'] += source_result['processing_time']
            else:
                results['failed'] += 1

        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Completed processing all sources in {total_time:.2f}s: "
            f"{results['successful']} successful, "
            f"{results['failed']} failed, "
            f"{results['skipped']} skipped, "
            f"{results['total_articles_added']} new articles"
        )

        return results
