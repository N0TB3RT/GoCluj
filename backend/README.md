# GoCluj backend

FastAPI + SQLAlchemy 2 + Alembic on PostgreSQL. Interactive docs: `http://localhost:8000/docs`.

## Layout

```
backend/
  app/
    main.py            FastAPI app, CORS, router registration
    db.py              engine, session, Base, get_db
    core/config.py     Settings (pydantic-settings)
    models/            SQLAlchemy ORM: User, Category, Event, Favorite, event_categories
    schemas/           Pydantic v2 request/response models
    routers/           events.py, categories.py, ingest.py
    services/ingest.py upsert logic
  alembic/             migrations (the only source of the DB schema)
  tests/               pytest suite (+ fixtures/livetickets_sample.jsonl)
```

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | required | SQLAlchemy URL. A bare `postgresql://` is rewritten to `postgresql+psycopg2://`. |
| `INGEST_TOKEN` | empty | Shared secret for `POST /api/ingest/events`. Empty disables ingest (always 401). |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins. |

The scraper uses the same `INGEST_TOKEN`, plus `INGEST_URL=http://backend:8000/api/ingest/events`.

## Migrations

The backend container runs `alembic upgrade head` on start. Manually:

```
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic revision --autogenerate -m "message"
```

The first migration creates the schema and seeds the 8 categories. It cannot be applied on top of a
database created by the old `data/schema1.sql`; use a fresh volume.

## Tests and lint

```
docker compose run --rm --no-deps backend pytest -q
docker compose run --rm --no-deps backend ruff check .
```

Tests use a separate database `<POSTGRES_DB>_test` on the same server. It is created if missing,
migrated with Alembic once per session, and `events`/`event_categories` are truncated between tests.

Dependencies: `requirements.txt` (runtime) and `requirements-dev.txt` (pytest, httpx, ruff), both pinned.

## Ingest endpoint

`POST /api/ingest/events` with header `X-Ingest-Token: <INGEST_TOKEN>` and body
`{"events": [...]}` (at most 500 events, unknown fields rejected with 422). Events are upserted by
`(source_name, external_id)`; category names in `categories` replace the event's links (unknown
names are ignored). Missing/wrong token or unset server token gives 401.

```json
{"received": 50, "created": 12, "updated": 38}
```

## Events API

- `GET /api/events?limit=20&offset=0` (limit 1..100, offset >= 0): upcoming events only
  (`coalesce(end_at, start_at) >= now()`), ordered by `start_at, id`.
- `GET /api/events/{id}`: one event (past events included), or 404 `{"detail": "Event not found"}`.
- `GET /api/categories`: all categories ordered by id.

```json
{
  "items": [
    {
      "id": 1,
      "source_name": "LiveTickets",
      "source_url": "https://www.livetickets.ro/bilete/balul-dintilor-de-lapte-1",
      "title": "Balul “Dinților de Lapte”",
      "description": null,
      "start_at": "2026-11-12T19:00:00Z",
      "end_at": "2026-11-13T03:00:00Z",
      "venue": {
        "name": "MATTER",
        "address": "Str. Universității 3",
        "city": "Cluj-Napoca",
        "lat": 46.7680736,
        "lng": 23.5902744
      },
      "price_text": "30 - 35 RON",
      "is_free": false,
      "categories": ["Party"],
      "source_category": "divertisment",
      "image_url": null,
      "image_url_large": null
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

Datetimes are ISO 8601 with an offset (`Z` = UTC).
