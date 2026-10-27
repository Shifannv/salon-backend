# Shared production API domain migration — 27 October 2026

The user approved `https://api.salones.in` for the website, customer app and owner
app, including DNS, GCP, local environment settings and website release. Keep
`https://apiv1.mudassirmhd.in` working for installed legacy builds. No old DNS,
certificate, image or service deletion is authorized by this migration.

## Architecture and cost boundary

`api.salones.in` → DNS-only A `34.117.51.175` → existing global HTTPS load balancer
→ `salon-production-api-backend` → Mumbai serverless NEG
`salon-production-api-neg` → Cloud Run `salon-api-production`.

The new Cloudflare DNS record uses its existing Free zone. No paid Cloudflare
feature, extra forwarding rule, load balancer, IP or Cloud Run service was added.
The pre-existing Google load balancer remains billable; this is not a wholly free
hosting architecture. Staging remains IAM protected and is not a production base.

## Resources and rollback

- New certificate: `salon-production-salones-api-cert`, domain `api.salones.in`.
- Existing certificate retained: `salon-production-api-cert` for the old hostname.
- Both certificates attached to `salon-production-api-proxy`.
- DNS A record TTL 300, proxy disabled; record ID `f8cd0533d37a333cda1445e6e9e4b41d`.
- Previous production revision: `salon-api-production-qr-www-20261026`.
- Candidate revision: `salon-api-production-api-domain-20261027`, review tag
  `api-domain-review`; created at zero production traffic.
- Image unchanged:
  `asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:dfb24746323e9d4cfa2a4fd9cff7d0fee1d7a02ee5d0893a8a436f9f3cfbcef1`.
- In-memory comparison confirmed the candidate container spec is identical except
  `PUBLIC_API_BASE_URL=https://api.salones.in`. Secret references are unchanged.
- Existing website deployment/rollback: `dpl_F5K9b2C3CfVXd13Jv6XCtUVU3Jzu`,
  project `salon-customer-web` / `prj_MATPZ41voAmtbEqbIVAyg0w736AN`, team
  `team_kjdQLrgsqWlgYTtkRWfqqaLS`. Rebuild that exact uploaded source rather than
  publishing unrelated working-tree changes.

Rollback the API by directing 100% traffic to the previous revision. Retain the
new DNS/certificate unless a verified issue requires changing them. A website
rollback to the saved deployment also restores its captured previous environment.

## Configuration

Local backend `.env`, both backend templates, both mobile app `.env` files,
their public templates and production EAS profiles, and the website app
`.env.local`/template now use the canonical origin. Only API URL fields were
read or edited; unrelated values and credentials were preserved. Duplicate owner
`EXPO_PUBLIC_API_URL` was removed. Unused staging API aliases in these local files
were aligned to production. Intentional synthetic/staging test configuration is
not redirected to production.

Vercel production `API_BASE_URL` and existing `NEXT_PUBLIC_API_URL` were updated
using the authenticated CLI after the connector returned 404/403 for this project.
No secret values were read. Existing nonproduction target scopes were preserved.
Backend workflow environment/health URLs and current operational guidance were
updated. Historical deployment receipts keep the hostname actually tested then.

Mobile release guard, its tests and QA scripts now use `api.salones.in`. The guard
rejects the old hostname for future production builds. Existing installed apps
retain their old embedded origin until replaced; editing `.env` cannot rewrite
an already installed APK. Store submission and iOS signing remain separate gates.

Customer local Android build succeeded in 16m10s. Packaging scan found the new
origin, no old/staging API host, no private packaged files and no matches for 12
checked private local configuration values. APK SHA256:
`25fbca65053075919e419af9e2188cb414553b75309692da7b0809b40b1eb83e`.
The owner's first 3m09s build reused an outdated JS bundle: the artifact check
caught the missing new hostname. Reran only `app:createBundleReleaseJsAndAssets
--rerun` plus `app:assembleRelease`; build succeeded in 2m12s. Always inspect bundle
markers after environment-only changes; a successful incremental Gradle build
alone does not prove that new environment values were embedded.

Both final APKs pass new-origin-present, old-origin-absent, staging-origin-absent
and private-file-absent checks. Final owner APK SHA256:
`84c7dcbe16cac977c801fa7a912aea07039fde0edad1e10621365de4400b8951`.

Both use the existing Android Debug verification certificate (SHA256
`fac61745dc0903786fb9ede62a962b399f7348f0bb6f899b8332667591033b9c`), not store
distribution signing. No device installation, OTA publication or store submission
was performed. APK files live in each app's
`android/app/build/outputs/apk/release/app-release.apk`.

## Verification so far

- Backend Ruff passed; pytest 1438 passed, 176 opt-in skips, one dependency warning.
- Website, customer and owner TypeScript checks passed.
- Customer full suite: 400 tests / 69 suites passed. Owner API-client suite:
  17 passed. Mobile lint: zero errors, 50 customer and 3 owner existing warnings.
- Customer release checks: 8 passed, including rejecting the old production origin.
- Candidate HTTP checks: 7/7 passed (health, DB, Redis, Swagger, OpenAPI, discovery,
  auth rejection). OpenAPI has 119 paths and SHA256
  `5cbaddc10704e9e5468632fdd20bb8e9a7b7dfb208176e5d5272f70c458a395c`.
- Website suite: 420 passed, one discovery rendering timeout; focused file rerun
  9/9 passed. No test expectations or application behavior changed for this timeout.
- Website full lint includes 10 existing require-import errors in ignored
  `test-results/*.cjs` scratch files. Application lint excluding that directory
  passes with zero errors / 12 warnings; no unrelated scratch files were edited.
- Unauthenticated candidate upload-grant POST returned401. Direct-browser CORS
  preflight for `www.salones.in` returns400 under the inherited policy. The website
  uses its BFF server proxy, which does not depend on cross-origin browser access.
  CORS policy was not broadened by the hostname migration.
- Old hostname health remained HTTP200 while new HTTPS was provisioning.
- Authenticated image upload, booking mutations and account erasure have not been
  exercised by these read-only checks.

## Cutover status

Completed on 27 October 2026. Certificate and domain became ACTIVE about 33.5 minutes
after creation; trusted HTTPS passed immediately from this client. The new host
passed all 7 read-only checks before promotion. Cloud Run now routes 100% to
`salon-api-production-api-domain-20261027`. Effective `PUBLIC_API_BASE_URL` is
`https://api.salones.in`; image, service max 1, default min 0, CPU 1 and 512Mi memory
are preserved. Anonymous staging health still returns 403.

Exact-source website rebuild `dpl_HGNpHYpouqTNyKTADFJY5HsmTQkH` is READY at
`https://salon-customer-hjbpkhry6-shifannvs-projects.vercel.app`. Custom-domain
auto-assignment was disabled during testing. Authenticated CLI access to staged
BFF `/api/public/health` changed 503→200 after certificate issuance. The tested
deployment was then promoted; Vercel `inspect www.salones.in` confirms that same
deployment is serving production. Public Home/privacy/terms/account-deletion,
BFF health and BFF salon discovery all return 200. No deployment-protection setting
was disabled. Existing website source was rebuilt without uploading local changes.

After promotion, both `https://api.salones.in` and the retained old hostname pass
all 7 API checks; both OpenAPI contracts have 119 paths and the hash recorded above.
No old hostname redirect or removal occurred. Mobile installation/real-device
flows and store distribution are not established by APK marker checks.
