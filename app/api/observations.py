"""Read-only observation endpoints. Observations are append-only evidence:
this router deliberately defines GET and nothing else, so PATCH/PUT/DELETE
answer 405 Method Not Allowed."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import ObservationOut
from app.core.db import get_db_session
from app.core.errors import NotFoundError
from app.ingestion.repository import RawObservationRepository

router = APIRouter(prefix="/observations", tags=["observations"])


@router.get("/{observation_id}", response_model=ObservationOut)
def get_observation(
    observation_id: uuid.UUID, session: Session = Depends(get_db_session)
) -> ObservationOut:
    observation = RawObservationRepository(session).get(observation_id)
    if observation is None:
        raise NotFoundError(f"observation {observation_id} does not exist")
    return ObservationOut.model_validate(observation)
