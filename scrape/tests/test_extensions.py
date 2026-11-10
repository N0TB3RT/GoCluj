import json

from scrapy import Spider

from gocluj_scraper import settings
from gocluj_scraper.extensions import RunSummary
from gocluj_scraper.feeds import run_file


class DummySpider(Spider):
    name = "dummy"


def run_summary(make_spider, tmp_path, stats_values: dict) -> dict:
    spider = make_spider(DummySpider, settings={"OUTPUT_DIR": str(tmp_path)})
    for key, value in stats_values.items():
        spider.crawler.stats.set_value(key, value)
    RunSummary(spider.crawler).spider_closed(spider, "finished")
    path = run_file(str(tmp_path), spider.name, "summary.json")
    return json.loads(path.read_text(encoding="utf8"))


def test_summary_includes_every_events_counter(make_spider, tmp_path):
    summary = run_summary(
        make_spider,
        tmp_path,
        {"item_scraped_count": 2, "events/valid": 2, "events/not_cluj": 5, "other/x": 1},
    )
    assert summary["valid"] == 2
    assert summary["invalid"] == 0
    assert summary["past"] == 0
    assert summary["not_cluj"] == 5
    assert "x" not in summary and "other/x" not in summary
    assert summary["failed"] is False


def test_summary_failed_when_no_items(make_spider, tmp_path):
    summary = run_summary(make_spider, tmp_path, {})
    assert summary["failed"] is True
    assert summary["items"] == 0


def test_depth_limit_not_set():
    assert not hasattr(settings, "DEPTH_LIMIT")
