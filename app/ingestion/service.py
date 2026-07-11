"""Ingestion services. In M1 the only entry path is manual evidence."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConfigurationError
from app.ingestion.models import RawObservation, Source
from app.ingestion.repository import RawObservationRepository

MANUAL_SOURCE_KEY = "manual"
MANUAL_OBSERVATION_TYPE = "manual_note"


def get_manual_source(session: Session) -> Source:
    source = session.scalar(select(Source).where(Source.key == MANUAL_SOURCE_KEY))
    if source is None:
        raise ConfigurationError(
            "The 'manual' source is missing — run database migrations "
            "(`alembic upgrade head`) to seed it."
        )
    return source


def add_manual_observation(
    session: Session,
    *,
    candidate_id: uuid.UUID,
    payload: dict,
    source_url: str | None = None,
    fetched_at: datetime | None = None,
) -> RawObservation:
    """Record manually pasted evidence for a candidate. All writes go through
    the append-only repository."""
    source = get_manual_source(session)
    repo = RawObservationRepository(session)
    return repo.create(
        source_id=source.id,
        candidate_id=candidate_id,
        observation_type=MANUAL_OBSERVATION_TYPE,
        payload=payload,
        source_url=source_url,
        fetched_at=fetched_at or datetime.now(UTC),
    )
