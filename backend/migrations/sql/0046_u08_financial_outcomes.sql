-- Prepared only. No external refund/payout is issued by these SQL commands.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '30s';
-- statement --
CREATE TABLE public.booking_financial_outcomes (
  booking_id uuid PRIMARY KEY REFERENCES public.bookings(id) ON DELETE RESTRICT,
  policy_version text NOT NULL CHECK (policy_version='u08-2026-10-23-v1'),
  kind text NOT NULL CHECK (kind IN ('customer_cancellation','salon_cancellation','no_show','completed')),
  decision_at timestamptz NOT NULL,
  appointment_start timestamptz NOT NULL,
  captured_amount numeric(10,2) NOT NULL CHECK (captured_amount>=0),
  customer_refund_promised numeric(10,2) NOT NULL CHECK (customer_refund_promised>=0),
  cancellation_penalty numeric(10,2) NOT NULL CHECK (cancellation_penalty>=0),
  previously_refunded numeric(10,2) NOT NULL CHECK (previously_refunded>=0),
  refund_due numeric(10,2) NOT NULL CHECK (refund_due>=0),
  retained_amount numeric(10,2) NOT NULL CHECK (retained_amount>=0),
  provider_costs numeric(10,2) CHECK (provider_costs>=0),
  platform_share numeric(10,2) CHECK (platform_share>=0),
  salon_share numeric(10,2) CHECK (salon_share>=0),
  platform_shortfall numeric(10,2) CHECK (platform_shortfall>=0),
  funds_held_verified boolean NOT NULL DEFAULT false,
  requires_reconciliation boolean NOT NULL DEFAULT false,
  approved_amount numeric(10,2) NOT NULL DEFAULT 0 CHECK (approved_amount>=0),
  paid_out_amount numeric(10,2) NOT NULL DEFAULT 0 CHECK (paid_out_amount>=0),
  version integer NOT NULL DEFAULT 0 CHECK (version>=0),
  CHECK (customer_refund_promised<=captured_amount),
  CHECK (refund_due=greatest(0,customer_refund_promised-previously_refunded)),
  CHECK (paid_out_amount<=approved_amount),
  CHECK (approved_amount<=coalesce(salon_share,0))
);
-- statement --
CREATE TABLE public.booking_finance_commands (
  booking_id uuid NOT NULL REFERENCES public.booking_financial_outcomes(booking_id) ON DELETE RESTRICT,
  idempotency_key text NOT NULL CHECK (length(idempotency_key) BETWEEN 8 AND 128),
  action text NOT NULL,
  request jsonb NOT NULL,
  reference text NOT NULL CHECK (length(reference) BETWEEN 1 AND 128),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (booking_id,idempotency_key)
);
-- statement --
CREATE UNIQUE INDEX booking_finance_payout_reference ON public.booking_finance_commands(reference)
  WHERE action='record_payout';
-- statement --
CREATE TABLE public.booking_policy_refund_jobs (
  booking_id uuid PRIMARY KEY REFERENCES public.booking_financial_outcomes(booking_id) ON DELETE RESTRICT,
  amount numeric(10,2) NOT NULL CHECK (amount>0),
  status text NOT NULL DEFAULT 'pending_provider' CHECK (status IN ('pending_provider','reconciling','processed','manual_review')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
ALTER TABLE public.booking_financial_outcomes ENABLE ROW LEVEL SECURITY;
-- statement --
CREATE TABLE public.booking_finance_reconciliations (
  booking_id uuid PRIMARY KEY REFERENCES public.booking_financial_outcomes(booking_id) ON DELETE RESTRICT,
  reason text NOT NULL CHECK (reason IN ('pending_capture','ledger_changed')),
  observed_captured numeric(10,2) NOT NULL,
  observed_refunded numeric(10,2) NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
ALTER TABLE public.booking_finance_reconciliations ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.booking_finance_reconciliations FROM PUBLIC,anon,authenticated,service_role;
-- statement --
GRANT SELECT ON public.booking_finance_reconciliations TO service_role;
-- statement --
ALTER TABLE public.booking_finance_commands ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.booking_policy_refund_jobs ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.booking_financial_outcomes,public.booking_finance_commands,public.booking_policy_refund_jobs
  FROM PUBLIC,anon,authenticated,service_role;
-- statement --
GRANT SELECT ON public.booking_financial_outcomes,public.booking_finance_commands,public.booking_policy_refund_jobs TO service_role;
-- statement --
CREATE FUNCTION public.guard_financial_outcome_snapshot() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
  IF TG_OP IN ('DELETE','TRUNCATE') THEN RAISE EXCEPTION 'financial_history_is_immutable' USING ERRCODE='23514'; END IF;
  IF ROW(NEW.booking_id,NEW.policy_version,NEW.kind,NEW.decision_at,NEW.appointment_start,
      NEW.captured_amount,NEW.customer_refund_promised,NEW.cancellation_penalty,
      NEW.previously_refunded,NEW.refund_due,NEW.retained_amount)
    IS DISTINCT FROM ROW(OLD.booking_id,OLD.policy_version,OLD.kind,OLD.decision_at,OLD.appointment_start,
      OLD.captured_amount,OLD.customer_refund_promised,OLD.cancellation_penalty,
      OLD.previously_refunded,OLD.refund_due,OLD.retained_amount) THEN
    RAISE EXCEPTION 'financial_history_is_immutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER financial_outcome_snapshot BEFORE UPDATE OR DELETE ON public.booking_financial_outcomes
  FOR EACH ROW EXECUTE FUNCTION public.guard_financial_outcome_snapshot();
-- statement --
CREATE TRIGGER financial_outcome_no_truncate BEFORE TRUNCATE ON public.booking_financial_outcomes
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_financial_outcome_snapshot();
-- statement --
CREATE TRIGGER finance_commands_immutable BEFORE UPDATE OR DELETE ON public.booking_finance_commands
  FOR EACH ROW EXECUTE FUNCTION public.guard_booking_change_history();
-- statement --
CREATE TRIGGER finance_commands_no_truncate BEFORE TRUNCATE ON public.booking_finance_commands
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_booking_change_history();
-- statement --
REVOKE ALL ON FUNCTION public.guard_financial_outcome_snapshot() FROM PUBLIC,anon,authenticated;
-- statement --
CREATE FUNCTION public.snapshot_terminal_booking_finance() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE
  v_paid numeric(10,2);
  v_refunded numeric(10,2);
  v_refund numeric(10,2);
  v_penalty numeric(10,2);
  v_kind text;
  v_pending boolean;
  v_at timestamptz:=statement_timestamp();
BEGIN
  IF NEW.checkout_policy_version<>'u08-2026-10-23-v1' OR NEW.status=OLD.status
    OR NEW.status NOT IN ('cancelled','rejected','completed','no_show') THEN RETURN NULL; END IF;
  IF NEW.status='completed' AND NEW.payment_status<>'paid' THEN
    RAISE EXCEPTION 'payment_collection_required' USING ERRCODE='23514';
  END IF;
  SELECT coalesce(sum(amount-overcollected_amount),0) INTO v_paid FROM public.booking_payments
    WHERE booking_id=NEW.id AND channel='gateway' AND status IN ('captured','partially_refunded','refunded');
  SELECT coalesce(sum(r.amount),0) INTO v_refunded FROM public.payment_refunds r
    JOIN public.booking_payments p ON p.id=r.payment_id
    WHERE r.booking_id=NEW.id AND p.channel='gateway' AND r.status='processed' AND NOT r.applies_to_excess;
  IF EXISTS(SELECT 1 FROM public.booking_payments WHERE booking_id=NEW.id AND online_processing_charge<>0) THEN
    RAISE EXCEPTION 'u08_ledger_requires_reconciliation' USING ERRCODE='23514';
  END IF;
  v_kind:=CASE WHEN NEW.status='completed' THEN 'completed'
    WHEN NEW.status='rejected' THEN 'salon_cancellation'
    WHEN NEW.status='no_show' OR NEW.cancellation_reason LIKE 'Customer no-show%' THEN 'no_show'
    WHEN current_setting('app.booking_cancel_origin',true)='customer' THEN 'customer_cancellation'
    ELSE 'salon_cancellation' END;
  IF v_kind='salon_cancellation' AND OLD.status='checked_in' THEN
    RAISE EXCEPTION 'u08_cancellation_after_check_in_requires_review' USING ERRCODE='23514';
  END IF;
  v_penalty:=CASE WHEN v_kind='salon_cancellation' THEN 0
    WHEN v_kind IN ('completed','no_show') THEN v_paid
    WHEN NEW.start_datetime-v_at>=interval '48 hours' THEN least(20,v_paid)
    WHEN NEW.start_datetime-v_at>=interval '12 hours' THEN round(v_paid*0.05,2)
    WHEN NEW.start_datetime-v_at>interval '4 hours' THEN round(v_paid*0.35,2)
    ELSE v_paid END;
  v_refund:=CASE WHEN v_kind='completed' THEN 0 ELSE v_paid-v_penalty END;
  v_pending:=EXISTS(SELECT 1 FROM public.booking_payments WHERE booking_id=NEW.id AND status IN ('created','authorized'));
  INSERT INTO public.booking_financial_outcomes(booking_id,policy_version,kind,decision_at,appointment_start,
    captured_amount,customer_refund_promised,cancellation_penalty,previously_refunded,refund_due,retained_amount,
    provider_costs,platform_share,salon_share,platform_shortfall,requires_reconciliation)
  VALUES(NEW.id,NEW.checkout_policy_version,v_kind,v_at,NEW.start_datetime,v_paid,v_refund,
    CASE WHEN v_kind='completed' THEN 0 ELSE v_penalty END,
    v_refunded,greatest(0,v_refund-v_refunded),greatest(0,v_paid-greatest(v_refund,v_refunded)),
    CASE WHEN v_paid=0 THEN 0 ELSE NULL END,CASE WHEN v_paid=0 THEN 0 ELSE NULL END,
    CASE WHEN v_paid=0 THEN 0 ELSE NULL END,CASE WHEN v_paid=0 THEN 0 ELSE NULL END,v_pending);
  IF v_pending THEN
    INSERT INTO public.booking_finance_reconciliations(booking_id,reason,observed_captured,observed_refunded)
      VALUES(NEW.id,'pending_capture',v_paid,v_refunded);
  END IF;
  IF v_refund>v_refunded THEN
    INSERT INTO public.booking_policy_refund_jobs(booking_id,amount,status)
      VALUES(NEW.id,v_refund-v_refunded,CASE WHEN v_pending THEN 'manual_review' ELSE 'pending_provider' END);
  END IF;
  RETURN NULL;
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.snapshot_terminal_booking_finance() FROM PUBLIC,anon,authenticated;
-- statement --
CREATE TRIGGER booking_terminal_finance AFTER UPDATE ON public.bookings
  FOR EACH ROW EXECUTE FUNCTION public.snapshot_terminal_booking_finance();
-- statement --
CREATE FUNCTION public.reconcile_terminal_booking_funds() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE f public.booking_financial_outcomes%rowtype; c numeric(10,2); r numeric(10,2);
BEGIN
  SELECT * INTO f FROM public.booking_financial_outcomes WHERE booking_id=NEW.id FOR UPDATE;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT coalesce(sum(amount-overcollected_amount),0) INTO c FROM public.booking_payments
    WHERE booking_id=NEW.id AND channel='gateway' AND status IN ('captured','partially_refunded','refunded');
  SELECT coalesce(sum(rf.amount),0) INTO r FROM public.payment_refunds rf JOIN public.booking_payments p ON p.id=rf.payment_id
    WHERE rf.booking_id=NEW.id AND p.channel='gateway' AND rf.status='processed' AND NOT rf.applies_to_excess;
  IF c<>f.captured_amount OR r>greatest(f.previously_refunded,f.customer_refund_promised) THEN
    UPDATE public.booking_financial_outcomes SET requires_reconciliation=true,version=version+1 WHERE booking_id=NEW.id;
    INSERT INTO public.booking_finance_reconciliations(booking_id,reason,observed_captured,observed_refunded)
      VALUES(NEW.id,'ledger_changed',c,r) ON CONFLICT(booking_id) DO UPDATE SET reason='ledger_changed',
        observed_captured=excluded.observed_captured,observed_refunded=excluded.observed_refunded,updated_at=now();
    UPDATE public.booking_policy_refund_jobs SET status='manual_review',updated_at=now() WHERE booking_id=NEW.id;
  ELSIF r>=f.customer_refund_promised THEN
    UPDATE public.booking_policy_refund_jobs SET status='processed',updated_at=now() WHERE booking_id=NEW.id;
  END IF;
  RETURN NULL;
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.reconcile_terminal_booking_funds() FROM PUBLIC,anon,authenticated;
-- statement --
CREATE TRIGGER booking_finance_ledger_reconciliation AFTER UPDATE OF paid_amount,refunded_amount ON public.bookings
  FOR EACH ROW WHEN (OLD.paid_amount IS DISTINCT FROM NEW.paid_amount OR OLD.refunded_amount IS DISTINCT FROM NEW.refunded_amount)
  EXECUTE FUNCTION public.reconcile_terminal_booking_funds();
-- statement --
CREATE FUNCTION public.manage_booking_finance(p_booking uuid,p_version integer,p_key text,p_action text,
  p_amount numeric,p_reference text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE
  f public.booking_financial_outcomes%rowtype;
  prior jsonb;
  payload jsonb;
  pool numeric(10,2);
  salon_amount numeric(10,2);
  platform_amount numeric(10,2);
  shortfall numeric(10,2);
  captured_now numeric(10,2);
  refunded_now numeric(10,2);
BEGIN
  IF NOT EXISTS(SELECT 1 FROM public.profiles WHERE id=auth.uid() AND role='super_admin' AND is_active) THEN
    RAISE EXCEPTION 'finance_admin_required' USING ERRCODE='P0001';
  END IF;
  IF p_action NOT IN ('provider_costs','hold_review','approve','record_payout') OR p_amount IS NULL OR p_amount<0
    OR p_amount<>round(p_amount,2) OR p_amount::text IN ('NaN','Infinity','-Infinity')
    OR p_reference IS NULL OR p_reference !~ '^[A-Za-z0-9_:.\-]{1,128}$'
    OR p_key IS NULL OR length(p_key) NOT BETWEEN 8 AND 128 THEN
    RAISE EXCEPTION 'invalid_finance_command' USING ERRCODE='P0001'; END IF;
  -- Payment observation and terminal transitions lock the booking before the outcome.
  PERFORM 1 FROM public.bookings WHERE id=p_booking FOR UPDATE;
  SELECT * INTO f FROM public.booking_financial_outcomes WHERE booking_id=p_booking FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'finance_not_found' USING ERRCODE='P0001'; END IF;
  payload:=jsonb_build_object('action',p_action,'amount',p_amount,'reference',p_reference,'version',p_version);
  SELECT request INTO prior FROM public.booking_finance_commands WHERE booking_id=p_booking AND idempotency_key=p_key;
  IF FOUND THEN
    IF prior<>payload THEN RAISE EXCEPTION 'idempotency_key_reused' USING ERRCODE='P0001'; END IF;
    RETURN;
  END IF;
  IF f.version IS DISTINCT FROM p_version THEN RAISE EXCEPTION 'finance_version_conflict' USING ERRCODE='P0001'; END IF;
  IF p_action='provider_costs' THEN
    IF f.approved_amount>0 THEN RAISE EXCEPTION 'finance_already_approved' USING ERRCODE='P0001'; END IF;
    pool:=greatest(0,f.retained_amount-p_amount);
    IF f.kind='salon_cancellation' THEN salon_amount:=0;platform_amount:=0;shortfall:=p_amount;
    ELSIF f.kind='completed' THEN salon_amount:=pool;platform_amount:=0;shortfall:=greatest(0,p_amount-f.retained_amount);
    ELSE platform_amount:=round(pool*0.30,2);salon_amount:=pool-platform_amount;shortfall:=greatest(0,p_amount-f.retained_amount);
    END IF;
    UPDATE public.booking_financial_outcomes SET provider_costs=p_amount,salon_share=salon_amount,
      platform_share=platform_amount,platform_shortfall=shortfall,version=version+1 WHERE booking_id=p_booking;
  ELSIF p_action='hold_review' THEN
    IF p_amount<>0 THEN RAISE EXCEPTION 'invalid_finance_command' USING ERRCODE='P0001'; END IF;
    UPDATE public.booking_financial_outcomes SET funds_held_verified=true,version=version+1 WHERE booking_id=p_booking;
  ELSE
    SELECT coalesce(sum(amount-overcollected_amount),0) INTO captured_now FROM public.booking_payments
      WHERE booking_id=p_booking AND channel='gateway' AND status IN ('captured','partially_refunded','refunded');
    SELECT coalesce(sum(r.amount),0) INTO refunded_now FROM public.payment_refunds r
      JOIN public.booking_payments p ON p.id=r.payment_id WHERE r.booking_id=p_booking AND p.channel='gateway'
      AND r.status='processed' AND NOT r.applies_to_excess;
    IF f.requires_reconciliation OR NOT f.funds_held_verified OR f.provider_costs IS NULL OR captured_now<>f.captured_amount
      OR refunded_now<>greatest(f.previously_refunded,f.customer_refund_promised)
      OR EXISTS(SELECT 1 FROM public.booking_payments WHERE booking_id=p_booking AND status IN ('created','authorized'))
      OR EXISTS(SELECT 1 FROM public.payment_refunds WHERE booking_id=p_booking AND status='created') THEN
      RAISE EXCEPTION 'finance_reconciliation_required' USING ERRCODE='P0001'; END IF;
    IF p_action='approve' THEN
      IF p_amount<=f.approved_amount OR p_amount>f.salon_share OR f.kind='salon_cancellation' THEN
        RAISE EXCEPTION 'invalid_payout_amount' USING ERRCODE='P0001'; END IF;
      UPDATE public.booking_financial_outcomes SET approved_amount=p_amount,version=version+1 WHERE booking_id=p_booking;
    ELSE
      IF p_amount<=0 OR f.paid_out_amount+p_amount>f.approved_amount THEN
        RAISE EXCEPTION 'invalid_payout_amount' USING ERRCODE='P0001'; END IF;
      UPDATE public.booking_financial_outcomes SET paid_out_amount=paid_out_amount+p_amount,version=version+1 WHERE booking_id=p_booking;
    END IF;
  END IF;
  INSERT INTO public.booking_finance_commands(booking_id,idempotency_key,action,request,reference)
    VALUES(p_booking,p_key,p_action,payload,p_reference);
  INSERT INTO public.booking_audit_events(booking_id,actor_id,event_type,new_state)
    VALUES(p_booking,auth.uid(),'finance_'||p_action,p_amount::text);
  IF p_action IN ('approve','record_payout') THEN
    WITH notice AS (
      INSERT INTO public.notifications(user_id,booking_id,type,title,body)
      SELECT s.owner_id,p_booking,'payout_updated','Payout updated',
        'The approved payout status has changed. Open your payout statement for details.'
      FROM public.bookings b JOIN public.salons s ON s.id=b.salon_id
      WHERE b.id=p_booking AND s.owner_id IS NOT NULL RETURNING id,user_id
    ) INSERT INTO public.notification_outbox(notification_id,user_id) SELECT id,user_id FROM notice;
  END IF;
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.manage_booking_finance(uuid,integer,text,text,numeric,text) FROM PUBLIC,anon,authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.manage_booking_finance(uuid,integer,text,text,numeric,text) TO service_role;
