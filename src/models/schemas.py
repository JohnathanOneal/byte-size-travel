from datetime import datetime, date
from typing import List, Optional, Dict
from pydantic import BaseModel, field_validator

class DealData(BaseModel):
    type: Optional[str] = None
    price_tier: Optional[str] = None
    value_score: Optional[int] = None
    booking_deadline: Optional[date] = None
    travel_window: Optional[Dict[str, date]] = None
    origin: Optional[str] = None
    destination: Optional[str] = None

    @field_validator('*', mode='before')
    def validate_all_or_none(cls, v, values):
        # Get all values including the current field
        all_values = list(values.values()) + [v]
        
        # Filter out None values
        non_none_values = [x for x in all_values if x is not None]
        
        # Check if we have either all values or no values
        if len(non_none_values) not in [0, len(all_values)]:
            raise ValueError('Either all fields must be populated or all must be None')
        
        return v

class Locations(BaseModel):
    primary: str
    secondary: List[str]

class ProcessedArticle(BaseModel):
    id: Optional[int] = None
    fetched_article_id: int
    content_type: str
    deal_data: Optional[DealData] = None
    locations: Locations
    audience: List[str]
    key_themes: List[str]
    seasonality: List[str]
    processed_date: datetime
