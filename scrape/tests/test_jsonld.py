import json

from gocluj_scraper.parsing.jsonld import (
    breadcrumb_name,
    extract_jsonld_events,
    extract_jsonld_nodes,
    jsonld_to_fields,
)
from tests.conftest import fake_response

MUSIC_EVENT = {
    "@context": "https://schema.org",
    "@type": "MusicEvent",
    "name": "Concert  Test",
    "description": "Desc",
    "startDate": "2026-11-20T20:00:00+02:00",
    "endDate": "2026-11-20T23:00:00+02:00",
    "url": "https://www.iabilet.ro/bilete-concert-123/",
    "image": ["https://img.example/a.jpg"],
    "location": {
        "@type": "Place",
        "name": "Sala Polivalenta",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "Str. Uzinei 1",
            "addressLocality": "Cluj-Napoca",
        },
        "geo": {"latitude": "46.77", "longitude": 23.6},
    },
    "offers": {
        "@type": "AggregateOffer",
        "lowPrice": "59",
        "highPrice": 99,
        "priceCurrency": "RON",
    },
}


def _page(*blocks: str) -> str:
    scripts = "".join(f'<script type="application/ld+json">{b}</script>' for b in blocks)
    return f"<html><head>{scripts}</head><body></body></html>"


def test_extract_single_event():
    resp = fake_response("https://x.ro/", _page(json.dumps(MUSIC_EVENT)))
    assert extract_jsonld_events(resp) == [MUSIC_EVENT]


def test_extract_graph_and_list_and_invalid():
    graph = {"@graph": [{"@type": "WebSite"}, MUSIC_EVENT]}
    listing = [{"@type": ["Thing", "Festival"], "name": "F"}, {"@type": "Organization"}]
    resp = fake_response(
        "https://x.ro/", _page("{not json", json.dumps(graph), json.dumps(listing))
    )
    names = [e["name"] for e in extract_jsonld_events(resp)]
    assert names == ["Concert  Test", "F"]


def test_jsonld_to_fields():
    fields = jsonld_to_fields(MUSIC_EVENT)
    assert fields == {
        "title": "Concert  Test",
        "description": "Desc",
        "start_at": "2026-11-20T20:00:00+02:00",
        "end_at": "2026-11-20T23:00:00+02:00",
        "source_url": "https://www.iabilet.ro/bilete-concert-123/",
        "image_url": "https://img.example/a.jpg",
        "venue": {
            "name": "Sala Polivalenta",
            "address": "Str. Uzinei 1, Cluj-Napoca",
            "city": "Cluj-Napoca",
            "lat": 46.77,
            "lng": 23.6,
        },
        "price_text": "59 - 99 RON",
    }


def test_jsonld_to_fields_free_offer_and_image_object():
    fields = jsonld_to_fields(
        {
            "name": "X",
            "image": {"@type": "ImageObject", "url": "https://i/x.png"},
            "offers": [{"price": 0, "priceCurrency": "RON"}],
        }
    )
    assert fields == {"title": "X", "image_url": "https://i/x.png", "price_text": "0 RON"}


def test_extract_jsonld_nodes_shapes():
    graph = {"@graph": [{"@type": "WebSite"}, {"@type": "BreadcrumbList", "id": 1}]}
    listing = [{"@type": ["Thing", "BreadcrumbList"], "id": 2}, {"@type": "Organization"}]
    resp = fake_response(
        "https://x.ro/",
        _page(
            "{not json",
            json.dumps({"@type": "BreadcrumbList", "id": 0}),
            json.dumps(graph),
            json.dumps(listing),
        ),
    )
    nodes = extract_jsonld_nodes(resp, "BreadcrumbList")
    assert [n["id"] for n in nodes] == [0, 1, 2]
    assert extract_jsonld_nodes(resp, "Missing") == []


def _breadcrumb(*names: str) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n} for i, n in enumerate(names)
        ],
    }


def test_breadcrumb_name_found_skipping_short_lists():
    resp = fake_response(
        "https://x.ro/",
        _page(json.dumps(_breadcrumb("Home")), json.dumps(_breadcrumb("A", "B", "Concerte"))),
    )
    assert breadcrumb_name(resp, 2) == "Concerte"


def test_breadcrumb_name_out_of_range_or_missing():
    short = fake_response("https://x.ro/", _page(json.dumps(_breadcrumb("A", "B"))))
    assert breadcrumb_name(short, 2) is None
    none = fake_response("https://x.ro/", _page(json.dumps(MUSIC_EVENT)))
    assert breadcrumb_name(none, 2) is None


def test_address_does_not_duplicate_city():
    def venue(street):
        return jsonld_to_fields(
            {
                "name": "X",
                "location": {
                    "name": "V",
                    "address": {"streetAddress": street, "addressLocality": "Cluj-Napoca"},
                },
            }
        )["venue"]

    streets = (
        "Strada X 12, Cluj-Napoca",
        " Strada X 12, cluj-napoca, ",
        "Strada X 12, Cluj-Napoca,",
    )
    for street in streets:
        v = venue(street)
        assert v["address"] == street
        assert v["city"] == "Cluj-Napoca"
    assert venue("Strada X 12")["address"] == "Strada X 12, Cluj-Napoca"
    assert venue("Strada Țării 1, Cluj-Napoca")["address"] == "Strada Țării 1, Cluj-Napoca"
    postcode = "Strada Bucium 2, Cluj-Napoca 400535"
    assert venue(postcode)["address"] == postcode
    assert venue("Str. Horea 5, CLUJ-NAPOCA, jud. Cluj")["address"] == (
        "Str. Horea 5, CLUJ-NAPOCA, jud. Cluj"
    )


def test_address_city_must_match_whole_words():
    def address(street, city):
        node = {"location": {"address": {"streetAddress": street, "addressLocality": city}}}
        return jsonld_to_fields({"name": "X", **node})["venue"]["address"]

    assert address("Strada Clujului 5", "Cluj") == "Strada Clujului 5, Cluj"
    assert address("Strada Napoca 5", "Cluj-Napoca") == "Strada Napoca 5, Cluj-Napoca"
    assert address("Str. Mare 1, Cluj 400000", "Cluj") == "Str. Mare 1, Cluj 400000"
