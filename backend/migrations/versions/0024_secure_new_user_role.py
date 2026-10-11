"""Harden trusted role assignment and the browser-facing database surface.

Revision ID: 0024_secure_new_user_role
Revises: 0023_notification_data
Create Date: 2026-10-11 11:44:15.138823
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024_secure_new_user_role"
down_revision: str | Sequence[str] | None = "0023_notification_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Use trusted metadata, lock privileged RPCs, and fail closed with RLS."""
    op.execute(
        """
        create or replace function handle_new_user()
        returns trigger language plpgsql security definer set search_path = public as $$
        begin
          insert into public.profiles (id, email, phone, full_name, avatar_url, role)
          values (
            new.id,
            new.email,
            new.phone,
            coalesce(new.raw_user_meta_data ->> 'full_name',
                     new.raw_user_meta_data ->> 'name', ''),
            coalesce(new.raw_user_meta_data ->> 'avatar_url',
                     new.raw_user_meta_data ->> 'picture'),
            case
              when new.raw_app_meta_data ->> 'role' in
                   ('super_admin', 'owner', 'staff', 'customer')
                then (new.raw_app_meta_data ->> 'role')::user_role
              else 'customer'::user_role
            end
          )
          on conflict (id) do nothing;
          return new;
        end $$;
        """
    )
    op.execute("revoke execute on function public.handle_new_user() from public, anon, authenticated")
    op.execute("grant execute on function public.handle_new_user() to postgres, service_role")
    op.execute("revoke execute on function public.get_active_tokens(uuid) from public, anon, authenticated")
    op.execute("grant execute on function public.get_active_tokens(uuid) to postgres, service_role")
    op.execute(
        "revoke execute on function public.create_booking(uuid, uuid, uuid[], timestamptz, text, text, "
        "public.booking_source, text) from public, anon, authenticated"
    )
    op.execute(
        "grant execute on function public.create_booking(uuid, uuid, uuid[], timestamptz, text, text, "
        "public.booking_source, text) to postgres, service_role"
    )
    op.execute("revoke execute on function public.register_device_token(text, text, text) from public, anon")
    op.execute("grant execute on function public.register_device_token(text, text, text) to authenticated, service_role")
    op.execute("revoke execute on function public.deactivate_device_token(text) from public, anon")
    op.execute("grant execute on function public.deactivate_device_token(text) to authenticated, service_role")
    for table in (
        "subscription_plans",
        "subscription_provider_accounts",
        "salon_subscriptions",
        "subscription_events",
        "alembic_version",
    ):
        op.execute(f"alter table public.{table} enable row level security")
    op.execute("alter function public.demote_other_main_images() set search_path = public")
    op.execute(
        "alter function public.is_subscription_promotion_active("
        "public.subscription_status, timestamptz, timestamptz, timestamptz, timestamptz) "
        "set search_path = public"
    )
    op.execute("alter function public.set_audit_actor() set search_path = public")
    op.execute("alter function public.set_updated_at() set search_path = public")
    op.execute("alter function public.stamp_booking_lifecycle() set search_path = public")
    op.execute("alter function public.stamp_notification_read_at() set search_path = public")
    for name, table, column in (
        ("idx_booking_services_service_id", "booking_services", "service_id"),
        ("idx_staff_profile_id", "staff", "profile_id"),
        ("idx_notifications_booking_id", "notifications", "booking_id"),
        ("idx_notification_deliveries_device_token_id", "notification_deliveries", "device_token_id"),
        ("idx_notification_outbox_user_id", "notification_outbox", "user_id"),
        ("idx_salon_subscriptions_plan_id", "salon_subscriptions", "plan_id"),
    ):
        op.execute(f"create index if not exists {name} on public.{table}({column})")


def downgrade() -> None:
    """Restore the previous metadata behavior for a strict schema rollback."""
    op.execute(
        """
        create or replace function handle_new_user()
        returns trigger language plpgsql security definer set search_path = public as $$
        begin
          insert into public.profiles (id, email, phone, full_name, avatar_url, role)
          values (
            new.id,
            new.email,
            new.phone,
            coalesce(new.raw_user_meta_data ->> 'full_name',
                     new.raw_user_meta_data ->> 'name', ''),
            coalesce(new.raw_user_meta_data ->> 'avatar_url',
                     new.raw_user_meta_data ->> 'picture'),
            coalesce((new.raw_user_meta_data ->> 'role')::user_role, 'customer')
          )
          on conflict (id) do nothing;
          return new;
        end $$;
        """
    )
    op.execute("grant execute on function public.handle_new_user() to public, anon, authenticated")
    op.execute("grant execute on function public.get_active_tokens(uuid) to public, anon, authenticated")
    op.execute(
        "grant execute on function public.create_booking(uuid, uuid, uuid[], timestamptz, text, text, "
        "public.booking_source, text) to public, anon, authenticated"
    )
    op.execute("grant execute on function public.register_device_token(text, text, text) to public, anon")
    op.execute("grant execute on function public.deactivate_device_token(text) to public, anon")
    for table in (
        "subscription_plans",
        "subscription_provider_accounts",
        "salon_subscriptions",
        "subscription_events",
        "alembic_version",
    ):
        op.execute(f"alter table public.{table} disable row level security")
    for name in (
        "idx_booking_services_service_id",
        "idx_staff_profile_id",
        "idx_notifications_booking_id",
        "idx_notification_deliveries_device_token_id",
        "idx_notification_outbox_user_id",
        "idx_salon_subscriptions_plan_id",
    ):
        op.execute(f"drop index if exists public.{name}")
    op.execute("alter function public.demote_other_main_images() reset search_path")
    op.execute(
        "alter function public.is_subscription_promotion_active("
        "public.subscription_status, timestamptz, timestamptz, timestamptz, timestamptz) reset search_path"
    )
    op.execute("alter function public.set_audit_actor() reset search_path")
    op.execute("alter function public.set_updated_at() reset search_path")
    op.execute("alter function public.stamp_booking_lifecycle() reset search_path")
    op.execute("alter function public.stamp_notification_read_at() reset search_path")
