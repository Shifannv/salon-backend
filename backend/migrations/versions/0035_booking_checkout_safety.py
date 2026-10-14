"""Transactional trial, checkout, collection and append-only audit enforcement.

Revision ID: 0035_booking_checkout_safety
Revises: 0034_booking_lifecycle_states
"""

from pathlib import Path

from alembic import op

revision = "0035_booking_checkout_safety"
down_revision = "0034_booking_lifecycle_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Explicit boundaries: one statement per asyncpg prepared execution.
    sql = (Path(__file__).parents[1] / "0035_booking_checkout_safety.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    op.execute("""do $$ begin
      if exists(select 1 from public.booking_audit_events) or exists(select 1 from public.customer_booking_restrictions)
        or exists(select 1 from public.bookings where status in ('checked_in','no_show')) then
        raise exception 'Booking/audit history exists; use a reviewed forward migration';
      end if;
    end $$""")
    import importlib.util
    def load(filename):
        spec = importlib.util.spec_from_file_location(filename, Path(__file__).with_name(filename + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    # Restore the prior functions, while retaining revoked Data API mutation privileges.
    load("0022_salon_accepting_bookings")._replace_functions(gated=True)
    trial = load("0032_salon_access_state")
    op.execute(trial._START)
    op.execute(trial._RECOMPUTE)
    op.execute("create trigger t_bookings_trial_status after update of status on public.bookings for each row execute function public.tg_bookings_recompute_trial()")
    for sql in (
        "drop trigger booking_checkout_guard on public.bookings",
        "drop trigger booking_audit_append on public.bookings",
        "drop trigger payment_audit_append on public.booking_payments",
        "drop table public.booking_audit_events",
        "drop table public.customer_booking_restrictions",
        "drop function public.guard_booking_checkout()",
        "drop function public.booking_append_audit()",
        "drop function public.payment_append_audit()",
        "drop function public.guard_audit_immutable()",
        "drop function public.salon_booking_eligible(uuid)",
        "alter table public.bookings drop constraint bookings_no_overlap",
        "alter table public.bookings add constraint bookings_no_overlap exclude using gist (staff_id with =, tstzrange(start_datetime,end_datetime) with &&) where (status in ('pending','confirmed'))",
        "drop index public.idx_booking_pay_at_salon_day",
        "drop index public.idx_salon_access_eligibility",
        "drop index public.idx_subscription_booking_eligibility",
        "alter table public.bookings drop column booking_calendar_date",
        "alter table public.booking_payments drop column collection_method, drop column collected_by_owner",
    ):
        op.execute(sql)
