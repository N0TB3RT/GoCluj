"""Base spider shared by all event sources."""

from datetime import datetime
from zoneinfo import ZoneInfo

import scrapy
from pydantic import ValidationError

from gocluj_scraper.models import Event
from gocluj_scraper.parsing.text import TIMEZONE


class BaseEventSpider(scrapy.Spider):
    """Base class for source spiders: fetch and extract only.

    A source spider sets ``name`` and ``source_name``. The crawl shape is up to the
    spider: listing page -> detail page is one option, a JSON list + detail page is
    another. Whatever the shape, drop records early with ``self.skip(reason, url)``,
    ``yield self.make_event(**fields)`` (skip ``None``) and paginate with ``next_page``.
    Normalization, validation and stats live in ``make_event`` and ``models.Event``.
    """

    source_name: str = ""

    def __init__(self, *args, max_pages: int | str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages: int | None = int(max_pages) if max_pages else None

    def _inc_stat(self, key: str) -> None:
        crawler = getattr(self, "crawler", None)
        if crawler is not None:
            crawler.stats.inc_value(key)

    def skip(self, reason: str, url: str | None = None) -> None:
        """Count a dropped event under ``events/<reason>`` and log it at DEBUG."""
        self._inc_stat(f"events/{reason}")
        self.logger.debug("Skipping event (%s): %s", reason, url)

    def make_event(self, **fields) -> dict | None:
        """Validate fields into an Event dict; None if invalid or already past."""
        try:
            event = Event(source_name=self.source_name, **fields)
        except ValidationError as exc:
            self._inc_stat("events/invalid")
            first = exc.errors()[0]
            self.logger.warning(
                "Invalid event (url=%s, title=%s): %s %s",
                fields.get("source_url"),
                fields.get("title"),
                ".".join(str(p) for p in first["loc"]),
                first["msg"],
            )
            return None
        if (event.end_at or event.start_at) < datetime.now(ZoneInfo(TIMEZONE)):
            self.skip("past", event.source_url)
            return None
        self._inc_stat("events/valid")
        return event.model_dump(mode="json")

    def next_page(self, response, url: str, page: int, callback=None) -> scrapy.Request | None:
        """Request for listing page ``page``, or None once ``max_pages`` is exceeded."""
        if self.max_pages and page > self.max_pages:
            return None
        return response.follow(url, callback or self.parse, cb_kwargs={"page": page})
