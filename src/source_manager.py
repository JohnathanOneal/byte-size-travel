import yaml
from typing import Dict, List
from pathlib import Path


class SourceManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config/sources.yaml"
        
        self.config_path = Path(config_path).resolve()
        self._KEY_ORDER = ["name", "active", "quality_score", "category", "url", "last_checked", "error"]

    def load_sources(self) -> List[Dict]:
        """Load sources from yaml config file"""
        with open(self.config_path,  "r") as f:
            config = yaml.safe_load(f)
        return config["sources"]

    def save_sources(self, sources: List[Dict]) -> None:
        """Save the updated sources back to the YAML config file."""
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        # For consistency, we want to enforce an easily readable order for our sources config
        ordered_sources = [
            {key: source.get(key) for key in self._KEY_ORDER if key in source} for source in sources
        ]
        config["sources"] = ordered_sources

        with open(self.config_path, "w") as f:
            yaml.safe_dump(config, f, sort_keys=False)
