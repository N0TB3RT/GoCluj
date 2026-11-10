from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class VenueIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str | None, Field(max_length=255)] = None
    address: Annotated[str | None, Field(max_length=255)] = None
    city: Annotated[str | None, Field(max_length=100)] = None
    lat: float | None = None
    lng: float | None = None


class EventIngest(BaseModel):
    """One scraped event. Mirrors the scraper's `Event` model field for field."""

    model_config = ConfigDict(extra="forbid")

    source_name: Annotated[str, Field(min_length=1, max_length=100)]
    source_url: Annotated[str, Field(min_length=1, max_length=1000)]
    external_id: Annotated[str, Field(min_length=1, max_length=255)]
    title: Annotated[str, Field(min_length=1, max_length=500)]
    description: str | None = None
    start_at: AwareDatetime
    end_at: AwareDatetime | None = None
    venue: VenueIngest = Field(default_factory=VenueIngest)
    price_text: Annotated[str | None, Field(max_length=200)] = None
    is_free: bool | None = None
    categories: list[str] = Field(default_factory=list)
    source_category: Annotated[str | None, Field(max_length=100)] = None
    image_url: Annotated[str | None, Field(max_length=1000)] = None


class IngestRequest(BaseModel):
    events: Annotated[list[EventIngest], Field(max_length=500)]


class IngestResult(BaseModel):
    received: int
    created: int
    updated: int
