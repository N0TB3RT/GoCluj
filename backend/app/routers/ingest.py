import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.schemas import IngestRequest, IngestResult
from app.services.ingest import upsert_events


def require_ingest_token(x_ingest_token: str | None = Header(default=None)) -> None:
    """Reject the request unless X-Ingest-Token matches the configured shared secret."""
    expected = settings.ingest_token
    if not expected or not x_ingest_token:
        raise HTTPException(status_code=401, detail="Invalid or missing ingest token")
    if not secrets.compare_digest(x_ingest_token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing ingest token")


router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/events", response_model=IngestResult, dependencies=[Depends(require_ingest_token)])
def ingest_events(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResult:
    """Batch upsert of scraped events, keyed by (source_name, external_id)."""
    return upsert_events(db, payload.events)
