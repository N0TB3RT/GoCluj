from pathlib import Path

import pytest
from scrapy import Spider
from scrapy.crawler import Crawler
from scrapy.http import HtmlResponse, Request, TextResponse
from scrapy.settings import Settings
from scrapy.statscollectors import MemoryStatsCollector

FIXTURES = Path(__file__).parent / "fixtures"


def fake_response(
    url: str, body: str | bytes | None = None, fixture: str | None = None
) -> TextResponse:
    """Build a Scrapy response from inline ``body`` or a file in tests/fixtures/."""
    if fixture is not None:
        body = (FIXTURES / fixture).read_bytes()
    if isinstance(body, str):
        body = body.encode("utf8")
    cls = TextResponse if (fixture or url).endswith(".json") else HtmlResponse
    return cls(url=url, body=body or b"", encoding="utf8", request=Request(url))


@pytest.fixture(name="fake_response")
def _fake_response_fixture():
    return fake_response


def make_spider(spider_cls: type[Spider], settings: dict | None = None, **kwargs) -> Spider:
    """Build ``spider_cls`` attached to a bare crawler with working in-memory stats.

    Uses Scrapy defaults plus ``settings`` (no project settings), so no RunSummary and
    no feed files. No crawl is started and no reactor is needed.
    """
    crawler = Crawler(spider_cls, Settings(settings or {}))
    if crawler.stats is None:
        crawler.stats = MemoryStatsCollector(crawler)
    return spider_cls.from_crawler(crawler, **kwargs)


@pytest.fixture(name="make_spider")
def _make_spider_fixture():
    return make_spider
