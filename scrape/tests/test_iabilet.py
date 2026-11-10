from datetime import datetime, timedelta
from pathlib import Path

from gocluj_scraper.spiders.iabilet import IabiletSpider

FIXTURES = Path(__file__).parent / "fixtures" / "iabilet"

LIST_URL = "https://www.iabilet.ro/bilete-in-cluj-napoca/"
DETAIL_URL = (
    "https://www.iabilet.ro/bilete-cluj-napoca-gala-bobocilor-business-2026-masquerade-133857/"
)
CANONICAL = DETAIL_URL

# Dates as saved in the fixtures; replaced with future dates so tests do not depend on the clock.
SAVED_START = "2026-11-12T19:30:00+02:00"
SAVED_END = '"endDate":"2026-11-13"'


def load(name):
    return (FIXTURES / name).read_text(encoding="utf8")


def stat(spider, key):
    return spider.crawler.stats.get_value(f"events/{key}")


def run_parse(spider, fake_response, fixture="listing_p1.html", page=1):
    response = fake_response(LIST_URL, body=load(fixture))
    return list(spider.parse(response, page=page))


def detail_requests(spider, requests):
    return [r for r in requests if r.callback == spider.parse_event]


def run_event(spider, fake_response, fixture="detail_multiday.html", end="date", **kwargs):
    body = load(fixture)
    start = datetime.now() + timedelta(days=5)
    end_day = start + timedelta(days=1)
    body = body.replace(SAVED_START, start.strftime("%Y-%m-%dT19:30:00+02:00"))
    body = body.replace(SAVED_END, f'"endDate":"{end_day:%Y-%m-%d}"')
    return list(spider.parse_event(fake_response(DETAIL_URL, body=body), **kwargs)), end_day


def test_start_url(make_spider):
    assert make_spider(IabiletSpider).start_urls == [LIST_URL]


def test_cards_yield_canonical_detail_requests(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    requests = detail_requests(spider, run_parse(spider, fake_response))
    assert [r.url for r in requests] == [CANONICAL]
    assert "ica_" not in requests[0].url
    assert requests[0].cb_kwargs == {"external_id": "133857"}


def test_cancelled_card_is_skipped_and_counted(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    requests = detail_requests(spider, run_parse(spider, fake_response))
    assert all(r.cb_kwargs["external_id"] != "999001" for r in requests)
    assert stat(spider, "cancelled") == 1


def test_duplicate_promoted_card_is_skipped(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    ids = [
        r.cb_kwargs["external_id"]
        for r in detail_requests(spider, run_parse(spider, fake_response))
    ]
    assert ids == ["133857"]


def test_duplicate_across_pages_is_skipped(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    run_parse(spider, fake_response)
    again = [
        r for r in run_parse(spider, fake_response, page=2) if r.callback == spider.parse_event
    ]
    assert again == []


def test_btn_more_yields_next_page_request(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    next_requests = [r for r in run_parse(spider, fake_response) if r.callback == spider.parse]
    assert len(next_requests) == 1
    assert next_requests[0].url == "https://www.iabilet.ro/bilete-in-cluj-napoca?page=2"
    assert next_requests[0].cb_kwargs == {"page": 2}


def test_last_page_has_no_next_page_request(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    requests = run_parse(spider, fake_response, "listing_last.html", page=7)
    assert len(requests) == 2
    assert all(r.callback == spider.parse_event for r in requests)


def test_max_pages_stops_next_page_request(make_spider, fake_response):
    spider = make_spider(IabiletSpider, max_pages=1)
    requests = run_parse(spider, fake_response)
    assert [r.callback for r in requests] == [spider.parse_event]


def test_empty_listing_yields_nothing(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    response = fake_response(LIST_URL, body="<html><body></body></html>")
    assert list(spider.parse(response)) == []


def test_parse_event_maps_fields(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    (event,), _ = run_event(spider, fake_response, external_id="133857")
    assert event["external_id"] == "133857"
    assert event["source_url"] == CANONICAL
    assert event["title"] == "Gala Bobocilor Business 2026 - Masquerade"
    assert event["price_text"] == "21.21 - 31.82 RON"
    assert event["is_free"] is False
    assert event["source_category"] == "Party"
    assert event["venue"]["name"].strip() == "After Eight"
    assert event["venue"]["city"] == "Cluj-Napoca"
    assert stat(spider, "valid") == 1


def test_parse_event_external_id_falls_back_to_url(make_spider, fake_response):
    (event,), _ = run_event(make_spider(IabiletSpider), fake_response)
    assert event["external_id"] == "133857"


def test_parse_event_date_only_end_is_end_of_day(make_spider, fake_response):
    (event,), end_day = run_event(make_spider(IabiletSpider), fake_response)
    end = datetime.fromisoformat(event["end_at"])
    assert (end.year, end.month, end.day) == (end_day.year, end_day.month, end_day.day)
    assert (end.hour, end.minute, end.second) == (23, 59, 59)


def test_parse_event_single_day_date_only_end_is_dropped(make_spider, fake_response):
    body = load("detail_multiday.html")
    start = datetime.now() + timedelta(days=5)
    body = body.replace(SAVED_START, start.strftime("%Y-%m-%dT19:30:00+02:00"))
    body = body.replace(SAVED_END, f'"endDate":"{start:%Y-%m-%d}"')
    (event,) = make_spider(IabiletSpider).parse_event(fake_response(DETAIL_URL, body=body))
    assert event["end_at"] is None


def test_parse_event_address_city_not_duplicated(make_spider, fake_response):
    (event,), _ = run_event(make_spider(IabiletSpider), fake_response)
    assert event["venue"]["address"] == "Strada Brassai Sámuel 12, Cluj-Napoca"


def test_parse_event_images(make_spider, fake_response):
    (event,), _ = run_event(make_spider(IabiletSpider), fake_response)
    assert "/506x716/" in event["image_url"]
    assert "/fit-in/1200x1200/" in event["image_url_large"]
    assert event["image_url"] != event["image_url_large"]


def test_parse_event_free(make_spider, fake_response):
    (event,), _ = run_event(make_spider(IabiletSpider), fake_response, "detail_free.html")
    assert event["price_text"] == "0 RON"
    assert event["is_free"] is True


def test_parse_event_without_tariffs_uses_offer_price(make_spider, fake_response):
    body = load("detail_multiday.html")
    body = "\n".join(line for line in body.splitlines() if "data-tariff-sell-price" not in line)
    start = datetime.now() + timedelta(days=5)
    body = body.replace(SAVED_START, start.strftime("%Y-%m-%dT19:30:00+02:00"))
    (event,) = IabiletSpider.parse_event(
        make_spider(IabiletSpider), fake_response(DETAIL_URL, body=body)
    )
    assert event["price_text"] == "31.82 RON"


def test_cancelled_detail_is_dropped(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    events, _ = run_event(spider, fake_response, "detail_cancelled.html")
    assert events == []
    assert stat(spider, "cancelled") == 1


def test_detail_without_jsonld_is_counted(make_spider, fake_response):
    spider = make_spider(IabiletSpider)
    response = fake_response(DETAIL_URL, body="<html><body>no data</body></html>")
    assert list(spider.parse_event(response)) == []
    assert stat(spider, "no_jsonld") == 1
