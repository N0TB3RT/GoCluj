"""CLI entrypoint: crawl spiders (one subprocess each), then ingest the results.

Usage: python -m gocluj_scraper.run [--max-pages N] [spider ...]
Exit code is 0 only if every spider and the ingest step succeeded.
"""

import argparse
import json
import logging
import os
import subprocess
import sys

from scrapy.spiderloader import SpiderLoader
from scrapy.utils.project import get_project_settings

from gocluj_scraper.feeds import run_file
from gocluj_scraper.ingest import ingest_files

logger = logging.getLogger("run")


def run_spider(name: str, output_dir: str, max_pages: int | None) -> bool:
    """Run one spider in a subprocess; True if it finished with items and no errors."""
    summary_path = run_file(output_dir, name, "summary.json")
    summary_path.unlink(missing_ok=True)  # never trust a stale summary
    cmd = [sys.executable, "-m", "scrapy", "crawl", name]
    if max_pages:
        cmd += ["-a", f"max_pages={max_pages}"]
    env = {**os.environ, "SCRAPY_SETTINGS_MODULE": "gocluj_scraper.settings"}
    code = subprocess.run(cmd, env=env).returncode
    if code != 0 or not summary_path.exists():
        logger.error("Spider %s failed (exit code %d)", name, code)
        return False
    failed = json.loads(summary_path.read_text(encoding="utf8"))["failed"]
    if failed:
        logger.error("Spider %s reported a failed run (see its run_summary line)", name)
    return not failed


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spiders", nargs="*", help="spider names (default: all)")
    parser.add_argument("--max-pages", type=int, help="limit listing pages per spider")
    args = parser.parse_args(argv)

    settings = get_project_settings()
    output_dir = settings.get("OUTPUT_DIR", "out")
    names = args.spiders or sorted(SpiderLoader.from_settings(settings).list())

    results = {name: run_spider(name, output_dir, args.max_pages) for name in names}
    good = [str(run_file(output_dir, n, "jsonl")) for n, ok in results.items() if ok]

    ingest_ok = True
    if good:
        ingest_ok = ingest_files(
            good,
            os.getenv("INGEST_URL"),
            os.getenv("INGEST_TOKEN", ""),
            int(os.getenv("INGEST_BATCH_SIZE", "50")),
        )
    failed = [n for n, ok in results.items() if not ok]
    logger.info(
        "Done: ok=%s failed=%s ingest_ok=%s", sorted(set(results) - set(failed)), failed, ingest_ok
    )
    return 0 if not failed and ingest_ok else 1


if __name__ == "__main__":
    sys.exit(main())
