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
        external_id="e1",
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
    base = {"source_url": "https://x.ro", "external_id": "1"}
    assert spider.make_event(title="", start_at="2099-01-01", **base) is None
    assert spider.make_event(title="T", start_at="nope", **base) is None
    assert spider.make_event(title="T", **base) is None


def test_make_event_past_returns_none():
    spider = DummySpider()
    past = (datetime.now(TZ) - timedelta(days=2)).isoformat()
    event = spider.make_event(
        title="T", source_url="https://x.ro", external_id="1", start_at=past
    )
    assert event is None


def test_past_start_but_future_end_is_kept():
    spider = DummySpider()
    now = datetime.now(TZ)
    event = spider.make_event(
        title="T",
        source_url="https://x.ro",
        external_id="1",
        start_at=now - timedelta(days=1),
        end_at=now + timedelta(days=1),
    )
    assert event is not None


def test_naive_datetime_is_localized_and_extra_forbidden():
    event = Event(
        source_name="S",
        source_url="https://x.ro",
        external_id="1",
        title="T",
        start_at=datetime(2099, 1, 1, 10),
    )
    assert event.start_at.utcoffset() == timedelta(hours=2)
    assert event.is_free is None
    with pytest.raises(ValidationError):
        Event(
            source_name="S",
            source_url="u",
            external_id="1",
            title="T",
            start_at="2099-01-01",
            typo=1,
        )


def test_paid_price_sets_not_free():
    event = Event(
        source_name="S",
        source_url="https://x.ro",
        external_id="1",
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


def make(**overrides):
    fields = {
        "source_name": "S",
        "source_url": "https://x.ro",
        "external_id": "1",
        "title": "T",
        "start_at": "2099-01-01T10:00:00",
    }
    return Event(**(fields | overrides))


def test_date_only_end_becomes_end_of_day():
    event = make(end_at="2099-01-05")
    assert event.end_at == datetime(2099, 1, 5, 23, 59, 59, tzinfo=TZ)


def test_date_only_start_stays_midnight():
    assert make(start_at="2099-01-05").start_at == datetime(2099, 1, 5, tzinfo=TZ)


def test_end_with_time_is_unchanged():
    event = make(end_at="2099-01-01T12:30:00")
    assert event.end_at == datetime(2099, 1, 1, 12, 30, tzinfo=TZ)


@pytest.mark.parametrize("end_at", ["2099-01-01T10:00:00", "2099-01-01T09:00:00", "2098-12-31"])
def test_end_not_after_start_becomes_none(end_at):
    assert make(end_at=end_at).end_at is None


def test_same_day_date_only_end_is_kept():
    assert make(end_at="2099-01-01").end_at == datetime(2099, 1, 1, 23, 59, 59, tzinfo=TZ)


def test_event_happening_today_with_date_only_end_is_not_past():
    now = datetime.now(TZ)
    event = DummySpider().make_event(
        title="T",
        source_url="https://x.ro",
        external_id="1",
        start_at=now - timedelta(minutes=1),
        end_at=now.date().isoformat(),
    )
    assert event is not None


def test_description_html_and_line_breaks():
    event = make(description="<p>Hello&nbsp;<b>you</b></p><p>Line<br/>two<BR >three</p>")
    assert event.description == "Hello you\nLine\ntwo\nthree"


def test_description_plain_text_keeps_line_breaks():
    event = make(description="Line 1\r\n  Line   2\r\n\r\n\r\n\r\nLine 3")
    assert event.description == "Line 1\nLine 2\n\nLine 3"


def test_description_empty_is_none():
    assert make(description=" <br> \r\n ").description is None


def test_price_text_stays_single_line():
    assert make(price_text="59\n RON").price_text == "59 RON"


@pytest.mark.parametrize("external_id", ["", "   ", None])
def test_external_id_required_non_empty(external_id):
    with pytest.raises(ValidationError):
        make(external_id=external_id)


def test_external_id_is_stripped():
    assert make(external_id=" abc-1 ").external_id == "abc-1"


def test_source_category_is_cleaned():
    assert make().source_category is None
    assert make(source_category="  Muzică \n live ").source_category == "Muzică live"
