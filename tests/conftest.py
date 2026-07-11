"""Shared test fixtures.

SAFETY: tests run migrations up AND DOWN, which destroys data. They therefore
require a DEDICATED test database via TEST_DATABASE_URL and refuse to run
against anything else. There is deliberately NO fallback to DATABASE_URL.
"""

import os

import pytest
from alembic import command
from app.providers.keepa import KeepaRateLimitError, KeepaTransientError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from tests.db_safety import load_test_database_url, make_alembic_config

# Data tables cleared for a clean slate, in FK-safe order. `sources` is seed data.
_CLEANUP_TABLES = [
    "collection_summaries",
    "events",
    "signals",
    "facts",
    "candidate_external_ids",
    "raw_observations",
    "collection_runs",
    "candidates",
]


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
def tx_session(engine) -> Session:
    """A session whose commits are contained in an outer transaction that is
    rolled back at teardown. Sibling suites commit real rows into the shared test
    database, so the fixture first clears the data tables inside this same
    rolled-back transaction: each test gets a clean slate and no committed data is
    permanently destroyed."""
    connection = engine.connect()
    outer = connection.begin()
    for table in _CLEANUP_TABLES:
        connection.execute(text(f"DELETE FROM {table}"))

    session = Session(bind=connection, expire_on_commit=False)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    outer.rollback()
    connection.close()


def keepa_product(asin: str, title: str, rank: int) -> dict:
    """A Keepa product object shaped like the real API (rank at stats.current[3])."""
    return {"asin": asin, "title": title, "stats": {"current": [0, 0, 0, rank]}}


class FakeKeepaClient:
    """Stand-in for KeepaClient: returns scripted bestsellers/products, or raises
    the mapped provider error when `fail_on` is set."""

    def __init__(self, *, asin_list=None, products=None, fail_on=None):
        self._asin_list = asin_list or []
        self._products = products or {}
        self._fail_on = fail_on

    def get_bestsellers(self, category_id, **_kw):
        if self._fail_on == "bestsellers":
            raise KeepaTransientError("bestsellers unavailable")
        return {"bestSellersList": {"asinList": self._asin_list}, "tokensLeft": 100}

    def get_products(self, asins, **_kw):
        if self._fail_on == "products":
            raise KeepaRateLimitError("quota exhausted")
        return {
            "products": [self._products[a] for a in asins if a in self._products],
            "tokensLeft": 90,
        }


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
