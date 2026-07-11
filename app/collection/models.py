"""Tables owned by the collection module.

CollectionSummary is the deterministic, human-readable digest of one collection
run (Atlas Autonomy M1). It is generated at the end of every successful run and
is what `atlas morning-report` reads. Append-only, like the rest of the evidence
chain: a summary describes a run that already happened and is never rewritten.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.errors import AppendOnlyViolation


class CollectionSummary(Base):
    __tablename__ = "collection_summaries"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_collection_summaries_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_runs.id"))
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(12, 3))
    candidates_discovered: Mapped[int] = mapped_column(Integer)
    new_candidates: Mapped[int] = mapped_column(Integer)
    existing_candidates_updated: Mapped[int] = mapped_column(Integer)
    observations_stored: Mapped[int] = mapped_column(Integer)
    facts_created: Mapped[int] = mapped_column(Integer)
    signals_emitted: Mapped[int] = mapped_column(Integer)
    events_emitted: Mapped[int] = mapped_column(Integer)
    provider_warnings: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    provider_errors: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


@event.listens_for(CollectionSummary, "before_update")
def _reject_summary_update(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("collection_summaries is append-only: updates are not allowed")


@event.listens_for(CollectionSummary, "before_delete")
def _reject_summary_delete(mapper, connection, target):  # noqa: ARG001
    raise AppendOnlyViolation("collection_summaries is append-only: deletes are not allowed")
