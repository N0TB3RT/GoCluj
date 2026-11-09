from pathlib import Path

import pytest
from scrapy.http import HtmlResponse, Request, TextResponse

FIXTURES = Path(__file__).parent / "fixtures"


def fake_response(
    url: str, body: str | bytes | None = None, fixture: str | None = None
) -> TextResponse:
    """Build a Scrapy response from inline ``body`` or a file in tests/fixtures/."""
    if fixture is not None:
        body = (FIXTURES / fixture).read_bytes()
    if isinstance(body, str):
        body = body.encode("utf8")
    cls = TextResponse if (fixture or url).endswith(".json") else HtmlResponse
    return cls(url=url, body=body or b"", encoding="utf8", request=Request(url))


@pytest.fixture(name="fake_response")
def _fake_response_fixture():
    return fake_response
