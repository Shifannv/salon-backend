# Production release preflight — 1 November 2026

Target: `saloon-505509 / asia-south1 / salon-api-production`.
Requested source: canonical GitHub main, `6fefff404b148af4798105228418d96f03ad8e4c` (merged PR #33). Remote main was read again during this preflight and still matched. The local branch is shifan and contains uncommitted gate corrections; those changes are not approved deployment source.

## Fresh production observations

Read-only catalogue checks at `2026-11-01T06:44:52.179023Z` and `2026-11-01T06:46:36.109864Z` supersede older claims that 0051/0052 are absent:

- `public.alembic_version` contains `0052_booking_window_30_days`.
- All four finance objects exist: salon_expenses, salon_cash_adjustments, salon_day_closes and salon_expense_rules. RLS is enabled on all four.
- The three finance money tables each have an enabled statement-level BEFORE TRUNCATE guard using guard_finance_append_only.
- The catalogue reports zero direct finance-table grants to anon, authenticated or PUBLIC.
- The current create_booking and three-argument get_available_slots definitions contain the exact `v_today + 60` expression, matching the current main SQL's 60-day window despite the historical 30_days filename.
- A subsequent normalized function-body comparison matched all seven selected main definitions exactly: guard_finance_append_only, guard_expense_reversal, guard_cash_adjustment_reversal, guard_day_close_revision, guard_expense_rule, create_booking and the three-argument get_available_slots. MD5 was used as a convenient equality fingerprint, not as a security signature.
- booking_customer_changes, booking_financial_outcomes, booking_finance_commands, booking_policy_refund_jobs, booking_finance_reconciliations, support_erasure_events and salon_plan_prices exist.

These targeted catalogue observations establish present objects and selected guards; they do not claim that every historical SQL byte, live function, client behavior or worker path is equivalent. No database mutation was performed, and no migration is proposed by these observations.

## Current serving image

- 100% normal traffic remains on `salon-api-production-subpct-20261028`.
- Ready=True.
- Immutable platform image: `asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:76ce6bec396732f0ac82957248547eead50f662bbc35fce3a42cbdfdb728a9d7`.
- Cached image inspection reports no Config.Labels; a Git source SHA must not be invented for this hybrid image.
- api.salones.in `/health` and `/health/ready` return 200; `/version` returns 404. Legacy apiv1.mudassirmhd.in `/health` returns 200.
- Newest registry release inspected remains the 28 October subscription-percentage image. No latest-main image has been published by this preflight.

## Outstanding release gates

1. CI and image source verification completed after browser/device authentication as Shifannv (172572480). PR #33 was merged by that owner and main still matches the selected SHA. Backend CI run `41277297686`, attempt 1, passed both Lint and tests / Build and smoke test image. Artifact ID `13071593318` was downloaded by its exact run/name. Its API digest is `sha256:8776c5e82e495bb60154946bb7e5cfe82d274bdfbd4366125be5d44e9358ae67`. Local provenance/archive/config/layer/load verification passed. Archive SHA-256 is `b2b9a169264b0fadf3855244174c3f4571876c577b12ea6a2349da5a231f3a5d`; tested config digest is `sha256:76a44c94c44b1315d9db1f5478516cdc75e9c7a73c0538a2538adbddca65cfc8`. No rebuild was performed. Automatic run `41277297736` is at attempt 2 but retains an attempt-1 image, so it was not used as the image source.
2. Complete the separately reviewed first-release compatibility/provenance procedure. Existing automatic baseline checks reject an image without source labels. The bootstrap source comparison reports 25 migration-source differences against the historical image; this alone does not mean those migrations are unapplied. Fresh catalogue evidence must be reviewed with exact source hashes rather than blindly replaying SQL or bypassing the guard.
3. Offline inspection of the exact CI image verified its file-backed SHA. It exposes 148 paths versus production's 121, with no removed paths or operations. Existing strict contract verification fails with `Existing schema field removed`. The current image removes category/description from salon schemas, qr_token from public salon schemas and description from service/walk-in schemas. Other existing property shapes also change. Full details are in the local generated `backend/.artifacts/production-release-20261101/contract-review.json`; candidate contract hash (sorted JSON) is `10724547e3fa031d2332bf7621338417facabb5be120247521f2a9616f528a0b`. These changes need explicit review for the first release; no automatic compatibility bypass was added.
4. Prepare and verify a zero-traffic candidate only through the reviewed procedure; obtain the owner's separate traffic-promotion approval before assigning normal production traffic.

The earlier single-switch corrections remain uncommitted. Preparation did not merge or push Git source, alter any deployment switch, mutate WIF/IAM or runtime secrets, run migrations, create a revision, or change traffic. The subsequently approved zero-traffic revision and its test results are recorded below. The exact tested image was published under the unique registry tag `6fefff404b148af4798105228418d96f03ad8e4c-ci41277297686-a1`. Registry readback, immutable pull, config, layers and source labels match the tested CI image. Verified deployment image:

`asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:30846cbc3328574281f7c5bf3b9cf714386494ffb9138f994465786d1c58475a`

## One-time supervised candidate — approved and verified

The current automated baseline/source and strict compatibility guards remain unchanged. They reject this legacy-to-current transition. The owner explicitly approved accepting the reviewed catalogue/provenance evidence and the listed legacy contract changes for this one-time initial zero-traffic candidate procedure in chat. This is not approval for subsequent guard bypasses or for normal traffic promotion.

After approval, recheck current main, CI, serving revision and unchanged service resource version, then execute only this image update:

```text
gcloud run deploy salon-api-production --project=saloon-505509 --region=asia-south1 --image=asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:30846cbc3328574281f7c5bf3b9cf714386494ffb9138f994465786d1c58475a --revision-suffix=ci-6fefff4-20261101 --tag=main-6fefff4-review --no-traffic --quiet
```

No environment, secret-reference, service-account, scaling, ingress or load-balancer setting is supplied or changed. Compare the complete service/revision runtime settings privately before/after; preserve all existing tags and normal traffic. Verify candidate Ready and resolved digest; GET /health/ready, /version (exact SHA), /health, /health/db, /health/redis, /docs and /openapi.json. Compare the candidate contract to the reviewed exact image and report the legacy-field changes explicitly. Never call production mutation endpoints.

Stop on any failure and keep 100% normal traffic on `salon-api-production-subpct-20261028`. The API image startup performs database SELECT 1 and cache initialization, with no migrations or worker startup. After a successful candidate report, request the separate explicit traffic approval before promotion. The retained traffic rollback command is:

```text
gcloud run services update-traffic salon-api-production --project=saloon-505509 --region=asia-south1 --to-revisions=salon-api-production-subpct-20261028=100
```

## Candidate result

`PASS_AWAITING_EXPLICIT_TRAFFIC_APPROVAL`, completed `2026-11-01T07:07:36.801448Z`.

- Revision: `salon-api-production-ci-6fefff4-20261101`.
- Candidate URL: `https://main-6fefff4-review---salon-api-production-jmqpp743pa-el.a.run.app`.
- Ready=True; resolved immutable digest equals the verified registry image above.
- All seven GET checks returned 200: /health/ready, /version, /health, /health/db, /health/redis, /docs and /openapi.json.
- /version reports `6fefff404b148af4798105228418d96f03ad8e4c`; /health/ready reports status ok.
- Candidate OpenAPI exactly matches reviewed CI contract hash `10724547e3fa031d2332bf7621338417facabb5be120247521f2a9616f528a0b`, with 148 paths.
- Runtime settings compared privately before/after and remained unchanged. Existing normal traffic stayed 100% on salon-api-production-subpct-20261028.
- No migration, Alembic stamp, Git source commit/push, deployment flag, IAM/WIF, runtime-secret, DNS or load-balancer change occurred.
- Workers were not deployed or executed; worker and authenticated business-flow coverage is not established by these seven read-only checks.
- Local machine-readable receipt: `backend/.artifacts/production-release-20261101/candidate-result.json`.

## Production promotion result

The owner supplied the separate exact approval `PROMOTE CLOUD RUN CANDIDATE`. A
fresh preflight confirmed that remote `main`, merged PR #33, Backend CI run
`41277297686`, the candidate revision, immutable digest, candidate contract and
the previous 100% traffic target still matched the reviewed evidence.

`PASS_PRODUCTION_PROMOTED`, completed `2026-11-01T07:14:50.812521Z`
(`12:44:50 IST`).

- 100% normal traffic now serves `salon-api-production-ci-6fefff4-20261101`.
- The serving commit is `6fefff404b148af4798105228418d96f03ad8e4c`.
- The serving image is the immutable digest documented above; it was not rebuilt.
- Both `api.salones.in` and the retained legacy hostname passed `/health/ready`,
  `/version`, `/health`, `/health/db` and `/health/redis` with HTTP 200. Both
  `/version` responses reported the exact reviewed commit.
- Runtime configuration remained unchanged during the etag-protected traffic-only
  update. Final service resource version: `AAZfMciECb8`.
- `salon-api-production-subpct-20261028` remains Ready and retained as the rollback
  revision. No revision was deleted.
- No database migration, Alembic stamp, application mutation request, image rebuild,
  runtime secret, IAM/WIF, DNS, certificate, load-balancer, scaling, deployment-flag,
  Git commit, push or merge was performed by this promotion.
- Local machine-readable receipt:
  `backend/.artifacts/production-release-20261101/promotion-result.json`.

Rollback command, if a later operational issue requires it:

```text
gcloud run services update-traffic salon-api-production --project=saloon-505509 --region=asia-south1 --to-revisions=salon-api-production-subpct-20261028=100
```
