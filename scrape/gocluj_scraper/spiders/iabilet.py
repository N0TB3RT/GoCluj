"""Spider for iaBilet (https://www.iabilet.ro) - Cluj-Napoca events. Skeleton only."""

from gocluj_scraper.spiders.base import BaseEventSpider


class IabiletSpider(BaseEventSpider):
    name = "iabilet"
    source_name = "iaBilet"
    allowed_domains = ["iabilet.ro"]
    start_urls = ["https://www.iabilet.ro/bilete-in-cluj-napoca/"]

    def parse(self, response, page=1):
        """Parse a Cluj listing page and follow every event card to its detail page.

        TODO:
        1. Select event cards (listing is server-rendered, ~25 cards/page).
        2. If the page has no cards, stop (end of pagination).
        3. Listing dates lack year/time, so do not build events here: follow each
           card link with `response.follow(href, self.parse_event)`
           (pass cb_kwargs if listing data is needed later).
           Ignore listing prices - a few looked wrong; trust the detail page.
        4. Paginate with `?page=N`: yield `self.next_page(response, url, page + 1)`
           when it is not None (it returns None past max_pages).
        Note: sitemap-events.xml exists but is country-wide - not needed.
        """
        self.logger.warning("%s.parse not implemented yet", self.name)
        return

    def parse_event(self, response):
        """Parse an event detail page into an event item.

        TODO:
        1. `extract_jsonld_events(response)` - detail pages carry Event JSON-LD.
        2. Map each with `jsonld_to_fields(...)`.
        3. external_id = numeric id at the end of the slug (e.g. `...-126019/`).
        4. source_url = `canonical_url(response.url)` (strips `?ica_source=`).
        5. `item = self.make_event(**fields)`; yield it if not None.
        """
        self.logger.warning("%s.parse_event not implemented yet", self.name)
        return
