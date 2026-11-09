# GoCluj scraper

Collects public events in Cluj-Napoca from ticketing sites and pushes them to the GoCluj backend.
Design rationale: [../docs/data/scraper-design.md](../docs/data/scraper-design.md).

## Architecture

```
spider (one per source)
  -> make_event(): validate + normalize into the Event model
  -> JSONL file: $OUTPUT_DIR/<date>/<spider>.jsonl
  -> ingest: POST batches to $INGEST_URL (dry-run if unset)
```

## Layout

```
scrape/
  Dockerfile, .dockerignore   image that runs `python -m gocluj_scraper.run`
  requirements*.txt           runtime / dev dependencies
  pyproject.toml              ruff + pytest config
  scrapy.cfg                  Scrapy project config
  gocluj_scraper/
    settings.py               Scrapy settings (politeness, cache, feeds)
    models.py                 Event model (validation)
    extensions.py             Scrapy extensions (run stats)
    run.py                    entrypoint: run spiders, write JSONL, ingest
    ingest.py                 send JSONL files to the backend
    parsing/                  shared helpers (jsonld.py, text.py)
    spiders/base.py           BaseEventSpider (make_event, next_page, max_pages)
    spiders/iabilet.py        iaBilet spider (skeleton)
    spiders/livetickets.py    LiveTickets spider (skeleton)
  tests/                      pytest tests; tests/fixtures/<source>/ saved pages
```

## Quick start

Docker (from repo root):

```sh
docker compose run --rm scraper
docker compose run --rm scraper python -m scrapy crawl iabilet -a max_pages=1 -O /data/out/test.jsonl
```

Local venv (from `scrape/`):

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
scrapy list
HTTPCACHE_ENABLED=1 scrapy crawl iabilet -a max_pages=1
python -m gocluj_scraper.run iabilet --max-pages 1
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `INGEST_URL` | unset | Backend ingest endpoint; unset = dry-run |
| `INGEST_TOKEN` | unset | Auth token for ingest |
| `INGEST_BATCH_SIZE` | see `ingest.py` | Events per ingest request |
| `OUTPUT_DIR` | see `settings.py` (`/data/out` in Docker) | Where JSONL files are written |
| `HTTPCACHE_ENABLED` | `0` | `1` caches HTTP responses (dev only) |
| `LOG_LEVEL` | `INFO` | Scrapy log level (`SCRAPER_LOG_LEVEL` in compose) |

## Testing

```sh
ruff check .
pytest -q
```

Without a local Python:

```sh
docker run --rm -v "$PWD:/app" -w /app python:3.11-slim sh -c "pip install -q -r requirements.txt -r requirements-dev.txt && ruff check . && pytest -q"
```

## Adding a new source

1. Check robots.txt and ToS; record the result in [`docs/IMPLEMENTATION_PLAN.md`](../docs/IMPLEMENTATION_PLAN.md) §9 (INV-01).
2. Pick the data source in this order: JSON-LD > JSON API > HTML selectors > Playwright.
3. Subclass `BaseEventSpider` in `spiders/<source>.py`; set `name`, `source_name`, `allowed_domains`.
4. Filter to Cluj as early as possible (`is_cluj`), before fetching detail pages.
5. Always emit a stable `external_id`.
6. Save 1-2 pages to `tests/fixtures/<source>/` and write a parser test using `fake_response`.
7. Try it with `-a max_pages=1` and `HTTPCACHE_ENABLED=1`.
8. Set per-source politeness (delay, concurrency) in the spider's `custom_settings`.
