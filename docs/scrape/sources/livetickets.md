# LiveTickets spider

| | |
|---|---|
| Source | LiveTickets, https://www.livetickets.ro |
| Spider | `livetickets` (`scrape/gocluj_scraper/spiders/livetickets.py`) |
| Status | Stub today: `parse` and `parse_event` only log a warning |
| Tasks | T10 (terms check), T11 (fixtures + spider), T12 (image URL) |
| Site checked | 2026-11-10 (about 12 polite GETs) |
| Shared material | Model rules, shared changes S1-S8, counters, scalability, checklist: [../scraper-design.md](../scraper-design.md) |

> **BLOCKED on INV-01.** The site's terms on automated access and API reuse have not been read, and robots.txt gives no rules either way (see section 1). Do not implement or run against `api.livetickets.ro` until the owner records the answer in IMPLEMENTATION_PLAN §9 (T10). If the API may not be used, the fallback in the current design is `scrapy-playwright` on `/evenimente`; this spec would then need a rewrite of sections 2-5.

Everything below is the plan for the API route. Statements marked **unverified** have not been checked.

## 1. Site facts

| Topic | Fact |
|---|---|
| Site | `https://www.livetickets.ro/*` is an Angular SPA shell: no event data, no JSON-LD |
| robots | `www.livetickets.ro/robots.txt` returns the same HTML shell (no rules). `api.livetickets.ro/robots.txt` is 404. Scrapy treats both as allow-all, so `ROBOTSTXT_OBEY` does not protect us here |
| Terms | Not read (INV-01) |
| Client routes | `evenimente`, `evenimente/:cat`, `bilete/:url`, `event/:url`, `e/:url`, `cautare/:src`, `organizator/:org` |
| Public event URL | `https://www.livetickets.ro/bilete/<url>` |
| API base | `https://api.livetickets.ro` |
| Used endpoint 1 | `GET /public/events`: one JSON array, no pagination, no past events |
| Used endpoint 2 | `GET /public/events/getbyurl?url=<slug>`: one event with venue details |
| Volume (2026-11-10) | 311 items; 31 with `city == "Cluj-Napoca"`; 16 with empty `city` |
| Seen, not used | `/public/events/getbyid?id=`, `/public/events/categories` (returns Artist-type tags, not categories), `/public/events-home-v2`, `/public/events/get-tickets?url=` |
| Server-side filters | None found; query parameters were not tested (unverified) |

Empty-city items include a Cluj venue ("MATTER") and a Cluj-county one (venue text ends "Valea Drăganului, Cluj").

## 2. Request flow

```
start_requests ──► GET /public/events  (311 items)
                        │ parse
                        ├─ is_cluj(city)        ─┐
                        ├─ city empty           ─┴─► GET /public/events/getbyurl?url=<slug>
                        └─ other city  ─► skip("not_cluj")           │ parse_event
                                                                     ├─ not Cluj-Napoca ─► skip("not_cluj")
                                                                     ├─ status != online ─► skip("status_<value>")
                                                                     ├─ has_time_slots   ─► count + WARNING, still emit
                                                                     └─ make_event(**fields) ─► yield
```

1. `start_requests`: one request to `https://api.livetickets.ro/public/events`, callback `parse`.
2. `parse(response)`: `items = response.json()`. For each item:
   - `is_cluj(item["city"])` true, or `city` empty: yield a request to `getbyurl?url=<item["url"]>` with `cb_kwargs={"item": item}`.
   - Otherwise `self.skip("not_cluj")` (shared, S6).
   - Empty list or no Cluj item: log ERROR (the run then fails on 0 items, section 7).
3. `parse_event(response, item)`: `d = response.json()`.
   - City check on `d["location"]["city"]` (see the `is_cluj` note below); fail: `skip("not_cluj")`.
   - `d["status"] != "online"`: `skip("status_<value>")`. The allowlist is provisional (only "online" has been seen).
   - `d["has_time_slots"]` true: increment `events/time_slots`, log WARNING, still emit using the list `start_date` / `end_date`.
   - Build fields (section 4) and `yield` the result of `self.make_event(**fields)` when not `None`.

Helpers reused: `is_cluj` (`parsing/text.py:77`), `make_event` (`spiders/base.py:33`), `localize` (called by the model's date validators for naive datetimes, `parsing/text.py:82`). To be added by the shared tasks: `skip` (S6, T6), `format_price` (S4, T5), HTML description cleaning (S2, T3), required `external_id` and `source_category` (S3, T4), end-date rules (S1, T2). Do not duplicate them in the spider.

### What `is_cluj` actually matches

`is_cluj(text)` is `bool(text) and "cluj" in _fold(text)`: accent- and case-insensitive substring test for "cluj".

- Matches "Cluj-Napoca", "Cluj", and any text containing "cluj", including "Valea Drăganului, Cluj". It does **not** distinguish the city from the county.
- Does **not** match "MATTER" or any Cluj venue named without the word. The venue name alone cannot identify Cluj.
- Empty or `None` input returns falsy, so empty-city items must be handled explicitly (the detail request above), not by `is_cluj`.

So `is_cluj` is fine as the cheap pre-filter on list `city`, but it cannot implement "Cluj-Napoca city only" (open question O2 in the design doc) on the detail response. The detail check should compare the folded city to `cluj-napoca` (spider-local, using `strip_accents`), see rule R2. What the detail `location.city` contains for the Valea Drăganului item is **unverified**.

## 3. API field reference

### List item (`/public/events`)

| Field | Example | Used for |
|---|---|---|
| `url` | slug, e.g. `<name>-<n>` | detail request; `source_url` |
| `event_id` | UUID | `external_id` |
| `organizer_id` | number, e.g. `2477` | not used |
| `name` | event title | `title` |
| `price_min`, `price_max` | numbers | `price_text` |
| `location` | venue name string | venue fallback |
| `start_date`, `end_date` | `"2026-11-10T22:00:00"` (naive local) | `start_at`, `end_at` |
| `city` | `"Cluj-Napoca"` or empty | pre-filter |
| `country` | string | not used |
| `currency` | `{id, code, name, symbol}` | `code` goes into `price_text` |
| `description` | HTML with entities, `<br />`, `&nbsp;` | `description` |
| `images[]` | `path` like `<slug>/Background_MEDIUM.jpg` | `image_url` (blocked, R9) |
| `organizer_followers` | number | never stored |

### Detail (`/public/events/getbyurl`)

| Field | Example | Used for |
|---|---|---|
| `id` | equals list `event_id` | consistency check only |
| `status` | `"online"` (only value seen) | filter |
| `location{name, address, city, zip, country, lat, lng}` | | `venue` |
| `item_tags[]` | types City / Website / Promoter / Artist | not used (no category type seen) |
| `organizer{name, url}` | | not used |
| `has_time_slots`, `time_slots` | | counter, R5 |
| `ticket_count`, `remaining_count` | | not used (sold-out status is not stored) |
| `price_max` | number | repeats the list value |
| `company` | contains payment keys | **never store or log** (R11) |

## 4. Field mapping

| Event field | Source | Rule |
|---|---|---|
| `source_name` | class attribute `"LiveTickets"` | set by `make_event` |
| `external_id` | list `event_id` | UUID; slugs get numeric suffixes and are not a stable key |
| `source_url` | `https://www.livetickets.ro/bilete/<url>` | the model canonicalizes it |
| `title` | `name` | |
| `description` | `description` | HTML stripped by the model (S2) |
| `start_at`, `end_at` | `start_date`, `end_date` | naive local strings; the model localizes to Europe/Bucharest |
| `venue.name` | detail `location.name`, fallback list `location` | |
| `venue.address`, `city`, `lat`, `lng` | detail `location.*` | no geocoding needed |
| `price_text` | `format_price([price_min, price_max], currency["code"])` | `None` when `price_max == 0` (R7) |
| `is_free` | not set | derived from `price_text`, so `None` for unknown price |
| `image_url` | not set | until T12 |
| `source_category` | not set (`None`) | no real category field known |
| `categories` | not set | DATA-03 |

## 5. Rules for edge cases

| # | Case | How the API shows it | Spider does |
|---|---|---|---|
| R1 | Empty city | 16 of 311 list items have `city == ""`, including Cluj venues | Request the detail and decide on `location.city` |
| R2 | Cluj county vs city | A county venue's text ends in ", Cluj"; `is_cluj` matches it | Proposed default: keep Cluj-Napoca only (compare folded detail city to `cluj-napoca`). Detail city value for county items is unverified |
| R3 | Venue named without "Cluj" ("MATTER") | List `city` empty, name has no "cluj" | Same as R1; never filter on venue name |
| R4 | Non-online status | Detail `status`; only "online" seen, other values unverified | `skip("status_<value>")`; allowlist `{"online"}` until other values are known |
| R5 | Time slots | Detail `has_time_slots` true; `time_slots` structure unseen | Count `events/time_slots`, WARNING, emit one event from `start_date` / `end_date` |
| R6 | Repeated events | Separate items, each with its own slug and `event_id` | One event per item; no merge |
| R7 | Price 0 | 7 items have `price_max == 0`, mostly club nights; meaning (free vs. no online price) unverified | `price_text = None`, so `is_free` stays `None` (unknown). Do not claim "free" |
| R8 | Ends after midnight | `end_date` always set; parties often end 05:00 next day | Pass through unchanged. Past check uses `end_at`, so an event still running at 01:00 is kept |
| R9 | Image | `images[].path` is relative; CDN prefix unknown (`imageRoot` is `https://livetickets-cdn.azureedge.net` but two guessed paths returned 404) | Leave `image_url` unset until T12 |
| R10 | Category | No real category field; `/public/events/categories` returns Artist tags | `source_category = None` |
| R11 | Sensitive data | Detail `company` contains payment keys | Never read it into a variable that is logged, never store it, never save it in a fixture. Also not stored: `organizer_followers` |
| R12 | HTML description | Entities, `<br />`, `&nbsp;` | Pass raw to the model (S2); do not strip in the spider |

## 6. Settings and budget

- `allowed_domains = ["livetickets.ro"]` already covers `api.livetickets.ro` (subdomains are allowed). No `custom_settings`; shared defaults apply.
- Requests: 1 list + 31 Cluj + 16 empty-city = about 48. At the default 1 s delay: under 1 minute, far below the 600 s budget.
- **No pagination.** `/public/events` returns everything in one array, so `next_page` and `max_pages` are not used. If the list grows or the API starts truncating, the spider cannot tell. Mitigation: log the item count; revisit if the count approaches a round number such as 500 or 1000 (the API's limit is unknown). A list that no longer fits one response is a reason to re-read the API, not to add pagination blindly.

## 7. Failure modes

Counters and the `RunSummary` rules are defined in [../scraper-design.md](../scraper-design.md).

| Failure | Shows in the run summary |
|---|---|
| API shape change (missing key) | `KeyError` in callback, ERROR logged, errors > 0, run failed |
| Non-JSON response (HTML, error page) | `response.json()` raises, ERROR, run failed |
| HTTP 4xx/5xx after retries | ERROR, run failed |
| Zero Cluj items | items = 0, run failed |
| Detail fields invalid (empty title, bad date) | `events/invalid` rises; WARNING per item |
| Non-"online" status appears | `events/status_<value>` rises; no failure, visible in the summary |
| `has_time_slots` events | `events/time_slots` rises; events still emitted |
| Access blocked (e.g. 403) | Same as HTTP error; stop and re-check INV-01 |

## 8. Fixtures and tests (T11)

Fixtures in `scrape/tests/fixtures/livetickets/` (loaded with `fake_response(url, fixture=...)`; names ending `.json` give a `TextResponse`, see `tests/conftest.py`):

- `events.json`: about 4 trimmed list items: Cluj-Napoca, Bucharest, empty-city "MATTER", one with price 0/0. Trim `description`.
- `event_detail.json`: one detail response. **Remove `company` entirely** before committing; check with a grep that no key or secret-looking string remains.

Tests in `scrape/tests/test_livetickets.py`:

- `parse`: Cluj and empty-city items yield detail requests, Bucharest does not (`events/not_cluj`).
- `parse_event`: field mapping (external_id UUID, source_url, venue with lat/lng, `price_text` like "50 - 120 RON", naive dates localized).
- Price 0/0 gives `price_text None` and `is_free None`.
- Non-"online" status dropped with `events/status_<value>`.
- Detail city "Cluj" (county) vs "Cluj-Napoca" (R2), and a detail whose city is not Cluj.
- `has_time_slots` counts `events/time_slots` and still emits.
- Event ending after midnight is kept.

## 9. Unverified items and open questions

| Item | Proposed default |
|---|---|
| Terms on automated access and API reuse (INV-01) | Blocks T11. Owner records the answer in IMPLEMENTATION_PLAN §9 (T10). If not allowed: `scrapy-playwright` on `/evenimente` |
| Do Cluj-county events count? | No: Cluj-Napoca city only (owner decision, O2 in the design doc) |
| Detail `location.city` for county and empty-city items | Check when building fixtures; until then R2 is a proposal |
| Meaning of `price_max == 0` | Unknown (`price_text None`), not free (O4 in the design doc) |
| `status` values other than "online" | Allowlist `{"online"}`; the counters will reveal others |
| `time_slots` structure and whether `start_date` covers them | Emit one event, count and warn |
| Image URL path prefix | Leave `image_url` unset; T12 reads it from the browser network tab |
| Real event-category field | None; `source_category` stays `None` |
| Server-side city filter or query parameters | Not tested; use `is_cluj` + detail check. Test only after INV-01 |
| API limits (max list size, rate limits) | Stay at about 48 requests per run, shared politeness settings |
| Slug stability | Irrelevant: `external_id` is the UUID |
