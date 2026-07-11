"""Repository for candidates. No delete: candidates may carry evidence, and
evidence must never be silently destroyed; deletion policy is deferred."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog.models import Candidate, CandidateExternalId


class CandidateRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        *,
        name: str,
        niche: str | None = None,
        notes: str | None = None,
        seed_urls: list[str] | None = None,
    ) -> Candidate:
        candidate = Candidate(name=name, niche=niche, notes=notes, seed_urls=seed_urls or [])
        self._session.add(candidate)
        self._session.flush()
        return candidate

    def get(self, candidate_id: uuid.UUID) -> Candidate | None:
        return self._session.get(Candidate, candidate_id)

    def list(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[Candidate], int]:
        """Newest-first page of candidates, plus the total count."""
        stmt = select(Candidate)
        count_stmt = select(func.count()).select_from(Candidate)
        if status is not None:
            stmt = stmt.where(Candidate.status == status)
            count_stmt = count_stmt.where(Candidate.status == status)
        stmt = (
            stmt.order_by(Candidate.created_at.desc(), Candidate.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(self._session.scalars(stmt))
        total = self._session.scalar(count_stmt)
        return items, int(total or 0)

    def update(self, candidate: Candidate, **fields) -> Candidate:
        for key, value in fields.items():
            setattr(candidate, key, value)
        self._session.flush()
        return candidate

    def find_by_external_id(
        self, *, source_id: uuid.UUID, external_id: str
    ) -> Candidate | None:
        """Return the candidate mapped to (source, external_id), or None."""
        mapping = self._session.scalar(
            select(CandidateExternalId).where(
                CandidateExternalId.source_id == source_id,
                CandidateExternalId.external_id == external_id,
            )
        )
        if mapping is None:
            return None
        return self._session.get(Candidate, mapping.candidate_id)

    def get_or_create_by_external_id(
        self,
        *,
        source_id: uuid.UUID,
        external_id: str,
        name: str,
        niche: str | None = None,
        notes: str | None = None,
    ) -> tuple[Candidate, bool]:
        """Look up a candidate by (source, external_id); create it and the
        mapping if absent. Returns (candidate, created) where `created` is True
        only when a brand-new candidate was made — the caller uses that to
        decide whether to emit NewProductDiscovered. Identity is the external id,
        never the name."""
        existing = self.find_by_external_id(source_id=source_id, external_id=external_id)
        if existing is not None:
            return existing, False

        candidate = self.create(name=name, niche=niche, notes=notes)
        mapping = CandidateExternalId(
            candidate_id=candidate.id,
            source_id=source_id,
            external_id=external_id,
        )
        self._session.add(mapping)
        self._session.flush()
        return candidate, True
