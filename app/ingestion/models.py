"""Tables owned by the ingestion module: sources, collection_runs, raw_observations.

raw_observations is the evidence foundation of the whole system (FOUNDATION.md §7):
verbatim external payloads with URL and timestamp. It is APPEND-ONLY — the
SQLAlchemy event listeners at the bottom of this file reject any update or
delete at the application layer.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    Uuid,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.errors import AppendOnlyViolation

COMPLIANCE_VALUES = ("official_api", "licensed_data", "manual", "best_effort")
RUN_STATUS_VALUES = ("pending", "running", "succeeded", "failed")


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(f"compliance IN {COMPLIANCE_VALUES!r}", name="ck_sources_compliance"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    key: Mapped[str] = mapped_column(Text, unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    compliance: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    cost_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class CollectionRun(Base):
    __tablename__ = "collection_runs"
    __table_args__ = (
        CheckConstraint(f"status IN {RUN_STATUS_VALUES!r}", name="ck_collection_runs_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("candidates.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    status: Mapped[str] = mapped_column(Text, default="pending", server_default=text("'pending'"))
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class RawObservation(Base):
    __tablename__ = "raw_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    # Nullable: manual evidence entries are not produced by a collection run.
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("collection_runs.id"))
    # Nullable: future automated discovery may record evidence before a candidate exists.
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("candidates.id"), index=True)
    observation_type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)
    # Nullable: a manually typed note may have no URL; API observations must set it.
    source_url: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


@event.listens_for(RawObservation, "before_update")
def _reject_observation_update(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("raw_observations is append-only: updates are not allowed")


@event.listens_for(RawObservation, "before_delete")
def _reject_observation_delete(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("raw_observations is append-only: deletes are not allowed")
