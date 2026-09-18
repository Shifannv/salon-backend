"""Persist customer reports with self-read RLS and soft deletion.

Revision ID: 0010_salon_reports
Revises: 0009_booking_cancellation_reason
"""

from alembic import op

revision = "0010_salon_reports"
down_revision = "0009_booking_cancellation_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table salon_reports (
            id uuid primary key default gen_random_uuid(),
            reporter_id uuid not null references profiles(id),
            salon_id uuid not null references salons(id),
            reason text not null check (length(trim(reason)) between 1 and 200),
            details text not null default '' check (length(details) <= 5000),
            status text not null default 'received' check (status = 'received'),
            is_active boolean not null default true,
            created_at timestamptz not null default now()
        );
        create index salon_reports_reporter_idx on salon_reports (reporter_id, created_at);
        create index salon_reports_salon_idx on salon_reports (salon_id, created_at);
        alter table salon_reports enable row level security;
        revoke all on salon_reports from anon, authenticated;
        grant select on salon_reports to authenticated;
        grant all on salon_reports to service_role;
        create policy salon_reports_self_read on salon_reports for select to authenticated
            using (reporter_id = auth.uid() and is_active);
    """)


def downgrade() -> None:
    op.execute("drop table salon_reports")
