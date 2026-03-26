import requests

from config.logging_config import fetch_logger as logger
from content.fetching.parsers import clean_html_content
from database.fetch_database import FetchDatabase


class RssFullFetch:
    def __init__(self, db: FetchDatabase) -> None:
        self.db = db
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def fetch_pending_content(self, *, batch_size: int = 10) -> None:
        batch_number = 0
        while articles := self.db.get_articles_without_content(batch_size):
            for article in articles:
                self._process_article(article)
            batch_number += 1
            logger.info(
                "Processed batch %d of %d articles",
                batch_number,
                batch_size,
            )

    def _process_article(self, article: dict) -> None:
        try:
            content = self._fetch_url(article["url"])
            self.db.update_article_content(article["id"], content)
        except requests.RequestException:
            logger.exception("Error fetching %s", article["url"])

    def _fetch_url(self, url: str) -> str:
        response = requests.get(url, headers=self.headers, timeout=10)
        return clean_html_content(response.text)
