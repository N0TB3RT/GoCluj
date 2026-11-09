"""Scrapy extension that reports one summary per run and flags failed runs."""

import json
import time

from scrapy import signals

from gocluj_scraper.feeds import run_file


class RunSummary:
    """Log a JSON summary line and write ``<spider>.summary.json`` for ``run.py``.

    A run is failed when it finished abnormally, scraped 0 items or logged errors.
    """

    def __init__(self, crawler):
        self.crawler = crawler
        self.output_dir = crawler.settings.get("OUTPUT_DIR", "out")
        self.started = time.monotonic()

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls(crawler)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_closed(self, spider, reason):
        stats = self.crawler.stats
        summary = {
            "event": "run_summary",
            "source": spider.name,
            "reason": reason,
            "items": stats.get_value("item_scraped_count", 0),
            "valid": stats.get_value("events/valid", 0),
            "invalid": stats.get_value("events/invalid", 0),
            "past": stats.get_value("events/past", 0),
            "errors": stats.get_value("log_count/ERROR", 0),
            "duration_s": round(time.monotonic() - self.started, 1),
        }
        summary["failed"] = summary["items"] == 0 or reason != "finished" or summary["errors"] > 0
        if summary["failed"]:
            stats.set_value("run/failed", 1)
        spider.logger.info(json.dumps(summary))
        path = run_file(self.output_dir, spider.name, "summary.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary), encoding="utf8")
