# Graph Report - salon-backend  (2026-11-01)

## Corpus Check
- 894 files · ~916,851 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 25 file(s) not represented in the graph (top: (none) 16, .example 2, .csv 2)

## Summary
- 9755 nodes · 25181 edges · 491 communities (326 shown, 165 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 3006 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `56240fbd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- datetime
- payments/cashfree.py
- ConflictError
- Profile
- make_mock_repo
- assert_approved_workspace
- test_media_admission_http.py
- Money
- pathlib
- test_notification_outbox_worker.py
- test_admin_insights.py
- Data models
- make_owner
- PlatformRepository
- test_checkout_safety_sql.py
- test_u08_checkout_activation.py
- Settings
- test_cashfree_gateway.py
- erasure.py
- routes/payments.py
- RefundRequest
- routes/admin.py
- test_subscription_billing.py
- migration_policy.py
- test_payment_stage1_flows.py
- test_payment_flows.py
- ServiceUnavailableError
- sys
- time
- telemetry.py
- payments/booking.py
- R2StorageGateway
- use_cases/subscription_billing.py
- SubscriptionProviderResolver
- test_subscription_billing_sql.py
- SubscriptionProviderResolver
- AuthAdminGateway
- test_payments_foundation.py
- test_walkin_qr_contract.py
- test_booking_changes_sql.py
- test_api_input_bounds.py
- test_account_deletion_use_cases.py
- PillowImageProcessor
- test_account_erasure.py
- provision_super_admin.py
- customer.py
- G01-G09 payment/subscription/booking migration design groups (design review only)
- use_cases/account_deletion.py
- test_auth.py
- Module Group 50
- routes/support.py
- typing
- local_fixture_server.py
- get_current_actor
- panel.py
- test_payout_account.py
- test_account_deletion_sql.py
- RedisCache
- test_maintenance_job.py
- FakeBillingRepo
- post
- test_account_erasure_hardening.py
- FinanceRepository
- connections.py
- Salon Owner
- test_payment_stage1_api.py
- test_salon_ranking.py
- ConflictError
- Subscription billing (backend only, dormant, not sandbox-tested)
- routes/auth.py
- notifications.py
- subscriptions.py
- test_cashfree_subscription.py
- routes/admin_insights.py
- BookingActionRepository
- FCMGateway
- .get_available_slots
- Ledger
- use_cases/platform.py
- test_payment_fees_policy.py
- alembic
- architect.md
- MCP Server Best Practices
- UnauthorizedError
- OwnerCatalogMixin
- NotFoundError
- Node/TypeScript MCP Server Implementation Guide
- FakeWallet
- Module Group 89
- test_account_closure_steps.py
- UserNotifier
- schemas/platform.py
- test_subscription.py
- Website, customer app and owner app: developer handoff
- test_media_publication_safety.py
- json
- test_plan_prices.py
- pytest
- page_bounds
- use_cases/subscription_billing.py
- SupabaseAuthGateway
- test_public_discovery_contract.py
- schemas/admin.py
- test_accepting_bookings.py
- math
- PaymentGatewayResolver
- config.py
- MCP Server Evaluation Guide
- Python MCP Server Implementation Guide
- ci_image_bundle.py
- AdminUseCases
- test_owner_finance_api.py
- make_super_admin
- test_booking_finance_sql.py
- use_cases/wallet.py
- one_dict_or_none
- Changelog
- mumbai_browser.cjs
- Any
- CategoriesMixin
- ImageFamilies
- routes/finance.py
- .seed
- WalkInUseCases
- test_redis_recovery_sql.py
- Module Group 126
- test_subscription_status_guard.py
- FakeRepo
- Supabase
- Admin
- round_money
- docs/README.md
- test_image_families.py
- Any
- test_media_integration.py
- test_migration_tool_paths.py
- test_public_salon_visibility.py
- chief-of-staff.md
- Changelog
- routes/auth.py
- FinanceUseCases
- routes/walkin.py
- test_mumbai_forward_reconciliation.py
- Env
- Running Evaluations
- Writing Guidelines for Postgres References
- Customer App Backend API Contract
- exceptions.py
- BookingChangeRepository
- salon-backend
- Super-admin to owner review thread (spec; design, not built)
- Role
- Progress: shifan
- RazorpayGateway
- Review Priorities
- tdd-guide.md
- Rams Design Review
- van_westendorp.py
- Salon Owner App Backend API Contract
- NotificationUseCases
- Progress: thameem/cloud-run-startup-investigation
- PublicCatalogMixin
- Mumbai staging readiness review — 2026-10-16
- Build Error Resolver
- Documentation & Codemap Specialist
- E2E Test Runner
- planner.md
- Refactor & Dead Code Cleaner
- Complete backend API reference for frontend teams
- Agent Instructions
- ProfileUpdateRequest
- Module Group 172
- test_migration_policy.py
- test_build_identity.py
- _ChallengeMixin
- test_expo_push_includes_notification_payload
- Database Reviewer
- mcp-builder/SKILL.md
- Progress: thameem/mumbai-forward-reconciliation
- Progress: {branch}
- Progress: thameem/cloud-run-mumbai-staging
- Progress: thameem/local-docker-cold-start
- Progress: thameem/provider-agnostic-payments
- Progress: thameem/u08-verification-continuation
- test_salon_trials.py
- How to use the prompts
- test_cloud_run_auto.py
- _RequestMixin
- test_release_configuration.py
- routes/wallet.py
- AccountDeletionRepository
- Pass 2 — Clean Architecture & Standards
- redis_recovery_browser.cjs
- ProviderAccountMixin
- test_cloud_run_candidate.py
- test_payment_ledger_sql.py
- WalletRepository
- cache_recovery_worker.py
- founder-board
- ObservationMixin
- founder-ops
- Karpathy Guidelines
- Section Definitions
- Subscriptions
- .get_salon_by_qr
- test_checkout_safety_sql.py
- ports/__init__.py
- main.py
- _BookingMixin
- test_sql_bind_params.py
- source
- Gate A — Isolated Full-Data Restore Evidence
- booking_payments as Ledger Source of Truth
- NotificationOutboxMixin
- founder-consumer
- test_account_deletion_migration.py
- Codex prompt: deploy migration 0049 and the subscription backend to GCP
- WebhookEventMixin
- founder-marketing
- founder-offer
- BookingChangeGateway
- Isolated Restore Evidence Template
- test_migration_and_service_api_round_trip
- ._send_fcm
- IntakeLedger
- Production Alembic baseline/bridge strategy — architecture review
- io
- Agent memory
- Booking and payments
- founder-brand
- founder-competitors
- founder-plan
- founder-pricing
- Quality Checklist
- Web Application Testing
- Gate A — Isolated Restore Evidence
- get_my_profile
- Image integration review — 2026-10-10
- 0029_payment_monetary_policy.py
- 0030_subscription_billing.py
- 0033_payment_fee_snapshot.py
- test_booking_finance_policy.py
- founder-cfo
- founder-launch
- Knex Migration Drift
- Quality Checklist
- Testing
- Workers and deploy
- evaluation.py
- service
- OutboundMessage
- TrialLimits
- Operational Runbook (local setup, super-admin, workers)
- email_gateway.py
- 0049 Subscription price reconciliation
- Frontend Integration Prompt — Redis Feature Changes
- Module Group 257
- Alembic bridge graph validation
- Subscription 0049: applied database change and staging release
- Module Group 260
- test_drain_processes_each_due_event_once
- 0022_salon_accepting_bookings.py
- 0026_booking_payments.py
- 0027_payout_account_audit.py
- Evaluation Process
- Advanced MCP Features
- Advanced FastMCP Features
- Module Group 268
- Module Group 269
- Module Group 270
- Module Group 271
- Module Group 272
- Supabase Postgres Best Practices
- test_wif_claim_preflight.py
- Shared production API domain migration — 27 October 2026
- AdminInsightsRepo
- .throttle
- Mumbai staging readiness audit — 2026-10-15
- 0001_baseline.py
- 0002_notifications_read_at.py
- 0003_google_oauth_profile_metadata.py
- 0004_service_duration_slot_steps.py
- 0006_enable_realtime.py
- 0007_salon_qr_image_url.py
- 0008_salon_images_soft_delete.py
- 0009_booking_cancellation_reason.py
- 0011_holiday_soft_delete.py
- 0024_secure_new_user_role.py
- 0025_salon_payout_accounts.py
- 0032_salon_access_state.py
- 6. Required backup and restore execution plan
- test_account_deletion_blockers.py
- agent-sdk-verifier-py.md
- harness-optimizer.md
- loop-operator.md
- The three lenses
- Cashfree subscription checkout
- Roadmap
- 0005_staff_experience.py
- IdempotencyInProgressError
- Adding an endpoint
- Owner payout accounts and setup checklist
- 0015_salon_admin_approval.py
- Production migration reconciliation — correction and safe path
- 0035_booking_checkout_safety.py
- gcp-vm-release-compose.sh
- Mumbai Local Refresh Implementation and Verification 2026-10-15
- code-explorer.md
- test_booking_changes_sql.py
- test_cache_recovery.py
- Clear Technical English
- CommissionPolicy
- Payment integration: gap assessment and decision register
- test_staff_earnings_domain.py
- .settlement_model
- AdminSalonsMixin
- subscription_billing_records table (purchase attempt tracking)
- test_media_admission_http.py
- booking_finance_policy.py
- booking_updates.py
- select_rule
- Production Release Execution Tracker — 2026-10-31
- _Result
- AdminInsightsUseCases
- test_account_deletion_api.py
- create_holiday
- retire_unreferenced_media
- test_messaging.py
- reversal_due
- Production Migration Execution Runbook
- check-container.sh
- gcp-vm-deploy.sh
- code-architect.md
- start.md
- wrap.md
- register_exception_handlers
- render
- Owner finance: Phase 2 (local backend) implementation record
- Phase 1 checklist
- Prompt: build the subscription pages on salones.in
- .messages
- gcp-vm-install-docker.sh
- gcp-vm-release.sh
- debugger.md
- review.md
- advanced-full-text-search.md
- advanced-jsonb-indexing.md
- conn-idle-timeout.md
- conn-limits.md
- conn-pooling.md
- conn-prepared-statements.md
- data-batch-inserts.md
- data-n-plus-one.md
- data-pagination.md
- data-upsert.md
- lock-advisory.md
- lock-deadlock-prevention.md
- lock-short-transactions.md
- lock-skip-locked.md
- monitor-explain-analyze.md
- monitor-pg-stat-statements.md
- monitor-vacuum-analyze.md
- query-composite-indexes.md
- query-covering-indexes.md
- query-index-types.md
- query-missing-indexes.md
- query-partial-indexes.md
- schema-constraints.md
- schema-data-types.md
- schema-foreign-key-indexes.md
- schema-lowercase-identifiers.md
- schema-partitioning.md
- cloud_run_candidate.py
- security-privileges.md
- security-rls-basics.md
- security-rls-performance.md
- _template.md
- Progress: shifan-cloud-run-auto-deploy
- commands.md
- shared/README.md
- agent-skill-routing.md
- SALON_APPROVAL.md
- BookingFinanceRepository
- Rows
- Owner finance: Phase 0 discovery and approval request
- 3. Per-migration reconciliation: 0041–0052
- FakeInsightsRepo
- Progress: shifan-cloud-run-bootstrap
- Progress: shifan-cloud-run-oidc-cicd
- AuthUserContacts
- _Clock
- Role-Based Access Model (customer/owner/staff/super_admin)
- Env
- support_finance_reference.py
- expected_closing_cash
- Domain rules
- split_refund_across_lines
- Owner finance: Phase 1 schema and API design (review only)
- 6. API contracts (all under `/v1`, JSON, paise, `Idempotency-Key` required on every write)
- Cloud Run automatic-release gate fix — 1 November 2026
- TestRuleTable
- public_api
- routes/booking_finance.py
- measure_external
- 4. Proposed data model (proposal only; no revision ID assigned)
- 2. Proposed tables (text proposal, public schema, `salon_id uuid not null` everywhere)
- Server-side WebP image families
- CASHFREE_VERIFICATION_2026-10-29.md
- Canonical repository and Cloud Run CI/CD audit
- Production release preflight — 1 November 2026
- Rows
- BulkPlanPriceRequest
- install_database_metrics
- service_change_quote
- Owner finance: Phase 3 (owner app) record
- Local schema reconciliation rehearsal ? 29 October 2026
- Part 7 — Required isolated restore test stages
- business_checks
- test_finance_design_fixtures.py
- Production Gate B migration execution — 31 October 2026 session 2
- enqueue_and_deliver_notification
- PlanPriceSetRequest
- round_money
- ProfilesMixin
- outbox_worker.py
- Legacy Cloud Run baseline bootstrap
- Cloud Run deployment gate audit — 1 November 2026
- Subscription percentage release and owner-session verification
- Owner wallet and manual payouts
- net_expense_total
- add_salon
- test_automatic_pipeline_uses_tested_image_and_finishes_after_new_main
- Cloud Run Deployment Assessment 2026-10-22
- 6. Owner app and owner web: business workflows
- 0052_booking_window_30_days.py
- Salon Platform API
- CLOUD_RUN_FINAL_POLICY_DESIGN_2026-10-29.md
- API Latency Investigation 2026-10-14
- Provider-independent payments: mock implementation — 2026-10-18
- test_signed_artifact_download_verifies_digest_without_forwarding_auth
- Database plan
- Features
- walk

## God Nodes (most connected - your core abstractions)
1. `Profile` - 472 edges
2. `ValidationError` - 256 edges
3. `Role` - 233 edges
4. `NotFoundError` - 201 edges
5. `Settings` - 188 edges
6. `ForbiddenError` - 159 edges
7. `make_profile()` - 154 edges
8. `PlatformRepository` - 150 edges
9. `Data models` - 138 edges
10. `make_owner()` - 135 edges

## Surprising Connections (you probably didn't know these)
- `Where checks go` --references--> `require_role()`  [INFERRED]
  .claude/skills/auth-and-roles/SKILL.md → backend/app/api/deps.py
- `POST `/v1/admin/salons`` --references--> `create_salon()`  [INFERRED]
  docs/BACKEND_API_REFERENCE.md → backend/app/api/v1/routes/admin.py
- `GET `/v1/admin/salons/{salon_id}/onboarding`` --references--> `get_salon_onboarding()`  [INFERRED]
  docs/BACKEND_API_REFERENCE.md → backend/app/api/v1/routes/admin.py
- `GET `/v1/admin/catalog/languages`` --references--> `list_languages()`  [INFERRED]
  docs/BACKEND_API_REFERENCE.md → backend/app/api/v1/routes/admin.py
- `POST `/v1/bookings/{booking_id}/payment-confirmation-requests`` --references--> `create_payment_confirmation_request()`  [INFERRED]
  docs/BACKEND_API_REFERENCE.md → backend/app/api/v1/routes/booking_actions.py

## Import Cycles
- 3-file cycle: `backend/app/api/v1/routes/owner.py -> backend/app/api/v1/routes/owner_salon.py -> backend/app/api/v1/routes/owner_common.py -> backend/app/api/v1/routes/owner.py`
- 3-file cycle: `backend/app/api/v1/routes/owner.py -> backend/app/api/v1/routes/owner_catalog.py -> backend/app/api/v1/routes/owner_common.py -> backend/app/api/v1/routes/owner.py`
- 3-file cycle: `backend/app/api/v1/routes/owner.py -> backend/app/api/v1/routes/owner_blocks.py -> backend/app/api/v1/routes/owner_common.py -> backend/app/api/v1/routes/owner.py`
- 3-file cycle: `backend/app/api/v1/routes/owner.py -> backend/app/api/v1/routes/owner_holidays.py -> backend/app/api/v1/routes/owner_common.py -> backend/app/api/v1/routes/owner.py`

## Hyperedges (group relationships)
- **Account Deletion End-to-End Flow (auth -> erasure -> financial purge)** — backend_docs_account_deletion_flow, backend_docs_account_deletion_erasure_worker, backend_docs_account_deletion_financial_purge_design_overview [EXTRACTED 1.00]
- **All Compose Workers Depend on Redis Health** — backend_docker_compose_api_service, backend_docker_compose_notification_worker, backend_docker_compose_media_cleanup, backend_docker_compose_account_deletion_worker, backend_docker_compose_payment_webhook_worker, backend_docker_compose_email_worker, backend_docker_compose_redis [EXTRACTED 1.00]
- **Booking Creation Idempotency Pattern (Postgres + Redis + use cases)** — backend_docs_booking_flow_postgres_functions, backend_docs_payments_idempotency, backend_docs_architecture_redis_caching [INFERRED 0.85]

## Communities (491 total, 165 thin omitted)

### Community 0 - "datetime"
Cohesion: 0.03
Nodes (20): get_payment_gateway_resolver(), payment_webhook(), process_in_background(), EarningsMixin, _contains_pattern(), page_bounds(), _salon_actor_sql(), get_probe_session() (+12 more)

### Community 1 - "payments/cashfree.py"
Cohesion: 0.04
Nodes (30): ClientConfig, PaymentCallback, PaymentEvent, PaymentIntent, PaymentIntentRequest, ProviderPayment, PaymentProvider, WebhookVerifier (+22 more)

### Community 2 - "ConflictError"
Cohesion: 0.06
Nodes (5): ConflictError, PayAtSalonBlockedError, ClosuresMixin, LanguagesSlotsMixin, test_qr_route_forwards_retries_to_database_idempotency()

### Community 3 - "Profile"
Cohesion: 0.05
Nodes (11): BookingChangeUseCases, OwnerUseCases, _assert_admin(), SalonSubscriptionUseCases, Profile, is_owner(), _profile_from_row(), Storage and security (+3 more)

### Community 4 - "make_mock_repo"
Cohesion: 0.10
Nodes (29): BookingUseCases, make_booking(), make_mock_repo(), test_approve_as_owner(), test_approve_requires_owner(), test_availability_delegates_to_repo(), test_booking_response_can_cancel_only_before_start_time(), test_booking_response_exposes_late_cancellation_and_cash_claim_eligibility() (+21 more)

### Community 5 - "assert_approved_workspace"
Cohesion: 0.04
Nodes (18): SalonApprovalRepository, WorkspaceRepository, assert_approved_workspace(), BookingSourceNotAllowedError, BookingLine, BookingSource, BookingStatus, PaymentStatus (+10 more)

### Community 6 - "test_media_admission_http.py"
Cohesion: 0.19
Nodes (21): UploadAdmissionMiddleware, test_grant_json_is_bounded_before_parsing(), test_metadata_gets_share_admission_and_reject_request_bodies(), Downstream, invoke(), receive(), send(), scope() (+13 more)

### Community 7 - "Money"
Cohesion: 0.06
Nodes (39): PayoutProvider, IdempotencyKeyReuseError, RefundStatus, EvidenceSource, PayoutRequest, PayoutStatus, ProviderFeeReconciliation, ProviderFees (+31 more)

### Community 8 - "pathlib"
Cohesion: 0.05
Nodes (36): SQLProfileRepository, metric(), percentile(), run(), measure(), one(), main(), run() (+28 more)

### Community 10 - "test_admin_insights.py"
Cohesion: 0.12
Nodes (20): _rollup_money(), _today_ist(), FakePlans, _month(), test_a_bulk_offer_applies_to_none_when_any_salon_is_unknown(), test_a_bulk_offer_cannot_end_in_the_past(), test_a_bulk_offer_computes_the_price_once_and_applies_it_to_every_salon(), test_a_bulk_offer_follows_the_same_price_rules_as_a_single_offer() (+12 more)

### Community 11 - "Data models"
Cohesion: 0.02
Nodes (123): AccountDeletionAcceptedResponse, AccountDeletionStatusResponse, AdminAccountDeletionResponse, AdminCreateSalonRequest, AdminDeactivateSalonResponse, AdminRejectSalonRequest, AdminSalonOnboardingResponse, AdminSalonResponse (+115 more)

### Community 12 - "make_owner"
Cohesion: 0.06
Nodes (43): make_owner(), test_admin_ledger_requires_super_admin(), test_failed_avatar_publication_defers_cleanup_until_committed_reference_check(), gateway(), test_avatar_grants_have_distinct_keys(), test_inline_images_cannot_enter_media_records_or_cached_responses(), test_staff_grant_requires_owned_staff_before_storage(), test_upload_capability_cannot_overwrite_a_published_object() (+35 more)

### Community 13 - "PlatformRepository"
Cohesion: 0.02
Nodes (25): get_storage_gateway(), get_image_family(), upload_avatar(), upload_signed_image(), _use_cases(), get_avatar_upload_url(), update_my_profile(), AvatarResponse (+17 more)

### Community 14 - "test_checkout_safety_sql.py"
Cohesion: 0.09
Nodes (37): SupportUseCases, SQLAccountDeletionRepository, SupportRepository, deliver_once(), install(), finance_db(), install(), SafetyEnv (+29 more)

### Community 15 - "test_u08_checkout_activation.py"
Cohesion: 0.24
Nodes (6): checkout_quote(), test_pay_at_salon_is_fee_free_with_exact_instructions(), test_adding_provider_credentials_cannot_activate_u08_online_money(), test_new_booking_policy_selection_does_not_reprice_legacy_payment(), test_policy_selection_is_explicit_and_rejects_unknown_versions(), test_u08_checkout_has_no_customer_surcharge_and_reports_its_version()

### Community 16 - "Settings"
Cohesion: 0.04
Nodes (21): get_settings(), Settings, test_auto_release_cannot_be_enabled_it_is_not_built(), test_blank_env_values_mean_unset_not_zero(), test_provider_defaults_stay_none(), test_blank_account_deletion_secret_is_unconfigured(), test_explicit_r2_values_win_over_legacy_values(), test_messaging_is_off_by_default() (+13 more)

### Community 17 - "test_cashfree_gateway.py"
Cohesion: 0.06
Nodes (52): ignored(), both_client(), cf_settings(), event_body(), gateway(), IntakeRepo, intent_request(), order_handler() (+44 more)

### Community 18 - "erasure.py"
Cohesion: 0.11
Nodes (4): authored_quote_pattern(), personal_text_pattern(), quoted_text_pattern(), _ErasureMixin

### Community 19 - "routes/payments.py"
Cohesion: 0.08
Nodes (39): booking_quote(), cancel_payment(), confirm_payment(), create_payment_intent(), get_settlement_account(), list_booking_payments(), my_earnings(), payment_config() (+31 more)

### Community 20 - "RefundRequest"
Cohesion: 0.17
Nodes (5): RefundRequest, RefundResult, RefundProvider, FakeGateway, test_refund_timeout_is_recovered_without_a_second_operation()

### Community 22 - "routes/admin.py"
Cohesion: 0.08
Nodes (28): _admin_use_cases(), approve_salon(), _catalog_use_cases(), create_category(), create_salon(), create_subcategory(), deactivate_category(), deactivate_salon() (+20 more)

### Community 23 - "test_subscription_billing.py"
Cohesion: 0.07
Nodes (56): subscription_event_to_json(), owner(), sub_settings(), adapter(), ent(), handler_for(), http(), make() (+48 more)

### Community 24 - "migration_policy.py"
Cohesion: 0.11
Nodes (9): portable_revisions(), require_mumbai_url(), require_unambiguous_url(), do_run_migrations(), guard_requested_migration(), run_migrations_offline(), run_migrations_online(), main() (+1 more)

### Community 25 - "test_payment_stage1_flows.py"
Cohesion: 0.07
Nodes (48): PaymentAmountMismatchError, build(), capture(), details(), FakeGateway, process_events(), settings(), test_a_different_purpose_cannot_hijack_an_unacknowledged_intent() (+40 more)

### Community 26 - "test_payment_flows.py"
Cohesion: 0.08
Nodes (26): captured_body(), client(), FakeRepo, load(), make_processor(), run(), settings(), sign() (+18 more)

### Community 27 - "ServiceUnavailableError"
Cohesion: 0.14
Nodes (12): scrub_sentry(), ResendEmailGateway, test_invalid_money_is_rejected(), test_online_charge_uses_decimal_half_up(), test_only_resend_key_without_verified_sender_makes_no_network_call(), test_resend_payload_omits_reply_to_when_unset(), test_resend_payload_uses_configured_sender_and_support_reply_to(), test_resend_provider_key_is_server_only_and_retries_keep_same_idempotency_key() (+4 more)

### Community 28 - "sys"
Cohesion: 0.05
Nodes (42): Backup, Gate A isolated restore evidence — 30 October 2026, Harness results, Isolated restore, Stop condition and cleanup, Safety checks, Safety checks, Safety checks (must all be confirmed before running harness) (+34 more)

### Community 29 - "time"
Cohesion: 0.06
Nodes (38): export_backup(), gpg_path(), locate_tool(), main(), validate_destination(), validate_source(), distribution(), docker() (+30 more)

### Community 30 - "telemetry.py"
Cohesion: 0.12
Nodes (6): _add_request_id(), configure_logging(), get_request_id(), set_request_id(), RequestMetrics, main()

### Community 31 - "payments/booking.py"
Cohesion: 0.06
Nodes (16): BookingPaymentUseCases, _NoRepository, apply_provider_payment(), _clean_code(), event_to_json(), _fingerprint(), _json_default(), _ledger_row() (+8 more)

### Community 32 - "R2StorageGateway"
Cohesion: 0.08
Nodes (14): R2StorageGateway, test_token_purposes_stay_cryptographically_separate(), test_r2_media_resume_skips_previous_prefixes_and_uses_start_after(), test_assert_configured_passes_when_all_settings_present(), test_assert_configured_raises_when_settings_missing(), test_delete_object_calls_boto3_delete(), test_delete_object_raises_validation_error_on_boto3_failure(), test_delete_object_raises_when_r2_not_configured() (+6 more)

### Community 33 - "use_cases/subscription_billing.py"
Cohesion: 0.05
Nodes (16): ProviderOrder, ProviderPaymentObservation, ProviderRefund, ProviderSubscriptionEvent, SubscriptionClientConfig, SubscriptionOrderRequest, SubscriptionProvider, PaymentOutcomeUnknownError (+8 more)

### Community 34 - "SubscriptionProviderResolver"
Cohesion: 0.14
Nodes (28): cancel(), checkout(), list_purchasable_plans(), my_access_state(), my_subscription(), payments(), subscription_config(), _uc() (+20 more)

### Community 35 - "test_subscription_billing_sql.py"
Cohesion: 0.04
Nodes (39): PaymentWebhookUseCases, SubscriptionWebhookHandler, InvalidWebhookSignatureError, PaymentRepository, _row(), SubscriptionBillingRepository, reconcile_once(), test_fake_payment_and_refund_use_existing_intake_worker_and_replay_gate() (+31 more)

### Community 36 - "SubscriptionProviderResolver"
Cohesion: 0.08
Nodes (10): get_subscription_provider_resolver(), SubscriptionEventKind, SubscriptionReconciler, SubscriptionSettlement, drain_webhook_events(), reconcile_subscriptions_once(), run_forever(), build_subscription_provider() (+2 more)

### Community 37 - "AuthAdminGateway"
Cohesion: 0.07
Nodes (30): get_auth_admin_gateway(), closed_salon_statement(), confirm_account_deletion(), get_deletion_status(), list_account_deletions(), list_closed_salons(), start_deletion_challenge(), _use_cases() (+22 more)

### Community 38 - "test_payments_foundation.py"
Cohesion: 0.07
Nodes (23): derive_payment_state(), gateway_with(), hex_hmac(), make_settings(), test_callback_signature_vectors(), test_capabilities(), test_configured_provider_needs_credentials(), test_create_booking_request_accepts_new_preferences() (+15 more)

### Community 39 - "test_walkin_qr_contract.py"
Cohesion: 0.05
Nodes (36): require_qr_token_format(), BookingCheckoutUseCases, QrCodeNotFoundError, SlotUnavailableError, is_valid_qr_token_format(), test_u08_quote_does_not_advertise_online_collection_before_held_funds_workflow(), _as(), client() (+28 more)

### Community 40 - "test_booking_changes_sql.py"
Cohesion: 0.11
Nodes (29): _body(), _count(), _customer(), _direct_book(), _qr_book(), _second_customer(), test_availability_after_sixty_local_days_is_empty(), test_customer_booking_later_than_sixty_local_days_is_rejected() (+21 more)

### Community 41 - "test_api_input_bounds.py"
Cohesion: 0.06
Nodes (36): _action_use_cases(), apply_closure(), _closure_use_cases(), create_cancellation_request(), create_payment_confirmation_request(), list_booking_action_requests(), preview_closure(), respond_booking_action_request() (+28 more)

### Community 42 - "test_account_deletion_use_cases.py"
Cohesion: 0.15
Nodes (28): InvalidVerificationCodeError, build(), contacts(), FakeAuthGateway, test_a_subscription_bought_after_the_challenge_blocks_at_confirm(), test_active_subscription_blocks_only_with_a_real_provider(), test_challenge_and_token_cannot_authorize_another_account(), test_client_cannot_redirect_the_code_to_another_identifier() (+20 more)

### Community 43 - "PillowImageProcessor"
Cohesion: 0.11
Nodes (24): ImagePolicy, PillowImageProcessor, family(), test_integrated_multipart_rejects_multiple_files_before_processing(), test_result_token_is_read_only_and_upload_token_is_not_a_result_token(), photo(), test_bounded_retry_rejects_when_no_output_can_meet_limit(), test_client_bypass_is_processed_before_r2_publication() (+16 more)

### Community 44 - "test_account_erasure.py"
Cohesion: 0.09
Nodes (17): FakeAdmin, FakeLedger, FakeStorage, make_request(), make_service(), test_already_missing_auth_user_is_not_banned_and_delete_is_idempotent(), test_auth_delete_failure_is_retryable_and_resumes_without_repeating_steps(), test_customer_erasure_skips_salon_cache_keys() (+9 more)

### Community 45 - "provision_super_admin.py"
Cohesion: 0.09
Nodes (20): _admin_base(), _assert_safe_existing_profile(), _AuthUser, _create_auth_user(), _FakeGateway, _find_user_by_email(), _get_profile_state(), main() (+12 more)

### Community 46 - "customer.py"
Cohesion: 0.08
Nodes (14): get_profile(), get_salon(), list_public_categories(), list_public_subcategories(), list_salon_services(), list_salon_staff(), list_salons(), nearby_salons() (+6 more)

### Community 47 - "G01-G09 payment/subscription/booking migration design groups (design review only)"
Cohesion: 0.26
Nodes (22): Required owner approval decisions Q01-Q16 and A01-A06 before executable migration, Required 10-step forward-only reconciliation plan, Mumbai live catalog inspection (44 tables, 52 functions, empty Alembic history), RLS and privilege analysis (anon/authenticated zero rights, service_role broad rights), G02 Provider-fee reconciliation (financial_postings, accounting seals on G01 financial_events), G03 Cancellation policy versions (U03 bands: 48h flat, 5%, 35%, zero; 70/30 split), G04 Payout/dispute records (salon_payouts, payout_destination_versions, booking_financial_disputes), G05 Payout schedules (payout_capability_versions, salon_payout_schedule_versions) (+14 more)

### Community 48 - "use_cases/account_deletion.py"
Cohesion: 0.08
Nodes (12): AccountDeletionUseCases, deletion_stage(), mask_contact(), normalize_contact(), _statement_figures(), ContactMismatchError, DeletionBlockedError, digest() (+4 more)

### Community 49 - "test_auth.py"
Cohesion: 0.07
Nodes (16): MeOutput, GetMe, EnsureOwnerAccess, ProfileRepository, can_read_own_profile(), is_customer(), is_staff(), is_super_admin() (+8 more)

### Community 50 - "Module Group 50"
Cohesion: 0.14
Nodes (13): Account Deletion Worker Service, API Service (Docker Compose), Email Worker Service, Media Cleanup Worker Service, Notification Worker Service, Payment Webhook Worker Service, Redis Service (Docker Compose), Erasure Worker (lock/cancel/notify/refund/settle/erase) (+5 more)

### Community 51 - "routes/support.py"
Cohesion: 0.17
Nodes (14): create_ticket(), email_event(), read_ticket(), reply_ticket(), EmailEventResponse, SupportCreateRequest, SupportMessageResponse, SupportReplyRequest (+6 more)

### Community 52 - "typing"
Cohesion: 0.03
Nodes (17): BookingFinanceGateway, check_idempotency_key_length(), close_difference(), expected_closing_cash(), finance_allowed(), local_day_bounds(), month_bounds(), reason_is_written() (+9 more)

### Community 53 - "local_fixture_server.py"
Cohesion: 0.14
Nodes (7): app_factory(), get_user(), phone_verify(), session(), sign_in(), user(), fixture_manifest()

### Community 54 - "get_current_actor"
Cohesion: 0.06
Nodes (19): get_authenticated_session(), get_cache(), get_current_actor(), test_database_health_returns_safe_503_when_database_is_unavailable(), test_redis_health_disabled_when_not_configured(), test_redis_health_ok_when_reachable(), test_redis_health_returns_503_when_ping_fails(), _call() (+11 more)

### Community 55 - "panel.py"
Cohesion: 0.11
Nodes (19): _answer_ok(), check(), deal(), init(), load_state(), main(), _num(), PanelError (+11 more)

### Community 56 - "test_payout_account.py"
Cohesion: 0.07
Nodes (11): api(), FakeRepo, _migration(), _migration_named(), _sql(), test_0027_shape(), test_field_validation_rejects_bad_input(), test_migration_chain_and_security_shape() (+3 more)

### Community 57 - "test_account_deletion_sql.py"
Cohesion: 0.13
Nodes (33): 7. Safety, privacy and erasure, 8. Account erasure and retention, confirm(), drain(), engine(), FakeAdmin, finish_ledger(), make_due() (+25 more)

### Community 58 - "RedisCache"
Cohesion: 0.10
Nodes (16): close_redis_cache(), get_redis_cache(), init_redis_cache(), _redacted_target(), RedisCache, test_auth_limit_fails_closed_on_backend_error(), test_auth_limit_fails_closed_without_redis_but_booking_fallback_stays_available(), test_startup_outage_retains_client_and_retries_epoch_after_reconnect() (+8 more)

### Community 59 - "test_maintenance_job.py"
Cohesion: 0.06
Nodes (34): drain_queue(), main(), run_job(), run_pass(), attempt_one(), run_forever(), sweep_media(), heartbeat_path() (+26 more)

### Community 61 - "post"
Cohesion: 0.06
Nodes (43): approve_booking(), availability(), barber_cancel_booking(), booking_change_availability(), cancel_booking(), change_booking(), check_in(), complete_booking() (+35 more)

### Community 62 - "test_account_erasure_hardening.py"
Cohesion: 0.09
Nodes (25): heartbeat_path(), is_healthy(), main(), max_age_seconds(), touch(), storage_is_required(), validate_worker_configuration(), cascade_tables_in_migrations() (+17 more)

### Community 63 - "FinanceRepository"
Cohesion: 0.10
Nodes (4): TrialState, ExpenseRuleRepository, FinanceRepository, _row()

### Community 64 - "connections.py"
Cohesion: 0.08
Nodes (6): create_connection(), MCPConnection, MCPConnectionHTTP, MCPConnectionSSE, MCPConnectionStdio, supabase

### Community 65 - "Salon Owner"
Cohesion: 0.06
Nodes (34): DELETE `/v1/salons/me/blocks/{block_id}`, DELETE `/v1/salons/me/holidays/{holiday_id}`, DELETE `/v1/salons/me/images/{image_id}`, DELETE `/v1/salons/me/services/{service_id}`, DELETE `/v1/salons/me/staff/{staff_id}`, GET `/v1/salons/me`, GET `/v1/salons/me/blocks`, GET `/v1/salons/me/holidays` (+26 more)

### Community 66 - "test_payment_stage1_api.py"
Cohesion: 0.09
Nodes (14): CommissionBase, commission_reversal(), compute_commission(), test_zero_platform_commission_is_valid_in_the_commission_math(), FakeUseCases, load(), run(), test_0029_downgrade_restores_legacy_functions_and_drops_additions() (+6 more)

### Community 67 - "test_salon_ranking.py"
Cohesion: 0.16
Nodes (20): AdminUpdateSalonRequest, _actor(), add_salon(), ids(), ranked(), _subscribe(), test_admin_request_validates_priority(), test_admin_response_exposes_priority_and_audit_actor() (+12 more)

### Community 68 - "ConflictError"
Cohesion: 0.18
Nodes (17): _repository(), _Result, test_cancellation_owner_decision_releases_slot_only_when_approved(), test_closure_rejects_changed_impact_set(), test_cross_salon_decision_is_hidden(), test_direct_payment_rejects_cancelled_booking(), test_duplicate_pending_request_is_rejected(), test_immediate_cancel_rejects_late_request() (+9 more)

### Community 69 - "Subscription billing (backend only, dormant, not sandbox-tested)"
Cohesion: 0.25
Nodes (8): `GET /v1/salons/me/subscription/payments?limit=50&offset=0` (owner), `GET /v1/subscription-plans` (owner), `GET /v1/subscriptions/config` (no auth, always 200), `POST /v1/salons/me/subscription/cancel` (owner), `POST /v1/salons/me/subscription/checkout` (owner, approved salon), `POST /v1/salons/me/subscription/verify` (owner), Subscription billing (backend only, dormant, not sandbox-tested), Webhook (provider to backend, not an app route)

### Community 70 - "routes/auth.py"
Cohesion: 0.11
Nodes (14): forgot_password(), me(), owner_access(), refresh(), ForgotPasswordRequest, ForgotPasswordResponse, ProfileResponse, RefreshRequest (+6 more)

### Community 71 - "notifications.py"
Cohesion: 0.10
Nodes (13): deactivate_device(), list_notifications(), mark_all_notifications_read(), mark_notification_read(), register_device(), _use_cases(), DeviceRegisterRequest, DeviceRegisterResponse (+5 more)

### Community 72 - "subscriptions.py"
Cohesion: 0.24
Nodes (16): cancel_subscription(), clear_salon_plan_price(), create_plan(), create_test_subscription(), deactivate_plan(), get_salon_subscription(), get_salon_trial(), list_events() (+8 more)

### Community 73 - "test_cashfree_subscription.py"
Cohesion: 0.17
Nodes (18): adapter(), order(), request(), settings(), test_cancelled_refund_is_terminal_failure_in_api_and_webhook(), test_checkout_replay_and_server_verified_activation_use_existing_billing_flow(), handler(), test_configuration_is_independent_and_live_requires_explicit_activation() (+10 more)

### Community 74 - "routes/admin_insights.py"
Cohesion: 0.15
Nodes (14): bulk_set_plan_price(), list_salon_subscriptions(), salon_analytics(), salon_subscription_summary(), _uc(), BookingCounts, BulkPlanPriceResponse, MoneyTotals (+6 more)

### Community 76 - "FCMGateway"
Cohesion: 0.18
Nodes (4): FCMGateway, test_provider_data_ignores_non_object_notification_data(), test_provider_data_merges_notification_data_as_strings(), test_provider_data_still_works_for_notifications_without_data()

### Community 77 - ".get_available_slots"
Cohesion: 0.09
Nodes (16): B1 — Migration reconciliation and schema gap (BLOCKING), B2 — Shared staging/production database (BLOCKING), B3 — Bootstrap baseline incompatibility (BLOCKING), B4 — Old-client backward compatibility not certified (BLOCKING for 0042/0052), B5 — Erasure worker compatibility (BLOCKING for 0047/0048/0051), Production blockers, Check the diff against, Code reviewer (read-only) (+8 more)

### Community 78 - "Ledger"
Cohesion: 0.06
Nodes (3): Model, Ledger, Prepared backend additions — 24 October 2026 (not deployed)

### Community 79 - "use_cases/platform.py"
Cohesion: 0.06
Nodes (13): CustomerUseCases, build_setup_status(), _has_open_day(), mask_payout_account(), validate_payout_account(), _extract_r2_object_key(), _upload_extension(), _upload_result() (+5 more)

### Community 80 - "test_payment_fees_policy.py"
Cohesion: 0.14
Nodes (17): cancellation_deduction(), gateway_fee_amount(), payee_share(), _settings(), test_deduction_never_exceeds_amount_paid_and_never_negative(), test_flat_and_percent_rules_are_both_accepted_and_percent_is_capped(), test_flat_deduction(), test_gateway_fee_is_percent_rounded_half_up_to_paise() (+9 more)

### Community 82 - "architect.md"
Cohesion: 0.07
Nodes (27): 1. Current State Analysis, 1. Modularity & Separation of Concerns, 2. Requirements Gathering, 2. Scalability, 3. Design Proposal, 3. Maintainability, 4. Security, 4. Trade-Off Analysis (+19 more)

### Community 83 - "MCP Server Best Practices"
Cohesion: 0.07
Nodes (28): Authentication and Authorization, DNS Rebinding Protection, Documentation Requirements, Error Handling, Error Handling, Input Validation, JSON Format (`response_format="json"`), Markdown Format (`response_format="markdown"`, typically default) (+20 more)

### Community 84 - "UnauthorizedError"
Cohesion: 0.13
Nodes (9): UnauthorizedError, SupabaseJWTVerifier, test_deactivated_account_jwt_returns_401_on_deletion_endpoints(), _raise_unauthorized(), test_concurrent_unknown_keys_share_one_cold_refresh(), refresh(), test_failed_fetch_attempts_are_also_bounded(), test_rotation_refresh_is_allowed_after_bounded_cooldown() (+1 more)

### Community 86 - "NotFoundError"
Cohesion: 0.05
Nodes (22): resolve_offer_price(), NotFoundError, SalonSubscriptionRepo, SubscriptionEventRepo, SubscriptionPlanRepo, _admin_id(), _apply_0049(), env() (+14 more)

### Community 87 - "Node/TypeScript MCP Server Implementation Guide"
Cohesion: 0.07
Nodes (27): Async/Await Best Practices, Building and Running, Character Limits and Truncation, Code Best Practices, Code Composability and Reusability, Complete Example, Error Handling, Key Imports (+19 more)

### Community 88 - "FakeWallet"
Cohesion: 0.08
Nodes (11): WalletAdminUseCases, PayoutAlreadyProcessedError, ask(), FakeWallet, owner(), TestAccess, TestAdmin, TestCancel (+3 more)

### Community 89 - "Module Group 89"
Cohesion: 0.20
Nodes (9): Alembic migration, Checklist, Workflow, Mumbai forward revisions — prepared only — 2026-10-15, Mumbai reconciliation — least privilege — 2026-10-15, Alembic history reconciliation plan — no execution, Rollback / recovery plan — Mumbai, Exact known schema differences — Mumbai vs head (+1 more)

### Community 90 - "test_account_closure_steps.py"
Cohesion: 0.05
Nodes (25): AccountErasureService, closure_refund_provider_key(), ErasureVerificationError, phone_key_variants(), RefundsPendingError, build(), FakeGateway, FakeLedger (+17 more)

### Community 92 - "schemas/platform.py"
Cohesion: 0.03
Nodes (54): create_blocked_slot(), delete_blocked_slot(), list_blocked_slots(), assign_staff_service(), create_service(), create_staff(), deactivate_service(), deactivate_staff() (+46 more)

### Community 93 - "test_subscription.py"
Cohesion: 0.08
Nodes (25): ManualSubscriptionCreateRequest, PlanCreateRequest, PlanResponse, PlanUpdateRequest, SubscriptionEventResponse, SubscriptionResponse, SubscriptionStatus, is_subscription_promotion_active() (+17 more)

### Community 94 - "Website, customer app and owner app: developer handoff"
Cohesion: 0.10
Nodes (20): 1. Project and responsibility map, 2. Shared configuration and integration rules, 3. Shared customer workflows, 4. Website: screens and responsibilities, 5. Customer app: screens and responsibilities, 7. Shared notifications, profile, support and erasure, 8. Critical boundaries and release evidence, 9. Technical references (+12 more)

### Community 95 - "test_media_publication_safety.py"
Cohesion: 0.10
Nodes (25): FakeR2Client, storage_error(), gateway(), test_gateway_rejects_bad_metadata_keys_and_buckets(), test_gateway_rejects_expiry_tampering_and_wrong_mime_before_r2(), test_raw_storage_helper_is_not_exposed_and_family_type_is_required(), test_transient_head_failure_is_reported_not_silently_classed_as_legacy(), stored_head() (+17 more)

### Community 96 - "json"
Cohesion: 0.06
Nodes (34): build_engines(), MeasuredAsyncSession, current_path(), digest(), main(), reseal(), rewrite(), lifecycle_checks() (+26 more)

### Community 97 - "test_plan_prices.py"
Cohesion: 0.16
Nodes (17): SubscriptionPlanUseCases, profile(), billing(), FakePlanRepo, test_a_customer_cannot_list_purchasable_plans(), test_a_price_must_be_above_zero(), test_a_super_admin_can_set_a_percentage_and_the_backend_calculates_the_amount(), test_a_super_admin_sets_a_price_and_the_change_is_attributed_to_them() (+9 more)

### Community 98 - "pytest"
Cohesion: 0.21
Nodes (11): validate_salon_photo_write(), visible_salon_photos(), photo(), test_cover_replacement_keeps_slide_capacity(), test_legacy_duplicate_allows_metadata_updates_and_unique_replacement(), test_legacy_excess_does_not_allow_a_role_change_that_adds_capacity(), test_legacy_third_slide_does_not_block_replacing_a_visible_slide(), test_legacy_three_slides_cannot_add_a_fourth_photo_as_cover() (+3 more)

### Community 100 - "use_cases/subscription_billing.py"
Cohesion: 0.09
Nodes (16): _body_amount(), SubscriptionBillingUseCases, BillingInterval, BillingStatus, derive_entitlement(), Entitlement, EntitlementState, EventProcessingStatus (+8 more)

### Community 101 - "SupabaseAuthGateway"
Cohesion: 0.15
Nodes (5): get_auth_gateway(), channel_field(), SupabaseAuthGateway, test_password_reset_delegates_to_supabase_never_mints_tokens(), test_phone_otp_uses_supabase_verify_and_preserves_rejection()

### Community 102 - "test_public_discovery_contract.py"
Cohesion: 0.15
Nodes (11): found(), _listed(), test_city_filter_is_exact_but_ignores_case_and_spaces(), test_filters_combine_with_and(), test_inactive_category_service_search_keeps_literal_wildcards(), test_nearby_supports_the_same_filters(), test_percent_and_underscore_in_search_are_literal(), test_search_matches_name_city_or_address_ignoring_case() (+3 more)

### Community 103 - "schemas/admin.py"
Cohesion: 0.13
Nodes (7): AdminApproveSalonRequest, CategoryCreateRequest, CategoryUpdateRequest, SubcategoryCreateRequest, SubcategoryUpdateRequest, HostedMediaRequest, ProfileResponse

### Community 104 - "test_accepting_bookings.py"
Cohesion: 0.08
Nodes (30): SalonApprovalRequiredError, SalonNotAcceptingBookingsError, business_error(), infrastructure_error(), _PgError, client(), _migration_statements(), _owner_salon() (+22 more)

### Community 105 - "math"
Cohesion: 0.17
Nodes (15): analyse(), load(), main(), _money(), NumbersError, report(), sensitivity(), _sum() (+7 more)

### Community 106 - "PaymentGatewayResolver"
Cohesion: 0.08
Nodes (15): PaymentGateway, ProviderFeeReconciler, PaymentProviderNotConfiguredError, load_adapter(), NullPaymentGateway, _adapter_module(), build_gateway(), PaymentGatewayResolver (+7 more)

### Community 107 - "config.py"
Cohesion: 0.06
Nodes (18): ProviderOrderState, ProviderPaymentState, error_code_of(), from_paise(), to_paise(), verify_order_payment_signature(), verify_webhook_signature(), create_provider() (+10 more)

### Community 108 - "MCP Server Evaluation Guide"
Cohesion: 0.09
Nodes (23): Answer Guidelines, Complexity and Depth, Core Requirements, Diversity, Evaluation Examples, Evaluation Overview, Evaluation Requirements, Good Questions (+15 more)

### Community 109 - "Python MCP Server Implementation Guide"
Cohesion: 0.09
Nodes (23): Async/Await Best Practices, Code Best Practices, Code Composability and Reusability, Complete Example, Error Handling, Key Imports, MCP Python SDK and FastMCP, Overview (+15 more)

### Community 110 - "ci_image_bundle.py"
Cohesion: 0.17
Nodes (14): archive_config(), artifact_name(), create(), download(), load(), NoRedirect, sha256(), validate() (+6 more)

### Community 111 - "AdminUseCases"
Cohesion: 0.06
Nodes (16): AdminUseCases, CatalogAdminUseCases, test_admin_list_categories_super_admin_ok(), test_admin_approval_routes_enforce_use_case_authorization(), test_admin_cannot_approve_inactive_or_incomplete_salon(), test_decisions_record_verified_admin_and_trim_reason_without_banning_owner(), test_http_returns_approval_code_for_pending_workspace(), session() (+8 more)

### Community 112 - "test_owner_finance_api.py"
Cohesion: 0.12
Nodes (50): env(), occurrence(), record(), rule(), test_a_retried_create_replays_and_a_different_body_with_the_same_key_is_refused(), test_a_retry_of_an_old_create_still_replays_after_its_start_date_left_the_window(), test_a_rule_may_start_in_the_future_or_up_to_a_month_back(), test_a_stale_phone_cannot_record_days_the_rule_does_not_allow() (+42 more)

### Community 113 - "make_super_admin"
Cohesion: 0.08
Nodes (30): make_super_admin(), test_admin_ledger_is_super_admin_only_and_has_no_personal_fields(), catalog_client(), client(), _month(), _Repo, test_only_super_admin_can_list_or_read_statements(), test_routes_are_super_admin_only() (+22 more)

### Community 114 - "test_booking_finance_sql.py"
Cohesion: 0.22
Nodes (19): Rules the build keeps, command(), finance(), outcome(), setup(), terminal(), test_admin_finance_requires_mfa_and_other_owner_cannot_read_statement(), test_checked_in_collection_capability_is_owner_scoped() (+11 more)

### Community 115 - "use_cases/wallet.py"
Cohesion: 0.07
Nodes (17): _page_size(), _payout_entry(), WalletUseCases, InsufficientBalanceError, PayoutAccountMissingError, PayoutBelowMinimumError, PayoutDayInvalidError, PayoutNotCancellableError (+9 more)

### Community 116 - "one_dict_or_none"
Cohesion: 0.05
Nodes (3): IntentMixin, RefundMixin, one_dict_or_none()

### Community 117 - "Changelog"
Cohesion: 0.10
Nodes (20): [0.1.3](https://github.com/supabase/agent-skills/compare/v0.1.2...v0.1.3) (2026-06-02), [0.1.4](https://github.com/supabase/agent-skills/compare/v0.1.3...v0.1.4) (2026-06-05), [0.1.5](https://github.com/supabase/agent-skills/compare/v0.1.4...v0.1.5) (2026-07-10), [0.1.6](https://github.com/supabase/agent-skills/compare/v0.1.5...supabase-v0.1.6) (2026-07-30), [0.1.7](https://github.com/supabase/agent-skills/compare/v0.1.6...supabase-v0.1.7) (2026-08-12), [0.1.8](https://github.com/supabase/agent-skills/compare/v0.1.7...supabase-v0.1.8) (2026-09-24), [0.1.9](https://github.com/supabase/agent-skills/compare/v0.1.8...supabase-v0.1.9) (2026-09-28), Bug Fixes (+12 more)

### Community 118 - "mumbai_browser.cjs"
Cohesion: 0.12
Nodes (12): { chromium }, fs, path, allowed, checks, {chromium}, data, errors (+4 more)

### Community 119 - "Any"
Cohesion: 0.14
Nodes (4): FakeExpoClient, FakeExpoResponse, FakeMappings, FakeResult

### Community 121 - "ImageFamilies"
Cohesion: 0.08
Nodes (12): ImageProcessor, ProcessedImageFamily, ProcessedVariant, ValidationError, family_id(), ImageFamilies, member_path(), namespace_for() (+4 more)

### Community 122 - "routes/finance.py"
Cohesion: 0.10
Nodes (41): add_adjustment(), add_expense(), add_expense_rule(), add_expenses_batch(), close_day(), daily_ledger(), expense_changes(), expense_summary() (+33 more)

### Community 123 - ".seed"
Cohesion: 0.09
Nodes (12): TestRuleCreatorErasure, adjustment(), cashbook_db(), close(), env(), expense(), refused(), TestAppendOnly (+4 more)

### Community 124 - "WalkInUseCases"
Cohesion: 0.15
Nodes (7): WalkInUseCases, OnlinePaymentUnavailableError, QrSalonMismatchError, test_booking_context_rejects_cross_salon_and_keeps_qr_source(), test_booking_context_rejects_owner_before_database_lookup(), test_get_salon_by_qr_delegates(), test_get_salon_by_qr_not_found()

### Community 125 - "test_redis_recovery_sql.py"
Cohesion: 0.10
Nodes (12): read_cache_snapshot(), save(), ask(), Gate, test_concurrent_http_booking_and_idempotent_retry_during_redis_outage(), authenticated_session(), session(), test_independent_customers_compete_for_same_slot_without_serialized_fixture() (+4 more)

### Community 126 - "Module Group 126"
Cohesion: 0.11
Nodes (19): 1.1 Understand Modern MCP Design, 1.2 Study MCP Protocol Documentation, 1.3 Study Framework Documentation, 1.4 Plan Your Implementation, 2.1 Set Up Project Structure, 2.2 Implement Core Infrastructure, 2.3 Implement Tools, 3.1 Code Quality (+11 more)

### Community 127 - "test_subscription_status_guard.py"
Cohesion: 0.20
Nodes (11): _admin(), _FakeSession, _Result, test_cancel_allowed_from(), test_cancel_from_expired_conflicts(), test_missing_subscription_is_not_found(), test_repeat_cancel_is_idempotent_and_keeps_cancelled_at(), test_repeat_suspend_is_idempotent() (+3 more)

### Community 129 - "Supabase"
Cohesion: 0.11
Nodes (15): Fix suggestion, Source, What happened, Skill Feedback, Steps, Core Principles, Debugging, Making and Committing Schema Changes (+7 more)

### Community 130 - "Admin"
Cohesion: 0.11
Nodes (19): Admin, GET `/v1/admin/catalog/categories`, GET `/v1/admin/catalog/categories/{category_id}/subcategories`, GET `/v1/admin/catalog/languages`, GET `/v1/admin/salons`, GET `/v1/admin/salons/{salon_id}`, GET `/v1/admin/salons/{salon_id}/onboarding`, PATCH `/v1/admin/catalog/categories/{category_id}` (+11 more)

### Community 131 - "round_money"
Cohesion: 0.20
Nodes (10): 1. Start of every chat, 2. How a senior works, 3. When there is an error or failing test, 4. When improving or reviewing code, 5. Safe cleanup rules, 6. Database and money, 7. Security non-negotiables, 8. Definition of done (+2 more)

### Community 132 - "docs/README.md"
Cohesion: 0.12
Nodes (13): Checkout Safety and Verification Evidence, Folder structure, Account deletion contract (customer app, owner app, website), Frontend integration, Git workflow, Project overview, Project documentation, Technology stack (+5 more)

### Community 133 - "test_image_families.py"
Cohesion: 0.11
Nodes (31): age_objects(), api_client(), erasure_service(), gateway(), key(), references(), test_any_reference_protects_entire_family(), test_avatar_database_rollback_preserves_prior_reference_and_does_not_delete() (+23 more)

### Community 135 - "test_media_integration.py"
Cohesion: 0.08
Nodes (17): ReportRequest, ReportResponse, submit_report(), AvatarRepository, UploadAvatar, ReportRepository, SubmitReport, client_for() (+9 more)

### Community 136 - "test_migration_tool_paths.py"
Cohesion: 0.13
Nodes (5): offline_tools(), test_offline_bundle_matches_sealed_files(), test_revision_review_preserves_sealed_evidence(), test_runner_imports_without_network_or_credentials(), Gotchas

### Community 137 - "test_public_salon_visibility.py"
Cohesion: 0.21
Nodes (6): test_cached_walkin_requires_current_database_qr_validation(), test_detail_visibility_on_miss_and_stale_cache(), test_hidden_public_catalog_miss_stops_before_catalog_read(), test_list_sources_only_return_approved_active_complete(), test_public_catalog_miss_avoids_unused_photo_query(), test_revocation_blocks_existing_and_late_cache_fills()

### Community 138 - "chief-of-staff.md"
Cohesion: 0.12
Nodes (16): 1. skip (auto-archive), 2. info_only (summary only), 3. meeting_info (calendar cross-reference), 4. action_required (draft reply), 4-Tier Classification System, Briefing Output Format, Example Invocations, Key Design Principles (+8 more)

### Community 139 - "Changelog"
Cohesion: 0.12
Nodes (16): [1.2.0](https://github.com/supabase/agent-skills/compare/v1.1.1...v1.2.0) (2026-06-02), [1.3.0](https://github.com/supabase/agent-skills/compare/v1.2.0...v1.3.0) (2026-06-05), [1.4.0](https://github.com/supabase/agent-skills/compare/v1.3.0...v1.4.0) (2026-07-10), [1.5.0](https://github.com/supabase/agent-skills/compare/supabase-postgres-best-practices-v1.4.0...supabase-postgres-best-practices-v1.5.0) (2026-07-30), [1.6.0](https://github.com/supabase/agent-skills/compare/supabase-postgres-best-practices-v1.5.0...supabase-postgres-best-practices-v1.6.0) (2026-07-30), Bug Fixes, Bug Fixes, Bug Fixes (+8 more)

### Community 140 - "routes/auth.py"
Cohesion: 0.16
Nodes (3): AuthTokens, RefreshInput, Refresh

### Community 141 - "FinanceUseCases"
Cohesion: 0.09
Nodes (12): ExpenseRuleUseCases, FinanceUseCases, _paise(), fingerprint_of(), release_reservation(), require_idempotency_key(), DayInFutureError, DifferenceReasonRequiredError (+4 more)

### Community 142 - "routes/walkin.py"
Cohesion: 0.03
Nodes (37): get_payment_gateway(), create_walkin_booking(), get_qr_image(), resolve_qr(), _use_cases(), verify_phone(), _id_to_str(), _uuid_to_str() (+29 more)

### Community 143 - "test_mumbai_forward_reconciliation.py"
Cohesion: 0.13
Nodes (9): canonical_sha256(), main(), normalized(), RecordingSession, test_both_columns_are_classified_as_scrubbed(), test_customer_clear_happens_before_profile_reference_detachment(), test_forward_chain_and_non_destructive_downgrade(), test_schema_adoption_preserves_both_values_and_rejects_definition_drift() (+1 more)

### Community 145 - "Running Evaluations"
Cohesion: 0.12
Nodes (15): 1. Local STDIO Server, 2. Server-Sent Events (SSE), 3. HTTP (Streamable HTTP), Command-Line Options, Complete Example Workflow, Connection Errors, Evaluation File Format, Low Accuracy (+7 more)

### Community 146 - "Writing Guidelines for Postgres References"
Cohesion: 0.12
Nodes (15): 1. Concrete Transformation Patterns, 2. Error-First Structure, 3. Quantified Impact, 4. Self-Contained Examples, 5. Semantic Naming, Code Example Standards, Comments, Impact Level Guidelines (+7 more)

### Community 147 - "Customer App Backend API Contract"
Cohesion: 0.12
Nodes (16): Account deletion and closed salons, Audit result, Authentication, Availability, Avatar upload, Booking action requests, Booking list filters, Bulk notification read (+8 more)

### Community 148 - "exceptions.py"
Cohesion: 0.03
Nodes (22): CreatedAuthUser, app_error_response(), AppError, BookingIdempotencyKeyReusedError, BookingWindowExceededError, IdempotencyKeyRequiredError, PayloadTooLargeError, app_error_handler() (+14 more)

### Community 150 - "salon-backend"
Cohesion: 0.13
Nodes (14): Agents (`.claude/agents/`), Commands (run from `backend/`), Core backend agents, Founder skills (feature building and planning), graphify, Key rules, Layer map, Maintenance agents (+6 more)

### Community 151 - "Super-admin to owner review thread (spec; design, not built)"
Cohesion: 0.15
Nodes (15): resolved(), API (explicit `response_model`, status codes and `UUID` IDs), Authorization, Client impact (for the update lists), Data model (proposal), Decisions (from the interview), Erasure, Live status (+7 more)

### Community 152 - "Role"
Cohesion: 0.05
Nodes (45): require_role(), dependency(), BookingActionRequestUseCases, ClosureUseCases, paging_kwargs(), AdminMFARequiredError, ForbiddenError, Role (+37 more)

### Community 153 - "Progress: shifan"
Cohesion: 0.13
Nodes (15): 2026-10-24 continuation: lint/offline/live booking and fresh vendor check, 2026-10-31 — Gate B full-data rehearsal + owner production release authorization, Cashfree verification continuation — 29 October 2026, Decisions, Files touched, Goal, In progress, Latest scoped subscription release — 28 October 2026 (+7 more)

### Community 154 - "RazorpayGateway"
Cohesion: 0.09
Nodes (8): SettlementAccount, SettlementAccountRequest, PaymentCapabilityError, dumps_json(), _prepare(), create_gateway(), RazorpayGateway, test_razorpay_booking_adapter_still_works_alongside()

### Community 155 - "Review Priorities"
Cohesion: 0.14
Nodes (13): Approval Criteria, CRITICAL — Error Handling, CRITICAL — Security, Diagnostic Commands, Framework Checks, HIGH — Code Quality, HIGH — Concurrency, HIGH — Pythonic Patterns (+5 more)

### Community 156 - "tdd-guide.md"
Cohesion: 0.14
Nodes (13): 1. Write Test First (RED), 2. Run Test -- Verify it FAILS, 3. Write Minimal Implementation (GREEN), 4. Run Test -- Verify it PASSES, 5. Refactor (IMPROVE), 6. Verify Coverage, Edge Cases You MUST Test, Quality Checklist (+5 more)

### Community 157 - "Rams Design Review"
Cohesion: 0.14
Nodes (13): 1. Accessibility Review (WCAG 2.1), 2. Visual Design Review, Color & Contrast, Components, Critical (Must Fix), Guidelines, Layout & Spacing, Mode (+5 more)

### Community 158 - "van_westendorp.py"
Cohesion: 0.15
Nodes (11): build(), write(), validate(), analyse(), cross(), curves(), _f(), main() (+3 more)

### Community 159 - "Salon Owner App Backend API Contract"
Cohesion: 0.15
Nodes (13): Account deletion (owner), Audit result, Authentication, Closures and blocked time, Endpoint summary, Images, services, and staff, Media upload flow, Notifications, devices, and catalog (+5 more)

### Community 160 - "NotificationUseCases"
Cohesion: 0.12
Nodes (7): NotificationUseCases, test_notification_use_case_forwards_only_paging_the_caller_set(), test_deactivate_device_delegates_with_actor_id(), test_list_notifications_delegates(), test_mark_all_read_returns_updated_count(), test_mark_read_delegates(), test_register_device_passes_actor_id()

### Community 161 - "Progress: thameem/cloud-run-startup-investigation"
Cohesion: 0.15
Nodes (12): test_mumbai_validation_workflow_is_manual_and_has_no_scratch_service(), Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps (+4 more)

### Community 163 - "Mumbai staging readiness review — 2026-10-16"
Cohesion: 0.25
Nodes (8): CI Migration Policy Verification 2026-10-16, CI Password Regression 2026-10-14, Mumbai Cloud Run Staging Deployment 2026-10-16, Local Mumbai Database Health Recovery 2026-10-16, Mumbai Execution Preflight and Hold 2026-10-15, Final Mumbai Local Staging Acceptance 2026-10-15, Redis Recovery Verification 2026-10-16, Mumbai staging readiness review — 2026-10-16

### Community 164 - "Build Error Resolver"
Cohesion: 0.15
Nodes (12): 1. Collect All Errors, 2. Fix Strategy (MINIMAL CHANGES), 3. Common Fixes, Build Error Resolver, Core Responsibilities, Diagnostic Commands, DO and DON'T, Priority Levels (+4 more)

### Community 165 - "Documentation & Codemap Specialist"
Cohesion: 0.15
Nodes (12): 1. Analyze Repository, 2. Analyze Modules, 3. Generate Codemaps, 4. Codemap Format, Analysis Commands, Codemap Workflow, Core Responsibilities, Documentation & Codemap Specialist (+4 more)

### Community 166 - "E2E Test Runner"
Cohesion: 0.15
Nodes (12): 1. Plan, 2. Create, 3. Execute, Core Responsibilities, E2E Test Runner, Fallback: Playwright, Flaky Test Handling, Key Principles (+4 more)

### Community 167 - "planner.md"
Cohesion: 0.15
Nodes (12): 1. Requirements Analysis, 2. Architecture Review, 3. Step Breakdown, 4. Implementation Order, Best Practices, Plan Format, Planning Process, Red Flags to Check (+4 more)

### Community 168 - "Refactor & Dead Code Cleaner"
Cohesion: 0.15
Nodes (12): 1. Analyze, 2. Verify, 3. Remove Safely, 4. Consolidate Duplicates, Core Responsibilities, Detection Commands, Key Principles, Refactor & Dead Code Cleaner (+4 more)

### Community 169 - "Complete backend API reference for frontend teams"
Cohesion: 0.10
Nodes (20): Access and availability notes, Booking Actions, Complete backend API reference for frontend teams, Customer, Errors and schema limitations, GET `/v1/booking-action-requests`, GET `/v1/customer/profile`, How to use this reference (+12 more)

### Community 170 - "Agent Instructions"
Cohesion: 0.15
Nodes (12): Agent Instructions, Auth Rules, Backend Architecture Rules, Code Ownership, Database And Booking Rules, Dependency And Setup Files, Deployment Rules, Secrets And Environment (+4 more)

### Community 171 - "ProfileUpdateRequest"
Cohesion: 0.20
Nodes (10): ProfileUpdateRequest, test_existing_hosted_media_urls_and_clearing_remain_supported(), test_profile_name_cannot_be_cleared(), test_profile_name_is_trimmed_and_omitted_fields_stay_omitted(), test_profile_update_accepts_plus_91_storage_format(), test_profile_update_allows_repeated_digits_inside_valid_mobile(), test_profile_update_normalizes_indian_mobile(), test_profile_update_preserves_bundled_avatar_references() (+2 more)

### Community 172 - "Module Group 172"
Cohesion: 0.40
Nodes (6): For Customers / For Salons Dual Audience Section, Footer – Making every appointment a little simpler, Our Founders Section – Ziyarad Huq CEO, Shifan NV CPO, Shoiball CMO, Hero Section – Becoming your best aesthetic, Salon BRQ Marketing Landing Page, QR Code Scan-to-Book Customer Flow

### Community 173 - "test_migration_policy.py"
Cohesion: 0.09
Nodes (26): validate_migration_target(), validate_stamp_evidence(), _make_stamp_manifest(), test_0049_stamp_is_in_allowed_revisions(), test_approved_prices_differ_from_0049_sql_targets(), test_historical_migration_py_files_exist_and_have_stable_hashes(), test_mumbai_offline_sql_requires_reviewed_start(), test_mumbai_rejects_scratch_sydney_and_wrong_project() (+18 more)

### Community 174 - "test_build_identity.py"
Cohesion: 0.07
Nodes (18): database_health(), health(), readiness(), redis_health(), version(), DatabaseHealthResponse, HealthResponse, RedisHealthResponse (+10 more)

### Community 176 - "test_expo_push_includes_notification_payload"
Cohesion: 0.17
Nodes (4): FakeSession, test_expo_push_includes_notification_payload(), test_raw_fcm_receives_notification_payload_when_configured(), test_raw_fcm_without_credentials_records_failed_delivery()

### Community 177 - "Database Reviewer"
Cohesion: 0.17
Nodes (11): 1. Query Performance (CRITICAL), 2. Schema Design (HIGH), 3. Security (CRITICAL), Anti-Patterns to Flag, Core Responsibilities, Database Reviewer, Diagnostic Commands, Key Principles (+3 more)

### Community 178 - "mcp-builder/SKILL.md"
Cohesion: 0.17
Nodes (8): Core MCP Documentation (Load First), 📚 Documentation Library, Evaluation Guide (Load During Phase 4), Language-Specific Implementation Guides (Load During Phase 2), MCP Server Development Guide, Overview, Reference Files, SDK Documentation (Load During Phase 1/2)

### Community 179 - "Progress: thameem/mumbai-forward-reconciliation"
Cohesion: 0.18
Nodes (11): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: thameem/mumbai-forward-reconciliation (+3 more)

### Community 180 - "Progress: {branch}"
Cohesion: 0.17
Nodes (11): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: {branch} (+3 more)

### Community 181 - "Progress: thameem/cloud-run-mumbai-staging"
Cohesion: 0.17
Nodes (11): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: thameem/cloud-run-mumbai-staging (+3 more)

### Community 182 - "Progress: thameem/local-docker-cold-start"
Cohesion: 0.17
Nodes (11): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: thameem/local-docker-cold-start (+3 more)

### Community 183 - "Progress: thameem/provider-agnostic-payments"
Cohesion: 0.17
Nodes (11): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: thameem/provider-agnostic-payments (+3 more)

### Community 184 - "Progress: thameem/u08-verification-continuation"
Cohesion: 0.17
Nodes (11): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: thameem/u08-verification-continuation (+3 more)

### Community 185 - "test_salon_trials.py"
Cohesion: 0.09
Nodes (15): update_salon_trial(), SalonTrialResponse, TrialLimitsRequest, TrialUpdateRequest, SalonTrialUseCases, TrialRepository, require_super_admin(), test_empty_approval_body_retains_the_current_default_trial() (+7 more)

### Community 186 - "How to use the prompts"
Cohesion: 0.17
Nodes (11): Configuration: what belongs where, Critique and corrected product workflow, Frontend integration prompt pack, How to use the prompts, Model assignments and cost discipline, Prompt 0 — Backend readiness and corrected contract, Prompt 1 — Customer app, Prompt 2 — Owner app (+3 more)

### Community 187 - "test_cloud_run_auto.py"
Cohesion: 0.09
Nodes (19): require_verified_tls(), auto(), context(), health(), rollout(), patch(), state(), test_auto_refuses_unapproved_context() (+11 more)

### Community 188 - "_RequestMixin"
Cohesion: 0.15
Nodes (3): decode_json(), _RequestMixin, test_decode_json_handles_text_and_python_values()

### Community 189 - "test_release_configuration.py"
Cohesion: 0.10
Nodes (19): eligible(), forbidden(), modules(), saved_bundle(), test_actual_deploy_job_skips_when_authoritative_gate_is_false(), test_all_workflows_parse_and_actions_are_immutable(), test_artifact_substitution_is_rejected(), test_automatic_candidate_requires_tested_artifact_before_any_cloud_access() (+11 more)

### Community 190 - "routes/wallet.py"
Cohesion: 0.17
Nodes (19): _admin_use_cases(), cancel_payout(), list_payout_requests(), mark_payout_paid(), _owner_use_cases(), reject_payout(), request_payout(), wallet() (+11 more)

### Community 192 - "Pass 2 — Clean Architecture & Standards"
Cohesion: 0.20
Nodes (9): 1. Baseline before touching anything, 2. Review in three passes, 3. Apply or report, 4. Refactor one increment at a time, 5. Verify, then report, Pass 1 — Security, Pass 3 — Folder Structure, Salon Backend Code Refactorer (+1 more)

### Community 193 - "redis_recovery_browser.cjs"
Cohesion: 0.40
Nodes (3): {chromium}, readline, target

### Community 195 - "test_cloud_run_candidate.py"
Cohesion: 0.10
Nodes (16): attestation(), bootstrapped(), contract(), guarded(), test_attestation_target_and_paths_validated(), test_bootstrap_rejects_drift(), test_bootstrap_wrong_context_refused(), test_contract_additions_preserve_existing_routes_and_fields() (+8 more)

### Community 196 - "test_payment_ledger_sql.py"
Cohesion: 0.08
Nodes (30): changes_db(), env(), erase(), prepared_db(), seed_cash_book(), snapshot(), test_erasing_a_customer_leaves_the_cash_book_and_other_salons_alone(), test_owner_erasure_clears_free_text_and_keeps_every_money_record() (+22 more)

### Community 197 - "WalletRepository"
Cohesion: 0.12
Nodes (4): decode_cursor(), encode_cursor(), _row(), WalletRepository

### Community 198 - "cache_recovery_worker.py"
Cohesion: 0.11
Nodes (9): validated_cache_reads(), main(), test_disconnected_reader_recovers_before_serving_payload(), test_late_cache_fill_cannot_enter_new_epoch(), test_overlapping_request_contexts_do_not_share_cache_fill_versions(), request(), test_unvalidated_or_failed_database_read_never_uses_cached_payload(), build() (+1 more)

### Community 199 - "founder-board"
Cohesion: 0.20
Nodes (9): founder-board, Output, Rules, Step 0: the idea file, Step 1: brief the board, Step 2: convene, Step 3: the chair's summary, The rule about the three names (+1 more)

### Community 201 - "founder-ops"
Cohesion: 0.20
Nodes (9): founder-ops, Output, Step 1: what the business has to do every day, Step 2: suppliers, Step 3: people, Step 4: routines (SOPs), Step 5: tools, Step 6: licences, permits and insurance (+1 more)

### Community 202 - "Karpathy Guidelines"
Cohesion: 0.20
Nodes (9): 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution, 5. Don't Hide Confusion, 6. Question Assumptions, 7. Define Tests Upfront, 8. When in Doubt, Simplify (+1 more)

### Community 203 - "Section Definitions"
Cohesion: 0.20
Nodes (9): 1. Query Performance (query), 2. Connection Management (conn), 3. Security & RLS (security), 4. Schema Design (schema), 5. Concurrency & Locking (lock), 6. Data Access Patterns (data), 7. Monitoring & Diagnostics (monitor), 8. Advanced Features (advanced) (+1 more)

### Community 204 - "Subscriptions"
Cohesion: 0.20
Nodes (10): GET `/v1/admin/salons/{salon_id}/subscription`, GET `/v1/admin/subscription-events`, GET `/v1/admin/subscription-plans`, PATCH `/v1/admin/subscription-plans/{plan_id}`, POST `/v1/admin/salons/{salon_id}/subscription/test`, POST `/v1/admin/subscription-plans`, POST `/v1/admin/subscription-plans/{plan_id}/deactivate`, POST `/v1/admin/subscriptions/{subscription_id}/cancel` (+2 more)

### Community 205 - ".get_salon_by_qr"
Cohesion: 0.14
Nodes (10): 7. Destructive changes, incompatible signatures, and transformations requiring dedicated verification, 9. Client compatibility summary, Column drops (irreversible data loss if column had values), Data transformations (one-time, irreversible), Function signature changes (call-site incompatibility), Trigger replacements, 0041 locking risk, 0052 client compatibility risk (+2 more)

### Community 206 - "test_checkout_safety_sql.py"
Cohesion: 0.11
Nodes (22): set_actor_context(), _install_booking_window(), safety_db(), test_api_quote_auth_ownership_support_idempotency_and_safe_disabled_config(), actor(), session(), test_backend_only_tables_and_booking_function_are_not_data_api_writable(), test_booking_same_key_replays_and_different_payload_rejects() (+14 more)

### Community 208 - "main.py"
Cohesion: 0.10
Nodes (10): init_sentry(), TimingMiddleware, create_app(), _init_cache(), lifespan(), _prefetch_env_file(), _warm_database(), test_lifespan_warms_database_and_cache_concurrently() (+2 more)

### Community 210 - "test_sql_bind_params.py"
Cohesion: 0.20
Nodes (5): _sql_string_literals(), test_no_bind_param_is_immediately_followed_by_a_pg_cast(), test_no_bind_param_null_check_is_untyped(), test_reference_cast_function_form_compiles_correctly(), test_reference_repro_of_the_broken_pattern()

### Community 211 - "source"
Cohesion: 0.33
Nodes (5): source(), AccessStateResponse, BookingCreateRequest, BookingResponse, GET `/v1/bookings`

### Community 212 - "Gate A — Isolated Full-Data Restore Evidence"
Cohesion: 0.07
Nodes (26): 0051 (owner_finance_cashbook), 0052 (booking_window_30_days), alembic current after each migration step, Backend test suite, Backup integrity (pre-restore), Destructive DDL confirmation, Gate A — Isolated Full-Data Restore Evidence, Gate B sequence executed on full-data Docker DB (+18 more)

### Community 213 - "booking_payments as Ledger Source of Truth"
Cohesion: 0.22
Nodes (5): Payment Authorization Rules, Booking Lifecycle (pending/confirmed/completed/rejected/cancelled), Pausing New Bookings (accepting_bookings flag), Postgres Booking Functions (create_booking / get_available_slots), Overcollection Handling (recorded loudly, payment_anomalies)

### Community 215 - "founder-consumer"
Cohesion: 0.20
Nodes (9): founder-consumer, Honest limits, say them once, Output, Step 1: the target customer, Step 2: the pitch, Step 3: deal and run, Step 4: read it to the user, The brief every buyer gets (+1 more)

### Community 216 - "test_account_deletion_migration.py"
Cohesion: 0.50
Nodes (7): load(), run(), test_audit_trigger_escape_hatch_and_erasure_helper(), test_downgrade_restores_baseline_audit_trigger_and_drops_everything(), test_revision_chain_is_linear_after_media_guards(), test_upgrade_creates_bound_challenges_and_a_pii_free_ledger(), test_upgrade_relaxes_only_the_not_null_columns_erasure_must_clear()

### Community 217 - "Codex prompt: deploy migration 0049 and the subscription backend to GCP"
Cohesion: 0.20
Nodes (9): Codex prompt: deploy migration 0049 and the subscription backend to GCP, Hard rules, Report back, Step 1 — Find out which database each environment uses, Step 2 — Pre-flight checks on the target database (read-only), Step 3 — Back up, then apply 0049 (staging target first), Step 4 — Staging deploy (`salon-api-mumbai-staging`, project `saloon-505509`, region `asia-south1`), Step 5 — Production (`salon-api-production`), only after my approval (+1 more)

### Community 219 - "founder-marketing"
Cohesion: 0.22
Nodes (8): founder-marketing, Output, Rules, Step 1: read the evidence, Step 2: positioning, Step 3: channels, Step 4: the 30-day campaign, Step 5: budget and numbers

### Community 220 - "founder-offer"
Cohesion: 0.22
Nodes (8): founder-offer, Output, Rules, Step 1: read what is already known, Step 2: the problem list, Step 3: solutions, trimmed and stacked, Step 4: score it, Step 5: re-test it

### Community 222 - "Isolated Restore Evidence Template"
Cohesion: 0.08
Nodes (25): 1. Download a fresh Supabase backup, 2. Start a local Docker PostgreSQL, 3. Restore the backup into Docker, 4. Set harness environment variables, 5. Run harness phases in sequence, alembic current after each migration step, Destructive DDL reminder, For 0040_fastapi_only_access (+17 more)

### Community 226 - "Production Alembic baseline/bridge strategy — architecture review"
Cohesion: 0.09
Nodes (22): validate_evidence(), 10. Items requiring owner review before any bridge implementation begins, 1. Can Alembic safely begin at 0041 with no trustworthy baseline revision?, 2. Is changing historical migration files safe?, 3. Comparison of reconciliation approaches, 4. Recommended approach: A, with explicit stamp paradox resolution, 5. Truthfulness: how the bridge records production state without false claims, 6. How future upgrades reach 0051 and 0052 safely (+14 more)

### Community 227 - "io"
Cohesion: 0.13
Nodes (8): _build_walkin_url(), make_qr_png(), make_qr_svg(), test_encrypted_pipeline_only_records_complete_exports(), test_unsafe_source_cannot_start_any_export(), test_build_walkin_url_appends_token_to_route_prefix(), test_different_salon_tokens_produce_different_qr_images(), test_qr_render_is_deterministic_for_permanent_salon_identity()

### Community 228 - "Agent memory"
Cohesion: 0.25
Nodes (7): Agent memory, Layout, Privacy, Progress file sections, Promote progress -> shared, SESSIONS.md row, Writing rules

### Community 229 - "Booking and payments"
Cohesion: 0.25
Nodes (7): Booking and payments, Conflicts, Dormant, Hard rules, Payments, Status flow, Tests

### Community 230 - "founder-brand"
Cohesion: 0.25
Nodes (7): founder-brand, Output, Rules, Step 1: read the brief, Step 2: name candidates, Step 3: voice and promise, Step 4: the look, as a brief

### Community 231 - "founder-competitors"
Cohesion: 0.25
Nodes (7): founder-competitors, Output, Step 1: who is there, Step 2: the facts, Step 3: what their customers say, Step 4: the map and the gap, The rules

### Community 232 - "founder-plan"
Cohesion: 0.25
Nodes (7): founder-plan, Output, Rules, Step 1: see what is there, Step 2: the summary, Step 3: compile, Step 4: the one-pager

### Community 233 - "founder-pricing"
Cohesion: 0.25
Nodes (7): founder-pricing, Output, Rules, Step 1: what buyers said, Step 2: what competitors charge, Step 3: what the business needs, Step 4: decide

### Community 234 - "Quality Checklist"
Cohesion: 0.25
Nodes (8): Advanced Features (where applicable), Code Quality, Implementation Quality, Project Configuration, Quality Checklist, Strategic Design, Testing and Build, TypeScript Quality

### Community 235 - "Web Application Testing"
Cohesion: 0.25
Nodes (7): Best Practices, Common Pitfall, Decision Tree: Choosing Your Approach, Example: Using with_server.py, Reconnaissance-Then-Action Pattern, Reference Files, Web Application Testing

### Community 236 - "Gate A — Isolated Restore Evidence"
Cohesion: 0.08
Nodes (23): 0051 (owner_finance_cashbook), 0052 (booking_window_30_days), alembic current after each migration step, Backend test suite (step 11), Destructive DDL confirmation, Gate A — Isolated Restore Evidence, Gate B sequence executed on Docker DB, Gate C assessment (step 13) (+15 more)

### Community 237 - "get_my_profile"
Cohesion: 0.29
Nodes (5): get_my_profile(), GET `/v1/profiles/me`, PATCH `/v1/profiles/me`, POST `/v1/profiles/me/avatar-upload-url`, Profiles

### Community 238 - "Image integration review — 2026-10-10"
Cohesion: 0.29
Nodes (6): Actual verification results, Confirmed findings and fixes, Deployment requirements and remaining limits, Files changed by this task, Image integration review — 2026-10-10, Upload-path matrix

### Community 239 - "0029_payment_monetary_policy.py"
Cohesion: 0.38
Nodes (3): downgrade(), _sql(), upgrade()

### Community 240 - "0030_subscription_billing.py"
Cohesion: 0.43
Nodes (4): downgrade(), _sql(), upgrade(), _validate()

### Community 241 - "0033_payment_fee_snapshot.py"
Cohesion: 0.38
Nodes (3): downgrade(), _sql(), upgrade()

### Community 242 - "test_booking_finance_policy.py"
Cohesion: 0.17
Nodes (18): cancellation_quote(), validate_customer_change(), test_actual_provider_cost_never_reduces_promised_refund(), test_aware_appointment_instants_are_required(), test_cancellation_exact_boundaries(), test_change_blocks_at_exactly_four_hours_and_later(), test_change_is_permitted_only_above_four_hours(), test_cutoffs_use_elapsed_time_across_daylight_saving_change() (+10 more)

### Community 243 - "founder-cfo"
Cohesion: 0.29
Nodes (6): founder-cfo, Output, Rules, Step 1: gather the inputs, Step 2: run it, Step 3: the CFO's note

### Community 244 - "founder-launch"
Cohesion: 0.29
Nodes (6): founder-launch, Output, Step 1: test before you spend, Step 2: the countdown, Step 3: launch day, Step 4: the first 30 days

### Community 245 - "Knex Migration Drift"
Cohesion: 0.29
Nodes (6): Diagnostic steps, Fix, Knex Migration Drift, Related anti-patterns to flag in review, Root cause to suspect, When this pattern applies

### Community 246 - "Quality Checklist"
Cohesion: 0.29
Nodes (7): Advanced Features (where applicable), Code Quality, Implementation Quality, Quality Checklist, Strategic Design, Testing, Tool Configuration

### Community 247 - "Testing"
Cohesion: 0.29
Nodes (6): Before finishing, Booking concurrency test, Real DB vs fakes, Role matrix, Rules, Testing

### Community 248 - "Workers and deploy"
Cohesion: 0.29
Nodes (6): Checks, Compose services, Deploy flow, Health, Worker rules, Workers and deploy

### Community 249 - "evaluation.py"
Cohesion: 0.16
Nodes (8): agent_loop(), evaluate_single_task(), extract_xml_content(), main(), parse_env_vars(), parse_evaluation_file(), parse_headers(), run_evaluation()

### Community 250 - "service"
Cohesion: 0.14
Nodes (17): service(), test_image_only_update_preserves_runtime(), Blockers and open questions, GET `/v1/salons`, GET `/v1/salons/nearby`, GET `/v1/salons/{salon_id}`, GET `/v1/salons/{salon_id}/services`, GET `/v1/salons/{salon_id}/staff` (+9 more)

### Community 251 - "OutboundMessage"
Cohesion: 0.17
Nodes (6): MessagingGateway, OutboundMessage, SendOutcome, FakeMessagingGateway, NoneMessagingGateway, TestFakeGateway

### Community 252 - "TrialLimits"
Cohesion: 0.20
Nodes (11): TrialLimits, SalonTrialRepository, env(), pending(), test_approval_grants_exact_limits_atomically_and_retry_preserves_usage(), test_expiring_trial_does_not_change_paid_subscription_or_access(), test_failed_initial_trial_update_rolls_back_the_approval(), fail() (+3 more)

### Community 253 - "Operational Runbook (local setup, super-admin, workers)"
Cohesion: 0.12
Nodes (15): GitHub Actions CI/CD Pipeline (test/build/deploy to GCP VM), Automatic production releases after main CI, Behavior, Exact IAM trust proposal — not yet applied, One-time prerequisites — activation is still pending, Approved GitHub Free OIDC configuration, Subsequent automatic-release proposal ? not applied, Finance 0051 review input (+7 more)

### Community 255 - "0049 Subscription price reconciliation"
Cohesion: 0.09
Nodes (21): 0049 Subscription price reconciliation, 1. Summary finding, 2. All sources of evidence, with exact prices, 2a. Migration 0031 — seed (INSERT baseline), 2b. Migration 0049 — original commit (2026-10-27 initial), 2c. Migration 0049 — revised commit (2026-10-27 same day, 6ff578f), 2d. SUBSCRIPTION_0049_STAGING_2026-10-27.md — postflight after 0049 direct SQL apply, 2e. subscription-percentage-release-2026-10-28.md — Oct 28 offer feature release (+13 more)

### Community 256 - "Frontend Integration Prompt — Redis Feature Changes"
Cohesion: 0.33
Nodes (5): Error Envelope Reference, Frontend Integration Prompt — Redis Feature Changes, Prompt — Customer App, Prompt — Owner App, UUID Generation — Language Quick Reference

### Community 258 - "Alembic bridge graph validation"
Cohesion: 0.09
Nodes (21): 0049 — `CREATE TABLE salon_plan_prices`, 0050 — `ADD COLUMN IF NOT EXISTS valid_until`, 1. Does 0053 → 0054 replay 0041–0052?, 2. Is the proposed bridge safe or unsafe?, 3. Recommended migration-history reconciliation path, 4. Exact conditions required before a baseline stamp, 5. How 0049/0050 can be truthfully reconciled, 6. Required restore tests before 0051 (+13 more)

### Community 259 - "Subscription 0049: applied database change and staging release"
Cohesion: 0.33
Nodes (5): Authorization and recovery, Database result, Staging image and runtime, Subscription 0049: applied database change and staging release, Verification

### Community 262 - "0022_salon_accepting_bookings.py"
Cohesion: 0.47
Nodes (3): downgrade(), _replace_functions(), upgrade()

### Community 263 - "0026_booking_payments.py"
Cohesion: 0.47
Nodes (3): downgrade(), _sql(), upgrade()

### Community 264 - "0027_payout_account_audit.py"
Cohesion: 0.47
Nodes (3): downgrade(), _sql(), upgrade()

### Community 265 - "Evaluation Process"
Cohesion: 0.33
Nodes (6): Evaluation Process, Step 1: Documentation Inspection, Step 2: Tool Inspection, Step 3: Developing Understanding, Step 4: Read-Only Content Inspection, Step 5: Task Generation

### Community 266 - "Advanced MCP Features"
Cohesion: 0.33
Nodes (6): Advanced MCP Features, Notification Support, Resource Registration, stdio (For Local Integrations), Streamable HTTP (Recommended for Remote Servers), Transport Options

### Community 267 - "Advanced FastMCP Features"
Cohesion: 0.33
Nodes (6): Advanced FastMCP Features, Context Parameter Injection, Lifespan Management, Resource Registration, Structured Output Types, Transport Options

### Community 273 - "Supabase Postgres Best Practices"
Cohesion: 0.33
Nodes (5): How to Use, References, Rule Categories by Priority, Supabase Postgres Best Practices, When to Apply

### Community 274 - "test_wif_claim_preflight.py"
Cohesion: 0.09
Nodes (19): qr_client(), validate_context(), preflight(), test_changed_trust_claim_fails_closed(), test_invalid_token_fails_closed(), test_jwt_decoder_never_logs_token(), token(), DELETE `/v1/devices/{token}` (+11 more)

### Community 275 - "Shared production API domain migration — 27 October 2026"
Cohesion: 0.29
Nodes (6): Architecture and cost boundary, Configuration, Cutover status, Resources and rollback, Shared production API domain migration — 27 October 2026, Verification so far

### Community 277 - ".throttle"
Cohesion: 0.40
Nodes (3): Checklist, Output, Security reviewer (read-only)

### Community 278 - "Mumbai staging readiness audit — 2026-10-15"
Cohesion: 0.17
Nodes (9): 1. `supabase-schema-backup/` in Git, 3. Evidence note, Migration cleanup plan and execution record, Authorized Local Cleanup 2026-10-15, Mumbai staging readiness audit — 2026-10-15, Mumbai destination migration progress — 2026-10-15, Mumbai runtime validation — 2026-10-15, All 37 revisions — final-state review — 2026-10-15 (+1 more)

### Community 287 - "0011_holiday_soft_delete.py"
Cohesion: 0.60
Nodes (3): downgrade(), _replace_database_functions(), upgrade()

### Community 291 - "6. Required backup and restore execution plan"
Cohesion: 0.10
Nodes (20): 1. Alembic version table, 2. Production table inventory (baseline vs. post-0040), 4. Exact reconciliation table (migration scope decision matrix), 5. Identified conflicts requiring manual resolution before ANY migration run, 6. Required backup and restore execution plan, 7. Discovery limitations and outstanding items, C1 — 0041 drops `salons.description` but 0045 is already applied, C2 — 0045 breaks the Alembic chain (+12 more)

### Community 293 - "agent-sdk-verifier-py.md"
Cohesion: 0.40
Nodes (4): Verification Focus, Verification Process, Verification Report Format, What NOT to Focus On

### Community 294 - "harness-optimizer.md"
Cohesion: 0.40
Nodes (4): Constraints, Mission, Output, Workflow

### Community 295 - "loop-operator.md"
Cohesion: 0.40
Nodes (4): Escalation, Mission, Required Checks, Workflow

### Community 296 - "The three lenses"
Cohesion: 0.40
Nodes (4): The Monopoly lens, The Offers lens, The Product lens, The three lenses

### Community 297 - "Cashfree subscription checkout"
Cohesion: 0.40
Nodes (4): Acceptance and recovery, Cashfree subscription checkout, Configuration after the merchant account is ready, Owner journey

### Community 298 - "Roadmap"
Cohesion: 0.40
Nodes (4): Built, Dormant, Not built, Roadmap

### Community 301 - "Adding an endpoint"
Cohesion: 0.40
Nodes (4): Adding an endpoint, Anti-patterns, Checklist, Recipe

### Community 302 - "Owner payout accounts and setup checklist"
Cohesion: 0.67
Nodes (3): Audit trail (migration `0027_payout_account_audit`), Owner payout accounts and setup checklist, Status

### Community 303 - "0015_salon_admin_approval.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_functions(), upgrade()

### Community 304 - "Production migration reconciliation — correction and safe path"
Cohesion: 0.10
Nodes (20): Approach A — New bridge migration (e.g., `0053_production_reconciliation_bridge`), Approach B — Idempotent forward repair (RECOMMENDED), Approach C — Compatibility release (hide endpoints until schema is ready), Approach D — Verified direct SQL with sequential Alembic stamps, Boundary 0: App-only release — NOT POSSIBLE, Boundary 1: Minimum schema release for core booking (0041–0045), Boundary 2: Schema compatibility release for erasure workers (add 0046, 0047, 0048), Boundary 3: Finance cashbook release (add 0049 idempotent, 0050 idempotent, 0051) (+12 more)

### Community 306 - "gcp-vm-release-compose.sh"
Cohesion: 0.50
Nodes (3): COMPOSE_ENV_FILE, COMPOSE_PROJECT_NAME, gcp-vm-release-compose.sh script

### Community 307 - "Mumbai Local Refresh Implementation and Verification 2026-10-15"
Cohesion: 0.67
Nodes (3): Mumbai Local Refresh Implementation and Verification 2026-10-15, Mumbai Customer and Owner Refresh Audit 2026-10-15, Mumbai Refresh Designs 2026-10-15

### Community 308 - "code-explorer.md"
Cohesion: 0.50
Nodes (3): Analysis Approach, Core Mission, Output Guidance

### Community 309 - "test_booking_changes_sql.py"
Cohesion: 0.21
Nodes (17): changes(), new_service(), reviewed(), setup_client(), test_booking_change_requires_key_and_rejects_key_reuse(), test_change_availability_excludes_only_own_booking_and_preserves_public_slots(), test_changed_catalog_quote_requires_reacceptance_and_time_only_keeps_booked_price(), test_cheaper_service_keeps_history_and_prepaid_money_but_reduces_unpaid_price() (+9 more)

### Community 310 - "test_cache_recovery.py"
Cohesion: 0.16
Nodes (8): run_forever(), worker(), Store, test_booking_and_availability_never_read_or_write_payload_cache(), test_erasure_worker_probes_retained_client_before_destructive_work(), test_explicit_invalidation_failure_is_logged_and_retried(), test_partitioned_writer_cannot_leave_stale_payload_for_healthy_reader(), test_snapshot_validation_rejects_unsafe_database_context()

### Community 311 - "Clear Technical English"
Cohesion: 0.50
Nodes (3): Check the result, Clear Technical English, Write the explanation

### Community 312 - "CommissionPolicy"
Cohesion: 0.19
Nodes (7): CommissionPolicy, earned_commission(), half_up_div(), refund_reversals(), lines_for(), policy(), TestCommission

### Community 313 - "Payment integration: gap assessment and decision register"
Cohesion: 0.11
Nodes (16): Decisions made for the initial build, Decisions still needed from the business, Evidence levels used in this repo, Gap assessment (verified against source), Payment integration: gap assessment and decision register, Provider facts to re-verify in sandbox (not confirmed from official pages), Stage 1 build status (2026-10-12), Stage 2 build status (owner subscription billing, 2026-10-13) (+8 more)

### Community 314 - "test_staff_earnings_domain.py"
Cohesion: 0.20
Nodes (5): CommissionRule, earned_amount(), rule(), TestEarnedAmount, TestVersionsAndDates

### Community 318 - "subscription_billing_records table (purchase attempt tracking)"
Cohesion: 0.12
Nodes (19): Admin salon approval API endpoints, POST /v1/salons/me/complete-profile endpoint, Migration 0015 salon admin approval, Migration 0018 subscription foundation tables, Razorpay subscription webhook integration, subscription_billing_records table (purchase attempt tracking), Subscription entitlement states (active, grace, cancelled_paid_through, expired, none), payment-webhook-worker subscription reconciliation (reconcile_subscriptions_once) (+11 more)

### Community 319 - "test_media_admission_http.py"
Cohesion: 0.20
Nodes (13): app_factory(), assert_error(), oversized(), request_asgi(), test_allowed_origin_oversized_upload_has_shared_error_cors_and_timing(), test_body_timeout_keeps_shared_error_headers(), stalled_receive(), test_busy_capacity_keeps_shared_error_headers_and_retry_after() (+5 more)

### Community 320 - "booking_finance_policy.py"
Cohesion: 0.16
Nodes (9): Allocation, _amount(), CancellationQuote, completed_service_allocation(), _remaining(), validate_no_show(), test_completed_service_cost_shortfall_is_not_negative_salon_money(), test_completed_service_has_zero_platform_commission() (+1 more)

### Community 321 - "booking_updates.py"
Cohesion: 0.19
Nodes (4): BookingChangeError, PaymentCollectionRequiredError, BookingUpdatesMixin, _booking_actor_sql()

### Community 322 - "select_rule"
Cohesion: 0.21
Nodes (3): select_rule(), _specificity(), TestPrecedence

### Community 323 - "Production Release Execution Tracker — 2026-10-31"
Cohesion: 0.12
Nodes (16): Approved prices (owner confirmed 2026-10-31, Path A), Current production state (as of 2026-10-31 session), Execution sequence for next session, Full-data restore rehearsal (authoritative), Key evidence files, Permission change made, Phase 2 checklist — PREPARATION COMPLETE (restore verification pending), Phase 3 checklist — FULL-DATA RESTORE REHEARSAL COMPLETE (+8 more)

### Community 325 - "_Result"
Cohesion: 0.17
Nodes (11): repo_with(), _Result, test_idempotency_first_use_reserves(), test_idempotency_mismatched_fingerprint_is_409(), test_idempotency_replays_completed_response(), test_idempotency_unfinished_original_is_in_progress(), test_manual_receipt_inserts_ledger_row_and_refuses_while_gateway_open(), test_observation_amount_mismatch_fails_row_and_never_captures() (+3 more)

### Community 327 - "AdminInsightsUseCases"
Cohesion: 0.19
Nodes (5): AdminInsightsUseCases, _assert_admin(), _counts(), test_a_bulk_offer_for_an_unknown_plan_is_a_clean_not_found(), get_plan()

### Community 328 - "test_account_deletion_api.py"
Cohesion: 0.12
Nodes (4): client(), test_deletion_blocked_409_body_contains_structured_counts(), test_domain_errors_map_to_documented_statuses(), test_status_is_authenticated_by_header_token_not_jwt()

### Community 329 - "create_holiday"
Cohesion: 0.14
Nodes (5): create_holiday(), delete_holiday(), list_holidays(), HolidayCreateRequest, HolidayResponse

### Community 332 - "test_messaging.py"
Cohesion: 0.22
Nodes (5): has_quota(), month_window(), QuotaWindow, remaining(), TestQuota

### Community 333 - "reversal_due"
Cohesion: 0.20
Nodes (3): _half_up(), reversal_due(), TestReversalAfterRefund

### Community 334 - "Production Migration Execution Runbook"
Cohesion: 0.13
Nodes (14): Client compatibility requirements, Conditions for setting AUTO_DEPLOY_ENABLED=true (Gate C), Exact production commands (Gate B session, NOT AUTHORIZED YET), Finance endpoint checks (after Gate C: 0051), Gate A — backup + isolated restore test (required before any production step), Gate B — 0040→0050 production sequence, Gate C — 0051/0052 + AUTO_DEPLOY_ENABLED, Option 1: Maintenance window + write freeze (recommended for first release) (+6 more)

### Community 341 - "register_exception_handlers"
Cohesion: 0.14
Nodes (8): _cors_headers(), register_exception_handlers(), http_exception_handler(), safe_validation_error_handler(), _sanitise(), unhandled_error_handler(), test_oversized_gateway_body_never_creates_object(), Decisions

### Community 350 - "render"
Cohesion: 0.23
Nodes (4): _check_text(), render(), UnsafeMessageError, TestTemplates

### Community 352 - "Owner finance: Phase 2 (local backend) implementation record"
Cohesion: 0.14
Nodes (12): A bug in Phase 2, found while designing this, and fixed, API additions since the Phase 1 contract (2026-10-29), Bug found by the tests and fixed in the migration, Deviations from the Phase 1 design (each deliberate), Erasure, Expense v2: custom name, batch push, change feed, month summary (2026-10-29), Gaps found while testing (read these), Not built yet (and why) (+4 more)

### Community 356 - "Phase 1 checklist"
Cohesion: 0.14
Nodes (10): Code changes — COMPLETE, New unit tests required, Phase 1 checklist, Regression tests added — COMPLETE, Tests NOT changed (correct for what they test), Validation, test_0049_sql_guards_will_not_fire_at_approved_prices(), test_canonical_prices_module_matches_harness_expectations() (+2 more)

### Community 359 - "Prompt: build the subscription pages on salones.in"
Cohesion: 0.15
Nodes (12): SubscriptionStateResponse, `GET /v1/salons/me/subscription` (owner), API, Design, Done when, Payment rules (do not skip), Prompt: build the subscription pages on salones.in, Routes (+4 more)

### Community 396 - "cloud_run_candidate.py"
Cohesion: 0.09
Nodes (51): 2. Root `migration_mumbai_*.py` runners (13) - current split implemented, B6 — Production-environment readback and OIDC not live-verified, B7 — GitHub Free / private enforcement limitation, Current merged CI/CD proof, Exact conditions for changing `AUTO_DEPLOY_ENABLED` from false to true, First supervised production release — execution plan, First supervised production release steps, Required backup and restore test (+43 more)

### Community 401 - "Progress: shifan-cloud-run-auto-deploy"
Cohesion: 0.08
Nodes (23): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: shifan-cloud-run-auto-deploy (+15 more)

### Community 408 - "BookingFinanceRepository"
Cohesion: 0.28
Nodes (7): admin_statement(), finance_command(), owner_statement(), BookingFinanceUseCases, Booking, BookingFinanceRepository, Part 4 — Why the current main code cannot be deployed without schema changes

### Community 418 - "Owner finance: Phase 0 discovery and approval request"
Cohesion: 0.17
Nodes (12): 10. Migration compatibility risks, 11. Proposed phases (unchanged from the brief), 1. Summary, 3. Reuse, do not duplicate, 5. Daily Ledger arithmetic (per salon-local day), 6. Proposed API (owner and admin only; staff get 403; cross-salon ids return 404), 8. Premium SMS (design status), 9. Decisions (+4 more)

### Community 419 - "3. Per-migration reconciliation: 0041–0052"
Cohesion: 0.17
Nodes (12): 0042 `remove_business_category` — **NOT APPLIED**, 0043 `no_show_attendance_guards` — **NOT APPLIED**, 0044 `versioned_checkout_policy` — **NOT APPLIED**, 0045 `customer_booking_changes` — **APPLIED** (outside Alembic, no version stamp), 0046 `u08_financial_outcomes` — **NOT APPLIED**, 0047 `booking_audit_erasure` — **NOT APPLIED** (table was created earlier; erasure columns absent), 0048 `support_billing_erasure` — **NOT APPLIED**, 0049 `trial_salon_plan_prices` — **LIKELY APPLIED** (data change; no structural indicator) (+4 more)

### Community 424 - "Progress: shifan-cloud-run-bootstrap"
Cohesion: 0.17
Nodes (11): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: shifan-cloud-run-bootstrap (+3 more)

### Community 425 - "Progress: shifan-cloud-run-oidc-cicd"
Cohesion: 0.17
Nodes (11): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: shifan-cloud-run-oidc-cicd (+3 more)

### Community 426 - "AuthUserContacts"
Cohesion: 0.24
Nodes (3): AuthUserContacts, FakeAdmin, FakeAuthAdmin

### Community 427 - "_Clock"
Cohesion: 0.20
Nodes (7): _Clock, _grant(), test_expiry_crossed_during_processing_stores_nothing_and_reports_the_failure(), test_expiry_crossed_during_storage_still_returns_204_and_extends_nothing(), test_failure_to_derive_the_link_never_turns_a_stored_upload_into_an_error(), broken(), test_put_with_query_string_commits_and_returns_204_with_the_result_link()

### Community 428 - "Role-Based Access Model (customer/owner/staff/super_admin)"
Cohesion: 0.22
Nodes (7): Account Deletion Flow (challenge/verify/confirm/status), Role-Based Access Model (customer/owner/staff/super_admin), Salon Access State (trialing/soft_locked/subscribed_growth/subscribed_premium), Booking Masking for Locked Salons, Smart Slot Filler (Premium discount windows), SMS/Push Alert Circuit Breaker (Premium feature), Split Bill and Daily Ledger (commission rules)

### Community 431 - "expected_closing_cash"
Cohesion: 0.29
Nodes (3): expected_closing_cash(), TestExampleDay, TestCashFormula

### Community 432 - "Domain rules"
Cohesion: 0.20
Nodes (9): Account deletion, Booking, Cancellation, no-show and payout holds (owner-approved U08 target; not released), Domain rules, Migration state (31 October 2026 — Gate B COMPLETE), Payments, Public salon visibility, Roles (+1 more)

### Community 435 - "Owner finance: Phase 1 schema and API design (review only)"
Cohesion: 0.22
Nodes (9): 0. Assumptions used (the Phase 0 questions are not answered yet), 10. What still needs your decision before Phase 2, 1. Principles, 3. Reads that build the Daily Ledger (no new table), 4. Lock order (every write follows it, to avoid deadlock), 5. Audit events, 7. Privileges and row-level security, 9. Corrections and rollback (+1 more)

### Community 436 - "6. API contracts (all under `/v1`, JSON, paise, `Idempotency-Key` required on every write)"
Cohesion: 0.22
Nodes (9): 6. API contracts (all under `/v1`, JSON, paise, `Idempotency-Key` required on every write), `GET|POST /salons/me/commission-rules`, `GET /salons/me/ledger/daily?date=YYYY-MM-DD`, `GET /salons/me/ledger/range?from=&to=` (max 93 days), `GET /salons/me/staff-earnings?from=&to=`, `POST /salons/me/expenses`, `GET /salons/me/expenses?from=&to=&limit=&offset=`, `POST /salons/me/expenses/{id}/reverse`, `POST /salons/me/ledger/adjustments`, `POST /salons/me/ledger/days/{date}/close` (+1 more)

### Community 437 - "Cloud Run automatic-release gate fix — 1 November 2026"
Cohesion: 0.22
Nodes (7): Cloud Run automatic-release gate fix — 1 November 2026, Correction, Deployment safety retained, First automatic-run result, Proven skipped-release root cause, Verification scope, Main-merge Cloud Run configuration — 30 October 2026

### Community 439 - "public_api"
Cohesion: 0.25
Nodes (5): test_category_requires_service_assigned_to_active_staff(), test_category_uses_service_presentation_not_salon_business_label(), public_api(), database(), DatabaseHealthResponse

### Community 440 - "routes/booking_finance.py"
Cohesion: 0.43
Nodes (3): AdminFinanceStatement, FinanceCommandRequest, OwnerPayoutStatement

### Community 441 - "measure_external"
Cohesion: 0.25
Nodes (3): measure_external(), decorate(), timed()

### Community 442 - "4. Proposed data model (proposal only; no revision ID assigned)"
Cohesion: 0.25
Nodes (7): 2. What exists today (verified in code), 4.1 `salon_expenses` (append-only), 4.2 `salon_cash_adjustments` (append-only), 4.3 `salon_day_closes` (append-only revisions), 4.4 Per-service staff attribution, 4.5 Commission policy, 4. Proposed data model (proposal only; no revision ID assigned)

### Community 443 - "2. Proposed tables (text proposal, public schema, `salon_id uuid not null` everywhere)"
Cohesion: 0.25
Nodes (8): 2.1 `salon_expenses`, 2.2 `salon_cash_adjustments`, 2.3 `salon_day_closes` (one row per revision), 2.4 `booking_service_staff` (per-service attribution), 2.5 `staff_commission_rule_versions` (extends the approved G06 design), 2.6 `staff_earning_events` (append-only), 2.7 Premium messaging (built only at Phase 4; shown so the schema is reviewed once), 2. Proposed tables (text proposal, public schema, `salon_id uuid not null` everywhere)

### Community 444 - "Server-side WebP image families"
Cohesion: 0.25
Nodes (7): Admission and resource limits, Family retirement and account erasure, Keys, proof and compatibility, Local verification, 2026-10-19, Policy, Server-side WebP image families, Verification boundary

### Community 445 - "CASHFREE_VERIFICATION_2026-10-29.md"
Cohesion: 0.25
Nodes (7): Activation finding, Activation prerequisites, Additional checks, Backend activation follow-up, Evidence, Local regression checks, Result

### Community 446 - "Canonical repository and Cloud Run CI/CD audit"
Cohesion: 0.25
Nodes (8): Approved IAM creation and readback, Canonical repository and Cloud Run CI/CD audit, GitHub configuration audit and changes, Implemented behavior, Local verification, Release hold, Repository and authentication, Verified GCP baseline

### Community 447 - "Production release preflight — 1 November 2026"
Cohesion: 0.25
Nodes (7): Candidate result, Current serving image, Fresh production observations, One-time supervised candidate — approved and verified, Outstanding release gates, Production promotion result, Production release preflight — 1 November 2026

### Community 449 - "BulkPlanPriceRequest"
Cohesion: 0.29
Nodes (4): BulkPlanPriceRequest, test_an_offer_end_without_a_timezone_is_refused_not_a_server_error(), test_the_bulk_request_needs_exactly_one_offer_input(), test_the_bulk_request_rejects_repeats_empty_and_oversized_lists_and_bad_ids()

### Community 450 - "install_database_metrics"
Cohesion: 0.38
Nodes (5): install_database_metrics(), after(), before(), PayoutHistoryEntryResponse, Payments and payout history (backend, dormant until a provider is configured)

### Community 451 - "service_change_quote"
Cohesion: 0.29
Nodes (5): service_change_quote(), ServiceChangeQuote, test_partial_or_manual_collected_money_is_not_treated_as_an_unpaid_change(), test_prepaid_service_changes_keep_prior_payment_and_quote_only_extra(), test_service_change_quote_rejects_invalid_money()

### Community 452 - "Owner finance: Phase 3 (owner app) record"
Cohesion: 0.29
Nodes (5): Not verified, and why, Owner finance: Phase 3 (owner app) record, Still to do, Tests, What the owner sees

### Community 453 - "Local schema reconciliation rehearsal ? 29 October 2026"
Cohesion: 0.29
Nodes (7): Append-only correction, Local schema reconciliation rehearsal ? 29 October 2026, Offline OpenAPI release check, Rehearsed SQL order, Release gate, Results and retention impact, Source and recovery point

### Community 454 - "Part 7 — Required isolated restore test stages"
Cohesion: 0.29
Nodes (7): Part 7 — Required isolated restore test stages, Stage 1 — Isolated restore environment, Stage 2 — Apply idempotent migration patch, Stage 3 — Sequential migration run on isolated restore, Stage 4 — Data integrity check on isolated restore, Stage 5 — Full test suite on isolated restore, Stage 6 — Record and owner-approve restore evidence

### Community 455 - "business_checks"
Cohesion: 0.33
Nodes (3): business_checks(), create(), request()

### Community 457 - "Production Gate B migration execution — 31 October 2026 session 2"
Cohesion: 0.29
Nodes (7): Blockers, Decisions, Files touched this session, Next steps (ordered), Production Gate B migration execution — 31 October 2026 session 2, Status, What was done this session

### Community 459 - "PlanPriceSetRequest"
Cohesion: 0.33
Nodes (3): PlanPriceSetRequest, test_the_request_accepts_exactly_one_offer_input(), test_the_request_accepts_whole_rupees_and_paise()

### Community 463 - "Legacy Cloud Run baseline bootstrap"
Cohesion: 0.33
Nodes (5): Legacy Cloud Run baseline bootstrap, Migration gate, Other fixes, Verified baseline, Workflow selection after review

### Community 464 - "Cloud Run deployment gate audit — 1 November 2026"
Cohesion: 0.33
Nodes (5): Cloud Run deployment gate audit — 1 November 2026, Complete conditions and sources, One authoritative switch, Verification and activation, Verified defect

### Community 465 - "Subscription percentage release and owner-session verification"
Cohesion: 0.33
Nodes (5): Cleanup and remaining boundaries, Database and configuration, Serving release, Subscription percentage release and owner-session verification, Verification

### Community 466 - "Owner wallet and manual payouts"
Cohesion: 0.33
Nodes (5): Admin routes (super admin + MFA), Open decisions (not made in code), Owner routes (owner only; staff and customers get 403), Owner wallet and manual payouts, Safety

### Community 468 - "add_salon"
Cohesion: 0.33
Nodes (4): add_salon(), catalog(), test_a_paused_salon_offers_no_payment_method(), test_service_search_only_counts_bookable_services_at_public_salons()

### Community 469 - "test_automatic_pipeline_uses_tested_image_and_finishes_after_new_main"
Cohesion: 0.33
Nodes (3): test_automatic_pipeline_uses_tested_image_and_finishes_after_new_main(), response(), test_public_http_200_with_wrong_commit_is_failed_and_stops_smoke()

### Community 470 - "Cloud Run Deployment Assessment 2026-10-22"
Cohesion: 0.40
Nodes (5): Cloud Run Deployment Assessment 2026-10-22, Mumbai Staging Startup Investigation 2026-10-16, Startup Profile Baseline and Import Review 2026-10-20, Local Docker Cold Start Measurement 2026-10-16, Infrastructure Ownership and Cost Audit 2026-10-16

### Community 471 - "6. Owner app and owner web: business workflows"
Cohesion: 0.33
Nodes (6): 6. Owner app and owner web: business workflows, Business resources, media and time off, Collections, payout and provider onboarding, Owner access, onboarding and review, Owner mobile subscription boundary, Owner screens and daily appointments

### Community 473 - "Salon Platform API"
Cohesion: 0.40
Nodes (5): Checks, Docker, Documentation, Local development, Salon Platform API

### Community 482 - "Database plan"
Cohesion: 0.67
Nodes (3): Account deletion (revision `0021_account_deletion`), Database plan, Payments and payout audit (migrations 0026, 0027)

### Community 483 - "Features"
Cohesion: 0.67
Nodes (3): Account deletion (implemented, not yet production-verified), Features, Payment collection (backend)

## Knowledge Gaps
- **28 isolated node(s):** `COMPOSE_ENV_FILE`, `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME`, `Footer – Making every appointment a little simpler`, `Our Founders Section – Ziyarad Huq CEO, Shifan NV CPO, Shoiball CMO` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 4027 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **165 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Profile` connect `Profile` to `datetime`, `payments/cashfree.py`, `make_mock_repo`, `assert_approved_workspace`, `test_media_integration.py`, `pathlib`, `routes/auth.py`, `PlatformRepository`, `routes/walkin.py`, `FinanceUseCases`, `test_checkout_safety_sql.py`, `make_owner`, `routes/payments.py`, `routes/admin.py`, `test_subscription_billing.py`, `BookingFinanceRepository`, `Role`, `payments/booking.py`, `NotificationUseCases`, `SubscriptionProviderResolver`, `AuthAdminGateway`, `test_walkin_qr_contract.py`, `test_booking_changes_sql.py`, `test_api_input_bounds.py`, `customer.py`, `use_cases/account_deletion.py`, `test_auth.py`, `routes/support.py`, `typing`, `get_current_actor`, `routes/booking_finance.py`, `test_salon_trials.py`, `post`, `routes/wallet.py`, `test_salon_ranking.py`, `routes/auth.py`, `notifications.py`, `subscriptions.py`, `create_holiday`, `routes/admin_insights.py`, `AdminInsightsUseCases`, `use_cases/platform.py`, `NotFoundError`, `FakeWallet`, `schemas/platform.py`, `test_subscription.py`, `test_plan_prices.py`, `use_cases/subscription_billing.py`, `config.py`, `get_my_profile`, `AdminUseCases`, `test_owner_finance_api.py`, `make_super_admin`, `use_cases/wallet.py`, `routes/finance.py`, `WalkInUseCases`, `test_subscription_status_guard.py`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._
- **Are the 215 inferred relationships involving `Profile` (e.g. with `get_authenticated_session()` and `get_current_actor()`) actually correct?**
  _`Profile` has 215 INFERRED edges - model-reasoned connections that need verification._
- **What connects `COMPOSE_ENV_FILE`, `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `datetime` be split into smaller, more focused modules?**
  _Cohesion score 0.026533996683250415 - nodes in this community are weakly interconnected._
- **Why does `ValidationError` connect `ImageFamilies` to `datetime`, `payments/cashfree.py`, `ConflictError`, `Profile`, `make_mock_repo`, `assert_approved_workspace`, `Any`, `test_media_integration.py`, `test_image_families.py`, `test_media_admission_http.py`, `test_admin_insights.py`, `routes/auth.py`, `PlatformRepository`, `FinanceUseCases`, `make_owner`, `test_cashfree_gateway.py`, `test_wif_claim_preflight.py`, `exceptions.py`, `BookingChangeRepository`, `Role`, `test_payment_stage1_flows.py`, `payments/booking.py`, `R2StorageGateway`, `use_cases/subscription_billing.py`, `PillowImageProcessor`, `_Clock`, `use_cases/account_deletion.py`, `typing`, `get_current_actor`, `measure_external`, `FinanceRepository`, `booking_updates.py`, `ConflictError`, `WalletRepository`, `AdminInsightsUseCases`, `test_cashfree_subscription.py`, `retire_unreferenced_media`, `use_cases/platform.py`, `OwnerCatalogMixin`, `NotFoundError`, `FakeWallet`, `test_subscription.py`, `test_migration_and_service_api_round_trip`, `test_media_publication_safety.py`, `test_plan_prices.py`, `pytest`, `use_cases/subscription_billing.py`, `SupabaseAuthGateway`, `config.py`, `AdminUseCases`, `use_cases/wallet.py`, `WalkInUseCases`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 100 inferred relationships involving `ValidationError` (e.g. with `upload_avatar()` and `upload_signed_image()`) actually correct?**
  _`ValidationError` has 100 INFERRED edges - model-reasoned connections that need verification._
- **Should `payments/cashfree.py` be split into smaller, more focused modules?**
  _Cohesion score 0.04413919413919414 - nodes in this community are weakly interconnected._