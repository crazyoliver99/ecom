"""Data access for Facts, Signals, and Events.

Application-layer validation mirrors the database constraints so callers get a
clear Python error instead of an opaque IntegrityError:
- a Fact must cite a source observation;
- a Signal must have confidence in [0, 1] and cite at least one fact.
"""

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
    source_observation_id: uuid.UUID,
) -> Fact:
    """Create and persist a Fact. source_observation_id is required: a fact with
    no stored observation behind it is not traceable evidence and is rejected."""
    if source_observation_id is None:
        raise ValueError("source_observation_id is required: every fact must cite an observation")
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
    """The current truth: the most recent fact of a type for a candidate.

    Call this BEFORE inserting a new fact to obtain the immediately prior fact.
    Calling it after an insert would return the just-inserted row (the newest),
    which is never what a change detector wants.
    """
    return session.execute(
        select(Fact)
        .where(Fact.candidate_id == candidate_id, Fact.fact_type == fact_type)
        .order_by(Fact.created_at.desc(), Fact.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def create_signal(
    session: Session,
    candidate_id: uuid.UUID,
    signal_type: str,
    detector_version: str,
    confidence: float,
    computed_at: datetime,
    fact_ids: list[uuid.UUID],
) -> Signal:
    """Create and persist a Signal. Enforces confidence in [0, 1] and a non-empty
    fact_ids list at the application layer (the database enforces the same)."""
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError(f"confidence must be within [0, 1], got {confidence}")
    if not fact_ids:
        raise ValueError("fact_ids must cite at least one fact")
    signal = Signal(
        candidate_id=candidate_id,
        signal_type=signal_type,
        detector_version=detector_version,
        confidence=confidence,
        # JSONB stores strings, not UUID objects — normalize here.
        fact_ids=[str(fid) for fid in fact_ids],
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
