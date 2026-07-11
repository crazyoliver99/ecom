"""Signals layer: Facts, Signals, Events (OPERATING_SYSTEM.md §4).

Facts: append-only, current truth values for observable properties at a point in
time. Multiple facts of the same type supersede prior versions (newest is current).

Signals: append-only, deterministic detector outputs. A signal fires when facts
change meaningfully — detector version is recorded for auditability. Confidence
is a versioned formula output, never agent judgment.

Events: append-only audit log of what happened. Tracks collections, facts, signals,
failures. Downstream logic (agents, dashboards, diagnostics) subscribes to events.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    Uuid,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.errors import AppendOnlyViolation


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"))
    fact_type: Mapped[str] = mapped_column(Text)
    value: Mapped[dict] = mapped_column(JSONB)
    source_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("raw_observations.id")
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


@event.listens_for(Fact, "before_update")
def _reject_fact_update(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("facts is append-only: updates are not allowed")


@event.listens_for(Fact, "before_delete")
def _reject_fact_delete(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("facts is append-only: deletes are not allowed")


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"))
    signal_type: Mapped[str] = mapped_column(Text)
    detector_version: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4))
    fact_ids: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


@event.listens_for(Signal, "before_update")
def _reject_signal_update(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("signals is append-only: updates are not allowed")


@event.listens_for(Signal, "before_delete")
def _reject_signal_delete(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("signals is append-only: deletes are not allowed")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    event_type: Mapped[str] = mapped_column(Text)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("collection_runs.id"))
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("candidates.id"))
    fact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facts.id"))
    signal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("signals.id"))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


@event.listens_for(Event, "before_update")
def _reject_event_update(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("events is append-only: updates are not allowed")


@event.listens_for(Event, "before_delete")
def _reject_event_delete(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("events is append-only: deletes are not allowed")
