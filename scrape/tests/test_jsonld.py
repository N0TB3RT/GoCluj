import json

from gocluj_scraper.parsing.jsonld import extract_jsonld_events, jsonld_to_fields
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
