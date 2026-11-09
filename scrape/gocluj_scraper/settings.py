"""Scrapy settings. Environment variables override the dev-friendly defaults."""

import os

from gocluj_scraper.parsing.text import TIMEZONE  # noqa: F401  (exposed as a setting)

BOT_NAME = "gocluj_scraper"
SPIDER_MODULES = ["gocluj_scraper.spiders"]
NEWSPIDER_MODULE = "gocluj_scraper.spiders"

# Politeness
ROBOTSTXT_OBEY = True
USER_AGENT = os.getenv("SCRAPER_USER_AGENT", "GoClujBot/0.1 (+https://github.com/gocluj)")
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1
AUTOTHROTTLE_ENABLED = True
RETRY_TIMES = 3
DOWNLOAD_TIMEOUT = 30
CLOSESPIDER_TIMEOUT = 600
CLOSESPIDER_ERRORCOUNT = 20
DEPTH_LIMIT = 10

# Dev-only HTTP cache to iterate on parsers offline
HTTPCACHE_ENABLED = os.getenv("HTTPCACHE_ENABLED", "").lower() in ("1", "true")
HTTPCACHE_DIR = os.getenv("HTTPCACHE_DIR", ".httpcache")

# Output: one JSONL file per spider per day
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "out")
FEED_URI_PARAMS = "gocluj_scraper.feeds.uri_params"
FEEDS = {
    f"{OUTPUT_DIR}/%(run_date)s/%(name)s.jsonl": {
        "format": "jsonlines",
        "encoding": "utf8",
        "overwrite": True,
    }
}

EXTENSIONS = {"gocluj_scraper.extensions.RunSummary": 500}
TELNETCONSOLE_ENABLED = False
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
