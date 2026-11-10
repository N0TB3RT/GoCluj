from datetime import datetime, timedelta

from gocluj_scraper.spiders.base import BaseEventSpider


class DummySpider(BaseEventSpider):
    name = "dummy"
    source_name = "Dummy"


def event_fields(start_at: datetime) -> dict:
    return {
        "external_id": "x1",
        "source_url": "https://example.com/e/1",
        "title": "Concert",
        "start_at": start_at,
    }


def test_skip_increments_reason_counter(make_spider):
    spider = make_spider(DummySpider)
    spider.skip("not_cluj", "https://example.com/e/1")
    spider.skip("not_cluj")
    assert spider.crawler.stats.get_value("events/not_cluj") == 2


def test_make_event_past_event_is_skipped(make_spider):
    spider = make_spider(DummySpider)
    result = spider.make_event(**event_fields(datetime.now() - timedelta(days=3)))
    assert result is None
    assert spider.crawler.stats.get_value("events/past") == 1
    assert spider.crawler.stats.get_value("events/valid") is None


def test_make_event_valid_event_is_counted(make_spider):
    spider = make_spider(DummySpider)
    result = spider.make_event(**event_fields(datetime.now() + timedelta(days=3)))
    assert result is not None
    assert spider.crawler.stats.get_value("events/valid") == 1


def test_skip_without_crawler_does_not_raise():
    DummySpider().skip("cancelled", "https://example.com/e/1")
