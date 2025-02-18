# src/content/fetching/rss_full_fetch.py
import requests
from content.fetching.parsers import clean_html_content
from config.logging_config import fetch_logger as logger

class RssFullFetch:
    def __init__(self, db):
        self.db = db
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def fetch_pending_content(self, batch_size=10):
        batch_number = 0
        while articles := self.db.get_articles_without_content(batch_size):
            for article in articles:
                self._process_article(article)
            batch_number += 1
            logger.info(f"Processed batch {batch_number} of {batch_size} articles")

    def _process_article(self, article):
        try:
            content = self._fetch_url(article['url'])
            self.db.update_article_content(article['id'], content)
        except Exception as e:
            logger.error(f"Error fetching {article['url']}: {e}")

    def _fetch_url(self, url):
        response = requests.get(url, headers=self.headers, timeout=10)
        return clean_html_content(response.text)
