from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Category
from app.schemas import CategoryOut

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.id)).all()
