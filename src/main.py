import os
from database.populate_db import PopulateDB
from database.fetch_database import FetchDatabase
from database.processed_database import ProcessedDatabase
from content.fetching.rss_full_fetch import RssFullFetch
from pathlib import Path
from dotenv import load_dotenv

from content.enriching.article_enricher import ArticleEnricher
from content.selection.article_selector import ArticleSelector

from config.logging_config import app_logger as logger

def load_environment():
    """Load environment variables from .env file, checking for required feilds"""
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
    
    required_vars = ['DATABASE_PATH', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please create a .env file with these variables or set them in your environment."
        )


def main():
    # Load environment variables
    load_environment()

    # # populate db with content from our sources
    # fetch_db = FetchDatabase("main")
    # populator = PopulateDB(fetch_db)
    # populator.populate_all_sources()

    # # fetch full rss content
    # fetcher = RssFullFetch(fetch_db)
    # fetcher.fetch_pending_content()
    # fetch_db.conn.close()
    
    # process data adding enriched metadata
    processed_db = ProcessedDatabase("main")
    enricher = ArticleEnricher(
        processed_db=processed_db,
        openai_model=os.getenv('OPENAI_MODEL')
    )
    processed_count = enricher.process_pending_articles()
    logger.info(f"Processed {processed_count} new articles")
    
    # Select newsletter content using enriched metadata
    # selector = ArticleSelector(processed_db)
    # try:
    #     newsletter_content = selector.select_newsletter_content()
    #     print("Newsletter content selected successfully")
    # except ValueError as e:
    #     print(f"Error selecting newsletter content: {str(e)}")
    
    # Clean up
    processed_db.conn.close()

if __name__ == "__main__":
    main()
