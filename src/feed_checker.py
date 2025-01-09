import yaml
import feedparser
from typing import Dict, List

class FeedChecker:
    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config_path = config_path

    def load_sources(self) -> List[Dict]:
        """Load sources from yaml config file"""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        return config["sources"]

    def check_feed(self, url: str) -> Dict:
        """Check if a feed URL is valid and accessible"""
        try:
            feed = feedparser.parse(url)
            
            if feed.bozo:  # feedparser's flag for malformed feeds
                return {"is_valid": False, "error": "Invalid feed format"}
                
            if not feed.entries:
                return {"is_valid": False, "error": "No entries found"}
                
            return {
                "is_valid": True,
                "title": feed.feed.title if "title" in feed.feed else "Unknown",
                "entry_count": len(feed.entries)
            }
            
        except Exception as e:
            return {"is_valid": False, "error": str(e)}
