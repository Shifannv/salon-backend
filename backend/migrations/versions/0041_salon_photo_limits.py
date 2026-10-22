"""Remove salon/service descriptions; keep one cover and two independent slides.

Prepared for review only. Existing Mumbai history must be reconciled separately;
the current migration policy intentionally does not authorize this revision.
"""

from pathlib import Path

from alembic import op

revision = "0041_salon_photo_limits"
down_revision = "0040_fastapi_only_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).parents[1] / "sql" / "0041_salon_photo_limits.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Irreversible description removal and gallery retirement; use a reviewed forward repair")
