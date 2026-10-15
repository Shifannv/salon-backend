"""Retain promotion-helper search_path hardening lost when 0030 replaces it."""

from pathlib import Path

from alembic import op

revision = "0039_promotion_search_path"
down_revision = "0038_cancellation_compatibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).parents[1] / "sql" / "0039_promotion_search_path.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Irreversible security hardening: do not reset search_path; use a reviewed forward revision")
