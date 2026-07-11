"""Tables owned by the catalog module. In M0 this is only `candidates`;
normalized `products` arrive in Phase 4 (FOUNDATION.md §10)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

CANDIDATE_STATUS_VALUES = ("new", "collecting", "analyzed", "decided")


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        CheckConstraint(f"status IN {CANDIDATE_STATUS_VALUES!r}", name="ck_candidates_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text)
    niche: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    seed_urls: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    status: Mapped[str] = mapped_column(Text, default="new", server_default=text("'new'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(UTC),
    )


class CandidateExternalId(Base):
    """Maps a provider's external product identifier (e.g. an Amazon ASIN) to a
    candidate. This is how automated collection recognizes a product it has seen
    before — identity comes from (source, external_id), never from the candidate
    name. UNIQUE(source_id, external_id) makes dedup exact and race-safe."""

    __tablename__ = "candidate_external_ids"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "external_id", name="uq_candidate_external_ids_source_ext"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
