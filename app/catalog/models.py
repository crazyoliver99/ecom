"""Tables owned by the catalog module. In M0 this is only `candidates`;
normalized `products` arrive in Phase 4 (FOUNDATION.md §10)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Text, Uuid, text
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
