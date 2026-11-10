"""Pydantic models: the single place where scraped data is validated and normalized."""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from w3lib.html import remove_tags

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

_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_BLOCK_END_RE = re.compile(r"</(?:p|div|li|h[1-6]|ul|ol)\s*>", re.IGNORECASE)
_DATE_ONLY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


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
    external_id: str
    title: str
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    venue: Venue = Field(default_factory=Venue)
    price_text: str | None = None
    is_free: bool | None = None
    categories: list[str] = Field(default_factory=list)
    source_category: str | None = None
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

    @field_validator("external_id", mode="before")
    @classmethod
    def _external_id(cls, value: Any) -> str:
        if not (external_id := clean_text(value)):
            raise ValueError("external_id must not be empty")
        return external_id

    @field_validator("price_text", "source_category", mode="before")
    @classmethod
    def _clean(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("description", mode="before")
    @classmethod
    def _description(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = _BR_RE.sub("\n", _BLOCK_END_RE.sub("\n", str(value)))
        return clean_text(remove_tags(text), multiline=True)

    @field_validator("start_at", mode="before")
    @classmethod
    def _start(cls, value: Any) -> datetime:
        return _to_datetime(value)

    @field_validator("end_at", mode="before")
    @classmethod
    def _end(cls, value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, str) and _DATE_ONLY_RE.fullmatch(value.strip()):
            return _to_datetime(value).replace(hour=23, minute=59, second=59)
        return _to_datetime(value)

    @model_validator(mode="after")
    def _finalize(self) -> "Event":
        if self.is_free is None:
            self.is_free = detect_is_free(self.price_text)
        if self.end_at is not None and self.end_at <= self.start_at:
            self.end_at = None
        return self
