-- Prepared only. Verified account erasure may redact these two immutable logs.
-- No historical migration is edited and no money, dates or audit rows are removed.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '30s';
-- statement --
ALTER TABLE public.booking_customer_changes ADD COLUMN anonymized_at timestamptz;
-- statement --
ALTER TABLE public.booking_finance_commands ADD COLUMN anonymized_at timestamptz;
-- statement --
CREATE FUNCTION public.booking_audit_identifier_hash(domain text, value text) RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE SET search_path=pg_catalog AS $$
  SELECT 'sha256:' || encode(sha256(convert_to(domain || ':' || value,'UTF8')),'hex')
$$;
-- statement --
REVOKE ALL ON FUNCTION public.booking_audit_identifier_hash(text,text) FROM PUBLIC,anon,authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.booking_audit_identifier_hash(text,text) TO service_role;
-- statement --
-- Equality remains enforced across raw future references and erased references.
CREATE UNIQUE INDEX booking_finance_reference_fingerprint ON public.booking_finance_commands
  ((CASE WHEN anonymized_at IS NULL THEN public.booking_audit_identifier_hash('finance-reference',reference)
         ELSE reference END)) WHERE action='record_payout';
-- statement --
CREATE UNIQUE INDEX booking_finance_key_fingerprint ON public.booking_finance_commands
  (booking_id,(CASE WHEN anonymized_at IS NULL THEN public.booking_audit_identifier_hash('finance-key',idempotency_key)
                   ELSE idempotency_key END));
-- statement --
CREATE UNIQUE INDEX booking_change_key_fingerprint ON public.booking_customer_changes
  (booking_id,(CASE WHEN anonymized_at IS NULL THEN public.booking_audit_identifier_hash('change-key',idempotency_key)
                   ELSE idempotency_key END));
-- statement --
CREATE FUNCTION public.redacted_booking_service_snapshot(snapshot jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
  SELECT coalesce(jsonb_agg(
    (CASE WHEN jsonb_typeof(item->'price')='number' THEN jsonb_build_object('price',item->'price') ELSE '{}'::jsonb END)
    || (CASE WHEN jsonb_typeof(item->'duration')='number' THEN jsonb_build_object('duration',item->'duration') ELSE '{}'::jsonb END)
    ORDER BY ord),'[]'::jsonb)
  FROM jsonb_array_elements(CASE WHEN jsonb_typeof(snapshot)='array' THEN snapshot ELSE '[]'::jsonb END)
    WITH ORDINALITY AS entries(item,ord)
$$;
-- statement --
REVOKE ALL ON FUNCTION public.redacted_booking_service_snapshot(jsonb) FROM PUBLIC,anon,authenticated,service_role;
-- statement --
CREATE FUNCTION public.redacted_booking_audit_row(table_name text, original jsonb, erased_at timestamptz)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE patch jsonb;
BEGIN
  IF table_name='booking_customer_changes' THEN
    patch:=jsonb_build_object(
      'idempotency_key',public.booking_audit_identifier_hash('change-key',original->>'idempotency_key'),
      'request','{}'::jsonb,
      'previous_services',public.redacted_booking_service_snapshot(original->'previous_services'),
      'committed_services',public.redacted_booking_service_snapshot(original->'committed_services'),
      'old_staff_id',substr(public.booking_audit_identifier_hash('change-staff',(original->>'id') || ':' || (original->>'old_staff_id')),8,32)::uuid,
      'new_staff_id',substr(public.booking_audit_identifier_hash('change-staff',(original->>'id') || ':' || (original->>'new_staff_id')),8,32)::uuid);
  ELSIF table_name='booking_finance_commands' THEN
    patch:=jsonb_build_object(
      'idempotency_key',public.booking_audit_identifier_hash('finance-key',original->>'idempotency_key'),
      'reference',public.booking_audit_identifier_hash('finance-reference',original->>'reference'),
      'request',
        (CASE WHEN jsonb_typeof(original->'request'->'amount')='number'
          THEN jsonb_build_object('amount',original->'request'->'amount') ELSE '{}'::jsonb END)
        || (CASE WHEN jsonb_typeof(original->'request'->'version')='number'
          THEN jsonb_build_object('version',original->'request'->'version') ELSE '{}'::jsonb END));
  ELSE
    RAISE EXCEPTION 'unsupported_booking_audit' USING ERRCODE='23514';
  END IF;
  RETURN original || patch || jsonb_build_object('anonymized_at',erased_at);
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.redacted_booking_audit_row(text,jsonb,timestamptz) FROM PUBLIC,anon,authenticated,service_role;
-- statement --
CREATE OR REPLACE FUNCTION public.guard_booking_change_history() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE subject uuid;
BEGIN
  IF TG_OP='UPDATE' AND OLD.anonymized_at IS NULL THEN
    subject:=nullif(current_setting('app.booking_audit_erasure_subject',true),'')::uuid;
    IF subject IS NOT NULL AND current_setting('app.account_erasure',true)='on'
      AND EXISTS(SELECT 1 FROM public.account_deletion_requests r JOIN public.profiles p ON p.id=r.user_id
        WHERE r.user_id=subject AND r.status='processing' AND r.role=p.role::text
          AND r.role IN ('customer','owner'))
      AND EXISTS(SELECT 1 FROM public.bookings b JOIN public.salons s ON s.id=b.salon_id
        WHERE b.id=OLD.booking_id AND (b.customer_id=subject OR s.owner_id=subject))
      AND to_jsonb(NEW)=public.redacted_booking_audit_row(TG_TABLE_NAME,to_jsonb(OLD),transaction_timestamp()) THEN
      RETURN NEW;
    END IF;
  END IF;
  RAISE EXCEPTION 'booking_change_history_is_immutable' USING ERRCODE='23514';
END $$;
-- statement --
-- Disallow forged already-redacted inserts, including through server-side callers.
CREATE FUNCTION public.guard_booking_audit_insert() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF NEW.anonymized_at IS NOT NULL THEN
    RAISE EXCEPTION 'booking_change_history_is_immutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER booking_change_insert_privacy BEFORE INSERT ON public.booking_customer_changes
  FOR EACH ROW EXECUTE FUNCTION public.guard_booking_audit_insert();
-- statement --
CREATE TRIGGER booking_finance_insert_privacy BEFORE INSERT ON public.booking_finance_commands
  FOR EACH ROW EXECUTE FUNCTION public.guard_booking_audit_insert();
-- statement --
REVOKE ALL ON FUNCTION public.guard_booking_audit_insert() FROM PUBLIC,anon,authenticated,service_role;
-- statement --
CREATE FUNCTION public.erase_booking_audit_personal_data(subject uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE prior_subject text; audit record; role_name text;
BEGIN
  IF current_setting('app.account_erasure',true) IS DISTINCT FROM 'on' THEN
    RAISE EXCEPTION 'verified_erasure_required' USING ERRCODE='42501';
  END IF;
  SELECT r.role INTO role_name FROM public.account_deletion_requests r JOIN public.profiles p ON p.id=r.user_id
    WHERE r.user_id=subject AND r.status='processing' AND r.role=p.role::text
      AND r.role IN ('customer','owner') FOR UPDATE OF r;
  IF role_name IS NULL THEN
    -- A retry after the profile was removed has nothing further to redact.
    IF NOT EXISTS(SELECT 1 FROM public.profiles WHERE id=subject) THEN RETURN; END IF;
    RAISE EXCEPTION 'verified_erasure_required' USING ERRCODE='42501';
  END IF;
  -- Serialize with customer changes/finance commands before detaching account FKs.
  PERFORM b.id FROM public.bookings b JOIN public.salons s ON s.id=b.salon_id
    WHERE b.customer_id=subject OR s.owner_id=subject ORDER BY b.id FOR UPDATE OF b;
  prior_subject:=current_setting('app.booking_audit_erasure_subject',true);
  PERFORM set_config('app.booking_audit_erasure_subject',subject::text,true);
  FOR audit IN SELECT c.* FROM public.booking_customer_changes c JOIN public.bookings b ON b.id=c.booking_id
    JOIN public.salons s ON s.id=b.salon_id
    WHERE c.anonymized_at IS NULL AND (b.customer_id=subject OR s.owner_id=subject)
  LOOP
    UPDATE public.booking_customer_changes SET
      (idempotency_key,request,previous_services,committed_services,old_staff_id,new_staff_id,anonymized_at)=
      (SELECT x.idempotency_key,x.request,x.previous_services,x.committed_services,x.old_staff_id,x.new_staff_id,x.anonymized_at
        FROM jsonb_populate_record(NULL::public.booking_customer_changes,
          public.redacted_booking_audit_row('booking_customer_changes',to_jsonb(audit),transaction_timestamp())) x)
      WHERE id=audit.id;
  END LOOP;
  FOR audit IN SELECT c.* FROM public.booking_finance_commands c JOIN public.bookings b ON b.id=c.booking_id
    JOIN public.salons s ON s.id=b.salon_id
    WHERE c.anonymized_at IS NULL AND (b.customer_id=subject OR s.owner_id=subject)
  LOOP
    UPDATE public.booking_finance_commands SET (idempotency_key,request,reference,anonymized_at)=
      (SELECT x.idempotency_key,x.request,x.reference,x.anonymized_at
        FROM jsonb_populate_record(NULL::public.booking_finance_commands,
          public.redacted_booking_audit_row('booking_finance_commands',to_jsonb(audit),transaction_timestamp())) x)
      WHERE booking_id=audit.booking_id AND idempotency_key=audit.idempotency_key;
  END LOOP;
  PERFORM set_config('app.booking_audit_erasure_subject',coalesce(prior_subject,''),true);
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.erase_booking_audit_personal_data(uuid) FROM PUBLIC,anon,authenticated,service_role;
-- statement --
GRANT EXECUTE ON FUNCTION public.erase_booking_audit_personal_data(uuid) TO service_role;
