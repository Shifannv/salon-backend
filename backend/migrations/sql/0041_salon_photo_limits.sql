-- PREPARED ONLY. Deploy compatible API/clients first, reconcile target history,
-- review affected rows and approve this exact revision before production execution.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '15s';
-- statement --
LOCK TABLE public.salons, public.services, public.salon_images IN ACCESS EXCLUSIVE MODE;
-- statement --
-- Keep the SQL RPC signature for existing callers, but remove its column dependency.
-- Its legacy description output becomes NULL; HTTP schemas omit that field entirely.
CREATE OR REPLACE FUNCTION public.get_salon_by_qr(p_qr_token text)
RETURNS TABLE (id uuid, name text, description text, city text, timezone text,
               approval_mode public.approval_mode)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT s.id, s.name, NULL::text, s.city, s.timezone, s.approval_mode
  FROM public.salons s
  WHERE s.qr_token = p_qr_token AND s.is_active AND s.profile_completed
    AND s.approval_status = 'approved';
$$;
-- statement --
ALTER TABLE public.salons DROP COLUMN description;
-- statement --
ALTER TABLE public.services DROP COLUMN description;
-- statement --
-- Stable order: cover wins duplicate URLs; keep the first two distinct non-cover
-- images. Retire excess references using the platform's existing soft-delete rule.
WITH distinct_photos AS (
  SELECT id, salon_id, is_main, sort_order, created_at,
         row_number() OVER (PARTITION BY salon_id, url
                            ORDER BY is_main DESC, sort_order, created_at, id) AS duplicate_rank
  FROM public.salon_images WHERE is_active
), ranked AS (
  SELECT id, row_number() OVER (PARTITION BY salon_id, is_main
                               ORDER BY sort_order, created_at, id) AS role_rank
  FROM distinct_photos WHERE duplicate_rank = 1
), retired AS (
  SELECT id FROM distinct_photos WHERE duplicate_rank > 1
  UNION
  SELECT r.id FROM ranked r JOIN distinct_photos d USING (id)
  WHERE r.role_rank > CASE WHEN d.is_main THEN 1 ELSE 2 END
)
UPDATE public.salon_images SET is_active = false, is_main = false
WHERE id IN (SELECT id FROM retired);
-- statement --
CREATE UNIQUE INDEX uq_salon_active_image_url ON public.salon_images(salon_id, url) WHERE is_active;
-- statement --
CREATE OR REPLACE FUNCTION public.guard_salon_photo_limits()
RETURNS trigger LANGUAGE plpgsql SET search_path = public AS $$
DECLARE photo_count integer;
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.salon_id IS DISTINCT FROM OLD.salon_id THEN
    RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'salon_photo_move_forbidden';
  END IF;
  IF NOT NEW.is_active THEN RETURN NEW; END IF;
  IF current_setting('transaction_isolation') <> 'read committed' THEN
    RAISE EXCEPTION USING ERRCODE = '40001', MESSAGE = 'salon_photos_require_read_committed';
  END IF;
  -- Serialize all API and direct DB writes for this salon before counting.
  PERFORM id FROM public.salons WHERE id = NEW.salon_id FOR UPDATE;
  SELECT count(*) INTO photo_count FROM public.salon_images
  WHERE salon_id = NEW.salon_id AND is_active AND id <> NEW.id AND is_main = NEW.is_main;
  IF photo_count >= (CASE WHEN NEW.is_main THEN 1 ELSE 2 END) THEN
    RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'salon_photo_limit';
  END IF;
  RETURN NEW;
END;
$$;
-- statement --
-- Runs before the legacy t_salon_main_image trigger can demote an existing cover.
CREATE TRIGGER t_salon_image_limits BEFORE INSERT OR UPDATE ON public.salon_images
FOR EACH ROW EXECUTE FUNCTION public.guard_salon_photo_limits();
-- statement --
REVOKE ALL ON FUNCTION public.guard_salon_photo_limits() FROM PUBLIC, anon, authenticated;
