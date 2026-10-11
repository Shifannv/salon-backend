"""Payment-collection foundation: ledger, refunds, webhook intake, idempotency.

``booking_payments`` is the source of truth for money. ``bookings.payment_status``,
``payment_method``, ``paid_amount`` and ``refunded_amount`` become a *derived cache*
written only by ``recompute_booking_payment_state`` (guarded by a trigger). The two
existing enums are deliberately NOT widened; every new status column is ``text`` +
``CHECK`` so it can be changed inside a transaction.

Landmines handled here:

* ``stamp_booking_lifecycle`` stamps ``payment_recorded_by`` from ``auth.uid()``, which is
  NULL on the webhook worker's session. Gateway attribution therefore lives on
  ``booking_payments.recorded_by`` and the recompute sets ``payment_recorded_at`` itself.
* If cash and a gateway capture both land, the recompute raises
  ``payment_overcollection`` (SQLSTATE 23514). The capture is refused rather than silently
  over-collected; a human issues a refund (see RUNBOOK.md).

Revision ID: 0026_booking_payments
Revises: 0025_salon_payout_accounts
Create Date: 2026-10-11 18:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0026_booking_payments"
down_revision: str | Sequence[str] | None = "0025_salon_payout_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every new table is backend-only: RLS on, withdraw Supabase's auto-grants.
_NEW_TABLES = (
    "booking_payments",
    "payment_refunds",
    "payment_webhook_events",
    "payment_idempotency_keys",
    "payment_provider_accounts",
)


def _sql(*statements: str) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    """Create the ledger, derived-cache columns, recompute function and triggers."""

    # ------------------------------------------------------------------ bookings
    _sql(
        """
        alter table public.bookings
          add column if not exists currency text not null default 'INR',
          add column if not exists deposit_amount numeric(10,2),
          add column if not exists paid_amount numeric(10,2) not null default 0,
          add column if not exists refunded_amount numeric(10,2) not null default 0
        """,
        "alter table public.bookings drop constraint if exists bookings_currency_format_check",
        """
        alter table public.bookings add constraint bookings_currency_format_check
          check (currency ~ '^[A-Z]{3}$')
        """,
        "alter table public.bookings drop constraint if exists bookings_deposit_amount_check",
        """
        alter table public.bookings add constraint bookings_deposit_amount_check
          check (deposit_amount is null or (deposit_amount >= 0 and deposit_amount <= total_price))
        """,
        "alter table public.bookings drop constraint if exists bookings_paid_amounts_check",
        """
        alter table public.bookings add constraint bookings_paid_amounts_check
          check (paid_amount >= 0 and refunded_amount >= 0 and refunded_amount <= paid_amount)
        """,
        # Widen 0013's CHECK. It was created with an explicit name, but sweep any CHECK that
        # mentions the column so a hand-edited deployment cannot keep the old, narrower rule.
        """
        do $$
        declare c record;
        begin
          for c in
            select conname from pg_constraint
            where conrelid = 'public.bookings'::regclass and contype = 'c'
              and pg_get_constraintdef(oid) like '%payment_preference%'
          loop
            execute format('alter table public.bookings drop constraint %I', c.conname);
          end loop;
        end $$
        """,
        """
        alter table public.bookings add constraint bookings_payment_preference_check
          check (payment_preference is null
                 or payment_preference in ('pay_at_salon', 'pay_advance', 'pay_full'))
        """,
    )

    # -------------------------------------------------------------------- ledger
    _sql(
        """
        create table if not exists public.booking_payments (
          id               uuid primary key default gen_random_uuid(),
          booking_id       uuid not null references public.bookings(id),
          salon_id         uuid not null references public.salons(id),
          payer_id         uuid references public.profiles(id),
          recorded_by      uuid references public.profiles(id),
          channel          text not null check (channel in ('manual', 'gateway')),
          purpose          text not null check (purpose in ('deposit', 'balance', 'full')),
          settlement_model text not null default 'offline'
            check (settlement_model in ('offline', 'platform_collect', 'direct_to_salon')),
          provider         text,
          method           text check (method is null or method in ('cash', 'online')),
          instrument       text check (instrument is null
                                       or instrument in ('upi', 'card', 'netbanking', 'wallet', 'other')),
          amount           numeric(10,2) not null check (amount >= 0),
          platform_fee_amount numeric(10,2) not null default 0 check (platform_fee_amount >= 0),
          currency         text not null default 'INR' check (currency ~ '^[A-Z]{3}$'),
          status           text not null default 'created'
            check (status in ('created', 'authorized', 'captured', 'failed', 'cancelled',
                              'expired', 'partially_refunded', 'refunded')),
          intent_reference text not null,
          order_ref        text,
          payment_ref      text,
          failure_code     text check (failure_code is null or char_length(failure_code) <= 120),
          expires_at       timestamptz,
          authorized_at    timestamptz,
          captured_at      timestamptz,
          created_by       uuid references public.profiles(id),
          updated_by       uuid references public.profiles(id),
          created_at       timestamptz not null default now(),
          updated_at       timestamptz not null default now(),
          constraint uq_booking_payments_intent_reference unique (intent_reference),
          constraint uq_booking_payments_provider_payment unique (provider, payment_ref),
          constraint uq_booking_payments_provider_order unique (provider, order_ref),
          constraint ck_booking_payments_provider_matches_channel
            check ((channel = 'manual') = (provider is null)),
          constraint ck_booking_payments_manual_is_settled
            check (channel = 'gateway' or (status = 'captured' and method is not null)),
          constraint ck_booking_payments_gateway_amount_positive
            check (channel = 'manual' or amount > 0)
        )
        """,
        "create index if not exists idx_booking_payments_booking on public.booking_payments(booking_id)",
        "create index if not exists idx_booking_payments_salon on public.booking_payments(salon_id, created_at desc)",
        "create index if not exists idx_booking_payments_payer on public.booking_payments(payer_id)",
        # At most one open gateway intent per booking: a second checkout must reuse or cancel it.
        """
        create unique index if not exists uq_booking_payments_one_open_intent
          on public.booking_payments(booking_id)
          where channel = 'gateway' and status in ('created', 'authorized')
        """,
        # Reconciliation scans non-terminal gateway intents by age.
        """
        create index if not exists idx_booking_payments_reconcile
          on public.booking_payments(updated_at)
          where channel = 'gateway' and status in ('created', 'authorized')
        """,
        """
        create table if not exists public.payment_refunds (
          id               uuid primary key default gen_random_uuid(),
          payment_id       uuid not null references public.booking_payments(id),
          booking_id       uuid not null references public.bookings(id),
          provider         text,
          refund_ref       text,
          amount           numeric(10,2) not null check (amount > 0),
          status           text not null default 'created'
            check (status in ('created', 'processed', 'failed')),
          reason           text check (reason is null or char_length(reason) <= 500),
          idempotency_key  text not null check (char_length(idempotency_key) between 1 and 200),
          failure_code     text check (failure_code is null or char_length(failure_code) <= 120),
          requested_by     uuid references public.profiles(id),
          processed_at     timestamptz,
          created_by       uuid references public.profiles(id),
          updated_by       uuid references public.profiles(id),
          created_at       timestamptz not null default now(),
          updated_at       timestamptz not null default now(),
          constraint uq_payment_refunds_provider_ref unique (provider, refund_ref),
          constraint uq_payment_refunds_idempotency unique (payment_id, idempotency_key)
        )
        """,
        "create index if not exists idx_payment_refunds_booking on public.payment_refunds(booking_id)",
        """
        create index if not exists idx_payment_refunds_open
          on public.payment_refunds(updated_at) where status = 'created'
        """,
        # --------------------------------------------------- webhook intake / replay gate
        """
        create table if not exists public.payment_webhook_events (
          id                       uuid primary key default gen_random_uuid(),
          provider_name            text not null,
          provider_event_reference text not null,
          event_type               text not null,
          payload_hash             text not null,
          normalized               jsonb not null default '{}'::jsonb,
          processing_status        text not null default 'received'
            check (processing_status in ('received', 'processing', 'processed', 'ignored', 'failed')),
          attempts                 integer not null default 0 check (attempts >= 0),
          next_attempt_at          timestamptz not null default now(),
          locked_at                timestamptz,
          last_error_code          text check (last_error_code is null or char_length(last_error_code) <= 120),
          received_at              timestamptz not null default now(),
          processed_at             timestamptz,
          constraint uq_payment_webhook_events_provider_ref
            unique (provider_name, provider_event_reference)
        )
        """,
        """
        create index if not exists idx_payment_webhook_events_due
          on public.payment_webhook_events(next_attempt_at)
          where processing_status in ('received', 'processing', 'failed')
        """,
        # ----------------------------------------------------- money-request idempotency
        """
        create table if not exists public.payment_idempotency_keys (
          id                  uuid primary key default gen_random_uuid(),
          actor_id            uuid not null,
          scope               text not null,
          idempotency_key     text not null check (char_length(idempotency_key) between 8 and 200),
          request_fingerprint text not null,
          response_status     integer,
          response_body       jsonb,
          created_at          timestamptz not null default now(),
          expires_at          timestamptz not null,
          constraint uq_payment_idempotency unique (actor_id, scope, idempotency_key)
        )
        """,
        "create index if not exists idx_payment_idempotency_expiry on public.payment_idempotency_keys(expires_at)",
        # --------------------------------- model (A): the salon as payee (not the payer)
        """
        create table if not exists public.payment_provider_accounts (
          id                 uuid primary key default gen_random_uuid(),
          salon_id           uuid not null references public.salons(id),
          provider           text not null,
          provider_account_ref text,
          onboarding_status  text not null default 'not_started'
            check (onboarding_status in ('not_started', 'pending', 'needs_action', 'active',
                                         'rejected', 'suspended')),
          requirements       jsonb not null default '[]'::jsonb,
          created_by         uuid references public.profiles(id),
          updated_by         uuid references public.profiles(id),
          created_at         timestamptz not null default now(),
          updated_at         timestamptz not null default now(),
          constraint uq_payment_provider_accounts_salon unique (salon_id, provider)
        )
        """,
    )

    # ------------------------------------------------------------ audit / timestamps
    for table in ("booking_payments", "payment_refunds", "payment_provider_accounts"):
        _sql(
            f"drop trigger if exists t_{table}_updated on public.{table}",
            f"create trigger t_{table}_updated before update on public.{table} "
            "for each row execute function set_updated_at()",
            f"drop trigger if exists t_{table}_audit on public.{table}",
            f"create trigger t_{table}_audit before insert or update on public.{table} "
            "for each row execute function set_audit_actor()",
        )

    # ------------------------------------------- backfill (before triggers exist)
    # Pre-ledger paid bookings get one synthetic manual row so that the first recompute
    # after this migration reproduces, rather than erases, their paid state.
    _sql(
        """
        insert into public.booking_payments
          (booking_id, salon_id, payer_id, recorded_by, channel, purpose, settlement_model,
           method, amount, currency, status, intent_reference, captured_at, created_at)
        select b.id, b.salon_id, b.customer_id, b.payment_recorded_by, 'manual', 'full', 'offline',
               coalesce(b.payment_method::text, 'cash'), b.total_price, 'INR', 'captured',
               'legacy:' || b.id::text, coalesce(b.payment_recorded_at, b.updated_at),
               coalesce(b.payment_recorded_at, b.updated_at)
        from public.bookings b
        where b.payment_status = 'paid'
        on conflict (intent_reference) do nothing
        """,
        # Keep the one-off backfill from rewriting updated_at/updated_by on history.
        "alter table public.bookings disable trigger t_bookings_updated",
        "alter table public.bookings disable trigger t_bookings_audit",
        "alter table public.bookings disable trigger t_bookings_lifecycle",
        "update public.bookings set paid_amount = total_price where payment_status = 'paid' and paid_amount = 0",
        "alter table public.bookings enable trigger t_bookings_updated",
        "alter table public.bookings enable trigger t_bookings_audit",
        "alter table public.bookings enable trigger t_bookings_lifecycle",
    )

    # ------------------------------------------------------------- recompute function
    _sql(
        """
        create or replace function public.recompute_booking_payment_state(p_booking_id uuid)
        returns void language plpgsql set search_path = public as $$
        declare
          v_total     numeric(10,2);
          v_paid      numeric(10,2);
          v_refunded  numeric(10,2);
          v_count     integer;
          v_net       numeric(10,2);
          v_method    text;
          v_at        timestamptz;
          v_by        uuid;
          v_new       public.payment_status;
        begin
          select total_price into v_total from public.bookings where id = p_booking_id for update;
          if not found then
            return;
          end if;

          select coalesce(sum(p.amount), 0), count(*) into v_paid, v_count
          from public.booking_payments p
          where p.booking_id = p_booking_id
            and p.status in ('captured', 'partially_refunded', 'refunded');

          select coalesce(sum(r.amount), 0) into v_refunded
          from public.payment_refunds r
          where r.booking_id = p_booking_id and r.status = 'processed';

          v_net := v_paid - v_refunded;
          if v_net > v_total then
            raise exception 'payment_overcollection'
              using errcode = '23514',
                    detail = format('booking %s: net collected %s exceeds total %s',
                                    p_booking_id, v_net, v_total);
          end if;

          v_new := case when v_count > 0 and v_net >= v_total then 'paid' else 'unpaid' end;

          select case when p.channel = 'gateway' then 'online' else coalesce(p.method, 'cash') end,
                 p.captured_at, p.recorded_by
            into v_method, v_at, v_by
          from public.booking_payments p
          where p.booking_id = p_booking_id
            and p.status in ('captured', 'partially_refunded', 'refunded')
          order by p.captured_at desc nulls last, p.created_at desc
          limit 1;

          perform set_config('app.payment_recompute', 'on', true);
          update public.bookings
          set paid_amount = v_paid,
              refunded_amount = v_refunded,
              payment_status = v_new,
              payment_method = case when v_count > 0 and (v_net > 0 or v_new = 'paid')
                                    then v_method::public.payment_method else null end,
              payment_recorded_at = case when v_new = 'paid'
                                         then coalesce(v_at, payment_recorded_at, now()) else null end,
              payment_recorded_by = case when v_new = 'paid'
                                         then coalesce(v_by, payment_recorded_by) else null end
          where id = p_booking_id;
          perform set_config('app.payment_recompute', 'off', true);
        end $$
        """,
        "revoke all on function public.recompute_booking_payment_state(uuid) from public, anon, authenticated",
        # A ledger change refreshes the booking cache.
        """
        create or replace function public.tg_booking_payments_recompute()
        returns trigger language plpgsql set search_path = public as $$
        begin
          if tg_op = 'DELETE' then
            perform public.recompute_booking_payment_state(old.booking_id);
            return old;
          end if;
          perform public.recompute_booking_payment_state(new.booking_id);
          return new;
        end $$
        """,
        # Ledger rows may move forward but never back out of a settled state, and the
        # identity of the money (booking, amount, intent) is immutable after insert.
        """
        create or replace function public.tg_booking_payments_guard()
        returns trigger language plpgsql set search_path = public as $$
        begin
          if new.booking_id is distinct from old.booking_id
             or new.amount is distinct from old.amount
             or new.intent_reference is distinct from old.intent_reference
             or new.channel is distinct from old.channel then
            raise exception 'booking_payment_identity_is_immutable' using errcode = '23514';
          end if;
          if old.status in ('captured', 'partially_refunded', 'refunded')
             and new.status in ('created', 'authorized', 'failed', 'cancelled', 'expired') then
            raise exception 'booking_payment_status_regression' using errcode = '23514';
          end if;
          return new;
        end $$
        """,
        # Processed refunds move the payment row through partially_refunded/refunded.
        """
        create or replace function public.tg_payment_refunds_guard()
        returns trigger language plpgsql set search_path = public as $$
        declare
          v_amount    numeric(10,2);
          v_committed numeric(10,2);
        begin
          select amount into v_amount from public.booking_payments where id = new.payment_id;
          select coalesce(sum(r.amount), 0) into v_committed
          from public.payment_refunds r
          where r.payment_id = new.payment_id and r.status <> 'failed'
            and (tg_op = 'INSERT' or r.id <> new.id);
          if new.status <> 'failed' and v_committed + new.amount > v_amount then
            raise exception 'refund_exceeds_payment' using errcode = '23514';
          end if;
          return new;
        end $$
        """,
        """
        create or replace function public.tg_payment_refunds_recompute()
        returns trigger language plpgsql set search_path = public as $$
        declare
          v_booking uuid := coalesce(new.booking_id, old.booking_id);
          v_payment uuid := coalesce(new.payment_id, old.payment_id);
          v_amount  numeric(10,2);
          v_status  text;
          v_done    numeric(10,2);
          v_next    text;
        begin
          select amount, status into v_amount, v_status
          from public.booking_payments where id = v_payment;
          select coalesce(sum(r.amount), 0) into v_done
          from public.payment_refunds r where r.payment_id = v_payment and r.status = 'processed';
          v_next := case when v_done = 0 then 'captured'
                         when v_done >= v_amount then 'refunded'
                         else 'partially_refunded' end;
          if v_status in ('captured', 'partially_refunded', 'refunded') and v_status <> v_next then
            -- booking_payments' own trigger recomputes the booking.
            update public.booking_payments set status = v_next where id = v_payment;
          else
            perform public.recompute_booking_payment_state(v_booking);
          end if;
          return coalesce(new, old);
        end $$
        """,
        # Nothing outside the recompute function may write the derived cache.
        """
        create or replace function public.guard_booking_payment_columns()
        returns trigger language plpgsql set search_path = public as $$
        begin
          if (new.payment_status is distinct from old.payment_status
              or new.payment_method is distinct from old.payment_method
              or new.paid_amount is distinct from old.paid_amount
              or new.refunded_amount is distinct from old.refunded_amount)
             and coalesce(current_setting('app.payment_recompute', true), '') <> 'on' then
            raise exception 'booking_payment_columns_are_derived' using errcode = '42501';
          end if;
          return new;
        end $$
        """,
        "drop trigger if exists t_booking_payments_guard on public.booking_payments",
        """
        create trigger t_booking_payments_guard before update on public.booking_payments
          for each row execute function public.tg_booking_payments_guard()
        """,
        "drop trigger if exists t_booking_payments_recompute on public.booking_payments",
        """
        create trigger t_booking_payments_recompute
          after insert or update or delete on public.booking_payments
          for each row execute function public.tg_booking_payments_recompute()
        """,
        "drop trigger if exists t_payment_refunds_guard on public.payment_refunds",
        """
        create trigger t_payment_refunds_guard before insert or update on public.payment_refunds
          for each row execute function public.tg_payment_refunds_guard()
        """,
        "drop trigger if exists t_payment_refunds_recompute on public.payment_refunds",
        """
        create trigger t_payment_refunds_recompute
          after insert or update on public.payment_refunds
          for each row execute function public.tg_payment_refunds_recompute()
        """,
        "drop trigger if exists t_bookings_payment_guard on public.bookings",
        """
        create trigger t_bookings_payment_guard before update on public.bookings
          for each row execute function public.guard_booking_payment_columns()
        """,
    )

    # ------------------------------------------------- RLS, policies, privileges
    for table in _NEW_TABLES:
        op.execute(f"alter table public.{table} enable row level security")
    _sql(
        # Read-only visibility for the parties to a payment; every write is backend-only.
        "drop policy if exists booking_payments_parties_read on public.booking_payments",
        """
        create policy booking_payments_parties_read on public.booking_payments
          for select using (payer_id = auth.uid() or public.owns_salon(salon_id) or public.is_super_admin())
        """,
        "drop policy if exists payment_refunds_parties_read on public.payment_refunds",
        """
        create policy payment_refunds_parties_read on public.payment_refunds
          for select using (exists (
            select 1 from public.booking_payments p
            where p.id = payment_id
              and (p.payer_id = auth.uid() or public.owns_salon(p.salon_id) or public.is_super_admin())
          ))
        """,
        "drop policy if exists payment_provider_accounts_owner_read on public.payment_provider_accounts",
        """
        create policy payment_provider_accounts_owner_read on public.payment_provider_accounts
          for select using (public.owns_salon(salon_id) or public.is_super_admin())
        """,
        # payment_webhook_events and payment_idempotency_keys: RLS on, no policy = deny-all.
    )
    for table in _NEW_TABLES:
        _sql(
            f"revoke all on public.{table} from public, anon, authenticated",
            f"grant all on public.{table} to postgres, service_role",
        )


def downgrade() -> None:
    """Remove the payment foundation. DESTROYS the ledger, refunds and webhook intake."""

    _sql(
        "drop trigger if exists t_bookings_payment_guard on public.bookings",
        "drop table if exists public.payment_provider_accounts",
        "drop table if exists public.payment_idempotency_keys",
        "drop table if exists public.payment_webhook_events",
        "drop table if exists public.payment_refunds",
        "drop table if exists public.booking_payments",
        "drop function if exists public.guard_booking_payment_columns()",
        "drop function if exists public.tg_payment_refunds_recompute()",
        "drop function if exists public.tg_payment_refunds_guard()",
        "drop function if exists public.tg_booking_payments_guard()",
        "drop function if exists public.tg_booking_payments_recompute()",
        "drop function if exists public.recompute_booking_payment_state(uuid)",
        # Restore the narrower 0013 rule; rows using the new values can no longer exist.
        "alter table public.bookings drop constraint if exists bookings_payment_preference_check",
        "alter table public.bookings disable trigger t_bookings_updated",
        """
        update public.bookings set payment_preference = 'pay_at_salon'
        where payment_preference in ('pay_advance', 'pay_full')
        """,
        "alter table public.bookings enable trigger t_bookings_updated",
        """
        alter table public.bookings add constraint bookings_payment_preference_check
          check (payment_preference is null or payment_preference = 'pay_at_salon')
        """,
        "alter table public.bookings drop constraint if exists bookings_paid_amounts_check",
        "alter table public.bookings drop constraint if exists bookings_deposit_amount_check",
        "alter table public.bookings drop constraint if exists bookings_currency_format_check",
        """
        alter table public.bookings
          drop column if exists refunded_amount,
          drop column if exists paid_amount,
          drop column if exists deposit_amount,
          drop column if exists currency
        """,
    )
