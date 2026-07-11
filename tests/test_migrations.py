from alembic import command
from sqlalchemy import create_engine, inspect, text

EXPECTED_TABLES = {
    "sources",
    "candidates",
    "collection_runs",
    "raw_observations",
    "facts",
    "signals",
    "events",
    "candidate_external_ids",
    "collection_summaries",
}


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


def _tables_include(db_url: str, table_names: set[str]) -> bool:
    engine = create_engine(db_url)
    try:
        actual = set(inspect(engine).get_table_names())
        return table_names.issubset(actual)
    finally:
        engine.dispose()


def _keepa_source_exists(db_url: str) -> bool:
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT 1 FROM sources WHERE key = 'keepa'")).first()
        return row is not None
    finally:
        engine.dispose()


def _collection_runs_candidate_nullable(db_url: str) -> bool:
    engine = create_engine(db_url)
    try:
        cols = inspect(engine).get_columns("collection_runs")
        for col in cols:
            if col["name"] == "candidate_id":
                return col["nullable"]
        return False
    finally:
        engine.dispose()


def _facts_source_observation_not_null(db_url: str) -> bool:
    engine = create_engine(db_url)
    try:
        for col in inspect(engine).get_columns("facts"):
            if col["name"] == "source_observation_id":
                return not col["nullable"]
        return False
    finally:
        engine.dispose()


def _signal_check_constraints(db_url: str) -> set[str]:
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'signals'::regclass AND contype = 'c'"
                )
            ).all()
        return {r[0] for r in rows}
    finally:
        engine.dispose()


def test_migration_0003_round_trip(alembic_config, db_url):
    new_tables = {"facts", "signals", "events", "candidate_external_ids"}

    # At head: new tables exist; Keepa source seeded; constraints present.
    command.upgrade(alembic_config, "head")
    assert _tables_include(db_url, new_tables)
    assert _keepa_source_exists(db_url)
    assert _collection_runs_candidate_nullable(db_url)
    assert _facts_source_observation_not_null(db_url)
    checks = _signal_check_constraints(db_url)
    assert "ck_signals_confidence_range" in checks
    assert "ck_signals_fact_ids_nonempty" in checks

    # Downgrade to 0002: new tables and Keepa source gone.
    command.downgrade(alembic_config, "0002")
    assert not _tables_include(db_url, new_tables)
    assert not _keepa_source_exists(db_url)
    assert not _collection_runs_candidate_nullable(db_url)

    # Back up, leaving the database at head.
    command.upgrade(alembic_config, "head")
    assert _tables_include(db_url, new_tables)
    assert _keepa_source_exists(db_url)


def test_migration_0004_round_trip(alembic_config, db_url):
    # At head: collection_summaries exists.
    command.upgrade(alembic_config, "head")
    assert _tables_include(db_url, {"collection_summaries"})

    # Downgrade to 0003: it's gone.
    command.downgrade(alembic_config, "0003")
    assert not _tables_include(db_url, {"collection_summaries"})

    # Back up, leaving the database at head.
    command.upgrade(alembic_config, "head")
    assert _tables_include(db_url, {"collection_summaries"})
