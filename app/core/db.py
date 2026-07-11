"""Database engine, session management, and the declarative base.

Uses synchronous SQLAlchemy with psycopg 3 — simple and more than fast enough
for a single-user system. FastAPI runs sync endpoints in a thread pool.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def get_db_session() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
