"""Apply the v3 Supabase schema baseline.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-02
"""

from pathlib import Path

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute the checked-in v3 SQL schema verbatim."""

    schema_path = Path(__file__).resolve().parents[1] / "sql" / "001_supabase_schema.sql"
    op.execute(schema_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    """Leave baseline downgrade explicit and manual."""

    raise NotImplementedError("Baseline schema downgrade is intentionally manual")
