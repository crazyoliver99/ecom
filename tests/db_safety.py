"""Guard rails that keep the test suite away from the development database.

The migration tests downgrade the schema to base, which DELETES ALL DATA in
whatever database they touch. These helpers make that impossible to do by
accident: tests only ever use TEST_DATABASE_URL (never DATABASE_URL), and the
database name itself must identify the database as a test database.
"""

import argparse
from collections.abc import Mapping
from pathlib import Path

from alembic.config import Config
from sqlalchemy.engine import make_url

HOW_TO_SET_UP = """\
Tests require a DEDICATED test database, configured via TEST_DATABASE_URL.
They intentionally never use DATABASE_URL — the migration tests wipe the
database they run against, and that must never be your real data.

How to set it up:

  1. Start the database:              docker compose up -d db
     (On a fresh volume, compose creates the `ecom_test` database for you.
      If your db volume predates this feature, run once:
        docker compose exec db createdb -U ecom ecom_test )
  2. Add this line to your .env file (see .env.example):
        TEST_DATABASE_URL=postgresql+psycopg://ecom:<your-password>@localhost:5432/ecom_test
  3. Run the tests again:             uv run pytest
"""


def _read_env_file(path: Path, key: str) -> str | None:
    """Minimal .env reader so `uv run pytest` works without exporting variables."""
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip("'\"") or None
    return None


def ensure_test_database_url(url: str) -> str:
    """Refuse any URL whose database name does not clearly mark it as a test DB."""
    try:
        database = make_url(url).database
    except Exception as exc:
        raise RuntimeError(f"TEST_DATABASE_URL is not a valid database URL: {exc}") from exc
    if not database or not (database.endswith("_test") or "test" in database):
        raise RuntimeError(
            f"Refusing to run tests against database '{database}': the test database "
            "name must end with '_test' (or at least contain 'test'), because the "
            f"migration tests destroy all data in it.\n\n{HOW_TO_SET_UP}"
        )
    return url


def load_test_database_url(environ: Mapping[str, str]) -> str:
    """TEST_DATABASE_URL from the environment or .env — never DATABASE_URL."""
    url = environ.get("TEST_DATABASE_URL") or _read_env_file(Path(".env"), "TEST_DATABASE_URL")
    if not url:
        raise RuntimeError(f"TEST_DATABASE_URL is not set.\n\n{HOW_TO_SET_UP}")
    return ensure_test_database_url(url)


def make_alembic_config(db_url: str) -> Config:
    """An Alembic Config bound to the (verified) test database.

    Equivalent of `alembic -x db_url=... upgrade head` — migrations/env.py reads
    the -x argument, so migrations never depend on cached application settings.
    """
    ensure_test_database_url(db_url)
    cfg = Config("alembic.ini")
    cfg.cmd_opts = argparse.Namespace(x=[f"db_url={db_url}"])
    return cfg
