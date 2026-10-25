-- Prepared only. Explicit reviewed migration, never API startup.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='30s';
-- statement --
ALTER TABLE public.support_tickets
  ADD COLUMN retained_restricted boolean NOT NULL DEFAULT false,
  ADD COLUMN erasure_policy_version text CHECK (erasure_policy_version='support-erasure-v1'),
  ADD COLUMN erasure_retention_reason text CHECK (erasure_retention_reason='operational_review_pending'),
  ALTER COLUMN customer_id DROP NOT NULL;
-- statement --
ALTER TABLE public.support_tickets ADD CONSTRAINT support_customer_or_retained
  CHECK (customer_id IS NOT NULL OR retained_restricted) NOT VALID;
-- statement --
ALTER TABLE public.support_tickets VALIDATE CONSTRAINT support_customer_or_retained;
-- statement --
CREATE TABLE public.support_erasure_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id uuid NOT NULL REFERENCES public.support_tickets(id) ON DELETE RESTRICT,
  actor_pseudonym text NOT NULL CHECK (actor_pseudonym ~ '^sha256:[a-f0-9]{64}$'),
  actor_role text NOT NULL CHECK (actor_role IN ('owner','customer','staff')),
  case_type text NOT NULL DEFAULT 'support' CHECK (case_type='support'),
  policy_version text NOT NULL CHECK (policy_version='support-erasure-v1'),
  retention_reason text NOT NULL CHECK (retention_reason='operational_review_pending'),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(ticket_id,actor_pseudonym,policy_version)
);
-- statement --
ALTER TABLE public.support_erasure_events ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.support_erasure_events FROM PUBLIC,anon,authenticated,service_role;
-- statement --
GRANT SELECT,INSERT ON public.support_erasure_events TO service_role;
-- statement --
CREATE FUNCTION public.guard_support_erasure_event() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  RAISE EXCEPTION 'support_erasure_history_is_immutable' USING ERRCODE='23514';
END $$;
-- statement --
CREATE TRIGGER support_erasure_immutable BEFORE UPDATE OR DELETE ON public.support_erasure_events
  FOR EACH ROW EXECUTE FUNCTION public.guard_support_erasure_event();
-- statement --
CREATE TRIGGER support_erasure_no_truncate BEFORE TRUNCATE ON public.support_erasure_events
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_support_erasure_event();
-- statement --
REVOKE ALL ON FUNCTION public.guard_support_erasure_event() FROM PUBLIC,anon,authenticated,service_role;
-- statement --
ALTER TABLE public.subscription_billing_records
  ADD COLUMN benefits_erased_at timestamptz,
  ADD COLUMN benefits_erasure_policy text CHECK (benefits_erasure_policy='benefits-erasure-v1');
-- statement --
CREATE FUNCTION public.retained_benefit_values(source jsonb, namespace text DEFAULT 'benefits') RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE item record; retained jsonb; result jsonb; retained_key text;
BEGIN
  IF jsonb_typeof(source) IN ('number','boolean') THEN RETURN source; END IF;
  IF jsonb_typeof(source)='object' THEN
    result:='{}'::jsonb;
    FOR item IN SELECT key,value AS child FROM jsonb_each(source) LOOP
      retained:=public.retained_benefit_values(item.child,namespace||'/key:'||item.key);
      IF retained IS NOT NULL THEN
        -- Only the published catalog's machine keys survive verbatim. Custom keys
        -- can themselves contain personal text; keep their values under pseudonyms.
        retained_key:=CASE WHEN item.key IN ('unlimited_bookings','split_bill','daily_ledger',
          'rank_boost','smart_slot_filler','sms_alerts','monthly_alert_cap') THEN item.key
          ELSE '_retained_'||encode(sha256(convert_to(namespace||'/key:'||item.key,'UTF8')),'hex') END;
        result:=result || jsonb_build_object(retained_key,retained);
      END IF;
    END LOOP;
    RETURN result;
  END IF;
  IF jsonb_typeof(source)='array' THEN
    result:='[]'::jsonb;
    FOR item IN SELECT child,ord FROM jsonb_array_elements(source) WITH ORDINALITY AS a(child,ord) ORDER BY ord LOOP
      retained:=public.retained_benefit_values(item.child,namespace||'/item:'||item.ord::text);
      IF retained IS NOT NULL THEN result:=result || jsonb_build_array(retained); END IF;
    END LOOP;
    RETURN result;
  END IF;
  RETURN NULL;
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.retained_benefit_values(jsonb,text) FROM PUBLIC,anon,authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.retained_benefit_values(jsonb,text) TO service_role;
-- statement --
CREATE OR REPLACE FUNCTION public.tg_subscription_billing_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE subject uuid; redaction boolean:=false;
BEGIN
  subject:=nullif(current_setting('app.benefits_erasure_subject',true),'')::uuid;
  IF subject IS NOT NULL AND current_setting('app.account_erasure',true)='on'
    AND OLD.benefits_erased_at IS NULL AND NEW.benefits_erased_at=transaction_timestamp()
    AND NEW.benefits_erasure_policy='benefits-erasure-v1'
    AND NEW.benefits=coalesce(public.retained_benefit_values(OLD.benefits,OLD.id::text),'{}'::jsonb)
    AND (to_jsonb(NEW)-ARRAY['benefits','benefits_erased_at','benefits_erasure_policy'])
       =(to_jsonb(OLD)-ARRAY['benefits','benefits_erased_at','benefits_erasure_policy'])
    AND EXISTS(SELECT 1 FROM public.account_deletion_requests r JOIN public.profiles p ON p.id=r.user_id
      JOIN public.salons s ON s.owner_id=r.user_id WHERE r.user_id=subject AND r.status='processing'
      AND r.role='owner' AND p.role::text='owner' AND s.id=OLD.salon_id) THEN
    redaction:=true;
  END IF;
  IF NEW.salon_id IS DISTINCT FROM OLD.salon_id OR NEW.plan_id IS DISTINCT FROM OLD.plan_id
    OR NEW.provider IS DISTINCT FROM OLD.provider OR NEW.receipt IS DISTINCT FROM OLD.receipt
    OR NEW.amount IS DISTINCT FROM OLD.amount OR NEW.currency IS DISTINCT FROM OLD.currency
    OR NEW.billing_interval IS DISTINCT FROM OLD.billing_interval OR NEW.plan_code IS DISTINCT FROM OLD.plan_code
    OR ((NEW.benefits IS DISTINCT FROM OLD.benefits OR NEW.benefits_erased_at IS DISTINCT FROM OLD.benefits_erased_at
      OR NEW.benefits_erasure_policy IS DISTINCT FROM OLD.benefits_erasure_policy) AND NOT redaction) THEN
    RAISE EXCEPTION 'subscription_billing_snapshot_is_immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.provider_order_ref IS NOT NULL AND NEW.provider_order_ref IS DISTINCT FROM OLD.provider_order_ref THEN
    RAISE EXCEPTION 'subscription_billing_order_is_immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.provider_payment_ref IS NOT NULL AND NEW.provider_payment_ref IS DISTINCT FROM OLD.provider_payment_ref THEN
    RAISE EXCEPTION 'subscription_billing_payment_is_immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.applied_at IS NOT NULL AND (NEW.applied_at IS DISTINCT FROM OLD.applied_at
    OR NEW.period_start IS DISTINCT FROM OLD.period_start OR NEW.period_end IS DISTINCT FROM OLD.period_end
    OR NEW.subscription_id IS DISTINCT FROM OLD.subscription_id) THEN
    RAISE EXCEPTION 'subscription_billing_application_is_immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.status IN ('paid','partially_refunded','refunded') AND NEW.status IN ('created','authorized','failed','expired') THEN
    RAISE EXCEPTION 'subscription_billing_status_regression' USING ERRCODE='23514';
  END IF;
  IF OLD.status='refunded' AND NEW.status IN ('paid','partially_refunded') THEN
    RAISE EXCEPTION 'subscription_billing_status_regression' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE FUNCTION public.erase_subscription_benefit_text(subject uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE prior_subject text;
BEGIN
  IF current_setting('app.account_erasure',true) IS DISTINCT FROM 'on' THEN
    RAISE EXCEPTION 'verified_erasure_required' USING ERRCODE='42501';
  END IF;
  PERFORM r.id FROM public.account_deletion_requests r JOIN public.profiles p ON p.id=r.user_id
    WHERE r.user_id=subject AND r.role='owner' AND p.role::text='owner' AND r.status='processing' FOR UPDATE OF r;
  IF NOT FOUND THEN RAISE EXCEPTION 'verified_erasure_required' USING ERRCODE='42501'; END IF;
  prior_subject:=current_setting('app.benefits_erasure_subject',true);
  PERFORM set_config('app.benefits_erasure_subject',subject::text,true);
  UPDATE public.subscription_billing_records SET
    benefits=coalesce(public.retained_benefit_values(benefits,id::text),'{}'::jsonb),
    benefits_erased_at=transaction_timestamp(),benefits_erasure_policy='benefits-erasure-v1'
    WHERE benefits_erased_at IS NULL AND salon_id IN (SELECT id FROM public.salons WHERE owner_id=subject);
  PERFORM set_config('app.benefits_erasure_subject',coalesce(prior_subject,''),true);
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.erase_subscription_benefit_text(uuid) FROM PUBLIC,anon,authenticated,service_role;
-- statement --
GRANT EXECUTE ON FUNCTION public.erase_subscription_benefit_text(uuid) TO service_role;
