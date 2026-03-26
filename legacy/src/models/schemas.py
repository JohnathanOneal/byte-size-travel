from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class TravelWindow(BaseModel):
    # Accept either date or string (including empty string)
    start: date | str = ""
    end: date | str = ""


class DealData(BaseModel):
    type: str | list[str] = Field(default_factory=list)
    price_tier: str | list[str] = Field(default_factory=list)
    value_score: int | None = None
    booking_deadline: date | str = ""
    travel_window: TravelWindow | None = None
    origin: str | list[str] = ""
    destination: str | list[str] = ""

    # Validators to normalize data
    @field_validator("type", "price_tier", mode="before")
    @classmethod
    def normalize_list_fields(cls, value: str | list[str] | None) -> list[str]:
        # convert string to a single-item list
        if isinstance(value, str) and value:
            return [value]
        # ensure we return an empty list for None values
        if value is None:
            return []
        return value

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def normalize_string_fields(cls, value: str | list[str]) -> str | list[str]:
        # handle list with a single value by converting to string
        if isinstance(value, list) and len(value) == 1:
            return value[0]
        return value

    @field_validator("price_tier", "type", mode="before")
    @classmethod
    def ensure_list(cls, value: list[str] | None) -> list[str]:
        # ensure these are always lists
        if value is None:
            return []
        return value


class Locations(BaseModel):
    primary: str
    secondary: list[str]


class ProcessedArticle(BaseModel):
    id: int | None = None
    fetched_article_id: int
    content_type: list[str]
    deal_data: DealData | None = None
    locations: Locations
    audience: list[str]
    key_themes: list[str]
    seasonality: list[str]
    processed_date: datetime
