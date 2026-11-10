import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Preia adresa bazei de date din docker-compose / .env
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please configure it in your .env file.")

# SQLAlchemy 2.1 maps a bare postgresql:// URL to psycopg 3, which is not installed.
# Force the psycopg2 driver so existing .env files keep working.
for _prefix in ("postgresql://", "postgres://"):
    if DATABASE_URL.startswith(_prefix):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len(_prefix):]
        break

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Functie care deschide si inchide sigur conexiunea pentru fiecare cerere
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()