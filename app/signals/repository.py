"""Data access for Facts, Signals, and Events."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.signals.models import Event, Fact, Signal


def create_fact(
    session: Session,
    candidate_id: uuid.UUID,
    fact_type: str,
    value: dict,
    observed_at: datetime,
    source_observation_id: uuid.UUID | None = None,
) -> Fact:
    """Create and persist a Fact."""
    fact = Fact(
        candidate_id=candidate_id,
        fact_type=fact_type,
        value=value,
        observed_at=observed_at,
        source_observation_id=source_observation_id,
    )
    session.add(fact)
    session.flush()
    return fact


def get_latest_fact_of_type(
    session: Session,
    candidate_id: uuid.UUID,
    fact_type: str,
) -> Fact | None:
    """Get the most recent fact of a given type for a candidate."""
    return session.execute(
        select(Fact)
        .where(Fact.candidate_id == candidate_id, Fact.fact_type == fact_type)
        .order_by(Fact.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def create_signal(
    session: Session,
    candidate_id: uuid.UUID,
    signal_type: str,
    detector_version: str,
    confidence: float,
    computed_at: datetime,
    fact_ids: list[uuid.UUID] | None = None,
) -> Signal:
    """Create and persist a Signal."""
    signal = Signal(
        candidate_id=candidate_id,
        signal_type=signal_type,
        detector_version=detector_version,
        confidence=confidence,
        fact_ids=fact_ids or [],
        computed_at=computed_at,
    )
    session.add(signal)
    session.flush()
    return signal


def create_event(
    session: Session,
    event_type: str,
    occurred_at: datetime,
    run_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    fact_id: uuid.UUID | None = None,
    signal_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> Event:
    """Create and persist an Event."""
    event = Event(
        event_type=event_type,
        run_id=run_id,
        candidate_id=candidate_id,
        fact_id=fact_id,
        signal_id=signal_id,
        payload=payload or {},
        occurred_at=occurred_at,
    )
    session.add(event)
    session.flush()
    return event
