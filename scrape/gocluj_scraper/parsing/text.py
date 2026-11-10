"""Pure text helpers: cleaning, URLs, price/free detection, Romanian dates."""

import html
import math
import re
import unicodedata
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

TIMEZONE = "Europe/Bucharest"

_TRACKING_PARAMS = {"fbclid", "gclid", "ref"}
_MONTHS = {
    "ianuarie": 1, "ian": 1,
    "februarie": 2, "feb": 2,
    "martie": 3, "mar": 3,
    "aprilie": 4, "apr": 4,
    "mai": 5,
    "iunie": 6, "iun": 6,
    "iulie": 7, "iul": 7,
    "august": 8, "aug": 8,
    "septembrie": 9, "sept": 9, "sep": 9,
    "octombrie": 10, "oct": 10,
    "noiembrie": 11, "noi": 11, "nov": 11,
    "decembrie": 12, "dec": 12,
}  # fmt: skip
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_DOTTED_RE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
_DAY_MONTH_RE = re.compile(r"\b(\d{1,2})\s+([a-z]+)\.?(?:,?\s+(\d{4}))?")
_PRICE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:lei|ron|eur|€)|(?:€|eur)\s*(\d+(?:[.,]\d+)?)")


def clean_text(value: str | None, multiline: bool = False) -> str | None:
    """Unescape HTML entities, collapse whitespace; empty becomes None.

    With ``multiline=True`` line breaks are kept (max one blank line) and each line is stripped.
    """
    if value is None:
        return None
    unescaped = html.unescape(str(value))
    if not multiline:
        return " ".join(unescaped.split()) or None
    unescaped = unescaped.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in unescaped.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() or None


def strip_accents(text: str) -> str:
    """Remove diacritics (ș/ş -> s, ț/ţ -> t, ă/â -> a, î -> i)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _fold(text: str) -> str:
    return strip_accents(text).lower()


def canonical_url(url: str) -> str:
    """Drop the fragment and tracking query params (utm_*, ica_*, fbclid, gclid, ref)."""
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not (k.startswith(("utm_", "ica_")) or k in _TRACKING_PARAMS)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def detect_is_free(price_text: str | None) -> bool | None:
    """True for free wording or zero prices, False for a nonzero price, else None."""
    if not price_text:
        return None
    text = _fold(price_text)
    if re.search(r"\bgratuit|intrare libera|\bfree\b", text):
        return True
    amounts = [
        float((m.group(1) or m.group(2)).replace(",", ".")) for m in _PRICE_RE.finditer(text)
    ]
    if not amounts:
        return None
    return all(a == 0 for a in amounts)


def _amount(value) -> float | None:
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(number: float) -> str:
    return str(int(number)) if number == int(number) else f"{number:g}"


def format_price(amounts: Iterable, currency: str | None = None) -> str | None:
    """Format amounts as 'min - max CUR' (or 'x CUR' when all equal); None if no usable amount."""
    values = [a for a in map(_amount, amounts) if a is not None and math.isfinite(a)]
    if not values:
        return None
    low, high = min(values), max(values)
    text = _format_number(low)
    if high != low:
        text = f"{text} - {_format_number(high)}"
    return f"{text} {currency}" if currency else text


def is_cluj(text: str | None) -> bool:
    """Accent/case-insensitive check for 'Cluj' (covers Cluj-Napoca)."""
    return bool(text) and "cluj" in _fold(text)


def localize(dt: datetime) -> datetime:
    """Attach Europe/Bucharest to naive datetimes; keep aware ones unchanged."""
    return dt if dt.tzinfo else dt.replace(tzinfo=ZoneInfo(TIMEZONE))


def _infer_year(month: int, day: int, now: datetime) -> int:
    """Use now's year, or next year if that date is more than 60 days in the past."""
    candidate = date(now.year, month, day)
    return now.year + 1 if candidate < (now - timedelta(days=60)).date() else now.year


def _find_day_month(folded: str) -> re.Match | None:
    return next((m for m in _DAY_MONTH_RE.finditer(folded) if m.group(2) in _MONTHS), None)


def parse_ro_datetime(text: str, now: datetime | None = None) -> datetime | None:
    """Parse ISO or Romanian date text into an aware Europe/Bucharest datetime."""
    if not text or not text.strip():
        return None
    try:
        return localize(datetime.fromisoformat(text.strip()))
    except ValueError:
        pass
    now = localize(now) if now else datetime.now(ZoneInfo(TIMEZONE))
    folded = _fold(text)
    time_match = _TIME_RE.search(folded)
    hour, minute = (int(time_match.group(1)), int(time_match.group(2))) if time_match else (0, 0)
    try:
        if m := _DOTTED_RE.search(folded):
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        elif m := _find_day_month(folded):
            day, month = int(m.group(1)), _MONTHS[m.group(2)]
            year = int(m.group(3)) if m.group(3) else _infer_year(month, day, now)
        else:
            return None
        return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(TIMEZONE))
    except ValueError:
        return None
