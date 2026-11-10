from sqlalchemy import delete, func, literal_column, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Category, Event, event_categories
from app.schemas.ingest import EventIngest, IngestResult

_CONTENT_COLUMNS = (
    "source_url",
    "title",
    "description",
    "start_at",
    "end_at",
    "venue_name",
    "venue_address",
    "venue_city",
    "lat",
    "lng",
    "price_text",
    "is_free",
    "source_category",
    "image_url",
)


def _row_values(item: EventIngest) -> dict:
    return {
        "source_name": item.source_name,
        "external_id": item.external_id,
        "source_url": item.source_url,
        "title": item.title,
        "description": item.description,
        "start_at": item.start_at,
        "end_at": item.end_at,
        "venue_name": item.venue.name,
        "venue_address": item.venue.address,
        "venue_city": item.venue.city,
        "lat": item.venue.lat,
        "lng": item.venue.lng,
        "price_text": item.price_text,
        "is_free": item.is_free,
        "source_category": item.source_category,
        "image_url": item.image_url,
    }


def upsert_events(db: Session, items: list[EventIngest]) -> IngestResult:
    """Upsert events by (source_name, external_id) and replace their category links."""
    category_ids = {name: id_ for id_, name in db.execute(select(Category.id, Category.name))}
    created = 0

    for item in items:
        values = _row_values(item)
        stmt = insert(Event).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_events_source_external_id",
            set_={
                **{col: stmt.excluded[col] for col in _CONTENT_COLUMNS},
                "updated_at": func.now(),
                "last_seen_at": func.now(),
            },
        ).returning(Event.id, literal_column("(xmax = 0)").label("inserted"))
        event_id, inserted = db.execute(stmt).one()
        created += bool(inserted)

        wanted = {category_ids[name] for name in item.categories if name in category_ids}
        db.execute(delete(event_categories).where(event_categories.c.event_id == event_id))
        if wanted:
            db.execute(
                insert(event_categories),
                [{"event_id": event_id, "category_id": cid} for cid in sorted(wanted)],
            )

    db.commit()
    return IngestResult(received=len(items), created=created, updated=len(items) - created)
