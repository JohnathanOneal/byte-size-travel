from datetime import datetime, date
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, field_validator, model_validator, Field

class TravelWindow(BaseModel):
    # Accept either date or string (including empty string)
    start: Union[date, str] = ''
    end: Union[date, str] = ''

class DealData(BaseModel):
    type: Union[str, List[str]] = Field(default_factory=list)
    price_tier: Union[str, List[str]] = Field(default_factory=list)
    value_score: Optional[int] = None
    booking_deadline: Union[date, str] = ''
    travel_window: Optional[TravelWindow] = None
    origin: Union[str, List[str]] = ''
    destination: Union[str, List[str]] = ''
    
    # Validators to normalize data
    @field_validator('type', 'price_tier', mode='before')
    @classmethod
    def normalize_list_fields(cls, value):
        # Convert string to a single-item list
        if isinstance(value, str) and value:
            return [value]
        # Ensure we return an empty list for None values
        elif value is None:
            return []
        return value
    
    @field_validator('origin', 'destination', mode='before')
    @classmethod
    def normalize_string_fields(cls, value):
        # Handle list with a single value by converting to string
        if isinstance(value, list) and len(value) == 1:
            return value[0]
        return value
    
    @field_validator('price_tier', 'type', mode='before')
    @classmethod
    def ensure_list(cls, value):
        # Ensure these are always lists
        if value is None:
            return []
        return value

class Locations(BaseModel):
    primary: str
    secondary: List[str]

class ProcessedArticle(BaseModel):
    id: Optional[int] = None
    fetched_article_id: int
    content_type: List[str]
    deal_data: Optional[DealData] = None
    locations: Locations
    audience: List[str]
    key_themes: List[str]
    seasonality: List[str]
    processed_date: datetime
