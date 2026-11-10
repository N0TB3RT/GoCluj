# Scraper design

> Owner: Data team. Covers DATA-01..05. Code lives in [`scrape/`](../../scrape/README.md).
> Last updated: 2026-11-10.

**Status.** Implemented: Scrapy framework and settings, `Event` model, parsing helpers, `BaseEventSpider`, runner (`run.py`), `RunSummary`, `ingest.py`, unit tests. LiveTickets spider (`livetickets.py`, T11; `image_url`, T12; one live run on 2026-11-10). To do: the iaBilet spider (`iabilet.py`) is a stub; of the shared changes (§6) S1-S4 and S6-S8 are done, S5 is open. Ingest is live against the backend `POST /api/ingest/events` (BE-02): with `INGEST_URL` and `INGEST_TOKEN` set it posts for real; dry-run only when `INGEST_URL` is unset.

## 1. Goals and constraints

- Upcoming events in Cluj-Napoca from **≥4 sources**, refreshed **daily**, **unattended** (see the [implementation plan](../IMPLEMENTATION_PLAN.md), §1 and §4.4).
- Sources are a mix of server-rendered HTML, JSON-LD, internal JSON APIs and JS-only pages, and they change without notice.
- Small team and short timeline: **pick the boring option**, keep each source isolated and small, share everything else.
- A broken source must show up as a failed run, never as silently fewer events.

## 2. Tool decisions

| Question | Decision | Why |
|---|---|---|
| Crawling library | **Scrapy** (parsel selectors) instead of requests + BeautifulSoup | HTTP cache (iterate on parsers offline), AutoThrottle, per-domain concurrency, retries, timeouts, robots.txt, feed export (JSONL) and per-run stats out of the box. With requests + BS4 each of these becomes shared code to write and maintain. Each source is one small spider class. |
| JS-only sources | Prefer the site's JSON endpoint if the ToS allows it. Otherwise `scrapy-playwright`, opt-in per spider | Keeps the image small. Playwright is added to `requirements.txt` only when a source needs it. |
| Orchestration | **cron + `docker compose run --rm scraper`**. No Airflow, Prefect or Dagster | One daily batch of ~5 spiders on one VPS. Airflow needs its own scheduler, webserver, metadata DB and 2-4 GB of RAM. Revisit only if we get many inter-dependent jobs. |
| Dates | Small Romanian month map plus regex (`parsing/text.py`), not `dateparser` | Deterministic and fully unit-tested. ISO dates from JSON-LD/APIs are preferred whenever available. |
| JSON-LD | A ~40-line helper (`parsing/jsonld.py`), not `extruct` | We only need schema.org `*Event` objects. `extruct` pulls in rdflib and more. |
| Data model | **One** Pydantic `Event` model with `before` validators | Normalization happens in one place. Spiders yield plain dicts, so there is no itemadapter version coupling. |
| Delivery to backend | **Two steps:** crawl → JSONL file → `ingest` command | No blocking HTTP inside Scrapy's reactor. A backend outage doesn't fail the crawl, ingest can be re-run without re-crawling, the file is a debuggable artifact, and dry-run comes for free. |
| Process model | One `scrapy crawl` **subprocess per spider** | Failure isolation, per-source settings and a clear success/failure per source. |

## 3. Workflow

```
cron (OPS-04) ─► docker compose run --rm scraper   (= python -m gocluj_scraper.run)
                    │
                    ├─ for each spider (separate process, sequential):
                    │     source-specific fetch (HTML listing → detail, JSON list → detail, ...)
                    │       ├─ drop early: self.skip(reason)  → events/<reason>
                    │       └─ self.make_event(**fields)
                    │            ├─ Event model: clean text, parse dates (Europe/Bucharest),
                    │            │  canonical URL, derive is_free
                    │            ├─ invalid → events/invalid, dropped
                    │            ├─ past    → skip("past")   → events/past, dropped
                    │            └─ ok      → events/valid, yielded
                    │     stop: spider's own stop condition, max_pages, CLOSESPIDER_TIMEOUT
                    │     FEEDS      → $OUTPUT_DIR/<YYYY-MM-DD>/<spider>.jsonl
                    │     RunSummary → <spider>.summary.json + one JSON log line (§7)
                    │
                    └─ ingest: JSONL of successful spiders → POST /api/ingest/events
                               in batches, header X-Ingest-Token
                               (INGEST_URL unset ⇒ dry-run)
                    exit code ≠ 0 if any spider or the ingest failed → alert (DATA-05 / OPS-04)
```

No global `DEPTH_LIMIT` (removed by S8).

### Responsibilities

| Piece | Does | Does not |
|---|---|---|
| Source spider | Fetch, extract fields, filter Cluj, set `external_id` and `source_category`, decide its own stop condition, call `skip(reason)` for every deliberate drop | Clean, normalize, tag, call the backend. It is **not** forced into a listing → detail shape. |
| `BaseEventSpider` | `make_event()` (validate, normalize, drop past, count), `skip()` (S6), `next_page()` (respects `max_pages`) | Source-specific logic |
| `Event` model | The single place for normalization rules (§5) | I/O |
| `parsing/` | Pure helpers: JSON-LD, text, dates, URLs, `format_price` (S4), `is_free`, `is_cluj` | I/O |
| `RunSummary` | Per-source health: every `events/*` counter, items, errors, reason, duration, failed flag (§7) | Alerting itself |
| `run.py` | Runs spiders, decides success from the summary, calls ingest, sets the exit code | Scheduling (cron does that) |
| `ingest.py` | Batched, retried POST of JSONL files; dry-run without `INGEST_URL` | Dedup (the backend upserts) |
| Backend (BE-02) | Upsert, cross-source dedup, (proposed) geocoding | – |

## 4. Politeness defaults

`settings.py`, overridable per spider via `custom_settings`:

- `ROBOTSTXT_OBEY = True`; identifying user agent `GoClujBot/0.1 (+https://github.com/gocluj)` (env `SCRAPER_USER_AGENT`)
- `CONCURRENT_REQUESTS_PER_DOMAIN = 2`, `DOWNLOAD_DELAY = 1`, AutoThrottle on
- `RETRY_TIMES = 3`, `DOWNLOAD_TIMEOUT = 30`
- `CLOSESPIDER_TIMEOUT = 600` (10 min per spider), `CLOSESPIDER_ERRORCOUNT = 20`
- HTTP cache in development only (`HTTPCACHE_ENABLED=1`)
- No `DEPTH_LIMIT` (removed by S8)

## 5. Event contract

`models.Event` (`extra="forbid"`). Spiders pass raw values; the model normalizes.

| Field | Type | Req. | Set by | Normalization |
|---|---|---|---|---|
| `source_name` | str | yes | `make_event` (spider's `source_name`) | – |
| `source_url` | str | yes | spider | `canonical_url`: drop fragment and `utm_*`, `ica_*`, `fbclid`, `gclid`, `ref` |
| `external_id` | str | **yes, non-empty** (S3) | spider | Stable per-source id; proposed upsert key `(source_name, external_id)` |
| `title` | str | yes | spider | `clean_text`; empty → invalid |
| `description` | str \| None | no | spider | **S2:** `<br>` and closing block tags (`</p>`, `</div>`, `</li>`, ...) → `\n`, `w3lib.html.remove_tags`, then `clean_text(..., multiline=True)`: `\r\n` → `\n`, space runs collapse, lines stripped, at most one blank line kept. |
| `start_at` | datetime | yes | spider | ISO or Romanian text → aware Europe/Bucharest; naive values localized |
| `end_at` | datetime \| None | no | spider | Same as `start_at`. **S1:** date-only `YYYY-MM-DD` → that day 23:59:59 local; `end_at <= start_at` → None; end exactly 23:59:59 on start's local day → None (no real end time) |
| `venue` | `{name, address, city, lat, lng}` | no | spider | Text fields `clean_text`; extra keys forbidden |
| `price_text` | str \| None | no | spider, via `format_price` (S4) | `clean_text`; format "59 - 99 RON", single value when equal |
| `is_free` | bool \| None | no | model | Derived by `detect_is_free(price_text)` when not set ("0 RON", "gratuit", "intrare liberă" → True) |
| `categories` | list[str] | no | – | Empty until DATA-03 tagging |
| `source_category` | str \| None | no | spider (S3) | Raw category hint for DATA-03; not a tag |
| `image_url` | str \| None | no | spider | Card image (MEDIUM size for LiveTickets); absolute http(s) only |
| `image_url_large` | str \| None | no | spider | Larger image for the detail page (LiveTickets ZOOM, at most 1920x960); absolute http(s) only; None for other sources |

## 6. Shared changes (all done)

**Run-breaking** (had to be fixed before trusting any live numbers):

- **S1** (done) - date-only `endDate` dropped today's events: `parse_ro_datetime("2026-11-12")` gives 00:00, so the past check `(end_at or start_at) < now` (`spiders/base.py:54`) dropped every event happening today. The `end_at` validator now sets 23:59:59. Follow-up: when that lands on the start day (iaBilet single-day events: `endDate` = start date) `_finalize` sets `end_at = None` so the UI shows no invented "– 23:59"; such events fall back to `start_at` for the past check and disappear once started (accepted). Multi-day events keep 23:59:59 and stay listed until their last day. An explicit 23:59:59 end on the start day is also dropped (indistinguishable).
- **S8** (done) - the old `DEPTH_LIMIT = 10`: listing page N is depth N-1 and its detail pages depth N, so the events of listing pages past 10 were silently dropped. Removed from `settings.py`.
- **Pagination that never returns an empty page** (source-specific, iaBilet): pages past the end still return a promoted card, so "stop on empty page" never fires. See [iaBilet](sources/iabilet.md).

| # | Change | File | Why / users | Task | Status |
|---|---|---|---|---|---|
| S1 | Date-only end → 23:59:59 local; same-day 23:59:59 end → None; `end_at <= start_at` → None | `models.py` | **Bug:** today's events dropped as past | T2 | done |
| S2 | Description cleaning: `remove_tags` + `clean_text(multiline=True)` | `models.py`, `parsing/text.py` | LiveTickets (HTML), iaBilet (`\r\n` plain text) | T3 | done |
| S3 | `external_id` required non-empty; new `source_category` | `models.py`, `tests/test_models.py` | Upsert key; DATA-03 hint | T4 | done |
| S4 | `format_price(amounts, currency) -> str \| None`; `jsonld._price_text` calls it | `parsing/text.py`, `parsing/jsonld.py` | JSON-LD offers, iaBilet tariffs, LiveTickets min/max | T5 | done |
| S5 | `_address`: don't append city when `streetAddress` already contains it as whole words (accent/case-insensitive; e.g. "…, Cluj-Napoca 400535") | `parsing/jsonld.py` | iaBilet ("…, Cluj-Napoca" + locality "Cluj-Napoca") | T5 | done |
| S6 | `skip(reason, url=None)`: inc `events/<reason>`, DEBUG log; `make_event` uses it for past; docstring: listing → detail is optional | `spiders/base.py` | Every spider's drops; LiveTickets is JSON list + detail | T6 | done |
| S7 | `RunSummary` reports every `events/*` stat, not a hard-coded list | `extensions.py` | New counters/sources need no change there | T6 | done |
| S8 | Remove global `DEPTH_LIMIT` | `settings.py` | **Bug:** truncation past page 10; crawl bounded by stop condition, `max_pages`, `CLOSESPIDER_TIMEOUT` | T6 | done |

## 7. Run health

Counters (Scrapy stat keys):

| Key | Meaning | Set by |
|---|---|---|
| `events/valid` | Emitted | `make_event` |
| `events/invalid` | Failed `Event` validation | `make_event` |
| `events/past` | Already ended | `make_event` via `skip` |
| `events/cancelled` | Cancelled at source | spider `skip` (iaBilet) |
| `events/not_cluj` | Outside Cluj | spider `skip` (LiveTickets) |
| `events/no_city` | Source gives no city, so Cluj cannot be checked | spider `skip` (LiveTickets) |
| `events/no_jsonld` | Detail page without Event JSON-LD | spider `skip` (iaBilet) |
| `events/status_<value>` | Unexpected source status | spider `skip` (LiveTickets) |
| `events/time_slots` | Emitted, but source has time slots | spider (LiveTickets) |

**Failed run** (`extensions.py:46`): `items == 0`, or close reason ≠ `finished` (e.g. `closespider_timeout`, `closespider_errorcount`), or any ERROR log line. `run.py` also fails a spider whose subprocess exits non-zero or writes no summary. Failed spiders' JSONL is not ingested.

**RunSummary writes** one JSON log line and `$OUTPUT_DIR/<date>/<spider>.summary.json` with `event`, `source`, `reason`, `items`, `errors`, `duration_s`, `failed`, and the counters. Every `events/<name>` stat becomes a flat top-level key with the prefix removed (`valid`, `past`, `not_cluj`, ...); `valid`, `invalid` and `past` default to 0 (`extensions.py:33-36`).

## 8. Sources

| Source | Summary | Spec |
|---|---|---|
| iaBilet (`iabilet`) | Server-rendered Cluj listing (~7 pages, ~155 events), Event JSON-LD on detail pages. Stop when `a.btn-more` is absent; take all tariffs from the detail page; skip cancelled. ~3-4 min per run. | [sources/iabilet.md](sources/iabilet.md) |
| LiveTickets (`livetickets`) | Angular SPA; data from public JSON API (`api.livetickets.ro/public/events`, one list, no pagination) + per-event detail. Filter Cluj (city-less items skipped as `no_city`), then detail. Implemented; live run 2026-11-10: 31 events, 33 requests, ~1 min. | [sources/livetickets.md](sources/livetickets.md) |

## 9. Design principles applied

- **DRY where there are two users:** one `Event` model (all normalization), one `format_price`, one `skip()` helper for all drop counters, one `RunSummary` for health.
- **Rejected as premature:** listing/detail template base class or declarative selector config (one HTML source); `JsonApiSpider` base (one user); item pipelines / ItemLoaders (the model does it); shared seen-ids mixin (a set is two lines); per-source YAML config; parallel spider pool; proxy / Retry-After layer; Cluj-filter abstraction beyond `is_cluj`; tagging and geocoding in this phase; storing sold-out status (no contract field).
- **Rule:** add an abstraction when the **second real user** exists, not before.

## 10. Scalability

Adding source 3..6 costs one spider file (~60-120 lines), 2-3 fixtures and one test file. No change to `run.py`, `extensions.py`, `ingest.py` or `models.py` (unless Playwright is needed, which adds a dependency).

| Decision | At ~10 sources / 10x events |
|---|---|
| One subprocess per spider, sequential | Holds for isolation. Runtime adds up (~30-40 min, fine for daily cron). Later: small process pool in `run.py`. |
| JSONL + batched ingest | Holds. ~15k events is tens of MB; `read_events` loads all into memory, stream if that changes. |
| Per-spider time budget | **Breaks** for iaBilet at 10x (~1,600 detail pages ≈ 30 min). Knob: `custom_settings`; later: detail requests only for new ids (needs known ids from the backend). |
| `DEPTH_LIMIT` | **Breaks**; removed (S8). |
| Output `OUTPUT_DIR/<date>/<spider>.jsonl` | Holds; same-day re-runs overwrite; retention is a DevOps task. |
| "Any ERROR = failed run" | Gets noisy; later an error-rate threshold in `RunSummary` (one place). |

## 11. Adding a source (checklist)

1. Check robots.txt, ToS, and whether there is an API, feed or JSON-LD. Record it in [IMPLEMENTATION_PLAN §9](../IMPLEMENTATION_PLAN.md#9-decisions-log) under INV-01.
2. Extraction order: **JSON-LD → JSON API → HTML selectors → Playwright**.
3. Add `gocluj_scraper/spiders/<name>.py` subclassing `BaseEventSpider`; set `name`, `source_name`, `allowed_domains`, start URL(s). Any shape is fine (listing → detail is not required).
4. Set a **stable, non-empty `external_id`** (site id, not a slug that can change).
5. Define a **stop condition that is not "empty page"** (e.g. next-link absent, API has no pagination); keep `max_pages` working through `next_page()`.
6. **Canonicalise URLs before following** (`canonical_url`) and keep a seen-ids set, so tracking query variants are not crawled twice.
7. Filter Cluj as early as possible. Every deliberate drop goes through `self.skip(reason)`; every event through `self.make_event(...)`.
8. Save trimmed real responses to `tests/fixtures/<name>/` (remove secrets and non-JSON-LD scripts).
9. Write `tests/test_<name>.py` with `fake_response`: requests produced, stop condition, field mapping, each skip reason.
10. Develop with `HTTPCACHE_ENABLED=1` and `-a max_pages=1`; per-source tweaks go in `custom_settings`.

## 12. Implementation tasks

| # | Task | Difficulty | Files | Depends on |
|---|---|---|---|---|
| T1 | Doc fixes and this design | routine | docs | – |
| T2 | **Done.** Date-only end rule + `end_at <= start_at` rule, tests (S1) | moderate | `models.py`, `tests/test_models.py`, `tests/test_text.py` | – |
| T3 | **Done.** Description cleaning (S2), tests | routine | `parsing/text.py`, `models.py`, tests | – |
| T4 | **Done.** `external_id` required, `source_category` (S3); fix tests | routine | `models.py`, `tests/test_models.py` | – |
| T5 | **Done.** `format_price` (S4), `_address` city de-dup (S5); tests | routine | `parsing/text.py`, `parsing/jsonld.py`, tests | – |
| T6 | **Done.** `skip` (S6); `RunSummary` all `events/*` (S7); remove `DEPTH_LIMIT` (S8) | routine | `spiders/base.py`, `extensions.py`, `settings.py`, tests | – |
| T7 | **Done.** Save and trim iaBilet fixtures | routine | `tests/fixtures/iabilet/*` | – |
| T8 | **Done.** iaBilet listing: pagination, seen ids, cancelled skip | moderate | `spiders/iabilet.py`, `tests/test_iabilet.py` | T6, T7 |
| T9 | **Done.** iaBilet detail mapping (tariffs, title prefix, breadcrumb category) | moderate | `spiders/iabilet.py`, tests | T2-T5, T8 |
| T10 | **Done.** LiveTickets terms check (INV-01), recorded in IMPLEMENTATION_PLAN §9 | routine (owner) | `docs/IMPLEMENTATION_PLAN.md` | – |
| T11 | **Done.** LiveTickets fixtures + spider | moderate | `spiders/livetickets.py`, `tests/fixtures/livetickets/*`, `tests/test_livetickets.py` | T2-T6, T10 |
| T12 | **Done.** LiveTickets image URL template (R9 in the source spec) | routine | `spiders/livetickets.py`, `models.py` | T11 |
| T13 | **Partly done:** full `run.py` run with ingest verified 2026-11-10 (31 LiveTickets events, re-ingest without duplicates); the iaBilet spider is now implemented (T7-T9). Remaining: iaBilet run, timing, tune `custom_settings` | moderate | settings, spiders | T9, T11 |
| T14 | **Done (2026-11-10):** backend contract test ingests real scraper output | hard (cross-team) | `models.py`, `ingest.py`, tests | PRJ-01, BE-02 |

## 13. Open questions

**Owner**

| # | Question | Proposed default |
|---|---|---|
| O1 | Do LiveTickets terms allow API use? | Answered 2026-11-10: yes, the public API is used (IMPLEMENTATION_PLAN §9) |
| O2 | Do Cluj county events count? | Cluj-Napoca city only. Note: `is_cluj` is a substring test for "cluj" (`parsing/text.py:111`), so it also matches county places; a spider that must exclude them compares the city exactly (see [LiveTickets](sources/livetickets.md), R2). LiveTickets list items without a city are skipped (`no_city`), so Cluj and county events among them are lost (R1). |
| O3 | Keep sold-out events? | Yes |
| O4 | LiveTickets `price_max == 0`: free or unknown? | Unknown (`price_text` None) |
| O5 | Rescheduled events: show the new date only? | Yes |
| O6 | 20 min time limit for iaBilet acceptable? | Yes |

**Backend (PRJ-01 / BE-02)**

| # | Question | Proposed default |
|---|---|---|
| B1 | Upsert key | `(source_name, external_id)`; `source_url` alone breaks when one page lists several dates **Answered:** implemented as proposed (unique key + upsert). |
| B2 | Contract fields | Accept `source_category` and multi-line descriptions **Answered:** accepted; covered by the contract test (T14). |
| B3 | Events that disappear or get cancelled after ingest | Expire when not seen in N runs |
| B4 | Geocoding (DATA-04) | In the backend: needs a persistent venue cache and Nominatim at 1 req/s; the scraper is stateless. LiveTickets already supplies lat/lng. |
| B5 | Auth header and max batch size | `X-Ingest-Token`, batches of 50 (`INGEST_BATCH_SIZE`) **Answered:** `X-Ingest-Token` required (401 without it); response `{received, created, updated}`. |

**Cross-team items still open**

| Item | With | Proposal |
|---|---|---|
| Ingest payload | BE-02, PRJ-01 | `POST /api/ingest/events`, body `{"events": [Event, …]}`, header `X-Ingest-Token`. **Done (2026-11-10):** implemented; open `POST /api/events` removed. |
| Contract drift | Backend | **Covered:** backend contract test with real scraper output (T14). Optional: also commit the JSON schema (`model_json_schema()`) for a scraper-side check. |
| Tagging (DATA-03) | – | Pure function called from `make_event`, keyword lists in a config file; `source_category` as an input hint. |
| Scheduling and alerts | DevOps (OPS-04) | Daily cron runs `docker compose run --rm scraper`; non-zero exit → alert. Per-source health from `*.summary.json` (input for BE-10 source health). |
