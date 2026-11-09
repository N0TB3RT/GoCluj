# Scraper design

> Owner: Data team. Covers DATA-01..05. Code lives in [`scrape/`](../../scrape/README.md).
> Last updated: 2026-11-09.

## 1. Goals and constraints

- Upcoming events in Cluj-Napoca from **≥4 sources**, refreshed **daily**, **unattended** (see the [implementation plan](../IMPLEMENTATION_PLAN.md), §1 and §4.4).
- Sources are a mix of server-rendered HTML, JSON-LD, internal JSON APIs and JS-only pages, and they change without notice.
- Small team and short timeline: **pick the boring option**, keep each source isolated and small, and share everything else.

## 2. Tool decisions

| Question | Decision | Why |
|---|---|---|
| Crawling library | **Scrapy** (parsel selectors) instead of requests + BeautifulSoup | Gives us HTTP cache (iterate on parsers offline), AutoThrottle, per-domain concurrency, retries, timeouts, robots.txt, feed export (JSONL) and per-run stats out of the box. With requests + BS4 every one of these becomes shared code we would have to write and maintain. Each source is one small spider class. |
| JS-only sources | Prefer the site's JSON endpoint if the ToS allows it. Otherwise `scrapy-playwright`, opt-in per spider | Keeps the image small. Playwright is added to `requirements.txt` only when a source needs it. |
| Orchestration | **cron + `docker compose run --rm scraper`**. No Airflow, Prefect or Dagster | One daily batch of ~5 spiders on one VPS. Airflow needs its own scheduler, webserver, metadata DB and 2–4 GB of RAM, which is more infra than the rest of GoCluj combined. Revisit only if we get many inter-dependent jobs. |
| Dates | A small Romanian month map plus regex (`parsing/text.py`), not `dateparser` | Deterministic and fully unit-tested. ISO dates from JSON-LD are preferred whenever available. |
| JSON-LD | A ~40-line helper (`parsing/jsonld.py`), not `extruct` | We only need schema.org `*Event` objects. `extruct` pulls in rdflib and more. |
| Data model | **One** Pydantic `Event` model with `before` validators | Normalization (text, dates, `is_free`, canonical URL) happens in one place. Spiders yield plain dicts, so there is no itemadapter version coupling. |
| Delivery to backend | **Two steps:** crawl → JSONL file → `ingest` command | No blocking HTTP inside Scrapy's reactor. A backend outage doesn't fail the crawl, ingest can be re-run without re-crawling, the file is a debuggable artifact, and dry-run comes for free. |
| Process model | One `scrapy crawl` **subprocess per spider** | Failure isolation, per-source settings and a clear success/failure per source. |

## 3. Workflow

```
cron (OPS-04) ─► docker compose run --rm scraper   (= python -m gocluj_scraper.run)
                    │
                    ├─ for each spider (separate process):
                    │     listing pages ──► filter Cluj early ──► detail pages
                    │        └─► self.make_event(**fields)
                    │               ├─ Event model: clean text, parse dates (Europe/Bucharest),
                    │               │  canonical URL, derive is_free
                    │               ├─ invalid → counted (events/invalid), skipped
                    │               └─ past    → counted (events/past), skipped
                    │     FEEDS  → $OUTPUT_DIR/<YYYY-MM-DD>/<spider>.jsonl
                    │     RunSummary → <spider>.summary.json + one JSON log line
                    │                  (0 items / errors / abnormal close ⇒ failed)
                    │
                    └─ ingest: successful JSONL files → POST /api/ingest/events
                               in batches, header X-Ingest-Token
                               (INGEST_URL unset ⇒ dry-run)
                    exit code ≠ 0 if any spider or the ingest failed  → alert (DATA-05 / OPS-04)
```

### Responsibilities

| Piece | Does | Does not |
|---|---|---|
| Source spider | Fetch, extract fields, filter Cluj, set `external_id` | Clean, normalize, tag, call the backend |
| `BaseEventSpider` | `make_event()` (validate, normalize, drop past events, count stats), `next_page()` (respects `max_pages`) | Source-specific logic |
| `Event` model | The single place for normalization rules | I/O |
| `parsing/` | Pure helpers: JSON-LD, text, dates, URLs, `is_free`, `is_cluj` | I/O |
| `RunSummary` | Per-source health: items, invalid, past, errors, duration, failed flag | Alerting itself |
| `run.py` | Runs spiders, decides success, calls ingest, sets the exit code | Scheduling (cron does that) |
| `ingest.py` | Batched, retried POST of JSONL files | Dedup (the backend upserts) |
| Backend (BE-02) | Upsert, cross-source dedup, (proposed) geocoding | – |

### Politeness defaults (`settings.py`, overridable per spider via `custom_settings`)

- `ROBOTSTXT_OBEY`
- Identifying user agent `GoClujBot`
- 2 concurrent requests per domain, 1 s delay, AutoThrottle
- 3 retries and a 30 s timeout
- 10 min time budget per spider (`CLOSESPIDER_TIMEOUT`) and an error budget
- HTTP cache enabled in development only (`HTTPCACHE_ENABLED=1`)

## 4. Sources

### iaBilet (`iabilet`), source 1
- Server-rendered HTML with JSON-LD on listing and detail pages.
- The Cluj listing is `https://www.iabilet.ro/bilete-in-cluj-napoca/?page=N` (~25 cards/page). Paginate until a page has no cards.
- Card dates have no year or time, and some listing prices looked wrong, so follow every card to its **detail page** and read the Event JSON-LD there.
- `external_id`: the numeric id at the end of the slug (`…-126019/`).
- Tracking parameter `?ica_source=` is stripped by `canonical_url`.
- robots.txt allows listing and event pages and sets no crawl-delay.
- `sitemap-events.xml` exists but covers the whole country, so it isn't needed.

### LiveTickets (`livetickets`), source 2
- An Angular SPA: every URL, including `/robots.txt`, returns the same ~8 KB HTML shell. Data comes from an internal JSON API on `api.livetickets.ro`.
- **Open (INV-01):** check the ToS before using the JSON API. If it is not allowed, use `scrapy-playwright` on `/evenimente`.
- There is no city filter. Filter Cluj with `is_cluj()` on the venue or city **before** requesting details.
- `external_id`: the slug from `/bilete/<slug>`.

## 5. Adding a source (checklist)

1. Check robots.txt, the ToS, and whether there is an API, a feed or JSON-LD. Record the result in [IMPLEMENTATION_PLAN §9](../IMPLEMENTATION_PLAN.md#9-decisions-log) under INV-01.
2. Pick the extraction method in this order: **JSON-LD → JSON API → HTML selectors → Playwright**.
3. Add `gocluj_scraper/spiders/<name>.py` as a subclass of `BaseEventSpider`. Set `name`, `source_name`, `allowed_domains` and `start_urls`.
4. Filter Cluj as early as possible. Emit a stable `external_id`. Build every event through `self.make_event(...)`.
5. Save 1–2 real pages to `tests/fixtures/<name>/` and write a parser test using `fake_response`.
6. Develop with `HTTPCACHE_ENABLED=1` and `-a max_pages=1`. Put per-source politeness tweaks in `custom_settings`.

## 6. Open cross-team items

| Item | With | Proposal |
|---|---|---|
| Upsert key | Backend (BE-02), DATA-02 | Upsert by **`(source_name, external_id)`**, falling back to `source_url`. `source_url` alone breaks when one page lists several dates. |
| Ingest payload | Backend (BE-02), PRJ-01 | `POST /api/ingest/events` with body `{"events": [Event, …]}` and header `X-Ingest-Token`. The scraper's `models.Event` is a draft of PRJ-01 and will be aligned once PRJ-01 is merged. |
| Contract drift | Backend | After PRJ-01: commit the ingest JSON schema (`model_json_schema()`), and have a scraper test validate sample output against it. |
| Geocoding (DATA-04) | Backend | **Move geocoding to the backend.** It needs a persistent venue cache and Nominatim at 1 req/s. The scraper container is stateless and runs daily, so it would re-geocode everything. The scraper sends the venue name and address; the backend geocodes new venues only. |
| Tagging (DATA-03) | – | Stays in the scraper as a pure function called from `make_event`, with keyword lists in a config file. |
| Scheduling and alerts | DevOps (OPS-04) | The daily cron runs `docker compose run --rm scraper`. A non-zero exit code triggers an alert. Per-source health comes from the `*.summary.json` files (input for the admin panel's source health, BE-10). |
