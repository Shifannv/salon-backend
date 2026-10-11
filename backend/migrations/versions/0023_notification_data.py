"""Let a notification carry structured push metadata (e.g. salon approval status/reason).

Adds a nullable notifications.data jsonb. Existing rows and booking notifications keep
NULL; the push gateway merges it into the provider data payload when present.

Revision ID: 0023_notification_data
Revises: 0022_salon_accepting_bookings
"""

from alembic import op

revision = "0023_notification_data"
down_revision = "0022_salon_accepting_bookings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table notifications add column data jsonb")


def downgrade() -> None:
    op.execute("alter table notifications drop column data")
