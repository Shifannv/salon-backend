"""Let recipients dismiss notifications for good. Prepared only."""
from pathlib import Path

from alembic import op

revision = "0066_notification_soft_delete"
down_revision = "0065_age_and_guardian_consent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).resolve().parents[1] / "sql" / "0066_notification_soft_delete.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Dismissal markers are retained; use a reviewed forward migration")
