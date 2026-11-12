"""Notification audience routing: audience on notifications, app on device_tokens."""

from pathlib import Path

from alembic import op

revision = "0069_notification_audience"
down_revision = "0068_payout_transfers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).resolve().parents[1] / "sql" / "0069_notification_audience.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    op.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS audience")
    op.execute("ALTER TABLE device_tokens DROP COLUMN IF EXISTS app")
