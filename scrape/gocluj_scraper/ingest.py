"""CLI: send scraped JSONL files to the backend in batches.

Usage: python -m gocluj_scraper.ingest FILE [FILE...]
Env: INGEST_URL (unset = dry-run), INGEST_TOKEN, INGEST_BATCH_SIZE (default 50).
"""

import json
import logging
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import requests

logger = logging.getLogger("ingest")

TIMEOUT_S = 30
MAX_ATTEMPTS = 3


def read_events(paths: list[str]) -> list[dict]:
    lines = (line for p in paths for line in Path(p).read_text(encoding="utf8").splitlines())
    return [json.loads(line) for line in lines if line.strip()]


def _batches(items: list[dict], size: int) -> Iterator[list[dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _post_batch(session, url: str, token: str, batch: list[dict]) -> bool:
    """POST one batch with retries on connection errors and 5xx; 4xx fails immediately."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = session.post(
                url,
                json={"events": batch},
                headers={"X-Ingest-Token": token},
                timeout=TIMEOUT_S,
            )
        except requests.RequestException as exc:
            logger.warning("Attempt %d failed: %s", attempt, exc)
        else:
            if resp.status_code < 400:
                return True
            if resp.status_code < 500:
                logger.error("Rejected by backend (HTTP %d): %s", resp.status_code, resp.text[:200])
                return False
            logger.warning("Attempt %d: HTTP %d", attempt, resp.status_code)
        if attempt < MAX_ATTEMPTS:
            time.sleep(2**attempt)
    return False


def ingest_files(
    paths: list[str], url: str | None, token: str, batch_size: int = 50, session=None
) -> bool:
    """Send all events from ``paths``. Returns True on success (dry-run if no url)."""
    events = read_events(paths)
    if not url:
        logger.info("dry-run: INGEST_URL not set, %d events in %d files", len(events), len(paths))
        return True
    session = session or requests.Session()
    ok = True
    sent = 0
    for batch in _batches(events, batch_size):
        if _post_batch(session, url, token, batch):
            sent += len(batch)
        else:
            ok = False
    logger.info("ingest: sent %d/%d events", sent, len(events))
    return ok


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    paths = sys.argv[1:] if argv is None else argv
    if not paths:
        logger.error("Usage: python -m gocluj_scraper.ingest FILE [FILE...]")
        return 2
    ok = ingest_files(
        paths,
        os.getenv("INGEST_URL"),
        os.getenv("INGEST_TOKEN", ""),
        int(os.getenv("INGEST_BATCH_SIZE", "50")),
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
