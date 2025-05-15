#campground.py
"""
Pydantic models for data validation
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from pydantic import BaseModel, Field, validator, HttpUrl


class Campground(BaseModel):
    """
    Pydantic model for campground data validation
    """
    id: str
    type: str
    links: Dict[str, str] = Field(default_factory=dict)
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    region_name: Optional[str] = None
    administrative_area: Optional[str] = None
    nearest_city_name: Optional[str] = None
    accommodation_type_names: List[str] = Field(default_factory=list)
    bookable: bool = False
    camper_types: List[str] = Field(default_factory=list)
    operator: Optional[str] = None
    photo_url: Optional[Union[HttpUrl, str]] = None
    photo_urls: List[Union[HttpUrl, str]] = Field(default_factory=list)
    photos_count: int = 0
    rating: Optional[float] = None
    reviews_count: int = 0
    slug: Optional[str] = None
    price_low: Optional[float] = None
    price_high: Optional[float] = None
    availability_updated_at: Optional[datetime] = None
    address: Optional[str] = None  # Bonus field from geocoding
    
    class Config:
        arbitrary_types_allowed = True
        
    @validator('links', pre=True)
    def validate_links(cls, v):
        """Ensure links is a dictionary"""
        if not isinstance(v, dict):
            return {'self': str(v) if v else ''}
        return v
        
    @validator('photo_url', 'photo_urls', pre=True)
    def validate_urls(cls, v):
        """Handle URL validation"""
        if v is None:
            return v
        # For single URL
        if not isinstance(v, list):
            return str(v)
        # For list of URLs
        return [str(url) for url in v]