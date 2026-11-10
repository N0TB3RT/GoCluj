"""Minimal schema.org Event extraction from JSON-LD blocks."""

import json
from collections.abc import Callable
from typing import Any

from gocluj_scraper.parsing.text import format_price, strip_accents


def _has_type(node: Any, predicate: Callable[[str], bool]) -> bool:
    """True if a dict node has an @type (str or list) satisfying ``predicate``."""
    if not isinstance(node, dict):
        return False
    types = node.get("@type")
    types = [types] if isinstance(types, str) else (types or [])
    return any(isinstance(t, str) and predicate(t) for t in types)


def _is_event_type(type_name: str) -> bool:
    return type_name.endswith(("Event", "Festival"))


def _flatten(data: Any) -> list[dict]:
    """Flatten top-level lists and @graph into a flat list of dict nodes."""
    if isinstance(data, list):
        return [n for item in data for n in _flatten(item)]
    if isinstance(data, dict):
        return [data, *_flatten(data.get("@graph", []))]
    return []


def _load(raw: str) -> Any:
    try:
        return json.loads(raw, strict=False)
    except ValueError:
        return None


def _matching_nodes(response, predicate: Callable[[str], bool]) -> list[dict]:
    nodes = []
    for raw in response.css('script[type="application/ld+json"]::text').getall():
        nodes.extend(n for n in _flatten(_load(raw)) if _has_type(n, predicate))
    return nodes


def extract_jsonld_events(response) -> list[dict]:
    """Return every schema.org *Event dict found in the page's JSON-LD blocks."""
    return _matching_nodes(response, _is_event_type)


def extract_jsonld_nodes(response, type_name: str) -> list[dict]:
    """Return every JSON-LD node whose @type equals ``type_name``."""
    return _matching_nodes(response, lambda t: t == type_name)


def breadcrumb_name(response, position: int) -> str | None:
    """Name at ``itemListElement[position]`` of the first BreadcrumbList that has one."""
    for crumb in extract_jsonld_nodes(response, "BreadcrumbList"):
        entries = crumb.get("itemListElement")
        if isinstance(entries, list) and len(entries) > position:
            entry = entries[position]
            name = entry.get("name") if isinstance(entry, dict) else None
            if isinstance(name, str):
                return name
    return None


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def _image(value: Any) -> str | None:
    value = _first(value)
    if isinstance(value, dict):
        value = value.get("url")
    return value if isinstance(value, str) else None


def _text(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


def _norm(text: str) -> str:
    """Casefold, strip accents, whitespace and a trailing comma for comparison."""
    return strip_accents(text).casefold().strip().rstrip(",").rstrip()


def _address(value: Any) -> tuple[str | None, str | None]:
    """Return (full address, city) from a string or PostalAddress."""
    if isinstance(value, str):
        return value, None
    if not isinstance(value, dict):
        return None, None
    street, city = value.get("streetAddress"), value.get("addressLocality")
    if street and city and _norm(street).endswith(_norm(city)):
        return street, city
    return ", ".join(p for p in (street, city) if p) or None, city


def _venue(location: Any) -> dict:
    location = _first(location)
    if isinstance(location, str):
        return {"name": location}
    if not isinstance(location, dict):
        return {}
    address, city = _address(location.get("address"))
    geo = location.get("geo") or {}
    venue = {
        "name": location.get("name"),
        "address": address,
        "city": city,
        "lat": _to_float(geo.get("latitude")),
        "lng": _to_float(geo.get("longitude")),
    }
    return {k: v for k, v in venue.items() if v is not None}


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _price_text(offers: Any) -> str | None:
    """Build e.g. '59 - 99 RON' from an Offer, AggregateOffer or a list of offers."""
    amounts: list[Any] = []
    currency = None
    for offer in offers if isinstance(offers, list) else [offers]:
        if not isinstance(offer, dict):
            continue
        currency = currency or offer.get("priceCurrency")
        amounts.extend(offer.get(key) for key in ("lowPrice", "price", "highPrice"))
    return format_price(amounts, currency)


def jsonld_to_fields(data: dict) -> dict:
    """Map a schema.org Event dict to ``make_event`` kwargs (None values omitted)."""
    fields = {
        "title": _text(data.get("name")),
        "description": _text(data.get("description")),
        "start_at": data.get("startDate"),
        "end_at": data.get("endDate"),
        "source_url": data.get("url"),
        "image_url": _image(data.get("image")),
        "venue": _venue(data.get("location")) or None,
        "price_text": _price_text(data.get("offers")),
    }
    return {k: v for k, v in fields.items() if v is not None}
