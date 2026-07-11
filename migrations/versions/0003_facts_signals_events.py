"""Introduce Facts, Signals, Events, ASIN mapping; nullable collection_runs.candidate_id.

Schema evolution for Phase 2 (autonomous collection):
- Facts: append-only layer between observations and signals. Each fact is the
  current truth value for a property at a point in time. source_observation_id is
  NOT NULL: every fact must cite exactly one stored raw observation (evidence
  traceability — a fact with no observation behind it cannot exist).
- Signals: append-only deterministic detector outputs. confidence is constrained
  to [0, 1] and fact_ids must be a non-empty JSON array (a signal that cites no
  facts is meaningless and cannot exist).
- Events: append-only event log for auditability and triggering downstream logic.
- candidate_external_ids: maps a provider's external product id (e.g. an Amazon
  ASIN) to a candidate, giving stable identity-based dedup that never relies on
  candidate name. UNIQUE(source_id, external_id).
- collection_runs.candidate_id becomes nullable: a discovery run finds many
  candidates and is not scoped to one.
- Seeds the 'keepa' source row (licensed_data, ~$53/mo).

Downgrade is fully executable and reverses every change in dependency order.

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
    # A discovery run is not scoped to a single candidate; it finds many.
    op.alter_column(
        "collection_runs",
        "candidate_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # Facts: append-only. source_observation_id NOT NULL — every fact cites its
    # stored evidence.
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
            nullable=False,
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
    # Fast "latest fact of this type for this candidate" lookup.
    op.create_index(
        "ix_facts_candidate_type_created",
        "facts",
        ["candidate_id", "fact_type", "created_at"],
    )

    # Signals: append-only. confidence in [0,1]; fact_ids a non-empty JSON array.
    op.create_table(
        "signals",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("detector_version", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("fact_ids", JSONB(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_signals_confidence_range",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(fact_ids) = 'array' AND jsonb_array_length(fact_ids) >= 1",
            name="ck_signals_fact_ids_nonempty",
        ),
    )
    op.create_index("ix_signals_candidate_id", "signals", ["candidate_id"])
    op.create_index("ix_signals_signal_type", "signals", ["signal_type"])
    op.create_index("ix_signals_created_at", "signals", ["created_at"])

    # Events: append-only audit log. Each event references the entity it concerns.
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

    # External-id map: (source, external_id) -> candidate. Identity-based dedup
    # that never relies on candidate name.
    op.create_table(
        "candidate_external_ids",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "source_id", "external_id", name="uq_candidate_external_ids_source_ext"
        ),
    )
    op.create_index(
        "ix_candidate_external_ids_candidate_id",
        "candidate_external_ids",
        ["candidate_id"],
    )

    # Seed Keepa source: licensed Amazon API data, ~$53/mo.
    op.execute(
        "INSERT INTO sources (key, display_name, compliance, cost_note) "
        "VALUES ('keepa', 'Keepa API', 'licensed_data', '~€49 (~$53)/mo') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    # Remove Keepa source (cascades to its runs/observations via FK ordering
    # once dependent rows are gone; delete children first below).
    op.drop_index(
        "ix_candidate_external_ids_candidate_id", table_name="candidate_external_ids"
    )
    op.drop_table("candidate_external_ids")

    # Events reference facts and signals — drop first.
    op.drop_table("events")
    op.drop_table("signals")
    op.drop_table("facts")

    # Reversing "introduce Keepa" removes Keepa's data too. Delete dependents in
    # FK order (observations -> runs) before the source itself.
    op.execute(
        "DELETE FROM raw_observations "
        "WHERE source_id IN (SELECT id FROM sources WHERE key = 'keepa')"
    )
    op.execute(
        "DELETE FROM collection_runs "
        "WHERE source_id IN (SELECT id FROM sources WHERE key = 'keepa')"
    )
    op.execute("DELETE FROM sources WHERE key = 'keepa'")

    # Restore collection_runs.candidate_id to NOT NULL.
    op.alter_column(
        "collection_runs",
        "candidate_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
