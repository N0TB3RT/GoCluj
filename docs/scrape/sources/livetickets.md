# LiveTickets spider

| | |
|---|---|
| Source | LiveTickets, https://www.livetickets.ro |
| Spider | `livetickets` (`scrape/gocluj_scraper/spiders/livetickets.py`) |
| Status | Implemented (T11, commit 4403e5e); one live run on 2026-11-10 |
| Tasks | T10 (terms check, done), T11 (fixtures + spider, done), T12 (image URL, done) |
| Site checked | 2026-11-10 (real API capture and one live run) |
| Shared material | Model rules, shared changes S1-S8, counters, scalability, checklist: [../scraper-design.md](../scraper-design.md) |

> INV-01 resolved on 2026-11-10: the owner decided to use the public API; terms and accepted risks are in IMPLEMENTATION_PLAN §9.
> The `scrapy-playwright` fallback is no longer planned.

Statements marked **unverified** have not been checked.

## 1. Site facts

| Topic | Fact |
|---|---|
| Site | `https://www.livetickets.ro/*` is an Angular SPA shell: no event data, no JSON-LD |
| robots | `www.livetickets.ro/robots.txt` returns the same HTML shell (no rules). `api.livetickets.ro/robots.txt` is 404. Scrapy treats both as allow-all, so `ROBOTSTXT_OBEY` does not protect us here |
| Terms | `https://www.livetickets.ro/legal/termeni-si-conditii`: nothing on bots or API use; §11 restricts content reuse to personal use, with exceptions. Full descriptions are an accepted risk (IMPLEMENTATION_PLAN §9) |
| Client routes | `evenimente`, `evenimente/:cat`, `bilete/:url`, `event/:url`, `e/:url`, `cautare/:src`, `organizator/:org` |
| Public event URL | `https://www.livetickets.ro/bilete/<url>` |
| API base | `https://api.livetickets.ro` |
| Response format | XML unless the request sends `Accept: application/json`; the spider sends it on both requests |
| Used endpoint 1 | `GET /public/events`: one JSON array, no pagination, no past events |
| Used endpoint 2 | `GET /public/events/getbyurl?url=<slug>`: one event with venue details |
| Volume (2026-11-10) | 310 items; 31 with `city == "Cluj-Napoca"`; 15 without a city |
| Seen, not used | `/public/events/getbyid?id=`, `/public/events/categories` (returns Artist-type tags), `/public/events-home-v2`, `/public/events/get-tickets?url=` |
| Server-side filters | None found; query parameters were not tested (unverified) |

City-less list items have no `city` and no `country` key at all (not an empty string). Their detail `location` is only `{name, lat: 0.0, lng: 0.0}`: no city, no address, so a detail request cannot classify them. On 2026-11-10 they included at least two real Cluj events (venue "MATTER", and "Fuel @ Cluj Napoca, Secret Location") and the Cluj-county item "MOX 2027" (venue text ends "Valea Drăganului, Cluj").

## 2. Request flow

```
start() ──► GET /public/events  (Accept: application/json)
                  │ parse
                  ├─ no city           ─► skip("no_city")
                  ├─ other city        ─► skip("not_cluj")
                  └─ is_cluj(city)     ─► GET /public/events/getbyurl?url=<slug>
                                                │ parse_event
                                                ├─ not Cluj-Napoca  ─► skip("not_cluj")
                                                ├─ status != online ─► skip("status_<value>")
                                                ├─ has_time_slots   ─► count + WARNING, still emit
                                                └─ make_event(**fields) ─► yield
```

1. `start()` (async, Scrapy 2.13; not `start_requests`): one request to `https://api.livetickets.ro/public/events` with `Accept: application/json`, callback `parse`.
2. `parse(response)`: `items = response.json()`. For each item:
   - No `city` (missing or empty): `self.skip("no_city")`, no detail request.
   - `is_cluj(item["city"])` false: `self.skip("not_cluj")` (shared, S6).
   - Otherwise: yield a request to `getbyurl?url=<url-encoded slug>` with the JSON header and `cb_kwargs={"item": item}`.
   - Logs the item and candidate counts at INFO; no candidates: log ERROR (the run then fails on 0 items, section 7).
3. `parse_event(response, item)`: `detail = response.json()`.
   - Folded `detail["location"]["city"]` must equal `cluj-napoca` (R2); otherwise `skip("not_cluj")`.
   - `detail["status"] != "online"`: `skip("status_<value>")`. The allowlist is provisional (only "online" has been seen).
   - `has_time_slots` true: increment `events/time_slots`, log WARNING, still emit using the list `start_date` / `end_date`.
   - Build fields (section 4) and `yield` the result of `self.make_event(**fields)` when not `None`.

Helpers reused: `is_cluj`, `strip_accents`, `format_price` (`parsing/text.py`, S4), `make_event` and `skip` (`spiders/base.py`, S6), `localize` (called by the model's date validators for naive datetimes). Already done in the `Event` model: HTML description cleaning (S2), required non-empty `external_id` and `source_category` (S3), end-date rules (S1). The spider does not duplicate them.

### What `is_cluj` actually matches

`is_cluj(text)` is `bool(text) and "cluj" in _fold(text)`: accent- and case-insensitive substring test for "cluj".

- Matches "Cluj-Napoca", "Cluj", and any text containing "cluj". It does **not** distinguish the city from the county.
- Does **not** match "MATTER" or any Cluj venue named without the word.

So `is_cluj` is the cheap pre-filter on list `city`; the detail check compares the folded city to `cluj-napoca` (spider-local `_is_cluj_napoca`, using `strip_accents`), see R2.

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
| `city` | `"Cluj-Napoca"`; key missing on city-less items | pre-filter |
| `country` | string; key missing on city-less items | not used |
| `currency` | `{id, code, name, symbol}` | `code` goes into `price_text` |
| `description` | HTML with entities, `<br />`, `&nbsp;` | `description` |
| `images[]` | `path` like `<slug>/Background_MEDIUM.jpg` | `image_url` (R9) |
| `organizer_followers` | number | never stored |

### Detail (`/public/events/getbyurl`)

Keys seen: `id, name, start_date, end_date, ticket_count, remaining_count, seating, description, currency, created, url, price_max, location, item_tags, allow_refunds, images, status, organizer, has_time_slots, time_slots`, sometimes `fb_pixel`. No `company` key in 4 captured details.

| Field | Example | Used for |
|---|---|---|
| `status` | `"online"` (only value seen) | filter |
| `location{name, address, city, zip, country, lat, lng}` | city-less items: only `{name, lat: 0.0, lng: 0.0}` | `venue` |
| `item_tags[]` | types Website, Promoter, City, Artist, Category, Subcategory | first `Category` name is `source_category` |
| `has_time_slots`, `time_slots` | `false` and `[]` in all captured details | counter, R5 |
| `price_min`, `price_max` | `price_min` null; `price_max` can differ from the list (list 30-35, detail 40; reason unverified) | not used; list values win |
| `organizer`, `fb_pixel` | contain personal or tracking data | **never store or log** (R11) |
| `ticket_count`, `remaining_count` | | not used (sold-out status is not stored) |

## 4. Field mapping

| Event field | Source | Rule |
|---|---|---|
| `source_name` | class attribute `"LiveTickets"` | set by `make_event` |
| `external_id` | list `event_id` | UUID; slugs get numeric suffixes and are not a stable key |
| `source_url` | `https://www.livetickets.ro/bilete/<url>` | the model canonicalizes it |
| `title` | list `name` | |
| `description` | list `description` | HTML stripped by the model (S2) |
| `start_at`, `end_at` | list `start_date`, `end_date` | naive local strings; the model localizes to Europe/Bucharest |
| `venue.name` | detail `location.name`, fallback list `location` | |
| `venue.address`, `city` | detail `location.*` | no geocoding needed |
| `venue.lat`, `lng` | detail `location.lat/lng` | 0.0 means unknown: `None` unless both are non-zero |
| `price_text` | `format_price([price_min, price_max], currency["code"])` from the list | `None` when list `price_max` is 0 or missing (R7) |
| `is_free` | not set | derived from `price_text`, so `None` for unknown price |
| `image_url` | `IMAGE_ROOT` + `images[].path` of a Background image (detail first, then list item), ranked MEDIUM, SQUARE, ZOOM | R9 |
| `image_url_large` | Same as `image_url` but ranked ZOOM, MEDIUM, SQUARE | R9 |
| `source_category` | name of the first detail `item_tags` entry with `type == "Category"`, else `None` | raw hint only (R10) |
| `categories` | not set | DATA-03 |

## 5. Rules for edge cases

| # | Case | How the API shows it | Spider does |
|---|---|---|---|
| R1 | No city | 15 of 310 list items have no `city` key; the detail has no city either | `skip("no_city")` in `parse`, no detail request. Known loss: real Cluj events (see section 1) |
| R2 | Cluj county vs city | `is_cluj` matches any text containing "cluj" | Keep Cluj-Napoca only: folded detail `location.city == "cluj-napoca"`. In practice the county item seen (MOX 2027) is city-less, so it stops at R1 |
| R3 | Venue named without "Cluj" ("MATTER") | List item is city-less | Covered by R1; never filter on venue name |
| R4 | Non-online status | Detail `status`; only "online" seen, other values unverified | `skip("status_<value>")`; allowlist `{"online"}` until other values are known |
| R5 | Time slots | `has_time_slots` false in all captured details; `time_slots` structure unseen | Count `events/time_slots`, WARNING, emit one event from `start_date` / `end_date` |
| R6 | Repeated events | Separate items, each with its own slug and `event_id` | One event per item; no merge |
| R7 | Price 0 | Some items have `price_max == 0`, mostly club nights; meaning (free vs. no online price) unverified | `price_text = None`, so `is_free` stays `None` (unknown). Do not claim "free" |
| R8 | Ends after midnight | `end_date` always set; parties often end 05:00 next day | Pass through unchanged. Past check uses `end_at`, so an event still running at 01:00 is kept |
| R9 | Image | `images[].path` is relative. Verified 2026-11-10: `https://livetickets-cdn.azureedge.net/itemimages/{path}` returns 200 without token or referrer (wrong path: 404). `token` is only a cache-buster. Detail sizes: Background SQUARE/ZOOM/MEDIUM, Ticket SQUARE/REGULAR/THUMB; declared width/height are upper bounds (fit inside, not cropped), so the frontend uses `object-fit` | Background only, preferring MEDIUM, then SQUARE, ZOOM, any; never use `token`. The model keeps only absolute http(s) URLs |
| R10 | Category | `Category` tags exist in detail `item_tags`; live run: 16 of 31 had none; values "concert" (6), "Trending events" (3), "divertisment" (2), "Evenimente recomandate" (2), "art" (1), "open bar" (1) | `source_category` = first Category name. Some values are promotional labels, not genres: DATA-03 treats it as a raw hint |
| R11 | Sensitive data | Detail `fb_pixel`; `item_tags` entries carry `ga_id`, `fb_pixel`, `tiktok_pixel`, `contactEmail`; `organizer.contactEmail` | The spider reads only the keys in section 4; never store, log or commit these. Fixtures were stripped (tags reduced to `id, url, name, type`, organizer to `name, url`, image `token` removed). Also not stored: `organizer_followers` |
| R12 | HTML description | Entities, `<br />`, `&nbsp;` | Pass raw to the model (S2); do not strip in the spider |
| R13 | Coordinates 0.0 | `lat`/`lng` 0.0 means unknown (2 of 31 in the live run) | Store `None` |

## 6. Settings and budget

- `allowed_domains = ["livetickets.ro"]` covers `api.livetickets.ro` (subdomains are allowed). No `custom_settings`; shared defaults apply.
- Requests: 1 list + 31 Cluj details (plus the robots.txt 404). Live run 2026-11-10: 33 requests, 56.5 s, far below the 600 s budget.
- **No pagination.** `/public/events` returns everything in one array. If the list grows or the API starts truncating, the spider cannot tell. Mitigation: the item count is logged; revisit if it approaches a round number such as 500 or 1000 (the API's limit is unknown).

Live run summary (2026-11-10): `items 31, valid 31, invalid 0, past 0, no_city 15, not_cluj 264, errors 0, failed false`. All 31 had a price; 1 had no description; no HTML left in descriptions.

## 7. Failure modes

Counters and the `RunSummary` rules are defined in [../scraper-design.md](../scraper-design.md).

| Failure | Shows in the run summary |
|---|---|
| API shape change (missing key) | `KeyError` in callback, ERROR logged, errors > 0, run failed |
| XML instead of JSON (missing `Accept: application/json`) or other non-JSON response | `response.json()` raises, ERROR, run failed |
| HTTP 4xx/5xx after retries | ERROR, run failed |
| Zero Cluj candidates | ERROR in `parse`; items = 0, run failed |
| City-less list items | `events/no_city` rises; no failure (15 on 2026-11-10) |
| Detail fields invalid (empty title, bad date) | `events/invalid` rises; WARNING per item |
| Non-"online" status appears | `events/status_<value>` rises; no failure, visible in the summary |
| `has_time_slots` events | `events/time_slots` rises; events still emitted |
| Access blocked (e.g. 403) | Same as HTTP error; stop and re-check INV-01 |

## 8. Fixtures and tests (T11)

Fixtures in `scrape/tests/fixtures/livetickets/` (stripped as described in R11):

- `events.json`: 5 list items: two Cluj-Napoca, one București with price 0, two city-less (one is MOX 2027).
- `event_detail.json`: one detail response.

`scrape/tests/test_livetickets.py` has 16 tests. Test dates are overridden with future dates so the tests do not expire. Covered: the list request and its JSON header; `parse` yields detail requests for Cluj only (`no_city`, `not_cluj`), URL-encodes the slug, logs ERROR on an empty list; `parse_event` field mapping, HTML description cleaning, price 0 not free, missing currency and price, non-"online" status, county city and missing city rejected, city case and whitespace accepted, time slots counted and emitted, overnight event kept, zero coordinates become `None`, no Category tag.

## 9. Resolved and open questions

| Item | Status |
|---|---|
| Terms on automated access and API reuse (INV-01) | Resolved 2026-11-10: use the public API (IMPLEMENTATION_PLAN §9) |
| Do Cluj-county events count? | No: Cluj-Napoca city only (O2 in the design doc) |
| Detail `location.city` for city-less items | Verified: no city. Skipped as `no_city` |
| Real event-category field | Verified: `Category` tags in `item_tags` (R10) |
| Recover city-less Cluj events | Open, not implemented: match the list `location` against venue names seen with city Cluj-Napoca in the same run, or `is_cluj` on the title |
| Meaning of `price_max == 0` | Open: unknown (`price_text None`), not free (O4 in the design doc) |
| Why detail `price_max` differs from the list | Open; the spider uses the list values |
| `status` values other than "online" | Open; allowlist `{"online"}`, the counters will reveal others |
| `time_slots` structure and whether `start_date` covers them | Open; emit one event, count and warn |
| Image URL path prefix | Resolved 2026-11-10 (T12): `.../itemimages/{path}` (R9) |
| Server-side city filter or query parameters | Open; not tested |
| API limits (max list size, rate limits) | Open; about 33 requests per run, shared politeness settings |
| Credit line / shorter descriptions | Open; needed if the project goes public (IMPLEMENTATION_PLAN §9) |
| Slug stability | Irrelevant: `external_id` is the UUID |

## 10. What still needs fixing

Findings from the first live run (2026-11-10), in priority order. The first three need work; the last two are already handled and are listed so nobody undoes them.

| # | Finding | State | What to do |
|---|---|---|---|
| F1 | **City-less events are lost.** 15 of 310 list items have no city, and their detail has none either, so they cannot be confirmed as Cluj. Counted under `events/no_city`. At least two real Cluj events were lost from that day's list (one at MATTER, one "secret location" party) | To fix | Recover them by matching the list `location` against venue names seen with city Cluj-Napoca in the same run, or by `is_cluj` on the title. Add a fixture for each case. Until then, watch `no_city` in the run summary |
| F2 | **`source_category` is unreliable.** 16 of 31 events had no Category tag, and some values are promotional labels ("Trending events", "Evenimente recomandate"), not genres (R10) | To fix | Skip the known promotional labels and take the next Category tag, or leave this to categorisation (DATA-03), which must treat the field as a raw hint |
| F3 | **Prices differ between list and detail** (for example 35 vs 40 RON max; detail `price_min` is null). The spider uses the list values; the reason is unknown | To investigate | Compare both values with the price shown on a few event pages, then keep the source that matches |
| F4 | The API returns XML by default; the first live run failed on this | Handled | Keep `Accept: application/json` on both requests (`JSON_HEADERS`); the tests assert it |
| F5 | No `company` block appeared, but details carry tracking ids and organizer contact emails (R11) | Handled | The spider never reads them and the fixtures are stripped. Whenever a fixture is added or refreshed, check that `git grep -n -i -E "company|secret|token|pixel|email|password" -- scrape/tests/fixtures/livetickets` returns nothing |
| F6 | The detail page uses the same MEDIUM image as the card; it can be small (e.g. 363x450) and looks soft when enlarged | Handled | The detail page uses ZOOM through the new `image_url_large` field; the frontend shows images with object-fit contain plus a blurred backdrop |
