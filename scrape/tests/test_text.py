from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from gocluj_scraper.parsing.text import (
    canonical_url,
    clean_text,
    detect_is_free,
    is_cluj,
    parse_ro_datetime,
    strip_accents,
)

TZ = ZoneInfo("Europe/Bucharest")
NOW = datetime(2026, 11, 9, 12, 0, tzinfo=TZ)


def test_clean_text():
    assert clean_text("  Foo &amp;\n  bar\t") == "Foo & bar"
    assert clean_text("   ") is None
    assert clean_text(None) is None


def test_strip_accents():
    assert strip_accents("Ședință Țară ăâî ş ţ") == "Sedinta Tara aai s t"


def test_canonical_url():
    url = "https://x.ro/e/1?ica_source=a&id=5&utm_source=f&fbclid=z&b=2#top "
    assert canonical_url(url) == "https://x.ro/e/1?id=5&b=2"
    assert canonical_url("https://x.ro/e/1?ica_source=a") == "https://x.ro/e/1"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Gratuit", True),
        ("Intrare liberă", True),
        ("intrare libera", True),
        ("Free entry", True),
        ("0 lei", True),
        ("0 RON", True),
        ("59 - 99 RON", False),
        ("de la 20 lei", False),
        ("€ 15", False),
        ("Vezi pe site", None),
        (None, None),
    ],
)
def test_detect_is_free(text, expected):
    assert detect_is_free(text) is expected


def test_is_cluj():
    assert is_cluj("Cluj-Napoca")
    assert is_cluj("CLUJ NAPOCA")
    assert is_cluj("Sala Polivalentă, cluj")
    assert not is_cluj("București")
    assert not is_cluj(None)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("6 noiembrie 2026, 22:00", datetime(2026, 11, 6, 22, 0, tzinfo=TZ)),
        ("Vineri, 6 Noiembrie 2026", datetime(2026, 11, 6, 0, 0, tzinfo=TZ)),
        ("09 nov", datetime(2026, 11, 9, 0, 0, tzinfo=TZ)),
        ("09 nov 2026 19:30", datetime(2026, 11, 9, 19, 30, tzinfo=TZ)),
        ("06.11.2026 20:00", datetime(2026, 11, 6, 20, 0, tzinfo=TZ)),
        ("2026-11-06T20:00:00+02:00", datetime(2026, 11, 6, 20, 0, tzinfo=TZ)),
        ("2026-11-06T20:00:00", datetime(2026, 11, 6, 20, 0, tzinfo=TZ)),
        ("15 mar", datetime(2027, 3, 15, 0, 0, tzinfo=TZ)),  # >60 days past -> next year
        ("15 sept 2026", datetime(2026, 9, 15, 0, 0, tzinfo=TZ)),
        ("1 dec", datetime(2026, 12, 1, 0, 0, tzinfo=TZ)),
        ("2 ian", datetime(2027, 1, 2, 0, 0, tzinfo=TZ)),
    ],
)
def test_parse_ro_datetime(text, expected):
    result = parse_ro_datetime(text, now=NOW)
    assert result == expected
    assert result.tzinfo is not None


def test_parse_ro_datetime_recent_past_keeps_year():
    assert parse_ro_datetime("1 oct", now=NOW) == datetime(2026, 10, 1, tzinfo=TZ)


@pytest.mark.parametrize("text", ["", "mâine seara", "31 februarie 2026", "foo 12"])
def test_parse_ro_datetime_unparseable(text):
    assert parse_ro_datetime(text, now=NOW) is None


def test_clean_text_default_is_single_line():
    assert clean_text("a\r\nb\n\n\nc") == "a b c"


def test_clean_text_multiline():
    assert clean_text("a\r\nb\rc", multiline=True) == "a\nb\nc"
    assert clean_text("  a \t b\u00a0 c  \n  d  ", multiline=True) == "a b c\nd"
    assert clean_text("a\n\n\n\n\nb\n\nc", multiline=True) == "a\n\nb\n\nc"
    assert clean_text("x&nbsp;&amp;&nbsp;y", multiline=True) == "x & y"
    assert clean_text(" \r\n \n", multiline=True) is None
    assert clean_text(None, multiline=True) is None
