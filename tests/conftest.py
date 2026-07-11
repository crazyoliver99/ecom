"""Shared test fixtures.

Tests run against a real PostgreSQL database. The URL comes from
TEST_DATABASE_URL, falling back to DATABASE_URL (see .env.example).
"""

import argparse
import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="session")
def db_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        # Fall back to the local .env file, same as the application does.
        try:
            from app.core.config import Settings

            url = Settings().database_url
        except Exception:
            pytest.exit(
                "Set TEST_DATABASE_URL or DATABASE_URL (or create a .env file, see "
                ".env.example) pointing at a PostgreSQL database to run the tests.",
                returncode=1,
            )
    return url


@pytest.fixture(scope="session")
def alembic_config(db_url: str) -> Config:
    cfg = Config("alembic.ini")
    # Equivalent of `alembic -x db_url=... upgrade head` — migrations/env.py
    # reads this so tests never depend on cached application settings.
    cfg.cmd_opts = argparse.Namespace(x=[f"db_url={db_url}"])
    return cfg


@pytest.fixture(scope="session")
def migrated_db(alembic_config: Config, db_url: str):
    """Ensure the schema is at head for tests that need tables."""
    command.upgrade(alembic_config, "head")
    yield db_url


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
