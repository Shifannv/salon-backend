"""Add read_at timestamp to notifications.

Adds a nullable ``read_at timestamptz`` column to ``notifications``.  When
``read`` is set to ``true`` the column is stamped with ``now()`` via a new
trigger so historical data is automatically back-filled on first read.

Revision ID: 0002_notifications_read_at
Revises: 0001_baseline
Create Date: 2026-08-04
"""

from alembic import op

revision = "0002_notifications_read_at"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add read_at column and stamp trigger."""

    op.execute(
        """
        alter table notifications
          add column if not exists read_at timestamptz;
        """
    )

    # Back-fill already-read rows so the column is immediately useful.
    op.execute(
        """
        do $$
        begin
          if exists (
            select 1 from information_schema.columns
            where table_schema = 'public'
              and table_name = 'notifications'
              and column_name = 'updated_at'
          ) then
            execute 'update notifications set read_at = updated_at where read = true and read_at is null';
          else
            update notifications
            set read_at = created_at
            where read = true and read_at is null;
          end if;
        end $$;
        """
    )

    # Trigger: whenever read flips true, stamp read_at if not already set.
    op.execute(
        """
        create or replace function stamp_notification_read_at()
        returns trigger language plpgsql as $$
        begin
          if new.read = true and old.read = false and new.read_at is null then
            new.read_at := now();
          end if;
          return new;
        end;
        $$;
        """
    )

    op.execute("drop trigger if exists trg_notification_read_at on notifications;")
    op.execute(
        """
        create trigger trg_notification_read_at
          before update on notifications
          for each row execute procedure stamp_notification_read_at();
        """
    )


def downgrade() -> None:
    """Drop stamp trigger and read_at column."""

    op.execute("drop trigger if exists trg_notification_read_at on notifications;")
    op.execute("drop function if exists stamp_notification_read_at();")
    op.execute("alter table notifications drop column if exists read_at;")
