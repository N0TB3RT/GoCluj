from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event
from app.schemas import EventOut, EventPage, VenueOut

router = APIRouter(prefix="/api/events", tags=["events"])


def to_event_out(event: Event) -> EventOut:
    return EventOut(
        id=event.id,
        source_name=event.source_name,
        source_url=event.source_url,
        title=event.title,
        description=event.description,
        start_at=event.start_at,
        end_at=event.end_at,
        venue=VenueOut(
            name=event.venue_name,
            address=event.venue_address,
            city=event.venue_city,
            lat=event.lat,
            lng=event.lng,
        ),
        price_text=event.price_text,
        is_free=event.is_free,
        categories=[category.name for category in event.categories],
        source_category=event.source_category,
        image_url=event.image_url,
    )


@router.get("", response_model=EventPage)
def list_events(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> EventPage:
    """Upcoming events (not yet ended), ordered by start time."""
    upcoming = func.coalesce(Event.end_at, Event.start_at) >= func.now()
    total = db.scalar(select(func.count()).select_from(Event).where(upcoming)) or 0
    events = db.scalars(
        select(Event).where(upcoming).order_by(Event.start_at, Event.id).limit(limit).offset(offset)
    ).all()
    return EventPage(
        items=[to_event_out(e) for e in events], total=total, limit=limit, offset=offset
    )


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)) -> EventOut:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return to_event_out(event)
