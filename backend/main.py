from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import models
import schemas
from database import engine, get_db

app = FastAPI(title="GoCluj API")

@app.post("/api/events")
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    # .model_dump() este metoda noua din Pydantic v2 pentru a extrage dictionarul
    db_event = models.Event(**event.model_dump())
    
    try:
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return {"message": "Eveniment salvat cu succes!", "id": db_event.id}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="Acest eveniment (source_url) există deja în baza de date."
        )
    
@app.get("/api/events", response_model=list[schemas.EventResponse])
def get_events(db: Session = Depends(get_db)):

    events = db.query(models.Event).order_by(
        models.Event.event_date.asc()
    ).all()

    return events