import asyncio
import copy
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from gocluj_scraper.spiders.livetickets import LiveticketsSpider

FIXTURES = Path(__file__).parent / "fixtures"

LIST_URL = "https://api.livetickets.ro/public/events"
DETAIL_URL = LIST_URL + "/getbyurl?url=balul-dintilor-de-lapte-1"


def load(fixture):
    return json.loads((FIXTURES / "livetickets" / fixture).read_text(encoding="utf8"))


def future(days, hour=21):
    day = datetime.now() + timedelta(days=days)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def stat(spider, key):
    return spider.crawler.stats.get_value(f"events/{key}")


def run_parse(spider, fake_response, items=None):
    body = json.dumps(items) if items is not None else None
    fixture = None if items is not None else "livetickets/events.json"
    response = fake_response(LIST_URL, body=body, fixture=fixture)
    return list(spider.parse(response))


def run_event(spider, fake_response, item=None, detail=None):
    item = copy.deepcopy(item or load("events.json")[0])
    item["start_date"], item["end_date"] = future(3), future(4, 5)
    detail = detail or load("event_detail.json")
    response = fake_response(DETAIL_URL, body=json.dumps(detail))
    return list(spider.parse_event(response, item=item)), item


def test_start_requests_list_endpoint(make_spider):
    spider = make_spider(LiveticketsSpider)

    async def first():
        return [request async for request in spider.start()]

    (request,) = asyncio.run(first())
    assert request.url == LIST_URL
    assert request.headers.get("Accept") == b"application/json"


def test_parse_yields_detail_requests_for_cluj_only(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    requests = run_parse(spider, fake_response)
    items = load("events.json")
    assert all(r.headers.get("Accept") == b"application/json" for r in requests)
    assert [r.url for r in requests] == [
        LIST_URL + "/getbyurl?url=balul-dintilor-de-lapte-1",
        LIST_URL + "/getbyurl?url=galant-featuring-tzanca-uraganu-the-king-is-back-party",
    ]
    assert all(r.callback == spider.parse_event for r in requests)
    assert requests[0].cb_kwargs == {"item": items[0]}
    assert requests[1].cb_kwargs == {"item": items[4]}
    assert stat(spider, "not_cluj") == 1
    assert stat(spider, "no_city") == 2


def test_parse_url_encodes_slug(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    item = load("events.json")[0] | {"url": "a b/c&d"}
    (request,) = run_parse(spider, fake_response, [item])
    assert request.url.endswith("getbyurl?url=a%20b%2Fc%26d")


def test_parse_empty_list_logs_error(make_spider, fake_response, caplog):
    spider = make_spider(LiveticketsSpider)
    with caplog.at_level(logging.ERROR):
        assert run_parse(spider, fake_response, []) == []
    assert any(r.levelno == logging.ERROR for r in caplog.records)


def test_parse_event_maps_fields(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    (event,), item = run_event(spider, fake_response)
    assert event["external_id"] == "76fca833-4112-45d5-933f-e4aaa11480a5"
    assert event["source_url"] == "https://www.livetickets.ro/bilete/balul-dintilor-de-lapte-1"
    assert event["title"] == "Balul “Dinților de Lapte”"
    venue = event["venue"]
    assert venue["name"] == "MATTER"
    assert venue["address"] == "Str. Universității 3"
    assert venue["city"] == "Cluj-Napoca"
    assert (venue["lat"], venue["lng"]) == (46.7680736, 23.5902744)
    assert event["price_text"] == "30 - 35 RON"
    assert event["source_category"] == "divertisment"
    assert event["start_at"].startswith(item["start_date"])
    assert event["start_at"][19:] in ("+02:00", "+03:00")
    assert event["end_at"][19:] in ("+02:00", "+03:00")
    assert stat(spider, "valid") == 1


def test_parse_event_cleans_html_description(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    item = load("events.json")[3]
    (event,), _ = run_event(spider, fake_response, item=item)
    assert "<br" not in event["description"]
    assert "&icirc;" not in event["description"]
    assert event["description"].startswith("THE MUSIC - THE OUTDOORS - THE EXPERIENCE\n")
    assert "în vârf de munte" in event["description"]


def test_parse_event_zero_price_is_not_free(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    item = load("events.json")[0] | {"price_min": 0.0, "price_max": 0.0}
    (event,), _ = run_event(spider, fake_response, item=item)
    assert event["price_text"] is None
    assert event["is_free"] is None


def test_parse_event_missing_currency_and_price(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    item = load("events.json")[0] | {"currency": None, "price_min": None, "price_max": None}
    (event,), _ = run_event(spider, fake_response, item=item)
    assert event["price_text"] is None
    item = load("events.json")[0] | {"currency": None}
    (event,), _ = run_event(spider, fake_response, item=item)
    assert event["price_text"] == "30 - 35"


def test_parse_event_non_online_status_is_skipped(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    detail = load("event_detail.json") | {"status": "sold_out"}
    events, _ = run_event(spider, fake_response, detail=detail)
    assert events == []
    assert stat(spider, "status_sold_out") == 1


def test_parse_event_county_city_is_not_cluj(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    detail = load("event_detail.json")
    detail["location"]["city"] = "Cluj"
    events, _ = run_event(spider, fake_response, detail=detail)
    assert events == []
    assert stat(spider, "not_cluj") == 1


def test_parse_event_missing_city_is_not_cluj(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    detail = load("event_detail.json")
    del detail["location"]["city"]
    events, _ = run_event(spider, fake_response, detail=detail)
    assert events == []
    assert stat(spider, "not_cluj") == 1


def test_parse_event_city_case_and_whitespace_accepted(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    detail = load("event_detail.json")
    detail["location"]["city"] = "CLUJ-NAPOCA "
    events, _ = run_event(spider, fake_response, detail=detail)
    assert len(events) == 1


def test_parse_event_time_slots_counted_and_emitted(make_spider, fake_response, caplog):
    spider = make_spider(LiveticketsSpider)
    detail = load("event_detail.json") | {"has_time_slots": True}
    with caplog.at_level(logging.WARNING):
        events, _ = run_event(spider, fake_response, detail=detail)
    assert len(events) == 1
    assert stat(spider, "time_slots") == 1
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_parse_event_overnight_event_is_kept(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    item = load("events.json")[0] | {"start_date": future(-1, 23), "end_date": future(0, 23)}
    # end is today 23:00 local: still in the future unless the test runs after that hour
    if datetime.now().hour >= 23:
        item["end_date"] = future(1, 5)
    response = fake_response(DETAIL_URL, body=json.dumps(load("event_detail.json")))
    events = list(spider.parse_event(response, item=item))
    assert len(events) == 1
    assert stat(spider, "past") is None


def test_parse_event_zero_coordinates_become_none(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    detail = load("event_detail.json")
    detail["location"]["lat"] = 0.0
    detail["location"]["lng"] = 0.0
    (event,), _ = run_event(spider, fake_response, detail=detail)
    assert event["venue"]["lat"] is None
    assert event["venue"]["lng"] is None


def test_parse_event_without_category_tag(make_spider, fake_response):
    spider = make_spider(LiveticketsSpider)
    detail = load("event_detail.json")
    detail["item_tags"] = [t for t in detail["item_tags"] if t["type"] != "Category"]
    (event,), _ = run_event(spider, fake_response, detail=detail)
    assert event["source_category"] is None


IMAGE = "https://livetickets-cdn.azureedge.net/itemimages/balul-dintilor-de-lapte-1/"


def test_parse_event_image_url_prefers_medium(make_spider, fake_response):
    (event,), _ = run_event(make_spider(LiveticketsSpider), fake_response)
    assert event["image_url"] == IMAGE + "Background_MEDIUM.jpg"


def test_parse_event_image_url_falls_back_to_square(make_spider, fake_response):
    detail = load("event_detail.json")
    detail["images"] = [i for i in detail["images"] if i["size"] != "MEDIUM"]
    (event,), _ = run_event(make_spider(LiveticketsSpider), fake_response, detail=detail)
    assert event["image_url"] == IMAGE + "Background_SQUARE.jpg"


def test_parse_event_image_url_falls_back_to_list_item(make_spider, fake_response):
    detail = load("event_detail.json") | {"images": []}
    item = load("events.json")[0]
    item["images"] = [{"name": "Background", "path": "x y/Background_MEDIUM.jpg", "size": "MEDIUM"}]
    (event,), _ = run_event(make_spider(LiveticketsSpider), fake_response, item=item, detail=detail)
    assert event["image_url"] == (
        "https://livetickets-cdn.azureedge.net/itemimages/x%20y/Background_MEDIUM.jpg"
    )
    assert event["image_url_large"] == event["image_url"]


def test_parse_event_image_url_large_prefers_zoom(make_spider, fake_response):
    (event,), _ = run_event(make_spider(LiveticketsSpider), fake_response)
    assert event["image_url_large"] == IMAGE + "Background_ZOOM.jpg"


def test_parse_event_image_url_large_falls_back_to_medium(make_spider, fake_response):
    detail = load("event_detail.json") | {"images": []}
    item = load("events.json")[0]
    item["images"] = [{"name": "Background", "path": "a/Background_MEDIUM.jpg", "size": "MEDIUM"}]
    (event,), _ = run_event(make_spider(LiveticketsSpider), fake_response, item=item, detail=detail)
    assert event["image_url_large"] == (
        "https://livetickets-cdn.azureedge.net/itemimages/a/Background_MEDIUM.jpg"
    )


def test_parse_event_image_url_never_uses_ticket_images(make_spider, fake_response):
    detail = load("event_detail.json")
    detail["images"] = [i for i in detail["images"] if i["name"] != "Background"]
    item = load("events.json")[0] | {"images": []}
    (event,), _ = run_event(make_spider(LiveticketsSpider), fake_response, item=item, detail=detail)
    assert event["image_url"] is None
    assert event["image_url_large"] is None
