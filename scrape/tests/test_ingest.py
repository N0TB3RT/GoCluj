import json
import logging

import pytest

from gocluj_scraper import ingest


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.text = ""


class FakeSession:
    def __init__(self, *statuses):
        self.statuses = list(statuses) or [200]
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return FakeResponse(status)


@pytest.fixture
def jsonl(tmp_path):
    path = tmp_path / "a.jsonl"
    path.write_text("\n".join(json.dumps({"title": f"E{i}"}) for i in range(5)) + "\n")
    return str(path)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(ingest.time, "sleep", lambda s: None)


def test_batches_and_token(jsonl):
    session = FakeSession(200)
    assert ingest.ingest_files([jsonl], "http://api/ingest", "secret", 2, session=session)
    assert [len(c["json"]["events"]) for c in session.calls] == [2, 2, 1]
    assert all(c["headers"] == {"X-Ingest-Token": "secret"} for c in session.calls)
    assert session.calls[0]["url"] == "http://api/ingest"


def test_dry_run_without_url(jsonl, caplog):
    session = FakeSession()
    with caplog.at_level(logging.INFO, logger="ingest"):
        assert ingest.ingest_files([jsonl], None, "", 50, session=session)
    assert session.calls == []
    assert "dry-run" in caplog.text and "5 events" in caplog.text


def test_4xx_fails_without_retry(jsonl):
    session = FakeSession(400)
    assert not ingest.ingest_files([jsonl], "http://api", "t", 50, session=session)
    assert len(session.calls) == 1


def test_5xx_retries_then_succeeds(jsonl):
    session = FakeSession(503, 200)
    assert ingest.ingest_files([jsonl], "http://api", "t", 50, session=session)
    assert len(session.calls) == 2


def test_5xx_gives_up_after_three_attempts(jsonl):
    session = FakeSession(500)
    assert not ingest.ingest_files([jsonl], "http://api", "t", 50, session=session)
    assert len(session.calls) == 3
