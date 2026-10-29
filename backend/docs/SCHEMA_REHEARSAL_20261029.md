# Local schema reconciliation rehearsal ? 29 October 2026

Review evidence only. No production migration, deployment or traffic change is authorized by this report.

## Source and recovery point

- Reviewed Git base: `848ac73f7e28fc312dcb7b584ffe0a4eb5791919`.
- Proposed 0051 includes three additional statement-level TRUNCATE triggers from this branch.
- Encrypted logical backup captured 2026-10-29 10:03:07 UTC (15:33:07 IST).
- Archive and recovery metadata were decrypted and SHA-256 verified in memory.
- A local restore preserved all 84 exported table row counts and canonical row hashes, financial totals, owners and effective ACLs.
- Recovery files stay outside the repository in the operator's SalonRecovery directory. No plaintext archive was saved.
- This is a local logical recovery copy, not hosted PITR or an off-device backup. Storage object contents, provider configuration and credentials are excluded.

## Rehearsed SQL order

Each file ran through psql with `--single-transaction -v ON_ERROR_STOP=1` on network-isolated local clones. No Alembic upgrade or stamp ran. 0049/0050 were skipped because their effects already exist. Hashes are committed/proposed LF bytes.

| SQL file | Statements | SHA-256 |
| --- | ---: | --- |
| `0041_salon_photo_limits.sql` | 11 | `bb79194ef5dbd5ddb222f359a2936fd8007e136f0d5579b257a74106273280ae` |
| `0042_remove_business_category.sql` | 3 | `9993eafdef3b2c673aa2490a4b4bbcd4a6d9c4f05b947f8293c19b157f8c3aab` |
| `0043_no_show_attendance_guards.sql` | 6 | `e9393e1ada475f9f1af861cdf5eda5a3336cebd43d289158ac8bf007d12d6eeb` |
| `0044_versioned_checkout_policy.sql` | 4 | `8c9230053eab4deea1d20459264a0dd3e04da1c65c329e19589c3fa4326734b0` |
| `0045_customer_booking_changes.sql` | 25 | `78cf50827ccff2393fccb41b51a9c20647502e6bda7545f2e4dfdbe2e191e65b` |
| `0046_u08_financial_outcomes.sql` | 30 | `91412933e0ec6d7185e126ab27999adfc583fc211af706bf2f5b75e5021752c8` |
| `0047_booking_audit_erasure.sql` | 22 | `90333a86c9806b8a2128ee041927a04b3c8520fefc5354c39af4ee7f74cb4bd9` |
| `0048_support_billing_erasure.sql` | 21 | `56ecb032b532e62892c0280c07f6093a080c75e30e3db7066886735e407ac0fc` |
| `0051_owner_finance_cashbook.sql` | 43 | `eca4e0d5a942c56ac9e9b2c79ecd8a2dd355bc62f3a3174c1991d964a782c01f` |

## Results and retention impact

- Finance-only clone: all 84 original table hashes unchanged; original row counts and financial totals preserved.
- Full ordered clone: original row counts and financial totals preserved; only salons, services, salon_images, bookings and booking_services fingerprints changed as expected.
- The untouched restore baseline still matches all source fingerprints.
- 0041 soft-retired five of eleven active photos. It also removes salons.description and services.description; the snapshot contained no nonempty descriptions.
- 0042 removes salons.category; one salon had a category value. The encrypted backup retains the snapshot value. These retention changes require explicit review before production execution.
- Public-role access was denied, finance updates/deletes refused, negative amounts rejected, and synthetic probes rolled back.
- All three owner-role money-table TRUNCATE attempts now raise P0001. service_role retains its existing permission denial (42501).
- Expense-rule RLS, public-role denial and service_role TRUNCATE denial were verified.
- Local Alembic history remains empty; it was not stamped.

## Append-only correction

The original 5903d47 finance SQL allowed service_role TRUNCATE. Main later revoked that privilege, but the table owner still bypassed row-level guards. Three failing owner regression cases reproduced this on latest main. BEFORE TRUNCATE FOR EACH STATEMENT triggers now reuse guard_finance_append_only and raise before NEW/OLD are accessed. Existing erasure updates and client restrictions are preserved. An owner can deliberately disable triggers; this protects normal SQL operations, not a hostile database administrator.

0051 remains a prepared migration: the four finance tables were absent in the managed target at the read-only preflight. Only disposable test/restored databases received it. If any shared environment has adopted 0051, stop and prepare a new reviewed revision instead of replaying the edited file.

## Release gate

Local success is not production schema adoption. Review and merge the correction, reconfirm latest main and exact hashes, take/verify a fresh recovery copy immediately before any separately approved production execution, and obtain approval for the specific shared target and retention effects. Do not replay 0049/0050, upgrade/stamp Alembic, activate workers or bypass the candidate migration guard. The release workflow still refuses migration differences; a separately reviewed compatibility attestation/gate change is needed after schema adoption. Only then test a zero-traffic candidate; production promotion requires the separate explicit confirmation.

## Offline OpenAPI release check

The exact local test image exposes 147 paths versus 121 in currently served production. No existing paths or operations disappear. This is an offline source-image comparison plus production GET, not a deployed candidate smoke test. The existing strict contract gate still requires separate review:

- The previously generated avatar multipart body schema is absent.
- Existing property shapes/required fields also differ, including removals shown below. No compatibility bypass was added.

| Schema | Removed fields | Changed fields | New required fields |
| --- | --- | --- | --- |
| AdminSalonOnboardingResponse | category, description | images | ? |
| AdminSalonResponse | category, description | ? | ? |
| BlockedSlotCreateRequest | ? | staff_id | ? |
| BookingCreateRequest | ? | customer_name, customer_phone, notes, salon_id, service_ids, staff_id | ? |
| ClosureApplyRequest | ? | affected_booking_ids, staff_id | ? |
| ClosurePreviewRequest | ? | staff_id | ? |
| HolidayCreateRequest | ? | title | ? |
| OwnerSalonCompleteProfileRequest | category, description | ? | ? |
| OwnerSalonResponse | category, description | images | ? |
| OwnerSalonUpdateRequest | category, description | ? | ? |
| SalonDetailResponse | category, description, qr_token | accepts_bookings, images, online_payment_available, online_payment_unavailable_reason, payment_options | ? |
| SalonSummaryResponse | category, description, qr_token | accepts_bookings, online_payment_available, online_payment_unavailable_reason, payment_options | ? |
| ServiceCreateRequest | description | duration_minutes | ? |
| ServiceResponse | description | ? | ? |
| ServiceUpdateRequest | description | duration_minutes | ? |
| StaffServiceAssignRequest | ? | duration_minutes | ? |
| SupportTicketResponse | ? | customer_id | ? |
| WalkInSalonResponse | description | ? | ? |
| WalkInServiceSummary | description | ? | ? |

These differences belong to earlier merged backend changes. Review intended client compatibility and necessary adapters before an approved zero-traffic release; do not silently weaken the contract comparison.
