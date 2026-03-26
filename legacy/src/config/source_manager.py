# src/source_manager.py
import json
import os
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Literal

import yaml
from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from config.logging_config import fetch_logger as logger

VALID_CATEGORIES = ["budget", "luxury", "travel_tips"]


class BaseSource(BaseModel):
    """Base model for all sources"""

    name: str
    active: bool = True
    quality_score: int = Field(ge=1, le=10)
    category: str
    last_checked: datetime | None = None
    error: str | None = None
    type: str

    class Config:
        json_encoders: ClassVar[dict] = {
            HttpUrl: str,
            EmailStr: str,
            datetime: lambda v: v.isoformat() if v else None,
        }

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in VALID_CATEGORIES:
            msg = (
                f"Invalid category: {value}. "
                f"Must be one of: {', '.join(VALID_CATEGORIES)}"
            )
            raise ValueError(msg)
        return value


class RSSSource(BaseSource):
    """RSS feed source"""

    type: Literal["rss"]
    url: HttpUrl


class EmailSource(BaseSource):
    """Email feed source"""

    type: Literal["email"]
    url: EmailStr
    password: str
    provider: str

    @field_validator("provider", "password", mode="before")
    @classmethod
    def validate_env_var(cls, value: str) -> str:
        if not os.getenv(value):
            msg = f"Environment variable {value} not found"
            raise ValueError(msg)
        return value


class SourceConfig(BaseModel):
    """Root config model"""

    sources: list[RSSSource | EmailSource]

    class Config:
        json_encoders: ClassVar[dict] = {
            HttpUrl: str,
            EmailStr: str,
            datetime: lambda v: v.isoformat() if v else None,
        }

    @field_validator("sources", mode="before")
    @classmethod
    def validate_sources(
        cls,
        v: list[dict],
    ) -> list[RSSSource | EmailSource]:
        validated = []
        for source in v:
            if source["type"] == "rss":
                validated.append(RSSSource(**source))
            elif source["type"] == "email":
                validated.append(EmailSource(**source))
            else:
                msg = f"Unknown source type: {source['type']}"
                raise ValueError(msg)
        return validated


class SourceManager:
    def __init__(self, config_path: str | None = None) -> None:
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config/sources.yaml"

        self.config_path = Path(config_path).resolve()
        self._KEY_ORDER = [
            "name",
            "active",
            "quality_score",
            "category",
            "url",
            "last_checked",
            "error",
            "type",
        ]
        logger.info(f"Initialized SourceManager with config: {self.config_path}")

    def load_sources(self) -> list[dict]:
        """Load and validate sources from yaml config file"""
        try:
            if not self.config_path.exists():
                return []

            with self.config_path.open() as f:
                raw_config = yaml.safe_load(f)

            config = SourceConfig(**raw_config)
            return [
                json.loads(source.model_dump_json(exclude_none=True))
                for source in config.sources
            ]

        except (yaml.YAMLError, ValueError, OSError) as e:
            logger.error(f"Error loading sources: {e!s}")
            raise

    def _order_source_dict(self, source_dict: dict) -> dict:
        """Helper to maintain consistent key ordering"""
        ordered = {k: source_dict[k] for k in self._KEY_ORDER if k in source_dict}
        ordered.update(
            {k: v for k, v in source_dict.items() if k not in self._KEY_ORDER}
        )
        return ordered

    def save_sources(self, sources: list[dict]) -> None:
        """Save sources with minimal file operations"""
        temp_path = self.config_path.with_suffix(".yaml.tmp")
        try:
            config = SourceConfig(sources=sources)

            ordered_sources = [
                self._order_source_dict(
                    json.loads(source.model_dump_json(exclude_none=True))
                )
                for source in config.sources
            ]

            with temp_path.open("w") as f:
                yaml.safe_dump({"sources": ordered_sources}, f, sort_keys=False)

            temp_path.replace(self.config_path)
            logger.info(f"Successfully saved {len(sources)} sources")

        except (yaml.YAMLError, ValueError, OSError) as e:
            if temp_path.exists():
                temp_path.unlink()
            logger.error(f"Error saving sources: {e!s}")
            raise

    def add_source(self, source_data: dict) -> None:
        """Add a new source with validation"""
        source_cls = {"rss": RSSSource, "email": EmailSource}.get(source_data["type"])

        if not source_cls:
            msg = f"Unknown source type: {source_data['type']}"
            raise ValueError(msg)

        validated_source = source_cls(**source_data)

        sources = self.load_sources()
        sources.append(json.loads(validated_source.model_dump_json(exclude_none=True)))
        self.save_sources(sources)

        logger.info(f"Successfully added new source: {source_data['name']}")

    def update_source(self, name: str, updates: dict) -> None:
        """Update an existing source with validation"""
        sources = self.load_sources()

        for i, source in enumerate(sources):
            if source["name"] == name:
                updated_data = {**source, **updates}

                source_cls = {"rss": RSSSource, "email": EmailSource}.get(
                    updated_data["type"]
                )

                if not source_cls:
                    msg = f"Unknown source type: {updated_data['type']}"
                    raise ValueError(msg)

                validated = source_cls(**updated_data)
                sources[i] = json.loads(validated.model_dump_json(exclude_none=True))

                self.save_sources(sources)
                logger.info(f"Successfully updated source: {name}")
                return

        msg = f"Source not found: {name}"
        raise ValueError(msg)
