"""Spider for iaBilet: Cluj listings followed by Event JSON-LD detail pages."""

import re
from urllib.parse import urlsplit

from gocluj_scraper.parsing.jsonld import (
    breadcrumb_name,
    extract_jsonld_events,
    jsonld_to_fields,
)
from gocluj_scraper.parsing.text import canonical_url, format_price
from gocluj_scraper.spiders.base import BaseEventSpider

_EVENT_ID_RE = re.compile(r"-(\d+)/?$")
# Match only documented prefixes; never strip arbitrary text before a city mention.
_TITLE_PREFIX_RE = re.compile(
    r"^\s*(?:SOLD-OUT\s+ÎN\s+\d+\s+ORE!\s+)?Cluj-Napoca:\s*", re.IGNORECASE
)


def _source_category(response) -> str | None:
    """Read the category from the second breadcrumb entry (position 2)."""
    name = breadcrumb_name(response, 2)
    return name.removesuffix(" în Cluj-Napoca") if name else None


class IabiletSpider(BaseEventSpider):
    name = "iabilet"
    source_name = "iaBilet"
    allowed_domains = ["iabilet.ro"]
    start_urls = ["https://www.iabilet.ro/bilete-in-cluj-napoca/"]
    custom_settings = {"CLOSESPIDER_TIMEOUT": 1200}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen: set[str] = set()

    def parse(self, response, page=1):
        """Follow unique, non-cancelled cards and the site's actual next-page link."""
        cards = response.css('div[data-event-list="item"]')
        if not cards:
            if page == 1:
                self.logger.error("iaBilet listing has no event cards: %s", response.url)
            return

        for card in cards:
            match = re.fullmatch(r"event/(\d+)", card.attrib.get("data-likable-item", ""))
            href = card.css(".title a::attr(href)").get()
            if match is None or not href:
                self.skip("invalid_card", response.url)
                self.logger.error("iaBilet card has no numeric id or detail link: %s", response.url)
                continue
            external_id = match.group(1)
            if external_id in self._seen:
                continue
            self._seen.add(external_id)
            url = canonical_url(response.urljoin(href))
            if "event-cancelled" in card.attrib.get("class", "").split():
                self.skip("cancelled", url)
                continue
            yield response.follow(url, self.parse_event, cb_kwargs={"external_id": external_id})

        # Out-of-range pages can still contain a promoted card, so emptiness is not enough.
        href = response.css("a.btn-more::attr(href)").get()
        if href:
            request = self.next_page(response, href, page + 1)
            if request is not None:
                yield request

    def parse_event(self, response, external_id=None):
        """Map detail JSON-LD, preferring all page tariffs over its single offer."""
        events = extract_jsonld_events(response)
        if not events:
            self.skip("no_jsonld", response.url)
            self.logger.warning("iaBilet detail has no Event JSON-LD: %s", response.url)
            return

        if external_id is None:
            match = _EVENT_ID_RE.search(urlsplit(response.url).path)
            external_id = match.group(1) if match else None
        price_text = format_price(
            response.css("[data-tariff-sell-price]::attr(data-tariff-sell-price)").getall(), "RON"
        )
        source_category = _source_category(response)
        # Image URLs are signed (resized variants return 400). The JSON-LD image is a 506x716
        # poster (cards); og:image is a fit-in 1200x1200 landscape banner (detail page).
        og_image = response.css('meta[property="og:image"]::attr(content)').get()
        for data in events:
            if (data.get("eventStatus") or "").endswith("EventCancelled"):
                self.skip("cancelled", response.url)
                continue
            fields = jsonld_to_fields(data)
            fields["external_id"] = external_id
            fields["source_url"] = canonical_url(fields.get("source_url") or response.url)
            if title := fields.get("title"):
                fields["title"] = _TITLE_PREFIX_RE.sub("", title, count=1).strip() or title
            if price_text is not None:
                fields["price_text"] = price_text
            fields["source_category"] = source_category
            fields["image_url_large"] = og_image
            item = self.make_event(**fields)
            if item is not None:
                yield item
