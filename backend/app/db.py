from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

DATABASE_URL = settings.database_url

# SQLAlchemy 2.1 maps a bare postgresql:// URL to psycopg 3, which is not installed.
# Force the psycopg2 driver so existing .env files keep working.
for _prefix in ("postgresql://", "postgres://"):
    if DATABASE_URL.startswith(_prefix):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len(_prefix) :]
        break

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """Open a session per request and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
