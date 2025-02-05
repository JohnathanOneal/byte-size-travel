# src/source_manager.py
from pathlib import Path
from typing import List, Dict, Optional, Literal, Union
import yaml
import json
from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_validator
from datetime import datetime
import os
from config.logging_config import fetch_logger as logger

VALID_CATEGORIES = ["budget", "luxury", "travel_tips"]


class BaseSource(BaseModel):
    """Base model for all sources"""
    name: str
    active: bool = True
    quality_score: int = Field(ge=1, le=10)
    category: str
    last_checked: Optional[datetime] = None
    error: Optional[str] = None
    type: str

    # Add serialization config
    class Config:
        json_encoders = {
            HttpUrl: str,
            EmailStr: str,
            datetime: lambda v: v.isoformat() if v else None
        }

    @field_validator('category', mode='before')
    def validate_category(cls, value: str) -> str:
        value = value.lower().strip()  # Normalize input
        if value not in VALID_CATEGORIES:
            raise ValueError(f'Invalid category: {value}. Must be one of: {", ".join(VALID_CATEGORIES)}')
        return value


class RSSSource(BaseSource):
    """RSS feed source"""
    type: Literal['rss']
    url: HttpUrl


class EmailSource(BaseSource):
    """Email feed source"""
    type: Literal['email']
    url: EmailStr
    password: str
    provider: str

    @field_validator('provider', 'password', mode='before')
    def validate_env_var(cls, value: str) -> str:
        if not os.getenv(value):
            raise ValueError(f'Environment variable {value} not found')
        return value


class SourceConfig(BaseModel):
    """Root config model"""
    sources: List[Union[RSSSource, EmailSource]]

    class Config:
        json_encoders = {
            HttpUrl: str,
            EmailStr: str,
            datetime: lambda v: v.isoformat() if v else None
        }

    @field_validator('sources', mode='before')
    def validate_sources(cls, v):
        validated = []
        for source in v:
            if source['type'] == 'rss':
                validated.append(RSSSource(**source))
            elif source['type'] == 'email':
                validated.append(EmailSource(**source))
            else:
                raise ValueError(f"Unknown source type: {source['type']}")
        return validated


class SourceManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config/sources.yaml"

        self.config_path = Path(config_path).resolve()
        self._KEY_ORDER = [
            "name", "active", "quality_score", "category",
            "url", "last_checked", "error", "type"
        ]
        logger.info(f"Initialized SourceManager with config: {self.config_path}")

    def load_sources(self) -> List[Dict]:
        """Load and validate sources from yaml config file"""
        try:
            if not self.config_path.exists():
                return []

            with open(self.config_path, "r") as f:
                raw_config = yaml.safe_load(f)

            config = SourceConfig(**raw_config)
            # Use model_dump_json and parse back to handle custom encoders
            return [
                json.loads(source.model_dump_json(exclude_none=True))
                for source in config.sources
            ]

        except Exception as e:
            logger.error(f"Error loading sources: {str(e)}")
            raise

    def _order_source_dict(self, source_dict: Dict) -> Dict:
        """Helper to maintain consistent key ordering in source dictionaries"""
        ordered = {k: source_dict[k] for k in self._KEY_ORDER if k in source_dict}
        # Add any remaining keys not in _KEY_ORDER
        ordered.update({k: v for k, v in source_dict.items() if k not in self._KEY_ORDER})
        return ordered

    def save_sources(self, sources: List[Dict]) -> None:
        """Save sources with minimal file operations"""
        try:
            # Validate sources through Pydantic models
            config = SourceConfig(sources=sources)

            # Properly serialize using model_dump_json to handle custom encoders
            ordered_sources = [
                self._order_source_dict(
                    json.loads(source.model_dump_json(exclude_none=True))
                )
                for source in config.sources
            ]

            # Use atomic write operation
            temp_path = self.config_path.with_suffix('.yaml.tmp')
            with open(temp_path, "w") as f:
                yaml.safe_dump({"sources": ordered_sources}, f, sort_keys=False)

            temp_path.replace(self.config_path)  # Atomic operation
            logger.info(f"Successfully saved {len(sources)} sources")

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            logger.error(f"Error saving sources: {str(e)}")
            raise

    def add_source(self, source_data: Dict) -> None:
        """Add a new source with validation"""
        try:
            # Validate new source
            source_cls = {
                'rss': RSSSource,
                'email': EmailSource
            }.get(source_data['type'])

            if not source_cls:
                raise ValueError(f"Unknown source type: {source_data['type']}")

            validated_source = source_cls(**source_data)

            # Append to existing sources
            sources = self.load_sources()
            sources.append(
                json.loads(validated_source.model_dump_json(exclude_none=True))
            )
            self.save_sources(sources)

            logger.info(f"Successfully added new source: {source_data['name']}")

        except Exception as e:
            logger.error(f"Error adding source: {str(e)}")
            raise

    def update_source(self, name: str, updates: Dict) -> None:
        """Update an existing source with validation"""
        try:
            sources = self.load_sources()

            for i, source in enumerate(sources):
                if source['name'] == name:
                    # Merge updates
                    updated_data = {**source, **updates}

                    # Validate using appropriate source type
                    source_cls = {
                        'rss': RSSSource,
                        'email': EmailSource
                    }.get(updated_data['type'])

                    if not source_cls:
                        raise ValueError(f"Unknown source type: {updated_data['type']}")

                    validated = source_cls(**updated_data)
                    sources[i] = json.loads(validated.model_dump_json(exclude_none=True))

                    self.save_sources(sources)
                    logger.info(f"Successfully updated source: {name}")
                    return

            raise ValueError(f"Source not found: {name}")

        except Exception as e:
            logger.error(f"Error updating source: {str(e)}")
            raise
