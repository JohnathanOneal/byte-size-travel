from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class DailyDropCategory(StrEnum):
    credit_card_news = "credit_card_news"
    points_strategy = "points_strategy"
    travel_guide = "travel_guide"
    deal_alert = "deal_alert"
    travel_tip = "travel_tip"
    comparison = "comparison"


class ArticleEnrichment(BaseModel):
    """Structured output model for OpenAI article enrichment."""

    daily_drop_category: DailyDropCategory = Field(
        description=("The Daily Drop content category this article best fits into"),
    )
    summary: str = Field(
        description=(
            "A 2-3 sentence summary of the article written"
            " for a Daily Drop editor scanning their dashboard"
        ),
    )
    headline_angle: str = Field(
        description=(
            "A suggested Daily Drop headline angle for this"
            " story, written in their conversational style"
        ),
    )
    urgency: Literal["breaking", "timely", "evergreen"] = Field(
        description=(
            "breaking: news that must be covered today."
            " timely: relevant now but not urgent."
            " evergreen: reference material with no expiry."
        ),
    )
    locations: list[str] = Field(
        default_factory=list,
        description=("Countries and cities mentioned in the article"),
    )
    programs_mentioned: list[str] = Field(
        default_factory=list,
        description=(
            "Loyalty programs, airlines, and hotel chains"
            " mentioned (e.g. Delta SkyMiles, Hyatt,"
            " United MileagePlus)"
        ),
    )
    cards_mentioned: list[str] = Field(
        default_factory=list,
        description=(
            "Credit cards mentioned (e.g. Chase Sapphire"
            " Reserve, Capital One Venture X)"
        ),
    )
    key_facts: list[str] = Field(
        description=(
            "3-5 bullet points of the most important facts"
            " a Daily Drop writer would need"
        ),
    )
    relevance_score: int = Field(
        ge=1,
        le=10,
        description=(
            "How relevant this article is to Daily Drop readers on a 1-10 scale"
        ),
    )
    why_relevant: str = Field(
        description=(
            "One sentence explaining why Daily Drop readers would care about this story"
        ),
    )
