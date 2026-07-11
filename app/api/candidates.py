"""Candidate CRUD and per-candidate evidence endpoints.

No DELETE anywhere: candidates may carry evidence, and evidence is never
silently destroyed. Observation writes go through the append-only repository
(via the ingestion service) — there are no update/delete routes for them.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas import (
    CandidateCreate,
    CandidateList,
    CandidateOut,
    CandidateStatus,
    CandidateUpdate,
    ObservationCreate,
    ObservationList,
    ObservationOut,
)
from app.catalog.models import Candidate
from app.catalog.repository import CandidateRepository
from app.core.db import get_db_session
from app.core.errors import NotFoundError
from app.ingestion.repository import RawObservationRepository
from app.ingestion.service import add_manual_observation

router = APIRouter(prefix="/candidates", tags=["candidates"])

LimitParam = Annotated[int, Query(ge=1, le=200, description="Page size (max 200)")]
OffsetParam = Annotated[int, Query(ge=0)]


def _get_candidate_or_404(session: Session, candidate_id: uuid.UUID) -> Candidate:
    candidate = CandidateRepository(session).get(candidate_id)
    if candidate is None:
        raise NotFoundError(f"candidate {candidate_id} does not exist")
    return candidate


@router.post("", response_model=CandidateOut, status_code=201)
def create_candidate(
    body: CandidateCreate, session: Session = Depends(get_db_session)
) -> Candidate:
    candidate = CandidateRepository(session).create(
        name=body.name, niche=body.niche, notes=body.notes, seed_urls=body.seed_urls
    )
    session.commit()
    return candidate


@router.get("", response_model=CandidateList)
def list_candidates(
    status: CandidateStatus | None = None,
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
    session: Session = Depends(get_db_session),
) -> CandidateList:
    items, total = CandidateRepository(session).list(status=status, limit=limit, offset=offset)
    return CandidateList(
        items=[CandidateOut.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: uuid.UUID, session: Session = Depends(get_db_session)) -> Candidate:
    return _get_candidate_or_404(session, candidate_id)


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: uuid.UUID,
    body: CandidateUpdate,
    session: Session = Depends(get_db_session),
) -> Candidate:
    candidate = _get_candidate_or_404(session, candidate_id)
    fields = body.model_dump(exclude_unset=True)
    candidate = CandidateRepository(session).update(candidate, **fields)
    session.commit()
    return candidate


@router.post("/{candidate_id}/observations", response_model=ObservationOut, status_code=201)
def add_evidence(
    candidate_id: uuid.UUID,
    body: ObservationCreate,
    session: Session = Depends(get_db_session),
) -> ObservationOut:
    _get_candidate_or_404(session, candidate_id)
    observation = add_manual_observation(
        session,
        candidate_id=candidate_id,
        payload=body.payload,
        source_url=str(body.source_url) if body.source_url else None,
        fetched_at=body.fetched_at,
    )
    session.commit()
    return ObservationOut.model_validate(observation)


@router.get("/{candidate_id}/observations", response_model=ObservationList)
def list_evidence(
    candidate_id: uuid.UUID,
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
    session: Session = Depends(get_db_session),
) -> ObservationList:
    _get_candidate_or_404(session, candidate_id)
    items, total = RawObservationRepository(session).list_for_candidate(
        candidate_id, limit=limit, offset=offset
    )
    return ObservationList(
        items=[ObservationOut.model_validate(o) for o in items],
        total=total,
        limit=limit,
        offset=offset,
    )
