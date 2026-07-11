from alembic import command
from sqlalchemy import create_engine, inspect, text

EXPECTED_TABLES = {"sources", "candidates", "collection_runs", "raw_observations"}


def _tables(db_url: str) -> set[str]:
    engine = create_engine(db_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_migration_round_trip(alembic_config, db_url):
    # Up: all four evidence tables exist.
    command.upgrade(alembic_config, "head")
    tables_after_upgrade = _tables(db_url)
    assert tables_after_upgrade >= EXPECTED_TABLES

    # Down: everything this migration created is gone again.
    command.downgrade(alembic_config, "base")
    tables_after_downgrade = _tables(db_url)
    assert EXPECTED_TABLES.isdisjoint(tables_after_downgrade)

    # Back up, leaving the database at head for the rest of the suite.
    command.upgrade(alembic_config, "head")
    assert _tables(db_url) >= EXPECTED_TABLES


def _observation_columns(db_url: str) -> set[str]:
    engine = create_engine(db_url)
    try:
        return {c["name"] for c in inspect(engine).get_columns("raw_observations")}
    finally:
        engine.dispose()


def _manual_source_exists(db_url: str) -> bool:
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT 1 FROM sources WHERE key = 'manual'")).first()
        return row is not None
    finally:
        engine.dispose()


def test_migration_0002_round_trip(alembic_config, db_url):
    # At head: candidate link column present and manual source seeded.
    command.upgrade(alembic_config, "head")
    assert "candidate_id" in _observation_columns(db_url)
    assert _manual_source_exists(db_url)

    # Seeding is idempotent: re-running the insert cannot duplicate the row.
    command.downgrade(alembic_config, "0001")
    assert "candidate_id" not in _observation_columns(db_url)
    assert not _manual_source_exists(db_url)

    command.upgrade(alembic_config, "head")
    assert "candidate_id" in _observation_columns(db_url)
    assert _manual_source_exists(db_url)
