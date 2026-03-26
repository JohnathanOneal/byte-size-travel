import os
from pathlib import Path

from dotenv import load_dotenv

from config.logging_config import app_logger as logger
from content.enriching.article_enricher import ArticleEnricher
from content.fetching.rss_full_fetch import RssFullFetch
from content.selection.article_selector import ArticleSelector
from content.writing.newsletter_writer import NewsletterWriter
from database.fetch_database import FetchDatabase
from database.populate_db import PopulateDB
from database.processed_database import ProcessedDatabase
from services.amazon_ses.amazon_ses_client import AmazonSesClient


def load_environment() -> None:
    """Load environment variables from .env file, checking for required feilds"""
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)

    required_vars = ["DATABASE_PATH", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        msg = (
            "Missing required environment variables: "
            f"{', '.join(missing_vars)}. "
            "Create a .env file with these variables."
        )
        raise ValueError(msg)


def main() -> None:
    # Load environment variables
    load_environment()

    # populate db with content from our sources
    fetch_db = FetchDatabase("main")
    populator = PopulateDB(fetch_db)
    populator.populate_all_sources()

    # fetch full rss content
    fetcher = RssFullFetch(fetch_db)
    fetcher.fetch_pending_content()
    fetch_db.conn.close()

    # process data adding enriched metadata
    processed_db = ProcessedDatabase("main")
    enricher = ArticleEnricher(processed_db=processed_db)
    processed_count = enricher.process_pending_articles()
    logger.info(f"Processed {processed_count} new articles")

    # Select newsletter content using enriched metadata
    processed_db = ProcessedDatabase("main")
    selector = ArticleSelector(processed_db)
    newsletter_content = selector.select_newsletter_content()

    # Generate the newsletter
    newsletter_writer = NewsletterWriter(processed_db)
    json_data = newsletter_writer.generate_newsletter(newsletter_content, mode="real")

    # Clean up
    processed_db.conn.close()

    ses_client = AmazonSesClient()
    ses_client.update_html_template(
        os.getenv("SES_NEWSLETTER_EDITION_ONE"), os.getenv("EMAIL_TEMPLATE_ONE_FILE")
    )
    ses_client.send_templated_email(
        os.getenv("SES_CONTACT_LIST_NAME"),
        os.getenv("SES_NEWSLETTER_EDITION_ONE"),
        json_data,
    )


if __name__ == "__main__":
    main()
