from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: datetime
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_info: Optional[str] = None
    is_free: Optional[bool] = False
    source_url: str
    category_id: Optional[int] = None