"""Immutable customer processing-charge snapshots on the existing ledger.

Revision ID: 0037_customer_processing_charge
Revises: 0036_support_email_outbox
"""

from pathlib import Path

from alembic import op

revision = "0037_customer_processing_charge"
down_revision = "0036_support_email_outbox"
branch_labels = None
depends_on = None


def upgrade():
    sql = (Path(__file__).parents[1] / "0037_customer_processing_charge.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    # Refuse to erase any new financial snapshot or provider session identity.
    op.execute("""do $$ begin
      if exists(select 1 from public.booking_payments where online_processing_charge <> 0 or provider_session_id is not null) then
        raise exception 'Processing charge history exists; use a reviewed forward migration';
      end if;
    end $$""")
    import importlib.util
    spec = importlib.util.spec_from_file_location("previous_payment_policy", Path(__file__).with_name("0029_payment_monetary_policy.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    op.execute(module._RECOMPUTE)
    for sql in (
        "drop trigger payment_collection_snapshot on public.booking_payments",
        "drop function public.guard_collection_snapshot()",
        "drop trigger checkout_policy_stamp on public.bookings",
        "drop function public.stamp_checkout_policy()",
        "alter table public.bookings drop column checkout_policy_version",
        "alter table public.booking_payments drop column service_amount, drop column online_processing_charge, drop column provider_session_id",
    ):
        op.execute(sql)
