import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import settings

URL = "/api/ingest/events"
FIXTURE = Path(__file__).parent / "fixtures" / "livetickets_sample.jsonl"


def make_event(external_id="e1", **overrides):
    start = datetime.now(UTC) + timedelta(days=10)
    event = {
        "source_name": "Test",
        "source_url": f"https://example.com/{external_id}",
        "external_id": external_id,
        "title": "Title",
        "description": None,
        "start_at": start.isoformat(),
        "end_at": None,
        "venue": {
            "name": "Hall",
            "address": "Str. 1",
            "city": "Cluj-Napoca",
            "lat": 46.7,
            "lng": 23.6,
        },
        "price_text": "10 RON",
        "is_free": False,
        "categories": [],
        "source_category": None,
        "image_url": None,
    }
    event.update(overrides)
    return event


def test_missing_token_is_401(client):
    assert client.post(URL, json={"events": []}).status_code == 401


def test_wrong_token_is_401(client):
    response = client.post(URL, json={"events": []}, headers={"X-Ingest-Token": "nope"})
    assert response.status_code == 401


def test_unset_token_setting_is_401(client, monkeypatch):
    monkeypatch.setattr(settings, "ingest_token", "")
    response = client.post(URL, json={"events": []}, headers={"X-Ingest-Token": ""})
    assert response.status_code == 401
    response = client.post(URL, json={"events": []}, headers={"X-Ingest-Token": "anything"})
    assert response.status_code == 401


def test_extra_field_is_422(client, auth):
    event = make_event(unexpected="x")
    assert client.post(URL, json={"events": [event]}, headers=auth).status_code == 422


def test_extra_venue_field_is_422(client, auth):
    event = make_event()
    event["venue"]["zip"] = "400000"
    assert client.post(URL, json={"events": [event]}, headers=auth).status_code == 422


def test_more_than_500_events_is_422(client, auth):
    events = [make_event(f"e{i}") for i in range(501)]
    assert client.post(URL, json={"events": events}, headers=auth).status_code == 422


def test_create_then_update(client, auth):
    first = client.post(URL, json={"events": [make_event()]}, headers=auth)
    assert first.status_code == 200
    assert first.json() == {"received": 1, "created": 1, "updated": 0}

    changed = make_event(title="New title", description="Line 1\nLine 2", is_free=None)
    second = client.post(URL, json={"events": [changed]}, headers=auth)
    assert second.json() == {"received": 1, "created": 0, "updated": 1}

    page = client.get("/api/events").json()
    assert page["total"] == 1
    item = page["items"][0]
    assert item["title"] == "New title"
    assert item["description"] == "Line 1\nLine 2"
    assert item["is_free"] is None


def test_batch_counts_mixed(client, auth):
    client.post(URL, json={"events": [make_event("a")]}, headers=auth)
    result = client.post(URL, json={"events": [make_event("a"), make_event("b")]}, headers=auth)
    assert result.json() == {"received": 2, "created": 1, "updated": 1}


def test_same_external_id_different_source_is_separate(client, auth):
    events = [make_event("x", source_name="A"), make_event("x", source_name="B")]
    result = client.post(URL, json={"events": events}, headers=auth)
    assert result.json()["created"] == 2


def test_categories_are_linked_by_name_and_replaced(client, auth):
    event = make_event(categories=["Party", "Sport", "Unknown"])
    client.post(URL, json={"events": [event]}, headers=auth)
    item = client.get("/api/events").json()["items"][0]
    assert item["categories"] == ["Party", "Sport"]

    client.post(URL, json={"events": [make_event(categories=["Cultură"])]}, headers=auth)
    item = client.get("/api/events").json()["items"][0]
    assert item["categories"] == ["Cultură"]


def test_livetickets_sample_contract(client, auth):
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines if line.strip()]
    assert len(events) == 3
    response = client.post(URL, json={"events": events}, headers=auth)
    assert response.status_code == 200
    assert response.json() == {"received": 3, "created": 3, "updated": 0}
    assert client.get("/api/events").json()["total"] == 3
