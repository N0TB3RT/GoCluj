from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from gocluj_scraper.models import Event
from gocluj_scraper.spiders.base import BaseEventSpider

TZ = ZoneInfo("Europe/Bucharest")


class DummySpider(BaseEventSpider):
    name = "dummy"
    source_name = "Dummy"

    def parse(self, response, page=1):
        pass


def test_make_event_normalizes():
    spider = DummySpider()
    event = spider.make_event(
        title="  Concert &amp; Party \n",
        source_url="https://x.ro/e/1?ica_source=home&id=7#frag",
        start_at="6 noiembrie 2099, 22:00",
        price_text="Gratuit",
        venue={"name": " Club  Form ", "city": "Cluj-Napoca"},
    )
    assert event["source_name"] == "Dummy"
    assert event["title"] == "Concert & Party"
    assert event["source_url"] == "https://x.ro/e/1?id=7"
    assert event["start_at"].startswith("2099-11-06T22:00:00+02:00")
    assert event["is_free"] is True
    assert event["venue"]["name"] == "Club Form"
    assert event["categories"] == []


def test_make_event_invalid_returns_none():
    spider = DummySpider()
    assert spider.make_event(title="", source_url="https://x.ro", start_at="2099-01-01") is None
    assert spider.make_event(title="T", source_url="https://x.ro", start_at="nope") is None
    assert spider.make_event(title="T", source_url="https://x.ro") is None


def test_make_event_past_returns_none():
    spider = DummySpider()
    past = (datetime.now(TZ) - timedelta(days=2)).isoformat()
    assert spider.make_event(title="T", source_url="https://x.ro", start_at=past) is None


def test_past_start_but_future_end_is_kept():
    spider = DummySpider()
    now = datetime.now(TZ)
    event = spider.make_event(
        title="T",
        source_url="https://x.ro",
        start_at=now - timedelta(days=1),
        end_at=now + timedelta(days=1),
    )
    assert event is not None


def test_naive_datetime_is_localized_and_extra_forbidden():
    event = Event(
        source_name="S", source_url="https://x.ro", title="T", start_at=datetime(2099, 1, 1, 10)
    )
    assert event.start_at.utcoffset() == timedelta(hours=2)
    assert event.is_free is None
    with pytest.raises(ValidationError):
        Event(source_name="S", source_url="u", title="T", start_at="2099-01-01", typo=1)


def test_paid_price_sets_not_free():
    event = Event(
        source_name="S",
        source_url="https://x.ro",
        title="T",
        start_at="2099-01-01",
        price_text="59 - 99 RON",
    )
    assert event.is_free is False


def test_max_pages_and_next_page():
    from tests.conftest import fake_response

    spider = DummySpider(max_pages="2")
    assert spider.max_pages == 2
    resp = fake_response("https://x.ro/list")
    assert spider.next_page(resp, "/list?page=2", 2).cb_kwargs == {"page": 2}
    assert spider.next_page(resp, "/list?page=3", 3) is None
    assert DummySpider().max_pages is None
