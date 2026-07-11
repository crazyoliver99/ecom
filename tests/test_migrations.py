from alembic import command
from sqlalchemy import create_engine, inspect

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
