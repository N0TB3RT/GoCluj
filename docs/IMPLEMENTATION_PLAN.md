# GoCluj – Implementation Plan

> Living document. Last updated: 2026-11-10.
> Ship target: **mid-January 2027** (about 10 weeks from now).
> Detailed per-team docs (`docs/devops/`, `docs/scrape/`, `docs/backend/`, `docs/frontend/`) will be added as features get built.

**Guiding principle: keep it simple.** Pick the boring, proven option. Timebox investigations. Build the core first, then social, then AI. Anything not required for launch goes to [After launch](#8-after-launch-backlog).

---

## 1. End goal

By **mid-January 2027**, GoCluj is live on a public HTTPS URL.

**Discover** (Must):
- a feed of **upcoming events in Cluj-Napoca**, refreshed **daily** from **at least 4 sources**,
- filters by **category**, **date** (today, this weekend, date range) and **free**, plus text **search**,
- events shown as **pins on a map**,
- an event page that **links back to the original source** (tickets / RSVP).

**Personal** (Must, except where marked):
- **accounts**, with events saved as **Favorite** or **Going** and listed in **"My events"**,
- **Google sign-in** alongside email + password (Should),
- **notifications** (Should): in-app, **email** (friend requests, hangout invites, reminders before Going events) and **web push**,
- the app is **installable as a PWA** on mobile, with push support and an offline view of saved events (Should),
- **English UI** next to Romanian (i18n) (Could).

**Social** (Should):
- **friends**: send, accept and remove friend requests,
- see **which events your friends are going to**,
- **hangouts**: plan a group outing to an event, invite friends, collect yes/maybe/no answers, and leave short comments,
- **real-time chat** inside a hangout (Could; otherwise the comments stay).

**Admin** (Should):
- an **admin panel** for moderating events (hide, edit, merge duplicates, re-tag), monitoring scraper/source health, and managing users.

**AI** (Could, stretch):
- a **"For you"** feed ranked by your interests (picked at sign-up, then learned from favorites, going and hangouts),
- **"Ask GoCluj"**: describe what you feel like doing in plain language (e.g. *"ceva chill vineri seara, sub 50 lei"*) and get matching events, each with a short reason.

**Operations** (Must):
- runs on a **shared environment** with automatic deploys from `main`,
- scrapers run **unattended once per day**,
- the database is **backed up nightly**.

**Priorities:**
- **Must** blocks the launch.
- **Should** is expected but can be simplified if time is short.
- **Could** ships only if it is stable on staging at the **S4 checkpoint** (start of S5). Otherwise it moves to the backlog.

**Out of scope for launch:** only what is listed in [After launch](#8-after-launch-backlog).

---

## 2. Current state

| Area | What exists |
|---|---|
| Infra | `docker-compose.yml` with Postgres 15, pgAdmin, backend, frontend, scraper |
| Backend | FastAPI `app/` package; token-protected `POST /api/ingest/events` (upsert on `(source_name, external_id)`); `GET /api/events` (paginated, upcoming only), `GET /api/events/{id}`, `GET /api/categories`; CORS from `CORS_ORIGINS`; pytest incl. a contract test with real scraper output. See `backend/README.md` |
| Database | Alembic migrations are the only schema source (run on backend start); `data/schema1.sql` removed |
| Data | Scrapy in `scrape/`; LiveTickets spider live and ingesting (incl. `image_url`); iaBilet still a stub |
| Frontend | PRJ-00 done; event cards with images, source label, date ranges and "Încarcă mai multe"; detail page `/evenimente/:id` with a link to the source |

Verified end to end on 2026-11-10: fresh DB via Alembic → `docker compose run --rm scraper` ingested 31 LiveTickets events (all with images) → re-ingest created no duplicates → frontend shows cards and the detail page.

Known gaps (fixed by the Epics below):

- ~~The schema is defined twice and there are no migrations.~~ Resolved (BE-01).
- ~~`backend/Dockerfile` ignores `requirements.txt`, versions not pinned.~~ Resolved (OPS-01).
- ~~`POST /api/events` is open to anyone.~~ Resolved: removed, ingest needs `X-Ingest-Token` (BE-02).
- ~~Compose passes `REACT_APP_API_URL`.~~ Resolved: removed (OPS-01).
- The compose settings are dev-only (`--reload`, public DB and pgAdmin ports, bind mounts). → OPS-01, OPS-03
- No venue, source, friendship or hangout entities; venue and source are flat columns on `events`. → DATA-04, BE-01

---

## 3. Architecture

```
  Event sources (ticketing sites, venues, city agenda)
                 │  HTTP (polite, once per day)
                 ▼
  ┌──────────────────────────────┐
  │ Scraper (Scrapy, cron)       │  fetch → parse → normalize → tag → JSONL file
  └──────────────┬───────────────┘
                 │  ingest step: POST /api/ingest/events  (token-protected, batched)
                 ▼
  ┌──────────────────────────────┐        ┌──────────────┐
  │ Backend (FastAPI)            │◄──────►│ PostgreSQL   │
  │  - public events API         │        └──────────────┘
  │  - auth, favorites           │
  │  - friends, hangouts         │        ┌──────────────┐
  │  - recommendations, AI       │───────►│ LLM API      │  (AI-02 only)
  │  - admin, notifications      │        └──────────────┘
  │                              │───────►  Email provider · Web Push (VAPID)
  └──────────────┬───────────────┘
                 │  REST/JSON
                 ▼
  ┌──────────────────────────────┐
  │ Frontend (React PWA, Vite)   │  feed · map · my events · friends · hangouts · AI · admin
  └──────────────────────────────┘
```

Everything runs as docker compose services on one host, with no queues. Social updates are fetched on page load, and a light polling interval drives the notification badge. Emails and push are sent from the backend: directly for instant ones, and from a small daily cron job for reminders. The only websocket is the optional hangout chat (BE-12). The LLM is an external API called only from the backend, so the API key never reaches the browser.

**Default stack** (change only with a reason, written down in section 9):

| Layer | Choice |
|---|---|
| Scraping | Scrapy (one spider per source, JSONL output + separate ingest step). `scrapy-playwright` only for sources that need JavaScript. See [`docs/scrape/scraper-design.md`](scrape/scraper-design.md) |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic v2, pytest |
| Database | PostgreSQL 15 (with `unaccent` for search) |
| Frontend | React + Vite, React Router, TanStack Query, Tailwind CSS, Leaflet (OpenStreetMap tiles) |
| Geocoding | Nominatim (OSM) with a local venue cache |
| Auth | Email + password, bcrypt, JWT + Google OAuth (Authlib) |
| Email | A transactional email provider with a free tier (e.g. Brevo, Resend) |
| PWA / push | `vite-plugin-pwa`, Web Push with VAPID keys (`pywebpush`) |
| i18n | `react-i18next` (only if FE-12 is picked up) |
| AI | Decided in INV-03. Default: a hosted LLM API (e.g. Claude) using a small, cheap model |
| CI/CD | GitHub Actions |
| Hosting | Decided in INV-02. Default: one VPS running docker compose, with Caddy for HTTPS |

---

## 4. Epics

### 4.1 Summary

| ID | Title | Team | Priority | Sprint | Depends on |
|---|---|---|---|---|---|
| PRJ-00 | Foundations (walking skeleton) | All | Must | **S0** | – |
| INV-01 | Event sources investigation | Data (+ all) | Must | S1 | – |
| PRJ-01 | Event data contract | All | Must | S1 | PRJ-00 |
| INV-02 | Hosting investigation | DevOps | Must | S1 | – |
| OPS-01 | Dev setup cleanup | DevOps | Must | S0–S1 | – |
| OPS-02 | CI pipeline | DevOps | Must | S1 | OPS-01 |
| OPS-03 | Shared environment + CD | DevOps | Must | S2 | INV-02, OPS-02 |
| OPS-04 | Scheduling, backups, monitoring | DevOps | Must | S3 | OPS-03 |
| OPS-05 | Email, push & OAuth setup | DevOps | Should | S3 | OPS-03 |
| DATA-01 | Scraper base + first 2 sources | Data | Must | S0–S1 | PRJ-00, INV-01, PRJ-01, BE-02 |
| DATA-02 | Normalization & dedup | Data | Must | S2 | DATA-01 |
| DATA-03 | Auto-tagging | Data | Must | S2 | DATA-01 |
| DATA-04 | Geocoding | Data | Must | S2 | DATA-02 |
| DATA-05 | More sources + health checks | Data | Must | S3 | DATA-02, OPS-04 |
| BE-01 | Structure & migrations | Backend | Must | S0–S1 | PRJ-01 |
| BE-02 | Ingest endpoint | Backend | Must | S1 | BE-01 |
| BE-03 | Events API | Backend | Must | S0–S2 | BE-01 |
| BE-04 | Search & map queries | Backend | Must | S2 | BE-03 |
| BE-05 | Auth & profile (+ Google sign-in: Should) | Backend | Must | S3 | BE-01, OPS-05 |
| BE-06 | Favorites / Going | Backend | Must | S3 | BE-05 |
| BE-07 | Friends | Backend | Should | S3 | BE-05 |
| BE-08 | Hangouts | Backend | Should | S4 | BE-06, BE-07 |
| BE-09 | Hardening | Backend | Must | S5 | – |
| BE-10 | Admin API | Backend | Should | S3–S4 | BE-05 |
| BE-11 | Email & push notifications | Backend | Should | S4 | BE-08, OPS-05 |
| BE-12 | Real-time hangout chat | Backend | Could | S4–S5 | BE-08 |
| FE-01 | Foundation | Frontend | Must | S0–S1 | – |
| FE-02 | Feed + filters + search | Frontend | Must | S1–S2 | FE-01, BE-03 |
| FE-03 | Event detail + source CTA | Frontend | Must | S2 | FE-02 |
| FE-04 | Map view | Frontend | Must | S2 | FE-02, BE-04, DATA-04 |
| FE-05 | Auth + My events | Frontend | Must | S3 | BE-05, BE-06 |
| FE-06 | Friends UI | Frontend | Should | S3 | BE-07 |
| FE-07 | Hangouts UI | Frontend | Should | S4 | BE-08 |
| FE-08 | Polish | Frontend | Must | S5 | – |
| FE-09 | Admin panel UI | Frontend | Should | S4 | BE-10 |
| FE-10 | PWA + push | Frontend | Should | S3–S4 | FE-01, BE-11 |
| FE-11 | Real-time chat UI | Frontend | Could | S4–S5 | BE-12, FE-07 |
| FE-12 | i18n (RO/EN) | Frontend | Could | S4–S5 | FE-01 |
| INV-03 | AI approach & provider | Data + Backend | Could | S2 | – |
| AI-01 | "For you" recommendations | Data + Backend | Could | S3–S4 | INV-03, BE-06 |
| AI-02 | "Ask GoCluj" assistant | Backend | Could | S4 | INV-03, BE-04 |
| AI-03 | AI UI | Frontend | Could | S4 | AI-01, AI-02 |

`[INV]` = timeboxed investigation. Its output is a short decision note added to section 9.

### 4.2 Cross-team

**PRJ-00 Foundations (walking skeleton)** · S0 (3 days, done by this Wednesday) · Must
- The thinnest possible version of the whole pipeline working end to end. Quick and pragmatic: it gets refined in S1.
- **Data:** one scraper for one real Cluj source (the easiest to scrape) that fetches upcoming events and sends them to the backend.
- **Backend:** the existing `POST /api/events` is kept for now (it gets protected in BE-02), plus `GET /api/events` that returns upcoming events sorted by date. CORS is enabled for the local frontend.
- **Frontend:** the Vite template is replaced by a simple page listing the events (title, date, venue, price, a link to the source), using `VITE_API_URL`.
- **DevOps:** `docker compose up` starts everything; `.env.example` and a short README with the run steps.
- **DoD:** on a fresh clone, `docker compose up` plus one scraper run shows real Cluj events in the browser. Demoed to the whole team on Wednesday.

**INV-01 [INV] Event sources** · S1 · Must
- List candidate Cluj sources: ticketing platforms, venue websites, the city/cultural agenda, university events.
- For each one, check robots.txt and the ToS, whether it has a public API or feed, whether it is static HTML or needs JavaScript, its volume of events, and its data quality.
- **DoD:** a ranked list is in section 9, with the second source for S1 and the next 2–4 picked.

**PRJ-01 Data contract** · S1 · Must
- **Event:** title, description, start/end, venue (name, address, lat/lng), price text, `is_free`, categories (many), image URL, `source_name`, `source_url`.
- **User:** email, unique `username`, display name, interests (categories), and a `going_visibility` setting (`friends` | `private`).
- Write these as Pydantic schemas, visible in OpenAPI `/docs`.
- Categories: Party, Festival, Târg / Expoziție, Tech & Meetups, Eveniment Local, Cultură, Sport, Altele.
- **DoD:** the schemas are merged and all teams have reviewed them.

### 4.3 DevOps

**INV-02 [INV] Hosting** · S1 · Must
- Default: one small VPS (Hetzner, DigitalOcean, or student cloud credits) running docker compose.
- Compare it with at most 1–2 PaaS options on cost, effort, Postgres support and cron support.
- Decide the domain (`gocluj.<domain>`, `staging.gocluj.<domain>`).
- **DoD:** the host is chosen, the account is created with team access, and the decision is in section 9.

**OPS-01 Dev setup cleanup** · S0–S1 · Must (`.env.example` and the README are needed in S0)
- Add `.env.example`.
- Pin versions in `requirements.txt` and make the Dockerfiles install from it.
- Rename to `VITE_API_URL`.
- Split compose into a base file, a dev override (reload, mounts, pgAdmin) and a prod file.
- Update the README.
- **DoD:** a fresh clone runs with `cp .env.example .env && docker compose up`.

**OPS-02 CI pipeline** · S1 · Must
- GitHub Actions on every PR: backend and scraper lint (ruff) and pytest, frontend lint and build, and Docker image builds.
- Protect `main`: changes go through a PR with green checks.
- **DoD:** the checks are required on `main`.

**OPS-03 Shared environment + CD** · S2 · Must
- Production images: a static frontend build, and the backend without `--reload`.
- Caddy or Nginx with automatic HTTPS.
- The DB and pgAdmin are not public.
- Secrets (including the LLM API key, later) live on the server or in GitHub secrets.
- Merging to `main` deploys to staging automatically.
- **DoD:** the staging URL is live over HTTPS and updates automatically.

**OPS-04 Scheduling, backups, monitoring** · S3 · Must
- Scrapers run daily via cron or a scheduler container.
- A nightly `pg_dump` with a copy off the server.
- An uptime check that alerts the team.
- Migrations run automatically on deploy.
- **DoD:** scrapers run unattended for 3 days in a row, a backup has been restored, and an outage alert reaches the team.

**OPS-05 Email, push & OAuth setup** · S3 · Should
- Create an account with the email provider.
- Add SPF/DKIM/DMARC DNS records for the domain.
- Generate VAPID keys for web push.
- Register the Google OAuth client with redirect URLs for local, staging and prod.
- Store everything as secrets per environment.
- **DoD:** staging can send an email that reaches the inbox (not spam), and Google login redirects work on staging.

### 4.4 Data Engineering

**DATA-01 Scraper base + first 2 sources** · S0–S1 · Must (the first source ships in PRJ-00)
- One module per source with `fetch()` → `parse()` → `normalize()`, plus a shared runner that posts to the ingest endpoint.
- Polite scraping: delays, a clear user agent, timeouts and retries.
- **DoD:** real events from 2 sources land in the DB.

**DATA-02 Normalization & dedup** · S2 · Must
- Dates in the Europe/Bucharest timezone, Romanian date formats, and "Gratuit" / "Intrare liberă" setting `is_free`.
- Clean the text.
- Upsert by `(source_name, external_id)` (proposed, pending Backend review; see the [scraper design](scrape/scraper-design.md)), plus a basic cross-source dedup (title + date + venue).
- **DoD:** re-runs create no duplicates, and the same event from 2 sources appears once.

**DATA-03 Auto-tagging** · S2 · Must
- Rule-based keyword lists (RO + EN) per category, kept in a config file. Multi-label, with "Altele" as the fallback.
- **DoD:** at least 80% of a hand-checked sample of 50 events is tagged correctly.

**DATA-04 Geocoding** · S2 · Must
- Nominatim limited to the Cluj area, at 1 request per second.
- A venue cache plus manual coordinates for the ~20 top venues.
- **DoD:** at least 90% of upcoming events have coordinates.

**DATA-05 More sources + health checks** · S3 · Must
- Add sources 3–4 (5–6 if time allows).
- Log a summary per run.
- Alert when a source returns 0 events.
- **DoD:** at least 4 sources run daily on staging.

### 4.5 Backend

**BE-01 Structure & migrations** · S0–S1 · Must
- Layout: `app/routers`, `app/services`, `app/models`, `app/schemas`, `app/core/config.py`.
- Alembic is the only schema source. Remove `data/schema1.sql`.
- Update the schema to PRJ-01.
- Set up pytest with a test database.
- **DoD:** `alembic upgrade head` builds the schema from scratch and the tests run in CI.

**BE-02 Ingest endpoint** · S1 · Must
- `POST /api/ingest/events` (batch upsert), protected by a token header.
- Remove the open `POST /api/events`.
- **DoD:** requests without the token get a 401, and the scrapers use the token.

**BE-03 Events API** · S0–S2 · Must (a basic list ships in PRJ-00)
- `GET /api/events` with pagination and filters for category, date range, today, weekend and free.
- `GET /api/events/{id}` and `GET /api/categories`.
- Upcoming events only by default.
- **DoD:** endpoints are documented in `/docs`, each filter has a test, and response time is under 300 ms.

**BE-04 Search & map queries** · S2 · Must
- A `q` parameter using Postgres FTS with `unaccent`.
- A `bbox` filter that can be combined with the other filters.
- **DoD:** "concert", "teatru" and "târg"/"targ" return relevant results.

**BE-05 Auth & profile** · S3 · Must
- Register, login (JWT) and `me` endpoints.
- A profile with username, display name, interests and the `going_visibility` setting.
- Account deletion.
- A user `role` (`user` | `admin`), used by BE-10.
- Password reset by email (once OPS-05 is ready).
- **Google sign-in (Should):** the OAuth login creates or links an account by email.
- **DoD:** the auth flow (including Google) is tested and protected endpoints reject invalid tokens.

**BE-06 Favorites / Going** · S3 · Must
- `PUT`/`DELETE /api/me/events/{id}` with status `favorite` | `going`, and `GET /api/me/events`.
- Event responses include the current user's status.
- **DoD:** the frontend flow works end to end on staging.

**BE-07 Friends** · S3 · Should
- Search users by username.
- Send, accept and decline friend requests, and remove friends.
- `GET /api/friends` and `GET /api/friends/requests`.
- **Friend activity:**
  - event responses include `friends_going` (count plus the first few names),
  - `GET /api/friends/activity` lists upcoming events friends are going to,
  - both respect `going_visibility`.
- **DoD:** two test users can become friends and see each other's Going events. A private user's events stay hidden.

**BE-08 Hangouts** · S4 · Should
- A hangout = event + creator + invited friends + an optional note and meeting time/place.
- Invitees answer **yes / maybe / no**. There is a flat comment list, which BE-12 upgrades to real-time chat.
- `GET /api/me/hangouts` and `GET /api/me/notifications`, the latter covering new friend requests, hangout invites and replies (in-app only, fetched by polling).
- Answering "yes" also marks the event as Going.
- **DoD:** a user creates a hangout, two friends reply and comment, and everyone sees the same state.

**BE-09 Hardening** · S5 · Must
- Restrict CORS.
- Rate-limit the auth and AI endpoints.
- Use a consistent error format.
- Check permissions on all social endpoints (users can only see their own and their friends' data).
- **DoD:** no open CORS in production, and permission tests exist for the friends, hangouts and admin endpoints.

**BE-10 Admin API** · S3–S4 · Should
- Admin-only endpoints, protected by `role = admin`.
- **Events:** search all events (including hidden and past ones), hide/unhide, edit fields, change categories, merge duplicates.
- **Sources:** list sources with their last run, events found and errors (from the DATA-05 run summaries), and enable/disable a source.
- **Users:** list, search, disable an account.
- Simple "report event" from users (wrong info, duplicate, spam) feeding an admin queue.
- Admin edits are kept when the scraper re-runs (manually edited fields are locked).
- **DoD:** an admin can fix a wrong event, and the fix survives the next scraper run.

**BE-11 Email & push notifications** · S4 · Should
- One notification service that sends each event (friend request, hangout invite, hangout reply, reminder) to every channel: in-app, email and push.
- Email templates in Romanian.
- Store push subscriptions per device.
- A daily job sends reminders the day before Going events and hangouts.
- Per-user settings to turn each channel on or off, plus an unsubscribe link in every email.
- **DoD:** a hangout invite arrives by email and push on staging, and turning a channel off stops it.

**BE-12 Real-time hangout chat** · S4–S5 · Could
- A FastAPI websocket per hangout. Only members can join (checked with their JWT).
- Messages are stored in the DB and the history is loaded over REST.
- One backend instance, so no broker is needed. If the socket drops, the client falls back to polling.
- **DoD:** 3 members chat on staging and see each other's messages instantly. Non-members can't connect.

### 4.6 Frontend

**FE-01 Foundation** · S0–S1 · Must (a simple events page ships in PRJ-00)
- Replace the template. Set up React Router, TanStack Query and Tailwind.
- Layout and nav: Feed / Map / My events / Friends.
- An API client using `VITE_API_URL`.
- Loading and error components.
- Low-fidelity wireframes.
- **DoD:** a mobile-first app shell runs locally and on staging.

**FE-02 Feed + filters + search** · S1–S2 · Must
- Event cards.
- A "load more" button.
- Category chips, Today / Weekend / date range, a Free toggle and a search box.
- Filters stored in the URL.
- **DoD:** every filter works against the real API on mobile and desktop.

**FE-03 Event detail + source CTA** · S2 · Must
- A detail page with a small map and a clear **"Bilete / Vezi sursa"** button.
- **DoD:** every event links back to its source.

**FE-04 Map view** · S2 · Must
- A Leaflet map centered on Cluj, with clustered pins and popups.
- Uses the same filters as the feed and reloads on map move.
- **DoD:** the map shows the same events as the filtered feed.

**FE-05 Auth + My events** · S3 · Must
- Sign up with an interest picker, login and logout.
- Favorite and Going buttons.
- A "My events" page and profile settings (including Going visibility).
- **DoD:** a user's saved events persist after logging out and back in.

**FE-06 Friends UI** · S3 · Should
- User search and friend requests (send, accept, decline).
- A friends list.
- A "Friends are going" badge on event cards and the detail page.
- A friends activity feed.
- **DoD:** the full friends flow works between two accounts on staging.

**FE-07 Hangouts UI** · S4 · Should
- A "Plan a hangout" button on the event page that opens a friend picker and a note.
- A hangout page with replies and comments, and a "My hangouts" list.
- A notification badge in the header.
- **DoD:** the full hangout flow works between three accounts on staging.

**FE-08 Polish** · S5 · Must
- Empty and error states, accessibility basics, and meta tags.
- **DoD:** Lighthouse mobile score of at least 80 for Performance and Accessibility on the feed page.

**FE-09 Admin panel UI** · S4 · Should
- An `/admin` section, visible only to admins.
- Pages:
  - an events table with search, hide, edit, re-tag and merge,
  - the reports queue,
  - source health (last run, counts, errors),
  - a users list.
- Keep it functional rather than pretty: plain tables and forms.
- **DoD:** an admin can handle a reported event end to end from the UI.

**FE-10 PWA + push** · S3–S4 · Should
- `vite-plugin-pwa`: a manifest, icons and a service worker. The app can be installed on Android and iOS.
- Offline: the app shell plus cached "My events" and hangouts.
- A push permission prompt shown at a sensible moment (e.g. after the first Going), and a notification settings page.
- **DoD:** the app installs on a phone, shows saved events offline, and receives a push notification from staging.

**FE-11 Real-time chat UI** · S4–S5 · Could
- The hangout comments become a live chat (messages and a basic "new messages" indicator).
- **DoD:** the chat works on mobile on staging and falls back to refreshing if the socket fails.

**FE-12 i18n (RO/EN)** · S4–S5 · Could
- Move UI strings to `react-i18next` with Romanian as the default and English as the second language, plus a language switcher.
- Event content stays in its original language.
- **DoD:** every page is fully translated, with no hard-coded strings left.

### 4.7 AI integration (Could)

The AI is built in two layers so that something useful ships even if the LLM part is cut. **AI-01** works without any LLM. **AI-02** adds the LLM on top.

**INV-03 [INV] AI approach & provider** · S2 · Could
- Pick an LLM provider and model (default: a hosted API such as Claude, using a small, cheap model) on cost per request, Romanian language quality, privacy terms and student credits.
- Validate the approach on 20 sample prompts: retrieve candidate events with existing filters and search, then let the LLM choose and explain. No fine-tuning and no vector DB unless the samples show it is needed.
- Set a **monthly budget cap** and a per-user daily limit.
- **DoD:** the provider is chosen, the prompt approach is validated on the samples, and the cost estimate is in section 9.

**AI-01 "For you" recommendations** · S3–S4 · Could
- Build an interest profile per user: the interests picked at sign-up, plus categories, venues and keywords from their Favorite / Going / hangout events.
- Score upcoming events by content: category match, keyword overlap, events friends are going to, and how soon the event is.
- `GET /api/me/recommendations` returns events with a simple reason (e.g. "Because you like Tech & Meetups").
- **DoD:** for 5 test users with different interests, at least 7 of the top 10 events are judged relevant by the team.

**AI-02 "Ask GoCluj" assistant** · S4 · Could
- `POST /api/ai/ask` takes a free-text request.
- The LLM turns the request into filters (category, date, price, keywords).
- The backend fetches up to ~30 candidate events.
- The LLM picks the best 3–5 and writes a one-line reason for each, using the user's profile when logged in.
- The LLM never invents events. Only IDs from the candidate list are returned, and they are validated server-side.
- Add timeouts, falling back to plain search on errors, the rate limits from INV-03, and logs of cost per request.
- **DoD:** 15 of the 20 INV-03 sample prompts give useful results, and no response contains an event that isn't in the DB.

**AI-03 AI UI** · S4 · Could
- A **"Pentru tine"** (For you) tab in the feed.
- An **"Ask GoCluj"** input with suggested prompts that shows the results as event cards with reasons.
- A clear "AI-generated suggestions" label.
- **DoD:** both features work on mobile on staging, and they degrade gracefully when the AI is off or failing.

---

## 5. Sprint plan

A short foundations sprint (S0), then **two-week sprints**, with a shorter final release sprint. Each sprint ends with a demo (on staging from S2 on), a short retro and an update to the Epic statuses in section 4.1.

| Sprint | Duration | Focus | Exit criteria |
|---|---|---|---|
| **S0** | 3 days (until this Wednesday) | **Foundations** | PRJ-00 done: one real scraper → backend → working UI listing real events, all running with `docker compose up` |
| **S1** | 2 weeks | **Solid base** | INV-01, INV-02 and PRJ-01 decided. Dev setup clean and CI live. Migrations, protected ingest, a 2nd source, a proper app shell and feed |
| **S2** | 2 weeks | **Browsing MVP** | Filters, search, tagging, dedup, geocoding, map, detail page + CTA. Staging live with CD. INV-03 done. **Milestone: public browsing MVP on staging** |
| **S3** | 2 weeks | **Accounts & friends** | Auth (+ Google), favorites, My events, friends + friend activity, admin API started, PWA basics. Daily scheduled scraping, backups, monitoring, 4+ sources, email/push/OAuth setup. AI-01 started. **Milestone: all Must features complete** |
| **S4** | 2 weeks (winter holidays, reduced capacity) | **Hangouts, notifications, admin & AI** | Hangouts, email + push notifications, admin panel, PWA push. AI-01 done, AI-02 + AI-03 on staging. Chat and i18n started if there is capacity. **Checkpoint at the end of S4:** unfinished Should features are simplified, unfinished Could features are cut |
| **S5** | ~1.5 weeks | **Hardening & release** | Finish Could features (chat, i18n, AI) only until the freeze. BE-09, FE-08, test gaps, data quality pass, production deploy. **Feature freeze a few days before release**, then **ship** + final demo |

Sprint load per team:

| Sprint | DevOps | Data | Backend | Frontend |
|---|---|---|---|---|
| S0 | PRJ-00 (compose, `.env.example`, README) | PRJ-00 (first scraper) | PRJ-00 (`GET /api/events`, CORS) | PRJ-00 (events list page) |
| S1 | INV-02, OPS-01, OPS-02 | INV-01, PRJ-01, DATA-01 | PRJ-01, BE-01, BE-02, BE-03 | FE-01, FE-02 (basic feed) |
| S2 | OPS-03 | DATA-02, DATA-03, DATA-04, INV-03 | BE-03 (filters), BE-04, INV-03 | FE-02, FE-03, FE-04 |
| S3 | OPS-04, OPS-05 | DATA-05, AI-01 (profile + scoring) | BE-05, BE-06, BE-07, BE-10 (start) | FE-05, FE-06, FE-10 (PWA basics) |
| S4 | LLM key/secrets, cost alerts, buffer | AI-01 (tuning), AI-02 prompts, source health data for admin | BE-08, BE-10, BE-11, AI-02, BE-12 (Could) | FE-07, FE-09, FE-10 (push), AI-03, FE-11/FE-12 (Could) |
| S5 | prod deploy, release | data quality | BE-09, BE-12 (Could), release | FE-08, FE-11/FE-12 (Could), release |

---

## 6. Global Definition of Done

A task or Epic is done when:

1. the code was reviewed in a PR, CI is green, and it is merged to `main`;
2. new backend and data logic has tests (social endpoints include permission tests);
3. it is deployed and checked on staging (from S2 on);
4. new env vars and setup steps are documented (`.env.example` or README).

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| A source changes its HTML or blocks the scraper | More sources than the minimum; health alerts (DATA-05); small isolated parser per source |
| A source's ToS forbids scraping | Check it in INV-01; store only a summary; always link to the original |
| Social, notifications, admin and AI scope is too much for the deadline | Clear Must/Should/Could priorities; Must features complete by the end of S3; cut-off checkpoint at the end of S4 |
| Low capacity over the holidays (S4) | S4 only carries Should/Could work; Must work is finished in S3 |
| Emails land in spam / push doesn't work on iOS | SPF/DKIM/DMARC in OPS-05; iOS push only works for an installed PWA (16.4+), and email covers the rest |
| Spam or abuse through invites and reports | Rate limits (BE-09), admin can disable accounts (BE-10) |
| Privacy of friends' activity (GDPR) | `going_visibility` setting, friends-only data, account deletion, permission tests |
| LLM cost, latency or hallucinated events | Budget cap + rate limits; the LLM only picks from DB candidates; fallback to plain search |
| Nominatim rate limits or poor accuracy | Venue cache + manual coordinates for top venues |

---

## 8. After launch (backlog)

Not planned before launch. Pick up only if everything above is done:

- LLM-assisted auto-tagging (reusing the INV-03 provider)
- Calendar export (.ics) / Google Calendar sync
- Friend suggestions ("people going to the same events")
- More social logins (Apple, Facebook)
- Native mobile apps (the PWA covers mobile for launch)

Could features (real-time chat, i18n, AI) that miss the end-of-S4 checkpoint move here.

---

## 9. Decisions log

Short notes from investigations and any change to the default stack. Use the format: **date · topic · decision · why**.

- _2026-11-09 · Plan · Initial plan created; 2-week sprints; social (Should) and AI (Could) added to scope._
- _2026-11-09 · Scope · Notifications (email + push), admin panel, PWA and Google sign-in added as Should; real-time chat and i18n added as Could._
- _2026-11-09 · Schedule · Added S0 (Foundations, 3 days, until Wednesday). Sprints are described by duration, not by dates._
- _2026-11-09 · Scraping stack · Scrapy instead of requests + BeautifulSoup · built-in throttling, retries, robots.txt, HTTP cache, feed export and per-run stats that we would otherwise write ourselves. Details in `docs/scrape/scraper-design.md`._
- _2026-11-09 · Scraper orchestration · cron + `docker compose run --rm scraper`, no Airflow · one daily batch on one VPS; Airflow's extra infra isn't justified._
- _2026-11-09 · Scraper delivery · two steps: crawl → JSONL → `ingest` command; one process per spider · a backend outage doesn't fail the crawl, re-runs and debugging are easy, and failures stay per source._
- _2026-11-09 · Proposals (pending Backend review) · upsert key `(source_name, external_id)`; geocoding moves to the backend (needs a persistent venue cache) · see `docs/scrape/scraper-design.md` §6._
- _2026-11-10 · Scraper sources · scraper design detailed for iaBilet and LiveTickets; per-source specs in `docs/scrape/sources/`; LiveTickets blocked on the INV-01 terms check._
- _2026-11-10 · LiveTickets terms (INV-01, T10) · use the public JSON API (`api.livetickets.ro/public/events`), about 33 requests per daily run, full description stored as specified in `docs/scrape/sources/livetickets.md` · owner decision for a non-commercial university project. Terms read at `https://www.livetickets.ro/legal/termeni-si-conditii` (Flow Concept SRL, no date or version shown): nothing on bots, scraping or API use; §11 limits site content to personal use, anything else needs written consent (support@livetickets.ro), except fragments of max. 2 paragraphs on non-commercial sites with the source cited, and links with a credit line. Accepted risk: full descriptions exceed that exception. Always link to the original event page; revisit (shorten descriptions, add the credit line, or ask for consent) if the project goes public or LiveTickets objects._
- _2026-11-10 · Upsert key · events are upserted on `(source_name, external_id)` · stable per-source identity, re-runs never duplicate (scraper-design B1)._
- _2026-11-10 · Events API · `GET /api/events` returns `{items, total, limit, offset}` with upcoming events only (`coalesce(end_at, start_at) >= now()`) · the frontend needs "load more", and past events are not useful in the feed._
- _2026-11-10 · Event images · hotlinked from the source CDN (URL stored, file never copied); every card and detail page links back to the source · consistent with the INV-01 LiveTickets decision; revisit if the project goes public._
- _2026-11-10 · Venue · kept as flat columns on `events` for now · keep it simple; a venue entity is deferred to DATA-04._
- _INV-01 · Event sources · pending for the remaining sources. First sources: iaBilet (server-rendered, JSON-LD) and LiveTickets (SPA, public JSON API; terms decision above)._
- _INV-02 · Hosting · pending_
- _INV-03 · AI approach & provider · pending_
