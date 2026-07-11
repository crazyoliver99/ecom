"""Shared test fixtures.

SAFETY: tests run migrations up AND DOWN, which destroys data. They therefore
require a DEDICATED test database via TEST_DATABASE_URL and refuse to run
against anything else. There is deliberately NO fallback to DATABASE_URL.
"""

import os

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tests.db_safety import load_test_database_url, make_alembic_config


@pytest.fixture(scope="session")
def db_url() -> str:
    """The dedicated test-database URL. Exits with instructions if missing/unsafe."""
    try:
        return load_test_database_url(os.environ)
    except RuntimeError as exc:
        pytest.exit(str(exc), returncode=1)


@pytest.fixture(scope="session")
def alembic_config(db_url: str):
    return make_alembic_config(db_url)


@pytest.fixture(scope="session")
def migrated_db(alembic_config, db_url: str):
    """Schema at Alembic head for tests that need tables — and guaranteed to be
    left at head again when the whole suite finishes."""
    command.upgrade(alembic_config, "head")
    yield db_url
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session")
def engine(migrated_db: str):
    eng = create_engine(migrated_db)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine) -> Session:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def client(migrated_db: str, monkeypatch) -> TestClient:
    """A TestClient against the real app, pointed at the test database."""
    monkeypatch.setenv("DATABASE_URL", migrated_db)

    # Reset cached settings/engine so the app picks up the test URL.
    import app.core.config as config_module
    import app.core.db as db_module

    config_module.get_settings.cache_clear()
    db_module._engine = None
    db_module._session_factory = None

    from app.main import create_app

    return TestClient(create_app(), raise_server_exceptions=False)
