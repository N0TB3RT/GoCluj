from datetime import UTC, datetime, timedelta

from tests.test_ingest import URL, make_event


def ingest(client, auth, *events):
    response = client.post(URL, json={"events": list(events)}, headers=auth)
    assert response.status_code == 200


def at(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def test_past_events_hidden_from_list_but_visible_in_detail(client, auth):
    past = make_event("past", start_at=at(-5), end_at=at(-4))
    future = make_event("future", start_at=at(5))
    ingest(client, auth, past, future)

    page = client.get("/api/events").json()
    assert page["total"] == 1
    assert [e["title"] for e in page["items"]] == ["Title"]
    assert page["items"][0]["source_url"].endswith("/future")

    past_id = 1  # first ingested row; identities are reset between tests
    detail = client.get(f"/api/events/{past_id}")
    assert detail.status_code == 200
    assert detail.json()["source_url"].endswith("/past")


def test_event_still_running_is_listed(client, auth):
    running = make_event("run", start_at=at(-1), end_at=at(1))
    ingest(client, auth, running)
    assert client.get("/api/events").json()["total"] == 1


def test_ordering_pagination_and_total(client, auth):
    events = [make_event(f"e{i}", title=f"T{i}", start_at=at(10 - i)) for i in range(5)]
    ingest(client, auth, *events)

    page = client.get("/api/events?limit=2&offset=0").json()
    assert page["total"] == 5
    assert page["limit"] == 2 and page["offset"] == 0
    assert [e["title"] for e in page["items"]] == ["T4", "T3"]

    page = client.get("/api/events?limit=2&offset=2").json()
    assert [e["title"] for e in page["items"]] == ["T2", "T1"]

    page = client.get("/api/events?limit=2&offset=4").json()
    assert [e["title"] for e in page["items"]] == ["T0"]


def test_limit_and_offset_validation(client):
    assert client.get("/api/events?limit=0").status_code == 422
    assert client.get("/api/events?limit=101").status_code == 422
    assert client.get("/api/events?offset=-1").status_code == 422


def test_event_shape(client, auth):
    ingest(
        client,
        auth,
        make_event(
            image_url="https://example.com/i.jpg", image_url_large="https://example.com/i-large.jpg"
        ),
    )
    item = client.get("/api/events").json()["items"][0]
    assert set(item) == {
        "id", "source_name", "source_url", "title", "description", "start_at", "end_at",
        "venue", "price_text", "is_free", "categories", "source_category", "image_url",
        "image_url_large",
    }  # fmt: skip
    assert item["venue"] == {
        "name": "Hall", "address": "Str. 1", "city": "Cluj-Napoca", "lat": 46.7, "lng": 23.6,
    }  # fmt: skip
    assert item["image_url_large"] == "https://example.com/i-large.jpg"
    assert datetime.fromisoformat(item["start_at"]).tzinfo is not None


def test_detail_404(client):
    response = client.get("/api/events/999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found"}


def test_categories_list(client):
    response = client.get("/api/categories")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 8
    assert [c["id"] for c in items] == sorted(c["id"] for c in items)
    assert items[0]["name"] == "Party"
    assert items[-1]["name"] == "Altele"
