"""Introduce Facts, Signals, Events, and make collection_runs.candidate_id nullable.

Schema evolution for Phase 2 (autonomous collection):
- Facts: append-only layer between observations and signals. Each fact is the
  current truth value for a property at a point in time.
- Signals: deterministic detectors that emit provider-agnostic signals when facts
  change meaningfully. Signals are first-class deterministic objects with versioned
  detector logic.
- Events: append-only event log for auditability and triggering downstream logic.
  Tracks what happened: when facts changed, when signals fired, when runs failed.
- collection_runs.candidate_id becomes nullable to support future discovery runs
  that may capture observations before any candidate exists.
- Seeds the 'keepa' source row (licensed_data, $53/mo).

Downgrade is fully executable: removes Keepa source and its cascading data, then
removes the new tables in dependency order.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Make collection_runs.candidate_id nullable.
    op.alter_column(
        "collection_runs",
        "candidate_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # Facts: append-only, indexed by candidate and type for lookup.
    op.create_table(
        "facts",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("fact_type", sa.Text(), nullable=False),
        sa.Column("value", JSONB(), nullable=False),
        sa.Column(
            "source_observation_id",
            sa.Uuid(),
            sa.ForeignKey("raw_observations.id"),
            nullable=True,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_facts_candidate_id", "facts", ["candidate_id"])
    op.create_index("ix_facts_fact_type", "facts", ["fact_type"])
    op.create_index("ix_facts_created_at", "facts", ["created_at"])

    # Signals: append-only, versioned detector logic, indexed by candidate and type.
    op.create_table(
        "signals",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("detector_version", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("fact_ids", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_signals_candidate_id", "signals", ["candidate_id"])
    op.create_index("ix_signals_signal_type", "signals", ["signal_type"])
    op.create_index("ix_signals_created_at", "signals", ["created_at"])

    # Events: append-only audit log. Each event references the entity it concerns:
    # run_id for collection lifecycle, candidate_id for discovery, fact_id for fact
    # changes, signal_id for detector fires. payload holds event-specific context.
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("collection_runs.id"), nullable=True),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id"), nullable=True),
        sa.Column("fact_id", sa.Uuid(), sa.ForeignKey("facts.id"), nullable=True),
        sa.Column("signal_id", sa.Uuid(), sa.ForeignKey("signals.id"), nullable=True),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_run_id", "events", ["run_id"])
    op.create_index("ix_events_candidate_id", "events", ["candidate_id"])
    op.create_index("ix_events_created_at", "events", ["created_at"])

    # Seed Keepa source: licensed Amazon API data, ~$53/mo.
    op.execute(
        "INSERT INTO sources (key, display_name, compliance, cost_note) "
        "VALUES ('keepa', 'Keepa API', 'licensed_data', '~€49 (~$53)/mo') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    # Remove Keepa source (cascades to collection_runs and observations via FK).
    op.execute("DELETE FROM sources WHERE key = 'keepa'")

    # Remove events (references facts and signals, must go first).
    op.drop_table("events")

    # Remove signals and facts in dependency order.
    op.drop_table("signals")
    op.drop_table("facts")

    # Restore collection_runs.candidate_id to NOT NULL.
    op.alter_column(
        "collection_runs",
        "candidate_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
