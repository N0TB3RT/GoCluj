"""Pydantic models: the single place where scraped data is validated and normalized."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from gocluj_scraper.parsing.text import (
    canonical_url,
    clean_text,
    detect_is_free,
    localize,
    parse_ro_datetime,
)

CATEGORIES = [
    "Party",
    "Festival",
    "Târg / Expoziție",
    "Tech & Meetups",
    "Eveniment Local",
    "Cultură",
    "Sport",
    "Altele",
]


class Venue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None

    @field_validator("name", "address", "city", mode="before")
    @classmethod
    def _clean(cls, value: Any) -> str | None:
        return clean_text(value)


def _to_datetime(value: Any) -> datetime:
    """Accept datetime, ISO string or Romanian date text; always return an aware datetime."""
    if isinstance(value, datetime):
        return localize(value)
    if isinstance(value, str) and (parsed := parse_ro_datetime(value)):
        return parsed
    raise ValueError(f"unparseable datetime: {value!r}")


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str
    source_url: str
    external_id: str | None = None
    title: str
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    venue: Venue = Field(default_factory=Venue)
    price_text: str | None = None
    is_free: bool | None = None
    categories: list[str] = Field(default_factory=list)
    image_url: str | None = None

    @field_validator("source_url", mode="before")
    @classmethod
    def _canonical_url(cls, value: Any) -> Any:
        return canonical_url(value) if isinstance(value, str) else value

    @field_validator("title", mode="before")
    @classmethod
    def _title(cls, value: Any) -> str:
        if not (title := clean_text(value)):
            raise ValueError("title must not be empty")
        return title

    @field_validator("description", "price_text", mode="before")
    @classmethod
    def _clean(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("start_at", mode="before")
    @classmethod
    def _start(cls, value: Any) -> datetime:
        return _to_datetime(value)

    @field_validator("end_at", mode="before")
    @classmethod
    def _end(cls, value: Any) -> datetime | None:
        return None if value in (None, "") else _to_datetime(value)

    @model_validator(mode="after")
    def _derive_is_free(self) -> "Event":
        if self.is_free is None:
            self.is_free = detect_is_free(self.price_text)
        return self
