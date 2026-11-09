"""Spider for LiveTickets (https://www.livetickets.ro) - Cluj-Napoca events. Skeleton only."""

from gocluj_scraper.spiders.base import BaseEventSpider


class LiveticketsSpider(BaseEventSpider):
    name = "livetickets"
    source_name = "LiveTickets"
    allowed_domains = ["livetickets.ro"]
    start_urls = ["https://www.livetickets.ro/evenimente"]

    def parse(self, response, page=1):
        """Fetch the event list and follow Cluj events to their details.

        TODO:
        - The site is an Angular SPA: every page (even /robots.txt) returns the
          same ~8 KB shell. Data comes from an internal JSON API on
          api.livetickets.ro. Whether we may use that API or must fall back to
          scrapy-playwright is decided in INV-01 (ToS check).
        - If the JSON API is used: add "api.livetickets.ro" to allowed_domains,
          request it from start_requests and parse with `response.json()`.
        - There is no city filter: drop non-Cluj events with `is_cluj(...)` on
          venue/city BEFORE fetching details.
        - Paginate via `self.next_page(response, url, page + 1)`.
        """
        self.logger.warning("%s.parse not implemented yet", self.name)
        return

    def parse_event(self, response):
        """Parse one event into an event item.

        TODO:
        - external_id = slug from `/bilete/<slug>`.
        - source_url = `canonical_url(...)`.
        - `item = self.make_event(**fields)`; yield it if not None.
        """
        self.logger.warning("%s.parse_event not implemented yet", self.name)
        return
