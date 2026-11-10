"""Spider for LiveTickets (https://www.livetickets.ro) - Cluj-Napoca events.

The site is an Angular SPA, so we use its public JSON API (INV-01 decision,
IMPLEMENTATION_PLAN section 9). Flow:

1. ``start``: GET ``/public/events`` (one list of all events, no pagination).
2. ``parse``: keep only items whose list ``city`` looks like Cluj; items without a city
   are skipped (``events/no_city``) because their detail has no city either. Each
   candidate gets a detail request (``/public/events/getbyurl?url=<slug>``).
3. ``parse_event``: confirm ``location.city == "Cluj-Napoca"`` in the detail, require
   status "online", then build the event from the list item plus a few detail keys.

``image_url`` is ``IMAGE_ROOT`` + an ``images[].path`` (detail first, then the list
item), preferring the Background MEDIUM size. The image ``token`` is only a cache-buster
and is never used.

Only the detail keys named below are read; the rest (organizer, company, tags, ...) is
never stored or logged. Unexpected response shapes raise, so the run fails visibly.
"""

from urllib.parse import quote

import scrapy

from gocluj_scraper.parsing.text import format_price, is_cluj, strip_accents
from gocluj_scraper.spiders.base import BaseEventSpider

API = "https://api.livetickets.ro/public/events"
EVENT_URL = "https://www.livetickets.ro/bilete/"
# Without this the API answers Scrapy's default Accept header with XML.
JSON_HEADERS = {"Accept": "application/json"}
IMAGE_ROOT = "https://livetickets-cdn.azureedge.net/itemimages/"
# Preferred Background sizes; declared sizes are upper bounds (fit inside, not cropped).
IMAGE_SIZES = ("MEDIUM", "SQUARE", "ZOOM")


def _is_cluj_napoca(city: str | None) -> bool:
    return strip_accents(city or "").lower().strip() == "cluj-napoca"


def _image_url(images) -> str | None:
    """Pick a Background image (MEDIUM, SQUARE, ZOOM, then any) and build its CDN URL."""
    backgrounds = [
        i
        for i in images or []
        if isinstance(i, dict) and i.get("name") == "Background" and i.get("path")
    ]
    if not backgrounds:
        return None
    rank = {size: n for n, size in enumerate(IMAGE_SIZES)}
    best = min(backgrounds, key=lambda i: rank.get(i.get("size"), len(rank)))
    return IMAGE_ROOT + quote(best["path"], safe="/")


class LiveticketsSpider(BaseEventSpider):
    name = "livetickets"
    source_name = "LiveTickets"
    allowed_domains = ["livetickets.ro"]

    async def start(self):
        yield scrapy.Request(API, headers=JSON_HEADERS, callback=self.parse)

    def parse(self, response):
        items = response.json()
        candidates = 0
        for item in items:
            url = EVENT_URL + item["url"]
            city = item.get("city")
            if not city:
                self.skip("no_city", url)
            elif not is_cluj(city):
                self.skip("not_cluj", url)
            else:
                candidates += 1
                detail_url = f"{API}/getbyurl?url={quote(item['url'], safe='')}"
                yield scrapy.Request(
                    detail_url,
                    headers=JSON_HEADERS,
                    callback=self.parse_event,
                    cb_kwargs={"item": item},
                )
        self.logger.info("LiveTickets list: %d items, %d Cluj candidates", len(items), candidates)
        if not candidates:
            self.logger.error("LiveTickets list has no Cluj candidates (%d items)", len(items))

    def parse_event(self, response, item):
        detail = response.json()
        location = detail["location"]
        url = EVENT_URL + item["url"]
        if not _is_cluj_napoca(location.get("city")):
            self.skip("not_cluj", url)
            return
        if detail["status"] != "online":
            self.skip(f"status_{detail['status']}", url)
            return
        if detail.get("has_time_slots"):
            self._inc_stat("events/time_slots")
            self.logger.warning("Event with time slots, emitted without them: %s", url)

        lat, lng = location.get("lat") or None, location.get("lng") or None
        price_max = item.get("price_max")
        currency = (item.get("currency") or {}).get("code")
        category = next(
            (t["name"] for t in detail.get("item_tags") or [] if t.get("type") == "Category"),
            None,
        )
        event = self.make_event(
            external_id=item["event_id"],
            source_url=url,
            title=item["name"],
            description=item.get("description"),
            start_at=item["start_date"],
            end_at=item.get("end_date"),
            venue={
                "name": location.get("name") or item.get("location"),
                "address": location.get("address"),
                "city": location.get("city"),
                "lat": lat if lat and lng else None,
                "lng": lng if lat and lng else None,
            },
            price_text=(
                format_price([item.get("price_min"), price_max], currency) if price_max else None
            ),
            source_category=category,
            image_url=_image_url(detail.get("images")) or _image_url(item.get("images")),
        )
        if event is not None:
            yield event
