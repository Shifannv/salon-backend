# G05: Payout schedules

**Design only; Approval required for implementation.** Review group G05.
Schema dependencies: G01, G04. No Alembic revision ID or parent is assigned.
The filename is a historical locator, not execution order. Inherits the
[shared rules](README.md), [field treatments](ERASURE_CLASSIFICATION.md) and
[G09 concurrency contract](09-slot-hold-concurrency-support.md).

## Purpose and compatibility

C16 permits owner choice only from verified account capabilities and admin
restrictions. Scheduling selects an execution opportunity **after** common G04
eligibility; it never creates funds, shortens holds or confirms a transfer.
No schedule defaults, cron jobs or automatic payout execution are installed.

## Tables and columns

| New table | Proposed columns in addition to shared ID/timestamps |
| --- | --- |
| `payout_capability_versions` | `provider text`, `provider_account_scope uuid`, `provider_environment text`, `provenance text`, `version integer`, `product_code text`, `schedule_code text`, `frequency text` (daily/weekly/monthly/provider_defined), `timezone text`, `cutoff_local time?`, `weekday smallint?`, `month_day smallint?`, `weekend_mode text?`, `holiday_calendar_version text?`, `valid_from timestamptz`, `valid_until timestamptz?`, `evidence_digest bytea`, `verified_at timestamptz`, `verified_by uuid?`, `is_active boolean` |
| `salon_payout_schedule_versions` | `salon_id uuid` -> salons, `capability_id uuid` -> capabilities, `destination_version_id uuid` -> payout_destination_versions, `version integer`, `effective_from timestamptz`, `effective_to timestamptz?`, `selected_by uuid?`, `source text` (owner/admin), `is_active boolean`; capability defines permitted timing, no unchecked JSON override |
| `salon_payout_restrictions` | `salon_id uuid` -> salons, `capability_id uuid?` -> capabilities, `version integer`, `restriction_code text` (paused/allowed_capability_only), `effective_from timestamptz`, `effective_to timestamptz?`, `reason_code text`, `actor_id uuid?`, `is_active boolean` |
| `salon_payout_schedule_events` | `salon_id uuid` -> salons, `schedule_id uuid?` -> schedules, `restriction_id uuid?` -> restrictions, `event_key text`, `event_type text`, `actor_id uuid?`, `reason_code text`, `effective_at timestamptz`, `correlation_id uuid`; `command_audit_event_id uuid` -> G01 sealed audit event for new-mode commands |

Extend `salon_payouts` with nullable indexed `schedule_version_id uuid` FK to
schedule versions. Manual payouts can remain unscheduled; automatic ones require
a valid selected schedule, capability and approval. Prior payout rows stay NULL.

## Indexes and constraints

- Unique capability `(provider, provider_account_scope, provider_environment, schedule_code, version)`,
  schedule `(salon_id, version)`, restriction `(salon_id, version)` and event key.
  Use temporal exclusion for overlapping active selections per salon, and
  conflicting active restriction versions per salon. No silent precedence rule.
- Index all FKs, capabilities `(provider_account_scope, is_active, valid_from)`,
  schedules `(salon_id, effective_from)`, active restrictions by salon and events
  `(salon_id, effective_at)`. Existing payout due index in G04 is reused.
- End > start, weekday 1-7/month-day 1-31 when relevant, approved codes and
  positive versions. Validated IANA timezone/calendar source; month-end clamping,
  DST/cutoff and missing calendar behavior require verified capability semantics,
  not a CHECK on a string. Unknown weekend/holiday support forbids a promise.
- `allowed_capability_only` requires a non-NULL capability FK; `paused` is an
  explicit salon-wide restriction and carries no capability selector. Frequency
  shapes are exclusive: daily has neither weekday nor month_day; weekly requires
  weekday only; monthly requires month_day only. `provider_defined` requires an
  approved immutable product/calendar specification, not inferred parameters.
  **Approval required** P03/Q14 for the actual supported choices/calendar rules.
- Capability, schedule and restriction financial/timing parameters are immutable
  after publication. Retirement, validity-end closure and revocation are narrow
  audited projection changes; changed parameters create a new version. Historical
  payout generations preserve the selected version. Exclusion/selection predicates
  must distinguish withdrawn drafts from published historical intervals so
  setting `is_active=false` cannot manufacture overlapping effective history.
  Immutable environment/provenance fields require attested provider-observed,
  scope-matched capabilities for real selection.
  Mock/sandbox capability evidence never authorizes a live schedule.
- Validate provider/account scope, product and destination salon match. Selection
  must be contained in capability validity and all active admin restrictions.
  Lock salon/schedule selection while changing it; events and G01 audit append
  in the same command. Closing an effective interval does not rewrite timing
  facts already snapshotted by a payout.
- A later executor locks due payout/entitlements, rechecks current eligibility,
  revoked capability, schedule, restriction and destination. Stale schedules block
  execution. Selection/restriction edits cannot strand an in-flight transfer or
  create a second payout; reconcile processing attempts against their snapshots.
  Follow the shared lock-order and minimum-rights contracts. Schedule selection
  grants no accounting-finalization, payout-approval or authority-management power.

## RLS/security impact

All four tables are backend-only with RLS/client revocations. Owners can request
their own eligible selection through use cases; no direct database schedule write.
Only approved finance actors may restrict/override and each action needs G01
audit/MFA. No admin schedule override bypasses completion/dispute/hold/reservation
checks. No outbound provider integration or scheduler is created here.

## Account-deletion behavior

Soft-retire current schedule and restrictions on owner erasure; retain
nonpersonal version/timing references needed by payout events on inert salon
shells. Nullable actor/selector/verifier FKs are cleared. No provider-account FK
blocks deletion of live onboarding mappings. Treat capability evidence digests
and any external identifiers as restricted under Q16; do not label them anonymous.
Add explicit erasure/classification coverage, not a new cascade/delete list.

## Downgrade safety and rollback plan

Empty/unused capabilities, schedules, restrictions and event tables plus all-NULL
payout schedule links may be dropped in reverse dependency order after writers
stop. Refuse downgrade after a schedule governed a payout or recorded decision.
Data-bearing rollback disables automated initiation, preserves pending/unknown
transfer reconciliation and history, and forward-repairs schedule versions.
Do not silently fall back to daily, immediate or manual execution.

## Unresolved approval and readiness

**Prepared for design review; not execution-ready.** Q05/Q13-Q16, P02/P03/P06,
L03/L05: provider-supported frequencies/timezones/cutoffs, weekend/calendar rules,
owner/admin powers, automation approval model, funding, retention and hold policy.
Daily/weekly/monthly are candidate codes, not confirmed Cashfree capabilities.

Later verification: unsupported selection, capability expiry/revocation, conflicting
selections, timezone/month-end/cutoff cases, admin pause during execution, equal
manual/automatic eligibility, no hold shortening, erasure and safe rollback.
No scheduler, provider call or SQL test runs in this phase.
