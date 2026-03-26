from datetime import UTC, datetime

from config.logging_config import fetch_logger as logger
from config.source_manager import SourceManager
from content.fetching.parsers import (
    check_email_feed,
    check_rss_feed,
    email_feed_parser_gmail,
    rss_feed_parser,
)
from database.fetch_database import FetchDatabase

FEED_PARSERS = {
    "rss": rss_feed_parser,
    "email": email_feed_parser_gmail,
}

FEED_CHECKERS = {
    "rss": check_rss_feed,
    "email": check_email_feed,
}


class PopulateDB:
    def __init__(self, db: FetchDatabase) -> None:
        self.db = db
        self.source_manager = SourceManager()

    def populate_single_source(self, source: dict) -> dict:
        logger.info(
            "Starting to process source: %s (%s)",
            source["name"],
            source["type"],
        )
        start_time = datetime.now(tz=UTC)

        parser = FEED_PARSERS.get(source["type"])
        if parser is None:
            msg = f"Unsupported source type: {source['type']}"
            raise ValueError(msg)

        try:
            entries = parser(source)
        except (ValueError, OSError):
            elapsed = (datetime.now(tz=UTC) - start_time).total_seconds()
            logger.exception("Error processing source %s", source["name"])
            return {
                "success": False,
                "error": "Feed parsing failed",
                "processing_time": elapsed,
            }

        logger.debug(
            "Retrieved %d entries from %s source %s",
            len(entries),
            source["type"],
            source["name"],
        )

        articles_added = 0
        articles_existing = 0

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
                (article["url"],),
            )
            exists_count = cursor.fetchone()[0]

            article_id = self.db.store_article(article)
            if article_id and exists_count == 0:
                articles_added += 1
                logger.debug(
                    "Added new article: %s...",
                    article["title"][:50],
                )
            else:
                articles_existing += 1

        elapsed = (datetime.now(tz=UTC) - start_time).total_seconds()
        logger.info(
            "Completed processing %s: Added %d new, %d existing (took %.2fs)",
            source["name"],
            articles_added,
            articles_existing,
            elapsed,
        )

        return {
            "success": True,
            "articles_added": articles_added,
            "articles_existing": articles_existing,
            "processing_time": elapsed,
        }

    def populate_all_sources(self, sources: list[dict] | None = None) -> dict:
        start_time = datetime.now(tz=UTC)

        if sources is None:
            sources = self.source_manager.load_sources()
            logger.info("Loaded %d sources from config", len(sources))

        results = {
            "total_sources": len(sources),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_articles_added": 0,
            "total_articles_existing": 0,
            "total_processing_time": 0.0,
        }

        logger.info("Starting population of %d sources", len(sources))

        for idx, source in enumerate(sources, 1):
            logger.info(
                "Processing source %d/%d: %s",
                idx,
                len(sources),
                source["name"],
            )

            if not source.get("active", True):
                logger.info(
                    "Skipping inactive source: %s",
                    source["name"],
                )
                results["skipped"] += 1
                continue

            if not self._validate_source(source, results):
                continue

            source_result = self.populate_single_source(source)
            self._update_source_after_populate(source, source_result)
            self._accumulate_results(results, source_result)

        elapsed = (datetime.now(tz=UTC) - start_time).total_seconds()
        logger.info(
            "Completed processing all sources in %.2fs: "
            "%d successful, %d failed, %d skipped, "
            "%d new articles",
            elapsed,
            results["successful"],
            results["failed"],
            results["skipped"],
            results["total_articles_added"],
        )

        return results

    def _validate_source(self, source: dict, results: dict) -> bool:
        checker = FEED_CHECKERS.get(source["type"])
        if checker is None:
            msg = f"Unsupported source type: {source['type']}"
            raise ValueError(msg)

        try:
            check_result = checker(source)
        except (ValueError, OSError):
            logger.exception("Error checking source %s", source["name"])
            results["failed"] += 1
            return False

        if not check_result.get("is_valid"):
            logger.error(
                "Invalid source %s: %s",
                source["name"],
                check_result["error"],
            )
            self.source_manager.update_source(
                source["name"],
                {
                    "active": False,
                    "last_checked": datetime.now(tz=UTC).isoformat(),
                    "error": check_result["error"],
                },
            )
            results["failed"] += 1
            return False

        return True

    def _update_source_after_populate(self, source: dict, result: dict) -> None:
        self.source_manager.update_source(
            source["name"],
            {
                "last_checked": datetime.now(tz=UTC).isoformat(),
                "error": result.get("error") if not result["success"] else None,
            },
        )

    @staticmethod
    def _accumulate_results(results: dict, source_result: dict) -> None:
        if source_result["success"]:
            results["successful"] += 1
            results["total_articles_added"] += source_result["articles_added"]
            results["total_articles_existing"] += source_result.get(
                "articles_existing", 0
            )
            results["total_processing_time"] += source_result["processing_time"]
        else:
            results["failed"] += 1
