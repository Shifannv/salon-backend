# Proposed treatment of the 43 unresolved fields

**Design review only. Every row is Approval required.** This is a proposed
classification of the exact 43 fields in Appendix C of the
[Mumbai reconciliation report](../MUMBAI_SCHEMA_HISTORY_RECONCILIATION_2026-10-18.md).
It changes no data, code, test classification, retention policy or immutable
guard. It is not permission to retain indefinitely, decrypt, backfill or delete.
The [specification](../../verification/payment-subscription-booking-spec.md)
Q15/Q16/L05 approval gates remain binding; other dependent questions are listed
per field.

## Category meanings

| Category | Meaning in this design |
| --- | --- |
| delete | Remove the specified personal/sensitive field payload at the approved end of operational need or verified erasure boundary; no new financial-row hard-delete exception |
| anonymize | Remove identifying content and reduce to an approved controlled nonpersonal fact/template; detaching a UUID, hashing or encryption alone is not anonymization |
| encrypt | Keep only necessary sensitive material under authenticated managed encryption or adequate tokenization, scoped access, key versions and a separately approved finite retention/scrub plan |
| retain | Preserve validated nonpersonal code/financial-contract fact under an approved schedule and access policy; not arbitrary text or an entitlement to keep the enclosing row |
| digest only | Keep only a keyed, domain-separated, versioned minimal dedup/throttle digest; no reversible input or hidden raw copy; still potentially personal/pseudonymous |
| provider-required retention | Conditional evidence class, not proof that a provider requires retention: establish actual provider purpose plus lawful retention/erasure basis, minimal encrypted/restricted references, duration, handoff and destruction first |

Primary classes are exclusive for counting; safeguards can overlap. For example,
provider-required retention uses encryption if approved, and an encrypted
reference can also need an approved keyed digest. A missing provider requirement
leaves the exception unapproved, not an automatic switch to deletion while an
obligation is unresolved. No P01-P06 claim is established here.

| Primary treatment | Fields |
| --- | --- |
| digest only | 2 |
| retain | 26 |
| delete | 3 |
| encrypt | 3 |
| anonymize | 6 |
| provider-required retention | 3 |

## Exact field-by-field classification

Each status is **Approval required**. Recommendations do not supply Q/P/L answers.

| # | Exact field | Proposed primary treatment | Bounded treatment | Approval gate |
| --- | --- | --- | --- | --- |
| 1 | `api_rate_limits.bucket_hash` | digest only | Keep only a versioned keyed bucket digest for the approved throttle window; no reversible contact/IP input. Existing hash algorithm is not presumed safe. | **Approval required** — Q15/Q16/L05: key, input minimization, expiry and erasure scope. |
| 2 | `booking_audit_events.event_type` | retain | Allowlisted event code only; preserve event meaning after actor detachment. | **Approval required** — Q16/L05: finite retention/access and handling invalid legacy values. |
| 3 | `booking_audit_events.new_state` | retain | Controlled state code; no copied reason, name or payload. | **Approval required** — Q16/L05: retention and legacy value validation. |
| 4 | `booking_audit_events.old_state` | retain | Controlled prior state code; preserve transition history. | **Approval required** — Q16/L05: retention and legacy value validation. |
| 5 | `booking_payments.collection_method` | retain | Controlled receipt-method category, separate from account/UPI details. | **Approval required** — Q16/L02/L05: financial classification and duration. |
| 6 | `booking_payments.commission_base` | retain | Preserve approved historical formula-basis code; do not reprice receipts. | **Approval required** — Q04/Q16/L02/L05: code validation, recognition and retention. |
| 7 | `booking_payments.commission_policy_version` | retain | Preserve historical policy version, containing no personal narrative. | **Approval required** — Q04/Q16/L02/L05: policy registry and retention. |
| 8 | `booking_payments.provider_session_id` | delete | Remove checkout-session material when no longer operationally needed and on applicable erasure; never put it into immutable audit. If it is a credential, restrict it during its operational life. | **Approval required** — Q15/Q16/P05/L05: actual field sensitivity, termination point and safe reconciliation handoff before removal. |
| 9 | `bookings.checkout_policy_version` | retain | Keep historical checkout policy identity; do not rewrite old surcharge orders. | **Approval required** — Q08/Q16/L02/L05: legacy treatment and retention. |
| 10 | `email_events.body` | delete | Clear personal message content at the approved erasure boundary; retain only separate nonpersonal event/status facts. | **Approval required** — Q16/L05: affected-recipient/third-party scope, pending-delivery cancellation and any hold exception. |
| 11 | `email_events.event_key` | digest only | Retain only keyed deduplication identity without embedded user/booking text; scope and version it. | **Approval required** — Q15/Q16/L05: atomic replay migration, key rotation and expiry; do not break existing unique-key retries. |
| 12 | `email_events.event_type` | retain | Allowlisted delivery-purpose code, not free text. | **Approval required** — Q16/L05: code allowlist and retention. |
| 13 | `email_events.last_error_code` | retain | Allowlisted sanitized error class only; raw provider errors are not retained as codes. | **Approval required** — Q16/L05: legacy sanitization, pending-work support and retention. |
| 14 | `email_events.provider_message_id` | encrypt | Restrict minimal operational provider correlation as authenticated ciphertext; scrub or destroy its key at approved end of need. | **Approval required** — Q15/Q16/L05: email-provider lookup need, authorized decryptor, expiry and backup handling; no provider requirement assumed. |
| 15 | `email_events.recipient` | delete | Remove address/contact on the applicable verified erasure; preserve no recipient in immutable audit, dedup keys or retry payloads. | **Approval required** — Q16/L05: unsent delivery handling, third-party associations and hold exceptions. |
| 16 | `email_events.status` | retain | Allowlisted delivery state only, with identity detached where allowed. | **Approval required** — Q16/L05: retention and residual linkability. |
| 17 | `email_events.subject` | anonymize | Replace erased-person content with a controlled nonpersonal template label; no original subject copied elsewhere. | **Approval required** — Q16/L05: exact redaction scope/template, unresolved delivery/holds and evidence that output is nonidentifying. |
| 18 | `payment_anomalies.detail` | anonymize | Remove arbitrary personal/provider payload; preserve only approved anomaly reason/fact references separately from restricted evidence. | **Approval required** — Q15/Q16/L02/L05: safe legacy decomposition and unresolved-anomaly evidence needs. |
| 19 | `payment_anomalies.kind` | retain | Allowlisted anomaly category; no arbitrary explanation. | **Approval required** — Q16/L02/L05: classification and retention. |
| 20 | `payment_anomalies.provider` | retain | Provider product/code only, excluding merchant/account identity. | **Approval required** — Q16/L02/L05: code validation and duration. |
| 21 | `payment_anomalies.provider_ref` | encrypt | Restricted encrypted minimum reconciliation locator; separately keyed digest if duplicate detection needs it. | **Approval required** — Q15/Q16/P05/L05: reference semantics, evidence need, key custody, erasure and retention. |
| 22 | `payment_provider_account_audit.action` | retain | Controlled onboarding action code; no before/after secret payload. | **Approval required** — Q16/L05: allowlist and duration. |
| 23 | `payment_provider_account_audit.detail` | anonymize | Replace personal/vendor payload with controlled result/reason facts; any justified evidence belongs in separately restricted storage. | **Approval required** — Q15/Q16/P04/L05: field-level extraction, lawful evidence retention and deletion scope. |
| 24 | `payment_provider_account_audit.new_status` | retain | Controlled onboarding state, not provider response text. | **Approval required** — Q16/P04/L05: state mapping and retention. |
| 25 | `payment_provider_account_audit.previous_status` | retain | Controlled prior onboarding state. | **Approval required** — Q16/P04/L05: state mapping and retention. |
| 26 | `payment_provider_account_audit.provider` | retain | Provider code only, not a vendor/account identifier. | **Approval required** — Q16/L05: validation and retention. |
| 27 | `payment_provider_account_audit.vendor_ref` | encrypt | Restrict vendor reconciliation reference after operational mapping deletion; never expose it as ordinary audit text. | **Approval required** — Q15/Q16/P04/P05/L05: need, duration, operator handoff and eventual key/reference destruction. |
| 28 | `payment_refunds.kind` | retain | Preserve controlled historical refund category and its meaning; no new cancellation-policy inference. | **Approval required** — Q01/Q02/Q16/L01/L02/L05: category compatibility and retention. |
| 29 | `salon_access.trial_ended_reason` | retain | Allowlisted reason only, not a personal explanation. Existing salon_access deletion still removes the whole operational row on owner erasure. | **Approval required** — Q06/Q16/L05: any distinct nonpersonal lifecycle-history retention; no extension of current row lifetime. |
| 30 | `subscription_billing_records.benefits` | anonymize | Preserve approved nonpersonal purchased-benefit facts while removing identifiers/free-form personal additions; never change the contractual economic entitlement. | **Approval required** — Q09/Q16/L02/L05: immutable-snapshot-compatible field schema/redaction and restricted evidence if exact payload is lawfully needed. |
| 31 | `subscription_billing_records.billing_interval` | retain | Preserve the purchased interval, not a newly inferred renewal policy. | **Approval required** — Q09/Q16/L02/L05: duration and historical meaning. |
| 32 | `subscription_billing_records.currency` | retain | Preserve the financial currency code. | **Approval required** — Q16/L02/L05: retention. |
| 33 | `subscription_billing_records.failure_code` | retain | Sanitized allowlisted error class only; no raw provider body. | **Approval required** — Q16/L05: code sanitization and unresolved purchase evidence. |
| 34 | `subscription_billing_records.plan_code` | retain | Preserve purchased plan identity, without reseeding/admin-price reset. | **Approval required** — Q09/Q16/L02/L05: validation and retention. |
| 35 | `subscription_billing_records.provider` | retain | Provider code only; no account scope or credentials embedded. | **Approval required** — Q16/L02/L05: code validation and retention. |
| 36 | `subscription_billing_records.provider_order_ref` | provider-required retention | Only if a named provider/financial evidence obligation is established: keep minimum exact locator encrypted/restricted, plus approved dedup digest; otherwise no provider exemption is established. | **Approval required** — Q15/Q16/P05/L02/L05: necessity, lawful basis, duration/hold, access and eventual destruction. |
| 37 | `subscription_billing_records.provider_payment_ref` | provider-required retention | Only verified necessary capture/refund evidence, encrypted/restricted with scope-matched dedup; not ordinary owner-visible history. | **Approval required** — Q15/Q16/P05/L02/L05: evidence mapping, duration, post-erasure reconciliation and destruction. |
| 38 | `subscription_billing_records.receipt` | provider-required retention | Preserve exact receipt only where required to reconcile or evidence the purchase; classify whether it is internal or provider-required before any exception. Restrict/encrypt if retained. | **Approval required** — Q15/Q16/P05/L02/L05: actual semantics, uniqueness/replay continuity, necessity and retention; the column name proves no provider requirement. |
| 39 | `subscription_billing_records.status` | retain | Controlled historical purchase state; preserve unresolved money and application facts. | **Approval required** — Q09/Q16/L02/L05: duration and wind-down semantics. |
| 40 | `subscription_plans.features` | retain | Curated nonpersonal plan-feature schema only. Personal/custom legacy text must be separately assessed, not grandfathered as public catalog content. | **Approval required** — Q09/Q16/L02/L05: benefits schema, legacy review and catalog retention. |
| 41 | `support_messages.body` | anonymize | Redact erased-person content or replace the affected authored message with a controlled removed-content marker; preserve other parties' content only where justified. | **Approval required** — Q16/L01/L05: author/mentioned-person scope, dispute evidence, legal hold and demonstrated nonidentifying output. |
| 42 | `support_tickets.status` | retain | Controlled support workflow state; this does not stop existing customer-ticket cascades or retain deleted rows. | **Approval required** — Q16/L05: any separately justified retained fact and duration. |
| 43 | `support_tickets.subject` | anonymize | Replace personal subject with a controlled nonpersonal support category, without copying the original to audit/logs. | **Approval required** — Q16/L01/L05: third-party scope, dispute evidence, holds and acceptable nonidentifying category. |

## Retention, erasure and immutable snapshots

- Do not change existing financial values, payment/refund states, snapshot
  meanings, source links, policy versions or processed outcomes as an erasure
  shortcut. A classification is not a data migration or a new statutory rule.
- Validate code fields against controlled allowlists. Unclassified historical
  arbitrary values require an approved narrow scrub/restricted-evidence plan;
  never reinterpret them as trusted accounting facts or copy them to a new log.
- For subscription benefits and other immutable payloads, separate an approved
  economic-facts projection from erasable/restricted explanation evidence.
  The current subscription snapshot guard prevents arbitrary benefit updates.
  Do not bypass it with an erasure flag: obtain a column-level future guard/
  storage design, prove conserved contract facts, and keep legacy bytes
  restricted only under approved authority until treatment is resolved.
- Personal content in other customers' support/email/anomaly records must be
  covered as well as direct actor/recipient FKs. Owner erasure preserves salon/
  booking shells and other customers' records. A whole-table delete or simply
  nulling author_id neither implements the needed redaction nor preserves scope.
- Existing email recipient/profile and customer-ticket cascades, and explicit
  salon_access deletion, remain as observed. A retain classification does not
  cancel existing deletion or copy a row into a new archive. New retention or
  hard-delete exceptions require explicit policy review.
- Pending notifications, refunds, purchases, disputes and unknown transfers need
  a durable restricted operator handoff. An operation cannot be marked failed,
  retried under a new identity, forgotten or paid twice to complete erasure.
  Removing checkout-session material must leave necessary operation identity
  available through an approved safer reference, not a secret session replay.
- Existing provider/receipt/error/session fields may be constrained or unique;
  do not replace values with ciphertext/digests in place. Later reviewed storage
  and guard adaptations must preserve equality, lookup, uniqueness, decryption,
  bounded rollback and deduplication across old/new key versions.
- Digest and ciphertext key rotation/destruction must include replicas, backups,
  caches, replay bodies and logs, plus legal holds. Destroying a dedup key cannot
  reopen settled/unknown operations to duplicate payment. Retain a lawful
  restricted linkage or another approved mechanism before destruction.
- No retention periods, automatic hold duration, legal basis, tax treatment or
  provider rule is selected. Approvals must identify field/purpose, data subject,
  permitted access, legal/contract basis, duration or event, hold/review process,
  operator handoff, key custody/destruction, backup expiry and residual
  reidentification risk. Unset policy blocks the dependent new workflow.
- G01's new command/authority/audit/seal fields and all other new digest/ciphertext/
  FK fields need their own complete classification before implementation. This
  43-row design closes a documentation inventory only, not the test/runtime gap.

## Future verification and readiness

With separate authorization, update runtime erasure paths and COLUMN_TREATMENT,
prove exact scoped redaction and zero residual seeded PII, preserve financial
facts and old snapshot semantics, test live/open-queue handoff and stable
deduplication through rotation, and verify restricted evidence cannot leak to
owner reports, outboxes, caches or logs. Test both missing/expired legal authority
and permitted holds. None of those tests or operations runs in this phase.

The 43 fields are proposals awaiting approval. No claim of legal compliance,
provider-required duration, irreversible anonymization or complete runtime
coverage follows from this classification.

