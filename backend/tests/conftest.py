import os
from collections.abc import Iterator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.core.config import settings
from app.db import DATABASE_URL, get_db
from app.main import app

TEST_TOKEN = "test-token"


def _test_database_url() -> str:
    url = make_url(DATABASE_URL)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


def _ensure_database(test_url: str) -> None:
    """Create the test database on the same server if it does not exist yet."""
    target = make_url(test_url)
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine():
    test_url = _test_database_url()
    _ensure_database(test_url)

    config = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    config.attributes["url"] = test_url
    command.upgrade(config, "head")

    test_engine = create_engine(test_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(engine) -> Iterator[None]:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE events, event_categories RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db_session(engine) -> Iterator:
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def ingest_token(monkeypatch) -> str:
    monkeypatch.setattr(settings, "ingest_token", TEST_TOKEN)
    return TEST_TOKEN


@pytest.fixture
def client(engine) -> Iterator[TestClient]:
    factory = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth() -> dict[str, str]:
    return {"X-Ingest-Token": TEST_TOKEN}
