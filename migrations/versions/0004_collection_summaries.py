"""Collection summaries: one deterministic digest per collection run.

Atlas Autonomy M1. A summary is generated at the end of every successful
collection run and read back by `atlas morning-report`. Append-only, UNIQUE on
run_id (one summary per run).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collection_summaries",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("collection_runs.id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(12, 3), nullable=True),
        sa.Column("candidates_discovered", sa.Integer(), nullable=False),
        sa.Column("new_candidates", sa.Integer(), nullable=False),
        sa.Column("existing_candidates_updated", sa.Integer(), nullable=False),
        sa.Column("observations_stored", sa.Integer(), nullable=False),
        sa.Column("facts_created", sa.Integer(), nullable=False),
        sa.Column("signals_emitted", sa.Integer(), nullable=False),
        sa.Column("events_emitted", sa.Integer(), nullable=False),
        sa.Column(
            "provider_warnings",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "provider_errors",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("run_id", name="uq_collection_summaries_run_id"),
    )
    op.create_index("ix_collection_summaries_status", "collection_summaries", ["status"])
    op.create_index("ix_collection_summaries_created_at", "collection_summaries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_collection_summaries_created_at", table_name="collection_summaries")
    op.drop_index("ix_collection_summaries_status", table_name="collection_summaries")
    op.drop_table("collection_summaries")
