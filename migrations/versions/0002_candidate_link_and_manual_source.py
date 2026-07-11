"""Link raw observations to candidates; seed the manual evidence source.

- Adds nullable, indexed raw_observations.candidate_id (FK -> candidates).
  Nullable because future automated discovery may capture observations before
  any candidate exists; run_id remains for Phase 3 collection runs.
- Seeds the 'manual' source row (idempotent: ON CONFLICT DO NOTHING).

Downgrade is fully executable: it removes the manual source row and, because
of the foreign key, must first delete any observations recorded against it.
Downgrading this migration therefore DELETES manually entered evidence —
which is exactly what reversing "introduce manual evidence" means.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("raw_observations", sa.Column("candidate_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_raw_observations_candidate_id",
        "raw_observations",
        "candidates",
        ["candidate_id"],
        ["id"],
    )
    op.create_index("ix_raw_observations_candidate_id", "raw_observations", ["candidate_id"])

    op.execute(
        "INSERT INTO sources (key, display_name, compliance, cost_note) "
        "VALUES ('manual', 'Manual evidence', 'manual', 'free') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM raw_observations "
        "WHERE source_id IN (SELECT id FROM sources WHERE key = 'manual')"
    )
    op.execute("DELETE FROM sources WHERE key = 'manual'")

    op.drop_index("ix_raw_observations_candidate_id", table_name="raw_observations")
    op.drop_constraint("fk_raw_observations_candidate_id", "raw_observations", type_="foreignkey")
    op.drop_column("raw_observations", "candidate_id")
