from datetime import datetime

from pydantic import BaseModel


class VenueOut(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None


class EventOut(BaseModel):
    id: int
    source_name: str
    source_url: str
    title: str
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    venue: VenueOut
    price_text: str | None = None
    is_free: bool | None = None
    categories: list[str]
    source_category: str | None = None
    image_url: str | None = None
    image_url_large: str | None = None


class EventPage(BaseModel):
    items: list[EventOut]
    total: int
    limit: int
    offset: int
