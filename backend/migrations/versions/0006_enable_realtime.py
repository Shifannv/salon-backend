"""Enable Supabase Realtime on bookings and blocked_slots.

Revision ID: 0006_enable_realtime
Revises: 0005_staff_experience
Create Date: 2026-08-14
"""

from alembic import op

revision = "0006_enable_realtime"
down_revision = "0005_staff_experience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add bookings/blocked_slots to the supabase_realtime publication.

    REPLICA IDENTITY FULL first: the default (primary key only) means an UPDATE/DELETE
    change payload carries only the row's id in `old`, not the fields that actually changed
    (e.g. the previous `status`) or, for DELETE, anything at all beyond the id. Clients
    reconciling a blocked-slot removal or a status transition need the full previous row.
    RLS on both tables (`bookings_read`, `blocked_read`) already scopes what each connected
    client receives -- unchanged by this migration.
    """

    op.execute("alter table bookings replica identity full")
    op.execute("alter table blocked_slots replica identity full")
    op.execute("alter publication supabase_realtime add table bookings, blocked_slots")


def downgrade() -> None:
    """Remove both tables from the publication and restore default replica identity."""

    op.execute("alter publication supabase_realtime drop table bookings, blocked_slots")
    op.execute("alter table blocked_slots replica identity default")
    op.execute("alter table bookings replica identity default")
