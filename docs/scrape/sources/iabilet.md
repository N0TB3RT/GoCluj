# iaBilet spider

> Source: iaBilet (`https://www.iabilet.ro`). Spider name: `iabilet`. Tasks: T7-T9.
> Status: **implemented** (`spiders/iabilet.py`, T7-T9). Full timed run still pending (T13).
> Site checked: 2026-11-10 (about 15 polite GETs). Last updated: 2026-11-10.
> Everything shared (Event model, counters, shared changes S1-S8, task list, scalability, adding a source) is in [../scraper-design.md](../scraper-design.md). This page covers only what is specific to iaBilet.

## 1. Site facts

| Topic | Fact |
|---|---|
| robots.txt | `User-agent: *` disallows only `/auth/ /account/ /cos/ /googleMap/ /l/ /o/ /b/`. No crawl-delay. Listing and event pages are allowed. Sitemaps (`sitemap.xml`, `sitemap-events.xml`) are country-wide and not used. |
| Listing URL | `https://www.iabilet.ro/bilete-in-cluj-napoca/` and `?page=N`. Server-rendered. The URL already filters by city, so no `is_cluj` check is needed. |
| Volume | 7 listing pages, 160 cards (checked 2026-11-10); about 155 unique events after promoted duplicates. |
| Listing has | Card id, detail link, title, venue and city, start day/month/'yy without time, minimum price ("de la 21<sup>21</sup> lei" = 21.21), status classes. |
| Listing lacks | Time, end date, description, image, full price range. The listing JSON-LD is only a `BreadcrumbList` (no Event). |
| Detail page has | Event JSON-LD (present on all 6 pages checked, including cancelled and sold-out): `name`, clean `url`, `description` (plain text with `\r\n`), `eventStatus`, `eventAttendanceMode`, `startDate` (ISO with offset), `endDate` (date only), `image`, `location{name, address{streetAddress, addressLocality, addressCountry}, url}`, `performer[]`, `offers{price, priceCurrency, availability}`. Also all tariffs as `data-tariff-sell-price` attributes and a breadcrumb JSON-LD. |
| Detail page lacks | `geo`, `organizer`, `lowPrice` / `highPrice`. |
| Images | `imgcdn` URLs are signed Thumbor URLs: resized variants return HTTP 400, so URLs are never rewritten. JSON-LD `image` is a 506x716 center-cropped poster. `<meta property="og:image">` is a fit-in 1200x1200 image, usually a separate landscape banner (~1200x675). The unsigned original on `static3.iabilet.ro` (~2830x4000, ~1.5 MB) is too heavy and not used. |

Why not build events from the listing: no time, no year-safe date, only the minimum price. The detail page is the source of truth.

## 2. Request flow

```
start_urls: /bilete-in-cluj-napoca/
   │
   ▼
parse(page=N) ── for each card ──► id seen? ──yes──► (ignore)
   │                                │no
   │                                ├─ card has event-cancelled ─► skip("cancelled")
   │                                └─ follow canonical_url(href) ─► parse_event(external_id=id)
   │                                                                     │
   └─ a.btn-more present? ─yes─► next_page(page + 1)                     ▼
                         │no                                  Event JSON-LD ─► make_event
                         ▼                                     (none ─► skip("no_jsonld");
                       stop                                    EventCancelled ─► skip("cancelled"))
```

`parse(response, page=1)`:
1. Select cards (`div[data-event-list="item"]`). Zero cards on page 1: log ERROR (layout change; the run then fails with `items=0`).
2. Per card read the id from `data-likable-item` (`event/<id>`). If the id is in `self._seen` (a plain `set` on the spider), ignore the card. Otherwise add it.
3. If the card class contains `event-cancelled`: `self.skip("cancelled")` and do not follow.
4. Otherwise follow `canonical_url(response.urljoin(href))` (href from `.title a`) to `parse_event`, with `cb_kwargs={"external_id": id}`.
5. If `a.btn-more` exists, `yield self.next_page(response, <its href>, page + 1)` when it is not `None` (existing helper, returns `None` past `max_pages`).

`parse_event(response, external_id)`:
1. `extract_jsonld_events(response)` (existing). Empty: `self.skip("no_jsonld")` plus a WARNING with the URL, return.
2. `eventStatus` ends with `EventCancelled`: `self.skip("cancelled")`, return.
3. `fields = jsonld_to_fields(data)` (existing), then apply the overrides in section 4.
4. `item = self.make_event(**fields)`; yield it when not `None`.

Shared helpers (not iaBilet-specific, see the design doc): `skip` (S6), `format_price` (S4) and `_address` city de-dup (S5) are done. Reused as is: `canonical_url`, `extract_jsonld_events`, `jsonld_to_fields`, `breadcrumb_name`, `make_event`, `next_page`.

## 3. Selectors

| What | Selector / attribute | Example |
|---|---|---|
| Card | `div[data-event-list="item"]` | 25 per full page |
| Event id | card `@data-likable-item`, strip `event/` | `event/133857` -> `133857` |
| Card status | card `@class` contains `event-cancelled`, `event-sold-out`, `event-without-stock`, `event-multi-day`, `promoted` | `event-list-item promoted ... event-single-day` |
| Detail link | `.title a::attr(href)` | `/bilete-<slug>-133857/?ica_source=TownPage...` |
| Next page | `a.btn-more::attr(href)` (inside `div[data-event-list="more"]`) | `/bilete-in-cluj-napoca?page=2` |
| Tariffs (detail) | `[data-tariff-sell-price]::attr(data-tariff-sell-price)` | `21.21`, `26.51`, `31.82` |
| Category (detail) | breadcrumb JSON-LD, entry at position 2, via `breadcrumb_name(response, 2)` | `Party în Cluj-Napoca` |
| Event data (detail) | Event JSON-LD via `extract_jsonld_events` | see section 4 |
| Large image (detail) | `meta[property="og:image"]::attr(content)` | fit-in 1200x1200 banner |

The breadcrumb is a second JSON-LD block (`BreadcrumbList`), not returned by `extract_jsonld_events`; the shared `jsonld.breadcrumb_name` helper reads it. Not used for events on the listing: `.date .date-start`, `.location a.venue span`, `.price`.

## 4. Field mapping

| Event field | Source | Rule |
|---|---|---|
| `source_name` | spider | `"iaBilet"` (existing) |
| `external_id` | card id | Fallback: regex `-(\d+)/?$` on the detail URL path. Required (S3). |
| `source_url` | JSON-LD `url` | Already clean; the model applies `canonical_url` anyway. |
| `title` | JSON-LD `name` | Remove only the documented prefixes `^(SOLD-OUT ÎN <n> ORE! )?Cluj-Napoca:\s*` (case-insensitive); never arbitrary text before a city mention. If the result is empty, keep the original name. |
| `description` | JSON-LD `description` | Plain text with `\r\n`; kept as multi-line by S2. |
| `start_at` | JSON-LD `startDate` | ISO with offset, e.g. `2026-11-12T19:30:00+02:00`. |
| `end_at` | JSON-LD `endDate` | Date only (`2026-11-13`). S1 turns it into 23:59:59 that day; if that is the start day (single-day events) `end_at` becomes `None`; `end_at <= start_at` becomes `None`. |
| `venue.name` | `location.name` | |
| `venue.address` | `location.address.streetAddress` | City not appended when already contained as whole words, e.g. "Strada Bucium 2, Cluj-Napoca 400535" (S5). |
| `venue.city` | `location.address.addressLocality` | |
| `venue.lat/lng` | – | Not available; the backend geocodes. |
| `price_text` | all `data-tariff-sell-price` values | `format_price(values, "RON")`, e.g. `21.21 - 31.82 RON`. Fallback: the JSON-LD offer. `None` when neither exists. The JSON-LD offer holds a single tariff (the highest in both cases checked), so it is not used first. |
| `is_free` | derived | From `price_text` by the model (`0 RON` is read as free). |
| `image_url` | JSON-LD `image` | 506x716 poster, used on cards. Never rewritten (signed URL). |
| `image_url_large` | `og:image` meta | Fit-in 1200x1200 banner, used on the detail page; the frontend falls back to `image_url`. |
| `source_category` | breadcrumb position 2 (`breadcrumb_name`) | Minus the suffix ` în Cluj-Napoca`, e.g. `Party`, `Rock`, `Clasica si Balet`. |
| `categories` | – | Empty until DATA-03. |

## 5. Edge-case rules

| Case | How the site shows it | Spider does |
|---|---|---|
| Promoted duplicate | The same event appears as a normal card and as a `promoted` card (`ica_source=TownPagePromoted...`). Event 132560 appears on every page, including pages past the end. About 160 cards give about 155 unique events. | `self._seen` set on the id; ignore repeats. Scrapy's dupefilter alone is not enough because it compares the full URL including the query. |
| Tracking params | `?ica_source=TownPage...` on every card link | `canonical_url` strips `ica_*` before following; `source_url` comes from JSON-LD `url`. |
| Cancelled | Card class `event-cancelled` with `data-cancelled-label="Anulat"`; detail `eventStatus` `EventCancelled`, no `offers` | Skipped on the card (no detail request); also dropped in `parse_event` as a second check. Counter `events/cancelled`. |
| Rescheduled | `eventStatus` `EventRescheduled` with `previousStartDate`; `startDate` is the new time | Keep; use the new `startDate`. Old date is ignored. |
| Sold out, variant A | Card class `event-sold-out`; JSON-LD has no `offers` | Keep; `price_text` from tariffs if any, else `None`. |
| Sold out, variant B | Card class `event-without-stock`; offer `availability` `SoldOut`, price present | Keep; price from tariffs. Sold-out status is not stored (no field in the contract). |
| Free | JSON-LD `"price":"0.00"`, `data-tariff-sell-price="0"`, card has no `.price` | `price_text` = `0 RON`; model derives `is_free=True`. |
| Multi-day | One event: `startDate` day 1, `endDate` last day (date only), card class `event-multi-day` | One Event with `end_at` = last day 23:59:59 (S1). |
| Multiple performances | Every case seen has one id per performance. **Unverified** that this always holds. | Treated as separate events by id. |
| Title prefix | `Cluj-Napoca: Andra...`, sometimes `SOLD-OUT ÎN 15 ORE! Cluj-Napoca: Andra...` | Strip as in section 4. |
| Address city duplication | `streetAddress` "Strada Brassai Sámuel 12, Cluj-Napoca" plus locality "Cluj-Napoca" | S5 (done) prevents "..., Cluj-Napoca, Cluj-Napoca". |
| Non-card links | Gift voucher `/bilete-voucher-cadou-iabilet-87881/` appears outside cards | Only links inside cards are followed. |
| Event today | `endDate` is the date of today (for example 132993: 2026-11-10) | Single-day: `end_at` is `None` (S1), so it is dropped as past once `start_at` has passed (accepted). Multi-day ending today: 23:59:59 keeps it listed. |

## 6. Pagination and stop condition

- Every page returns HTTP 200, including pages far past the end.
- Pages past the end are not empty. Page 8 and page 16 each still return one card: the promoted event 132560, which is also shown on every real page. So "stop when a page has no cards" never fires, and following `?page=N+1` blindly would crawl forever.
- Real pages carry `<a href="/bilete-in-cluj-napoca?page=N+1" class="btn btn-more">`. The last real page (7) has none. **Stop when `a.btn-more` is absent.** Follow its `href`, do not construct URLs.
- `max_pages` (spider argument) is the second bound; `CLOSESPIDER_TIMEOUT` is the third.
- Why the global `DEPTH_LIMIT = 10` was removed (S8, T6, done): listing page N is at depth N-1 and its detail pages at depth N, so detail pages of listing pages past 10 were dropped silently; beyond 10 pages the crawl would have been truncated with no error. Without it, a runaway crawl is still bounded by `btn-more`, `max_pages` and the timeout.

## 7. Settings and budget

```python
custom_settings = {"CLOSESPIDER_TIMEOUT": 1200}  # global default is 600
```

| Item | Value |
|---|---|
| Requests | robots.txt, 7 listing pages, about 155 detail pages: about 163 in total |
| Expected runtime | About 3-4 min at roughly 1 request/s (1 s delay, 2 concurrent, AutoThrottle). **Estimate**, to be measured in T13. |
| At 10x | About 1,600 detail pages is about 30 min, over the 20 min limit: the run would close with `closespider_timeout` and be marked failed. Knobs: raise `CLOSESPIDER_TIMEOUT` for this spider; later, request details only for ids the backend does not know yet (needs a known-ids endpoint). See the scalability table in the design doc. |

## 8. Failure modes and run summary

| Failure | Shows in the run summary as |
|---|---|
| Layout change, zero cards on page 1 | ERROR logged, `items=0`, run failed |
| Detail page without Event JSON-LD | `events/no_jsonld` > 0 plus WARNINGs. Proposed: fail the run when it is more than half of the detail pages (not implemented) |
| Detail 5xx after 3 retries | ERROR, run failed |
| Time budget exceeded | reason `closespider_timeout`, run failed |
| Bad or missing fields | `events/invalid` (WARNING per event, with URL and field) |
| Many cancelled / past | `events/cancelled`, `events/past`: informational, not failures |
| `btn-more` markup changed | Only page 1 is crawled; looks like a healthy but small run. Watch `items` against the usual ~155 (**no automatic check yet**) |

## 9. Fixtures and tests

Fixtures in `scrape/tests/fixtures/iabilet/` (T7, done): trimmed saved pages, only the JSON-LD scripts kept. For the origin of `detail_free.html`, see the comment at the top of the fixture.

| File | Content |
|---|---|
| `listing_p1.html` | 3 cards: normal, cancelled, promoted; with `a.btn-more` |
| `listing_last.html` | Last real page, no `btn-more` |
| `detail_multiday.html` | Multi-day event, 3 tariffs (e.g. 133857) |
| `detail_free.html` | Free event (price 0) |
| `detail_cancelled.html` | `EventCancelled`, no offers |

`tests/test_iabilet.py` (T8, T9, done) covers, using `fake_response` from `tests/conftest.py`:
- Cards produce requests to canonical URLs (no `ica_source`), with `cb_kwargs` id.
- Cancelled card is skipped; `events/cancelled` incremented.
- Duplicate id is skipped.
- `btn-more` present: next-page request; absent: none.
- `max_pages=1`: no next-page request.
- Detail mapping: title prefix removed, price `21.21 - 31.82 RON`, free gives `is_free=True`, `source_category` from breadcrumb, end date rule.
- `EventCancelled` detail is dropped.

## 10. Unverified items and open questions

- **Unverified:** multiple performances always get one id each; some detail pages lack Event JSON-LD (none seen in 6); the exact runtime.
- Owner questions (proposed defaults): keep sold-out events (yes); show only the new date for rescheduled events (yes); is a 20 min budget acceptable (yes); Cluj-Napoca city only.
- Backend: do disappeared or cancelled-after-ingest events expire; does the contract accept `source_category` and multi-line descriptions. Full list in the design doc.
