import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Preia adresa bazei de date din docker-compose / .env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password123@db:5432/gocluj")

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