# Codex prompt: deploy migration 0049 and the subscription backend to GCP

> Cashfree checkout follow-up (28 October 2026): the new one-time Cashfree subscription adapter and website integration are documented in `backend/docs/SUBSCRIPTION_CASHFREE_SETUP.md`. This older 0049 runbook alone does not enable that flow. Check the currently deployed contract and migration state before using it; never rerun 0049 if already applied or overwrite later admin price changes with the historical expected prices below. Merchant credentials belong in backend deployment secrets, not the owner app. Cashfree sandbox acceptance and production activation remain separate release gates.

Paste everything below the line into Codex. It runs with your gcloud CLI.

---

Deploy the salon-backend subscription release to GCP: **staging first, then production only after I approve.**
The code is on GitHub, repo `Thameempp/salon-backend`, branch `shifan`, commit `6ff578f` or later.
Work from `backend/`.

## What this release contains
- **Migration `0049_trial_salon_plan_prices`** (`backend/migrations/sql/0049_trial_salon_plan_prices.sql`):
  - `start_salon_trial()` gives new salons 60 days / 500 bookings. Running trials keep their limits.
  - `salon_access.trial_booking_limit` defaults to 500.
  - A new table `public.salon_plan_prices` holds admin-set per-salon prices. RLS is on, and it is granted to `service_role` only.
  - The default 6m/12m prices change to 20% / 30% off the monthly price. Each update only applies if the price still equals its seed value.

  | Plan | Old price | New price |
  |---|---|---|
  | `growth_6m` | 1499 | 1675 |
  | `growth_12m` | 1999 | 2932 |
  | `premium_6m` | 2499 | 2875 |
  | `premium_12m` | 3499 | 5032 |

- **API changes:**
  - `GET /v1/subscription-plans` adds `default_price_amount`, `custom_price`, `monthly_equivalent` and `discount_percent`.
  - `GET /v1/subscriptions/config` adds `checkout_url`.
  - Checkout charges the per-salon price when one is set.
  - There are new super-admin routes under `/v1/admin/salons/{salon_id}/plan-prices`.
- **New setting:** `SUBSCRIPTION_WEBSITE_URL`, which must be https.

**Order matters.** The new code reads `salon_plan_prices`, so in each environment apply 0049 *before* the new revision takes traffic. Otherwise the plan list and checkout return 500.

## Hard rules
- **Never run `alembic upgrade head` and never `alembic stamp`** on the Mumbai Supabase database (`wqjlgpnbiapcrlkxumcp`). `docs/verification/CLOUD_RUN_DEPLOYMENT_ASSESSMENT_2026-10-22.md` records that its `alembic_version` table is empty and that migrations 0038–0048 are held for review. Apply **only** the 0049 SQL file, statement by statement, as described below.
- **Never print, log or commit secret values**, including `DATABASE_URL`, keys and env-file contents. Read secrets into memory and pass them through stdin, as the existing deploy docs do.
- Don't create branches, delete anything, or change DNS, the load balancer, scaling, billing or the old VM.
- `apiv1.mudassirmhd.in` and `api.salones.in` must both keep working. They reach the same `salon-api-production` service.
- **Stop and report** instead of improvising if any pre-flight check fails.

## Step 1 — Find out which database each environment uses
1. Compare the database **host and project ref** used by staging (`salon-api-mumbai-staging`, secret `salon-mumbai-staging-database-url`) and by production (`salon-api-production`, secret `salon-production-env`). Print only the host and ref, never the password.
2. **If both use the same database,** staging is not a separate test of the migration. Tell me, and wait for me to choose one of these:
   - (a) apply 0049 once, then deploy staging, test, and deploy production;
   - (b) create a separate staging database first.

## Step 2 — Pre-flight checks on the target database (read-only)
Run these and show me the results:
- Does `public.salon_plan_prices` exist? (Expected: no.)
- Do these all exist: `public.salon_access` with `trial_booking_limit`, `public.start_salon_trial(uuid, timestamptz)`, `public.subscription_plans` with codes `growth_1m`, `growth_6m`, `growth_12m`, `premium_1m`, `premium_6m`, `premium_12m`, `public.salons`, `public.profiles`, and the roles `service_role`, `anon` and `authenticated`?
- `select code, price_amount from subscription_plans order by tier, code;`
- `select count(*) from salon_access where trial_started_at is not null;`, for information only.

If any prerequisite is missing, or `salon_plan_prices` already exists, **stop and report**.

## Step 3 — Back up, then apply 0049 (staging target first)
1. Take a backup of the affected objects, or confirm that a fresh Supabase backup or PITR point exists, and give me its time.
2. In **one transaction**, run every statement of `0049_trial_salon_plan_prices.sql`, split on the line `-- statement --`. The file starts with `SET LOCAL lock_timeout` and `statement_timeout`. Use `psql --single-transaction -v ON_ERROR_STOP=1` or an equivalent.
3. Verify the result:
   - `salon_plan_prices` exists, with RLS on.
   - `has_table_privilege('anon'|'authenticated', 'public.salon_plan_prices', 'SELECT')` is false.
   - The 6m/12m prices are 1675 / 2932 / 2875 / 5032. Any plan an admin had already edited keeps its price.
   - `select column_default from information_schema.columns where table_name='salon_access' and column_name='trial_booking_limit'` returns 500.

## Step 4 — Staging deploy (`salon-api-mumbai-staging`, project `saloon-505509`, region `asia-south1`)
1. Build the image from `backend/` using the existing `Dockerfile`, the same way `docs/verification/cloud-run-mumbai-staging-2026-10-16.md` does (including the Supabase CA layer). Push it to Artifact Registry repo `salon-mumbai-staging` and deploy by **digest** to a new revision.
2. Add these non-secret env vars to the revision:
   - `SUBSCRIPTION_WEBSITE_URL=https://salones.in/subscription/checkout`
   - `BACKEND_CORS_ORIGINS` must include `https://salones.in` and `https://www.salones.in`. Keep any existing origins.
3. Keep staging private: IAM invoker only, max instances 1. Smoke-test with an identity token:
   - `/health` returns 200.
   - `GET /v1/subscriptions/config` returns `checkout_url` = `https://salones.in/subscription/checkout`.
   - Called with an owner token, `GET /v1/subscription-plans` returns:
     - `growth_6m`: `price_amount` 1675.00, `discount_percent` 20, `monthly_equivalent` 279.17;
     - `growth_12m`: 2932.00 / 30 / 244.33;
     - `premium_6m`: 2875.00 / 20;
     - `premium_12m`: 5032.00 / 30;
     - monthly plans: `discount_percent` null.
   - `/openapi.json` lists `/v1/admin/salons/{salon_id}/plan-prices`.
4. **Report the staging results and stop. Wait for my "go production".**

## Step 5 — Production (`salon-api-production`), only after my approval
1. If production uses a different database from staging, repeat Steps 2–3 on the production database.
2. Build and push the same commit for production (production registry `salon-production/api`), or promote the verified image if the setup allows it. Deploy a new revision **with no traffic** (`--no-traffic --tag candidate0049`).
3. Production configuration comes from the mounted secret `salon-production-env`. Add a **new secret version** with `SUBSCRIPTION_WEBSITE_URL=https://salones.in/subscription/checkout` added. Also make sure `BACKEND_CORS_ORIGINS` includes `https://salones.in` and `https://www.salones.in`. Keep every other key unchanged, and never print the payload. Point the candidate revision at the new version.
4. Smoke-test the tagged candidate URL with the same checks as staging.
5. Shift 100% of traffic to it. Then verify these return what the staging checks expect:
   - `https://api.salones.in/health`
   - `https://api.salones.in/v1/subscriptions/config`
   - `https://api.salones.in/v1/subscription-plans` (owner token)
   - `https://apiv1.mudassirmhd.in/health`
6. **Rollback:** if any check fails, immediately send traffic back to the previous revision and report. The migration is additive, so the old code keeps working with the new table.

## Report back
- which databases staging and production use;
- the pre-flight results;
- the backup time;
- the migration verification output;
- the image digests and revision names;
- the smoke-test results (with secrets redacted);
- the rollback revision name.
