"""Repository for raw observations — the only sanctioned way to touch the table.

This class exposes CREATE and READ operations only. There is no update and no
delete method, by design: raw observations are the immutable evidence layer
(FOUNDATION.md §7). The SQLAlchemy event listeners in models.py back this up by
rejecting ORM-level mutations.

HONEST LIMITATION: both protections live in the application layer. Raw SQL
(`UPDATE raw_observations ...`), the `psql` shell, or any connection with
database-owner privileges can still modify or delete rows. A database-level
trigger could close that gap and is deliberately deferred for now.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.models import RawObservation


class RawObservationRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        *,
        source_id: uuid.UUID,
        observation_type: str,
        payload: dict,
        fetched_at: datetime,
        source_url: str | None = None,
        run_id: uuid.UUID | None = None,
        candidate_id: uuid.UUID | None = None,
    ) -> RawObservation:
        if fetched_at.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware (UTC)")
        observation = RawObservation(
            source_id=source_id,
            observation_type=observation_type,
            payload=payload,
            fetched_at=fetched_at.astimezone(UTC),
            source_url=source_url,
            run_id=run_id,
            candidate_id=candidate_id,
        )
        self._session.add(observation)
        self._session.flush()
        return observation

    def get(self, observation_id: uuid.UUID) -> RawObservation | None:
        return self._session.get(RawObservation, observation_id)

    def list_for_source(self, source_id: uuid.UUID, limit: int = 100) -> list[RawObservation]:
        stmt = (
            select(RawObservation)
            .where(RawObservation.source_id == source_id)
            .order_by(RawObservation.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    def list_for_run(self, run_id: uuid.UUID, limit: int = 100) -> list[RawObservation]:
        stmt = (
            select(RawObservation)
            .where(RawObservation.run_id == run_id)
            .order_by(RawObservation.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    def list_for_candidate(
        self, candidate_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[RawObservation], int]:
        """Newest-first page of a candidate's evidence, plus the total count."""
        where = RawObservation.candidate_id == candidate_id
        stmt = (
            select(RawObservation)
            .where(where)
            .order_by(RawObservation.created_at.desc(), RawObservation.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(self._session.scalars(stmt))
        total = self._session.scalar(select(func.count()).select_from(RawObservation).where(where))
        return items, int(total or 0)
