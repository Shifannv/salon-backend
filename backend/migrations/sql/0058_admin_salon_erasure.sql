-- Prepared only. Explicit reviewed migration, never API startup. Not applied to Mumbai, staging or production.
-- Admin salon erasure. A super admin can permanently delete one salon and everything that hangs off it,
-- including the append-only money records, once the application has settled refunds and payouts.
-- Two additions, nothing existing is altered:
--   1. salon_erasure_jobs: a tombstone with an opaque salon id, a status and step state. No name, phone
--      or amount. It makes a retry safe and lets late provider events for an erased salon be recognised.
--   2. erase_salon(uuid): deletes the salon in one transaction. The existing guard triggers stay exactly
--      as they are; the function disables only the row-level DELETE guards of the tables it deletes from
--      for the length of its own transaction (a rollback restores them), and re-enables them at the end.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
CREATE TABLE public.salon_erasure_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  salon_id uuid NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'erased' CHECK (status IN ('erased', 'cleanup_pending', 'complete')),
  step_state jsonb NOT NULL DEFAULT '{}'::jsonb,
  media_keys jsonb NOT NULL DEFAULT '[]'::jsonb,
  auth_user_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);
-- statement --
ALTER TABLE public.salon_erasure_jobs ENABLE ROW LEVEL SECURITY;
-- statement --
-- No policy: deny-all for the public roles. Only the backend's own role reads and writes.
REVOKE ALL ON public.salon_erasure_jobs FROM PUBLIC, anon, authenticated;
-- statement --
GRANT ALL ON public.salon_erasure_jobs TO postgres, service_role;
-- statement --
CREATE FUNCTION public.erase_salon(p_salon uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE
  v_owner uuid;
  v_proofs uuid[];
  v_guard record;
  v_disabled text[] := ARRAY[]::text[];  -- 'table|trigger|original tgenabled'
  v_item text;
  -- Every table the function deletes from. Keep in step with the integration test that walks the
  -- foreign-key graph from salons: a new table that references a salon fails it until listed here.
  v_tables text[] := ARRAY[
    'payout_audit', 'salon_payout_payments', 'salon_payout_corrections', 'salon_payout_requests', 'payout_proofs',
    'booking_finance_commands', 'booking_policy_refund_jobs', 'booking_finance_reconciliations',
    'booking_financial_outcomes', 'booking_customer_changes',
    'staff_earnings', 'booking_service_staff', 'staff_commission_rule_versions',
    'payment_refunds', 'payment_anomalies', 'booking_payments',
    'booking_action_requests', 'booking_audit_events', 'booking_services', 'bookings',
    'salon_expenses', 'salon_cash_adjustments', 'salon_day_closes', 'salon_expense_rules',
    'support_erasure_events', 'support_messages', 'support_tickets',
    'subscription_events', 'subscription_billing_records', 'salon_subscriptions', 'subscription_provider_accounts',
    'payment_provider_account_audit', 'payment_provider_accounts', 'salon_reports',
    'staff_services', 'services', 'staff', 'salons'];
BEGIN
  PERFORM set_config('lock_timeout', '5s', true);
  PERFORM set_config('statement_timeout', '120s', true);
  SELECT owner_id INTO v_owner FROM public.salons WHERE id = p_salon FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'salon_not_found' USING errcode = 'P0002';
  END IF;

  -- The append-only guards refuse every DELETE. Switch off exactly the row-level DELETE triggers of the
  -- tables listed above; TRUNCATE guards and every other trigger are untouched.
  FOR v_guard IN
    SELECT c.oid::regclass::text AS tbl, t.tgname, t.tgenabled
    FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
    WHERE c.relnamespace = 'public'::regnamespace AND c.relname = ANY (v_tables)
      AND NOT t.tgisinternal AND t.tgenabled <> 'D'
      AND (t.tgtype & 1) = 1 AND (t.tgtype & 8) = 8
    ORDER BY c.relname, t.tgname  -- one fixed lock order, so two erases cannot deadlock each other
  LOOP
    EXECUTE format('ALTER TABLE %s DISABLE TRIGGER %I', v_guard.tbl, v_guard.tgname);
    v_disabled := v_disabled || (v_guard.tbl || '|' || v_guard.tgname || '|' || v_guard.tgenabled::text);
  END LOOP;

  -- Proof files hang off payments and corrections; collect them before those rows go.
  SELECT coalesce(array_agg(DISTINCT x.proof_id), ARRAY[]::uuid[]) INTO v_proofs FROM (
    SELECT pay.proof_id FROM public.salon_payout_payments pay
      JOIN public.salon_payout_requests q ON q.id = pay.payout_id WHERE q.salon_id = p_salon
    UNION
    SELECT cor.proof_id FROM public.salon_payout_corrections cor
      JOIN public.salon_payout_requests q ON q.id = cor.payout_id WHERE q.salon_id = p_salon
  ) x WHERE x.proof_id IS NOT NULL;

  DELETE FROM public.payout_audit WHERE payout_id IN (SELECT id FROM public.salon_payout_requests WHERE salon_id = p_salon);
  DELETE FROM public.salon_payout_payments WHERE payout_id IN (SELECT id FROM public.salon_payout_requests WHERE salon_id = p_salon);
  DELETE FROM public.salon_payout_corrections WHERE payout_id IN (SELECT id FROM public.salon_payout_requests WHERE salon_id = p_salon);
  DELETE FROM public.salon_payout_requests WHERE salon_id = p_salon;
  DELETE FROM public.payout_proofs WHERE id = ANY (v_proofs);

  DELETE FROM public.booking_finance_commands WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);
  DELETE FROM public.booking_policy_refund_jobs WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);
  DELETE FROM public.booking_finance_reconciliations WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);
  DELETE FROM public.booking_financial_outcomes WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);
  DELETE FROM public.booking_customer_changes WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);

  DELETE FROM public.staff_earnings WHERE salon_id = p_salon;
  DELETE FROM public.booking_service_staff WHERE salon_id = p_salon;
  DELETE FROM public.staff_commission_rule_versions WHERE salon_id = p_salon;

  DELETE FROM public.payment_refunds WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);
  DELETE FROM public.payment_anomalies WHERE salon_id = p_salon
    OR booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);
  DELETE FROM public.booking_payments WHERE salon_id = p_salon;

  DELETE FROM public.booking_action_requests WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);
  DELETE FROM public.booking_audit_events WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);
  DELETE FROM public.booking_services WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);
  DELETE FROM public.bookings WHERE salon_id = p_salon;

  -- A reversal points at the entry it reverses (RESTRICT, and the entry type is tied to that link), so
  -- the reversals go first, then the entries they reversed.
  DELETE FROM public.salon_expenses WHERE salon_id = p_salon AND reverses_id IS NOT NULL;
  DELETE FROM public.salon_expenses WHERE salon_id = p_salon;
  DELETE FROM public.salon_cash_adjustments WHERE salon_id = p_salon AND reverses_id IS NOT NULL;
  DELETE FROM public.salon_cash_adjustments WHERE salon_id = p_salon;
  DELETE FROM public.salon_day_closes WHERE salon_id = p_salon;
  DELETE FROM public.salon_expense_rules WHERE salon_id = p_salon;

  DELETE FROM public.support_erasure_events WHERE ticket_id IN (SELECT id FROM public.support_tickets WHERE salon_id = p_salon);
  DELETE FROM public.support_messages WHERE ticket_id IN (SELECT id FROM public.support_tickets WHERE salon_id = p_salon);
  DELETE FROM public.support_tickets WHERE salon_id = p_salon;

  DELETE FROM public.subscription_events WHERE salon_subscription_id IN (SELECT id FROM public.salon_subscriptions WHERE salon_id = p_salon);
  DELETE FROM public.subscription_billing_records WHERE salon_id = p_salon;
  DELETE FROM public.salon_subscriptions WHERE salon_id = p_salon;
  DELETE FROM public.subscription_provider_accounts WHERE salon_id = p_salon;
  DELETE FROM public.payment_provider_account_audit WHERE salon_id = p_salon;
  DELETE FROM public.payment_provider_accounts WHERE salon_id = p_salon;
  DELETE FROM public.salon_reports WHERE salon_id = p_salon;
  DELETE FROM public.account_deletion_requests WHERE salon_id = p_salon;

  DELETE FROM public.staff_services WHERE staff_id IN (SELECT id FROM public.staff WHERE salon_id = p_salon);
  DELETE FROM public.services WHERE salon_id = p_salon;
  DELETE FROM public.staff WHERE salon_id = p_salon;
  -- Images, holidays, blocked slots, payout accounts, access, plan prices and overrides cascade.
  DELETE FROM public.salons WHERE id = p_salon;

  FOREACH v_item IN ARRAY v_disabled LOOP
    -- Back to exactly the mode each trigger had: 'O' origin, 'R' replica, 'A' always.
    EXECUTE format('ALTER TABLE %s %s %I', split_part(v_item, '|', 1),
      CASE split_part(v_item, '|', 3) WHEN 'R' THEN 'ENABLE REPLICA TRIGGER' WHEN 'A' THEN 'ENABLE ALWAYS TRIGGER' ELSE 'ENABLE TRIGGER' END,
      split_part(v_item, '|', 2));
  END LOOP;

  INSERT INTO public.salon_erasure_jobs (salon_id) VALUES (p_salon) ON CONFLICT (salon_id) DO NOTHING;
  RETURN v_owner;
END $$;
-- statement --
-- Only the backend's own role may run it: the function bypasses the append-only guards.
REVOKE ALL ON FUNCTION public.erase_salon(uuid) FROM PUBLIC, anon, authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.erase_salon(uuid) TO postgres, service_role;
