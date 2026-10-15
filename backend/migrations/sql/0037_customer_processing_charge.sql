alter table public.bookings add column checkout_policy_version text not null default 'legacy';
-- statement --
create function public.stamp_checkout_policy() returns trigger language plpgsql set search_path = public as $$
begin
  if tg_op = 'INSERT' then new.checkout_policy_version := 'customer_processing_v1';
  elsif new.checkout_policy_version is distinct from old.checkout_policy_version then
    raise exception 'checkout_policy_is_immutable' using errcode = '23514';
  end if;
  return new;
end $$;
-- statement --
create trigger checkout_policy_stamp before insert or update on public.bookings for each row execute function public.stamp_checkout_policy();
-- statement --
revoke all on function public.stamp_checkout_policy() from public, anon, authenticated;
-- statement --
alter table public.booking_payments add column online_processing_charge numeric(10,2) not null default 0
  check (online_processing_charge >= 0 and online_processing_charge <= amount
    and (channel = 'gateway' or online_processing_charge = 0));
-- statement --
alter table public.booking_payments add column service_amount numeric(10,2)
  generated always as (amount - online_processing_charge) stored;
-- statement --
alter table public.booking_payments add column provider_session_id text;
-- statement --
create or replace function public.guard_collection_snapshot() returns trigger
language plpgsql set search_path = public as $$
begin
  if tg_op = 'UPDATE' and (new.collection_method is distinct from old.collection_method
    or new.collected_by_owner is distinct from old.collected_by_owner
    or new.online_processing_charge is distinct from old.online_processing_charge
    or (new.recorded_by is distinct from old.recorded_by
        and not (coalesce(current_setting('app.account_erasure', true), '') = 'on' and new.recorded_by is null))
    or new.method is distinct from old.method and new.channel = 'manual') then
    raise exception 'payment_collection_snapshot_is_immutable' using errcode = '23514';
  end if;
  if tg_op = 'INSERT' and new.channel = 'manual' then
    new.collection_method := coalesce(new.collection_method,
      case when new.method = 'cash' then 'CASH' else 'UPI_DIRECT' end);
    new.collected_by_owner := exists(select 1 from public.salons s
      where s.id = new.salon_id and s.owner_id = new.recorded_by);
  end if;
  return new;
end $$;
-- statement --
create trigger payment_collection_snapshot before insert or update on public.booking_payments
  for each row execute function public.guard_collection_snapshot();
-- statement --
revoke all on function public.guard_collection_snapshot() from public, anon, authenticated;

-- statement --
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

  -- Money collected beyond what the booking was owed (overcollected_amount) is recorded on
  -- its ledger row but never counts towards the booking's paid state.
  select coalesce(sum(case when p.amount > 0 then round((p.amount - p.overcollected_amount) * p.service_amount / p.amount, 2) else 0 end), 0), count(*) into v_paid, v_count
  from public.booking_payments p
  where p.booking_id = p_booking_id
    and p.status in ('captured', 'partially_refunded', 'refunded');

  -- A refund of the excess does not reduce the paid state either.
  select coalesce(round(sum(case when p.amount > 0 then r.amount * p.service_amount / p.amount else 0 end), 2), 0) into v_refunded
  from public.payment_refunds r join public.booking_payments p on p.id = r.payment_id
  where r.booking_id = p_booking_id and r.status = 'processed' and not r.applies_to_excess;

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
    and p.amount > p.overcollected_amount
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
