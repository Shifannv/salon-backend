# Graph Report - salon-backend  (2026-11-02)

## Corpus Check
- 952 files · ~954,503 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 25 file(s) not represented in the graph (top: (none) 16, .example 2, .csv 2)

## Summary
- 10571 nodes · 27763 edges · 528 communities (332 shown, 196 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 3290 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a7641fcb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- NotFoundError
- payments/booking.py
- FeatureAccessRepository
- Profile
- require_super_admin
- assert_approved_workspace
- test_media_admission_http.py
- Money
- pathlib
- use_cases/payout_proof.py
- test_admin_insights.py
- Data models
- make_mock_repo
- PlatformRepository
- test_checkout_safety_sql.py
- FakeRepo
- Settings
- test_cashfree_gateway.py
- erasure.py
- schemas/payment.py
- PaymentProviderNotConfiguredError
- routes/admin.py
- test_subscription_billing.py
- os
- test_payment_stage1_flows.py
- test_payment_flows.py
- test_checkout_email_telemetry.py
- test_reconciliation_preflight.py
- time
- local_fixture_server.py
- BookingPaymentUseCases
- ValidationError
- SubscriptionProvider
- SubscriptionProviderResolver
- test_subscription_billing_sql.py
- PaymentRepository
- AuthAdminGateway
- test_payments_foundation.py
- test_walkin_qr_contract.py
- test_booking_changes_sql.py
- test_api_input_bounds.py
- routes/payout_proof.py
- unittest_mock
- test_account_erasure.py
- provision_super_admin.py
- CacheGateway
- G01-G09 payment/subscription/booking migration design groups (design review only)
- use_cases/account_deletion.py
- deps.py
- Module Group 50
- routes/support.py
- finance_ledger.py
- routes/staff_earnings.py
- test_wallet_api.py
- panel.py
- test_payout_account.py
- test_account_deletion_sql.py
- restore_database.py
- main.py
- FakeBillingRepo
- post
- test_account_erasure_hardening.py
- FinanceRepository
- connections.py
- Salon Owner
- test_payment_stage1_api.py
- test_salon_ranking.py
- pytest
- Salon Owner App Backend API Contract
- routes/auth.py
- notifications.py
- subscriptions.py
- test_cashfree_subscription.py
- routes/admin_insights.py
- BookingActionRepository
- FCMGateway
- .get_available_slots
- Ledger
- owner_setup.py
- test_payment_fees_policy.py
- alembic
- architect.md
- MCP Server Best Practices
- UnauthorizedError
- OwnerCatalogMixin
- test_plan_prices_sql.py
- Node/TypeScript MCP Server Implementation Guide
- FakeWallet
- fastapi_testclient
- test_account_closure_steps.py
- test_api_input_bounds.py
- schemas/platform.py
- test_subscription.py
- Website, customer app and owner app: developer handoff
- test_payment_settings_sql.py
- json
- Role
- booking_policy.py
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
- datetime
- IntentMixin
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
- AccountErasureService
- docs/README.md
- test_image_families.py
- test_booking_contract_sql.py
- client_for
- test_migration_tool_paths.py
- test_public_salon_visibility.py
- chief-of-staff.md
- Changelog
- schemas/booking.py
- FinanceUseCases
- schemas/platform.py
- test_mumbai_forward_reconciliation.py
- Env
- Running Evaluations
- Writing Guidelines for Postgres References
- Customer App Backend API Contract
- ServiceUnavailableError
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
- WalletUseCases
- NotificationUseCases
- Progress: thameem/cloud-run-startup-investigation
- WalletAdminUseCases
- Senior backend engineer
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
- collected_by_staff
- _ChallengeMixin
- StaffEarningsAdminRepository
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
- RedisCache
- founder-board
- ObservationMixin
- founder-ops
- Karpathy Guidelines
- Section Definitions
- Subscriptions
- common.py
- media/health.py
- payments.py
- reconciliation_harness.py
- _BookingMixin
- test_sql_bind_params.py
- source
- Gate A — Isolated Full-Data Restore Evidence
- booking_payments as Ledger Source of Truth
- NotificationOutboxMixin
- test_closed_salon_statement.py
- test_account_deletion_migration.py
- Codex prompt: deploy migration 0049 and the subscription backend to GCP
- WebhookEventMixin
- founder-marketing
- founder-offer
- BookingChangeGateway
- Isolated Restore Evidence Template
- OwnerPayoutAccountRequest
- SalonSubscriptionUseCases
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
- test_messaging.py
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
- Operational Runbook (local setup, super-admin, workers)
- AdminInsightsRepo
- test_reconciliation_finance_schema.py
- Mumbai reconciliation — least privilege — 2026-10-15
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
- SalonSubscriptionRepo
- ._scrub_owner_business
- 0015_salon_admin_approval.py
- Production migration reconciliation — correction and safe path
- 0035_booking_checkout_safety.py
- gcp-vm-release-compose.sh
- PayoutProofRepository
- code-explorer.md
- test_payout_proof_sql.py
- Gate A for migrations 0053–0055 — 1 November 2026
- Clear Technical English
- CommissionPolicy
- Payment integration: gap assessment and decision register
- test_staff_earnings_domain.py
- .settlement_model
- AdminSalonsMixin
- subscription_billing_records table (purchase attempt tracking)
- Any
- booking_finance_policy.py
- FakeLedger
- select_rule
- Production Release Execution Tracker — 2026-10-31
- test_salon_approval.py
- _Result
- AdminInsightsUseCases
- test_account_deletion_api.py
- create_holiday
- SubscriptionPlanRepo
- RefundMixin
- reversal_due
- Production Migration Execution Runbook
- check-container.sh
- gcp-vm-deploy.sh
- code-architect.md
- start.md
- wrap.md
- register_exception_handlers
- test_ci_registry_image.py
- Owner finance: Phase 2 (local backend) implementation record
- FakeRepo
- Payments
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
- routes/booking_finance.py
- Rows
- Owner finance: Phase 0 discovery and approval request
- 3. Per-migration reconciliation: 0041–0052
- FakeInsightsRepo
- Progress: shifan-cloud-run-bootstrap
- Progress: shifan-cloud-run-oidc-cicd
- AuthUserContacts
- Latest main candidate — 2 November 2026
- FakeLedger
- test_staff_earnings_completion.py
- support_finance_reference.py
- expected_closing_cash
- Domain rules
- split_refund_across_lines
- main
- Owner finance: Phase 1 schema and API design (review only)
- 6. API contracts (all under `/v1`, JSON, paise, `Idempotency-Key` required on every write)
- Cloud Run automatic-release gate fix — 1 November 2026
- salon_analytics
- public_api
- create_blocked_slot
- _validate_not_production
- hmac
- 2. Proposed tables (text proposal, public schema, `salon_id uuid not null` everywhere)
- Server-side WebP image families
- CASHFREE_VERIFICATION_2026-10-29.md
- Canonical repository and Cloud Run CI/CD audit
- Production release preflight — 1 November 2026
- Rows
- BulkPlanPriceRequest
- install_database_metrics
- create_walkin_booking
- Owner finance: Phase 3 (owner app) record
- Local schema reconciliation rehearsal ? 29 October 2026
- .list_notifications
- business_checks
- test_finance_design_fixtures.py
- SalonTrialUseCases
- test_staff_earnings_domain.py
- PlanPriceSetRequest
- round_money
- ProfilesMixin
- SqlHelpersMixin
- Legacy Cloud Run baseline bootstrap
- Cloud Run deployment gate audit — 1 November 2026
- reseal_layout_evidence.py
- Owner wallet and manual payouts
- net_expense_total
- _FakeSession
- schemas/support.py
- ProfileRepository
- 6. Owner app and owner web: business workflows
- 0052_booking_window_30_days.py
- PayoutNotices
- CLOUD_RUN_FINAL_POLICY_DESIGN_2026-10-29.md
- ExpenseRuleRepository
- Provider-independent payments: mock implementation — 2026-10-18
- MediaRefsMixin
- wif_claim_preflight.py
- test_ci_artifact_cleanup.py
- Features
- Account Deletion
- submit_report
- Phase 3 — Docker prerequisites (complete before filling evidence below)
- test_list_bookings_scoping.py
- test_removed_profile_fields.py
- Notifications
- Mumbai live catalog inspection (44 tables, 52 functions, empty Alembic history)
- _record
- test_service_search_requires_active_category_and_subcategory
- CI image transport: existing Artifact Registry
- CLOUD_RUN_TRAFFIC_METADATA_2026-11-02.md
- GITHUB_ARTIFACT_CLEANUP_2026-11-02.md

## God Nodes (most connected - your core abstractions)
1. `Profile` - 534 edges
2. `ValidationError` - 287 edges
3. `Role` - 269 edges
4. `NotFoundError` - 234 edges
5. `Settings` - 188 edges
6. `make_profile()` - 170 edges
7. `ForbiddenError` - 167 edges
8. `PlatformRepository` - 154 edges
9. `make_owner()` - 153 edges
10. `ConflictError` - 138 edges

## Surprising Connections (you probably didn't know these)
- `POST `/v1/account/deletion/challenges`` --references--> `start_deletion_challenge()`  [INFERRED]
  docs/BACKEND_API_REFERENCE.md → backend/app/api/v1/routes/account_deletion.py
- `POST `/v1/account/deletion/challenges/{challenge_id}/verify`` --references--> `verify_deletion_challenge()`  [INFERRED]
  docs/BACKEND_API_REFERENCE.md → backend/app/api/v1/routes/account_deletion.py
- `POST `/v1/account/deletion`` --references--> `confirm_account_deletion()`  [INFERRED]
  docs/BACKEND_API_REFERENCE.md → backend/app/api/v1/routes/account_deletion.py
- `GET `/v1/account/deletion/{request_id}`` --references--> `get_deletion_status()`  [INFERRED]
  docs/BACKEND_API_REFERENCE.md → backend/app/api/v1/routes/account_deletion.py
- `GET `/v1/admin/account-deletions`` --references--> `list_account_deletions()`  [INFERRED]
  docs/BACKEND_API_REFERENCE.md → backend/app/api/v1/routes/account_deletion.py

## Import Cycles
- 3-file cycle: `backend/app/api/v1/routes/owner.py -> backend/app/api/v1/routes/owner_salon.py -> backend/app/api/v1/routes/owner_common.py -> backend/app/api/v1/routes/owner.py`
- 3-file cycle: `backend/app/api/v1/routes/owner.py -> backend/app/api/v1/routes/owner_catalog.py -> backend/app/api/v1/routes/owner_common.py -> backend/app/api/v1/routes/owner.py`
- 3-file cycle: `backend/app/api/v1/routes/owner.py -> backend/app/api/v1/routes/owner_blocks.py -> backend/app/api/v1/routes/owner_common.py -> backend/app/api/v1/routes/owner.py`
- 3-file cycle: `backend/app/api/v1/routes/owner.py -> backend/app/api/v1/routes/owner_holidays.py -> backend/app/api/v1/routes/owner_common.py -> backend/app/api/v1/routes/owner.py`

## Hyperedges (group relationships)
- **Account Deletion End-to-End Flow (auth -> erasure -> financial purge)** — backend_docs_account_deletion_flow, backend_docs_account_deletion_erasure_worker, backend_docs_account_deletion_financial_purge_design_overview [EXTRACTED 1.00]
- **All Compose Workers Depend on Redis Health** — backend_docker_compose_api_service, backend_docker_compose_notification_worker, backend_docker_compose_media_cleanup, backend_docker_compose_account_deletion_worker, backend_docker_compose_payment_webhook_worker, backend_docker_compose_email_worker, backend_docker_compose_redis [EXTRACTED 1.00]
- **Booking Creation Idempotency Pattern (Postgres + Redis + use cases)** — backend_docs_booking_flow_postgres_functions, backend_docs_payments_idempotency, backend_docs_architecture_redis_caching [INFERRED 0.85]

## Communities (528 total, 196 thin omitted)

### Community 0 - "NotFoundError"
Cohesion: 0.02
Nodes (32): BookingChangeError, BookingIdempotencyKeyReusedError, BookingWindowExceededError, ConflictError, NotFoundError, PayAtSalonBlockedError, PayAtSalonDailyLimitError, PaymentCollectionRequiredError (+24 more)

### Community 1 - "payments/booking.py"
Cohesion: 0.05
Nodes (29): PaymentEvent, ProviderPayment, apply_provider_payment(), _clean_code(), event_to_json(), _fingerprint(), _json_default(), _ledger_row() (+21 more)

### Community 2 - "FeatureAccessRepository"
Cohesion: 0.05
Nodes (40): clear_feature_override(), get_features(), list_feature_overrides(), save_feature_matrix(), save_plan_content(), set_feature_override(), _uc(), update_feature() (+32 more)

### Community 3 - "Profile"
Cohesion: 0.05
Nodes (5): OwnerUseCases, Profile, is_customer(), is_staff(), _profile_from_row()

### Community 4 - "require_super_admin"
Cohesion: 0.08
Nodes (17): FeatureAccessStore, FeatureAccessUseCases, PaymentSettingsUseCases, _rate(), can_read_own_profile(), is_super_admin(), require_super_admin(), store() (+9 more)

### Community 5 - "assert_approved_workspace"
Cohesion: 0.06
Nodes (9): assert_approved_workspace(), is_owner_or_staff(), can_record_payment(), Cleanup and remaining boundaries, Database and configuration, Serving release, Subscription percentage release and owner-session verification, Verification (+1 more)

### Community 6 - "test_media_admission_http.py"
Cohesion: 0.08
Nodes (36): UploadAdmissionMiddleware, test_grant_json_is_bounded_before_parsing(), test_metadata_gets_share_admission_and_reject_request_bodies(), Downstream, app_factory(), build(), forbidden_dependency(), assert_error() (+28 more)

### Community 7 - "Money"
Cohesion: 0.06
Nodes (39): RefundRequest, PayoutProvider, ProviderFeeReconciler, RefundProvider, WebhookVerifier, IdempotencyKeyReuseError, EvidenceSource, PayoutRequest (+31 more)

### Community 8 - "pathlib"
Cohesion: 0.04
Nodes (41): source_commit(), personal_text_pattern(), quoted_text_pattern(), metric(), percentile(), run(), measure(), one() (+33 more)

### Community 9 - "use_cases/payout_proof.py"
Cohesion: 0.10
Nodes (17): _entry(), PayoutProofUseCases, _snapshot(), PayoutPaymentInvalidError, PayoutProofInvalidError, PayoutReferenceUsedError, check_method(), check_paid_at() (+9 more)

### Community 10 - "test_admin_insights.py"
Cohesion: 0.14
Nodes (18): _today_ist(), FakePlans, _month(), test_a_bulk_offer_applies_to_none_when_any_salon_is_unknown(), test_a_bulk_offer_cannot_end_in_the_past(), test_a_bulk_offer_computes_the_price_once_and_applies_it_to_every_salon(), test_a_bulk_offer_follows_the_same_price_rules_as_a_single_offer(), test_analytics_accepts_a_single_day_and_a_whole_lifetime() (+10 more)

### Community 11 - "Data models"
Cohesion: 0.02
Nodes (123): AccountDeletionAcceptedResponse, AccountDeletionStatusResponse, AdminAccountDeletionResponse, AdminCreateSalonRequest, AdminDeactivateSalonResponse, AdminRejectSalonRequest, AdminSalonOnboardingResponse, AdminSalonResponse (+115 more)

### Community 12 - "make_mock_repo"
Cohesion: 0.06
Nodes (60): BookingUseCases, make_booking(), make_mock_repo(), _owner_salon(), test_non_owner_cannot_toggle(), test_patch_settings_forbidden_for_customer_and_pending_salon(), test_patch_settings_toggles_and_invalidates_salon_and_walkin_cache(), test_toggle_only_writes_the_flag_and_leaves_existing_bookings_alone() (+52 more)

### Community 13 - "PlatformRepository"
Cohesion: 0.03
Nodes (25): get_image_family(), upload_avatar(), upload_signed_image(), get_avatar_upload_url(), update_my_profile(), MediaReferences, StorageGateway, managed_media_path() (+17 more)

### Community 14 - "test_checkout_safety_sql.py"
Cohesion: 0.05
Nodes (74): SQLAccountDeletionRepository, SupportRepository, set_actor_context(), deliver_once(), changes(), changes_db(), install(), finance_db() (+66 more)

### Community 15 - "FakeRepo"
Cohesion: 0.10
Nodes (6): FakeRepo, pay_args(), TestDetailProofAndCorrection, TestPay, TestReconciliationAndWalletHooks, uc()

### Community 16 - "Settings"
Cohesion: 0.05
Nodes (19): get_settings(), Settings, test_auto_release_cannot_be_enabled_it_is_not_built(), test_blank_env_values_mean_unset_not_zero(), test_provider_defaults_stay_none(), test_blank_account_deletion_secret_is_unconfigured(), test_explicit_r2_values_win_over_legacy_values(), test_messaging_is_off_by_default() (+11 more)

### Community 17 - "test_cashfree_gateway.py"
Cohesion: 0.06
Nodes (52): RefundStatus, ignored(), both_client(), cf_settings(), event_body(), gateway(), IntakeRepo, intent_request() (+44 more)

### Community 18 - "erasure.py"
Cohesion: 0.12
Nodes (3): authored_quote_pattern(), _ErasureMixin, What was built (the cash book)

### Community 19 - "schemas/payment.py"
Cohesion: 0.12
Nodes (12): BookingPaymentResponse, BookingQuoteRequest, BookingQuoteResponse, EarningsResponse, PaymentConfigResponse, PaymentIntentRequest, PaymentIntentResponse, PaymentRefreshRequest (+4 more)

### Community 20 - "PaymentProviderNotConfiguredError"
Cohesion: 0.05
Nodes (10): ClientConfig, PaymentIntent, PaymentIntentRequest, PaymentProvider, PaymentProviderNotConfiguredError, GatewayCapability, NullPaymentGateway, FakeGateway (+2 more)

### Community 22 - "routes/admin.py"
Cohesion: 0.09
Nodes (26): _admin_use_cases(), approve_salon(), _catalog_use_cases(), create_category(), create_salon(), create_subcategory(), deactivate_category(), deactivate_salon() (+18 more)

### Community 23 - "test_subscription_billing.py"
Cohesion: 0.06
Nodes (57): subscription_event_to_json(), _unused(), owner(), sub_settings(), adapter(), ent(), handler_for(), http() (+49 more)

### Community 24 - "os"
Cohesion: 0.10
Nodes (17): export_backup(), gpg_path(), locate_tool(), main(), validate_destination(), validate_source(), main(), release() (+9 more)

### Community 25 - "test_payment_stage1_flows.py"
Cohesion: 0.06
Nodes (58): PaymentWebhookUseCases, InvalidWebhookSignatureError, build(), test_existing_customer_authorization_is_enforced_with_fake_provider(), test_fake_payment_and_refund_use_existing_intake_worker_and_replay_gate(), test_http_intake_rejects_tampering_and_cashfree_path_without_storing_effects(), test_sdk_callback_never_marks_a_mock_payment_paid(), build() (+50 more)

### Community 26 - "test_payment_flows.py"
Cohesion: 0.13
Nodes (22): captured_body(), load(), make_processor(), run(), sign(), test_0026_chain_tables_and_security_shape(), test_0026_does_not_widen_the_enums(), test_0026_downgrade_restores_narrow_check_and_drops_everything() (+14 more)

### Community 27 - "test_checkout_email_telemetry.py"
Cohesion: 0.07
Nodes (22): BookingCheckoutUseCases, init_sentry(), scrub_sentry(), checkout_quote(), online_checkout_available(), ResendEmailGateway, test_invalid_money_is_rejected(), test_online_charge_uses_decimal_half_up() (+14 more)

### Community 28 - "test_reconciliation_preflight.py"
Cohesion: 0.17
Nodes (10): _assert_not_production(), _conn(), test_0049_equivalence_check_requires_correct_columns(), run(), test_0049_structure_check_returns_mismatches_for_missing_table(), run(), test_empty_alembic_version_check_structure(), run() (+2 more)

### Community 29 - "time"
Cohesion: 0.13
Nodes (19): distribution(), docker(), inventory(), main(), remove_owned(), poll(), request(), stamp_ns() (+11 more)

### Community 30 - "local_fixture_server.py"
Cohesion: 0.07
Nodes (14): _add_request_id(), configure_logging(), get_request_id(), set_request_id(), RequestMetrics, TimingMiddleware, main(), app_factory() (+6 more)

### Community 31 - "BookingPaymentUseCases"
Cohesion: 0.13
Nodes (5): BookingPaymentUseCases, _NoRepository, PaymentAmountMismatchError, test_cashfree_disabled_never_builds_adapter_or_calls_provider(), test_refresh_requires_an_idempotency_key_and_a_provider()

### Community 32 - "ValidationError"
Cohesion: 0.04
Nodes (31): validate_salon_photo_write(), visible_salon_photos(), resolve_offer_price(), ValidationError, OwnerSalonMixin, R2StorageGateway, test_token_purposes_stay_cryptographically_separate(), test_r2_media_resume_skips_previous_prefixes_and_uses_start_after() (+23 more)

### Community 33 - "SubscriptionProvider"
Cohesion: 0.06
Nodes (8): ProviderPaymentObservation, ProviderSubscriptionEvent, SubscriptionClientConfig, SubscriptionProvider, NullSubscriptionProvider, _refuse(), build_subscription_provider(), test_subscription_provider_defaults_to_none_and_enables_nothing()

### Community 34 - "SubscriptionProviderResolver"
Cohesion: 0.10
Nodes (34): get_subscription_provider_resolver(), cancel(), checkout(), list_purchasable_plans(), my_access_state(), my_subscription(), payments(), subscription_config() (+26 more)

### Community 35 - "test_subscription_billing_sql.py"
Cohesion: 0.05
Nodes (32): SubscriptionSettlement, _row(), SubscriptionBillingRepository, _plans(), test_0030_statements_are_idempotent_and_plan_checks_exist(), test_a_forged_signature_stores_nothing_and_both_providers_work_simultaneously(), subscription_side(), test_a_lapsed_active_row_within_stored_grace_keeps_the_benefit_without_a_sweep() (+24 more)

### Community 36 - "PaymentRepository"
Cohesion: 0.08
Nodes (12): get_payment_gateway(), SubscriptionReconciler, PaymentRepository, get_payment_resolver(), drain_webhook_events(), reconcile_once(), reconcile_subscriptions_once(), run_forever() (+4 more)

### Community 37 - "AuthAdminGateway"
Cohesion: 0.11
Nodes (21): closed_salon_statement(), confirm_account_deletion(), get_deletion_status(), list_account_deletions(), list_closed_salons(), start_deletion_challenge(), _use_cases(), verify_deletion_challenge() (+13 more)

### Community 38 - "test_payments_foundation.py"
Cohesion: 0.08
Nodes (20): PaymentCallback, gateway_with(), hex_hmac(), make_settings(), test_callback_signature_vectors(), test_configured_provider_needs_credentials(), test_create_intent_sends_paise_receipt_and_transfers(), handler() (+12 more)

### Community 39 - "test_walkin_qr_contract.py"
Cohesion: 0.05
Nodes (38): require_qr_token_format(), QrCodeNotFoundError, SlotUnavailableError, is_valid_qr_token_format(), _as(), client(), session(), _fingerprint() (+30 more)

### Community 40 - "test_booking_changes_sql.py"
Cohesion: 0.10
Nodes (30): create_app(), new_service(), reviewed(), setup_client(), test_booking_change_requires_key_and_rejects_key_reuse(), test_change_availability_excludes_only_own_booking_and_preserves_public_slots(), test_changed_catalog_quote_requires_reacceptance_and_time_only_keeps_booked_price(), test_cheaper_service_keeps_history_and_prepaid_money_but_reduces_unpaid_price() (+22 more)

### Community 41 - "test_api_input_bounds.py"
Cohesion: 0.07
Nodes (25): _action_use_cases(), apply_closure(), _closure_use_cases(), create_cancellation_request(), create_payment_confirmation_request(), list_booking_action_requests(), preview_closure(), respond_booking_action_request() (+17 more)

### Community 42 - "routes/payout_proof.py"
Cohesion: 0.13
Nodes (19): correct_payout(), correction_proof(), _file_response(), mark_payout_paid(), notify_owner(), payout_detail(), payout_notices(), payout_proof() (+11 more)

### Community 43 - "unittest_mock"
Cohesion: 0.04
Nodes (62): ImagePolicy, ImageProcessor, ProcessedImageFamily, ProcessedVariant, UploadAvatar, PillowImageProcessor, namespace_for(), FakeR2Client (+54 more)

### Community 44 - "test_account_erasure.py"
Cohesion: 0.21
Nodes (15): FakeStorage, make_request(), make_service(), test_already_missing_auth_user_is_not_banned_and_delete_is_idempotent(), test_auth_delete_failure_is_retryable_and_resumes_without_repeating_steps(), test_customer_erasure_skips_salon_cache_keys(), test_lock_is_released_even_when_storage_fails(), test_missing_storage_configuration_fails_instead_of_skipping_media() (+7 more)

### Community 45 - "provision_super_admin.py"
Cohesion: 0.09
Nodes (20): _admin_base(), _assert_safe_existing_profile(), _AuthUser, _create_auth_user(), _FakeGateway, _find_user_by_email(), _get_profile_state(), main() (+12 more)

### Community 46 - "CacheGateway"
Cohesion: 0.04
Nodes (33): get_cache(), get_profile(), get_salon(), list_public_categories(), list_public_subcategories(), list_salon_services(), list_salon_staff(), list_salons() (+25 more)

### Community 47 - "G01-G09 payment/subscription/booking migration design groups (design review only)"
Cohesion: 0.49
Nodes (17): G02 Provider-fee reconciliation (financial_postings, accounting seals on G01 financial_events), G03 Cancellation policy versions (U03 bands: 48h flat, 5%, 35%, zero; 70/30 split), G04 Payout/dispute records (salon_payouts, payout_destination_versions, booking_financial_disputes), G05 Payout schedules (payout_capability_versions, salon_payout_schedule_versions), G06 Staff commission ledger (staff_commission_rule_versions, booking_staff_commission_snapshots), G07 Subscription lifecycle (subscription_lifecycle_policies, lifecycle_events, renewal_mode), G08 Business closure and reschedule (business_closure_operations, booking_reschedule_requests, booking_schedule_events), G01 Admin financial audit and authority foundation (financial_command_identities, financial_events, audit_events) (+9 more)

### Community 48 - "use_cases/account_deletion.py"
Cohesion: 0.06
Nodes (45): AccountDeletionUseCases, deletion_stage(), mask_contact(), normalize_contact(), _statement_figures(), ContactMismatchError, DeletionBlockedError, InvalidVerificationCodeError (+37 more)

### Community 49 - "deps.py"
Cohesion: 0.03
Nodes (21): get_auth_gateway(), get_authenticated_session(), get_current_actor(), get_payment_gateway_resolver(), get_storage_gateway(), delete_holiday(), _use_cases(), process_in_background() (+13 more)

### Community 50 - "Module Group 50"
Cohesion: 0.10
Nodes (17): Account Deletion Worker Service, API Service (Docker Compose), Email Worker Service, Media Cleanup Worker Service, Notification Worker Service, Payment Webhook Worker Service, Redis Service (Docker Compose), Erasure Worker (lock/cancel/notify/refund/settle/erase) (+9 more)

### Community 51 - "routes/support.py"
Cohesion: 0.24
Nodes (9): create_ticket(), email_event(), read_ticket(), reply_ticket(), GET `/v1/email/events/{event_id}`, GET `/v1/support/tickets/{ticket_id}`, POST `/v1/support/tickets`, POST `/v1/support/tickets/{ticket_id}/reply` (+1 more)

### Community 52 - "finance_ledger.py"
Cohesion: 0.06
Nodes (19): close_difference(), expected_closing_cash(), finance_allowed(), month_bounds(), reason_is_written(), rule_applies_on(), today_in(), TrialState (+11 more)

### Community 53 - "routes/staff_earnings.py"
Cohesion: 0.14
Nodes (21): add_commission_rule(), list_commission_rules(), list_service_staff(), set_service_staff(), staff_earnings(), staff_earnings_detail(), _use_cases(), BookingLine (+13 more)

### Community 54 - "test_wallet_api.py"
Cohesion: 0.27
Nodes (7): _body(), test_a_payout_request_without_an_idempotency_key_is_refused_before_any_database_work(), test_admin_bodies_are_strict(), test_admin_payout_routes_reject_every_other_role(), session(), test_no_anonymous_access(), test_payout_request_body_is_strict()

### Community 55 - "panel.py"
Cohesion: 0.11
Nodes (28): _answer_ok(), check(), deal(), init(), load_state(), main(), _num(), PanelError (+20 more)

### Community 56 - "test_payout_account.py"
Cohesion: 0.07
Nodes (11): api(), FakeRepo, _migration(), _migration_named(), _sql(), test_0027_shape(), test_field_validation_rejects_bad_input(), test_migration_chain_and_security_shape() (+3 more)

### Community 57 - "test_account_deletion_sql.py"
Cohesion: 0.15
Nodes (28): confirm(), drain(), FakeAdmin, finish_ledger(), make_due(), make_service(), new_user(), one() (+20 more)

### Community 58 - "restore_database.py"
Cohesion: 0.12
Nodes (20): _DataBlob, _gpg_path(), inspect_empty_database(), inspect_isolated_container(), locate_tool(), main(), restore(), RestoreError (+12 more)

### Community 59 - "main.py"
Cohesion: 0.04
Nodes (32): close_redis_cache(), init_redis_cache(), _redacted_target(), drain_queue(), main(), run_job(), run_pass(), attempt_one() (+24 more)

### Community 61 - "post"
Cohesion: 0.09
Nodes (35): approve_booking(), availability(), barber_cancel_booking(), booking_change_availability(), cancel_booking(), change_booking(), check_in(), complete_booking() (+27 more)

### Community 62 - "test_account_erasure_hardening.py"
Cohesion: 0.08
Nodes (27): heartbeat_path(), is_healthy(), main(), max_age_seconds(), touch(), drain_account_deletions(), run_forever(), storage_is_required() (+19 more)

### Community 64 - "connections.py"
Cohesion: 0.07
Nodes (5): MCPConnection, MCPConnectionHTTP, MCPConnectionSSE, MCPConnectionStdio, supabase

### Community 65 - "Salon Owner"
Cohesion: 0.06
Nodes (33): DELETE `/v1/salons/me/blocks/{block_id}`, DELETE `/v1/salons/me/holidays/{holiday_id}`, DELETE `/v1/salons/me/images/{image_id}`, DELETE `/v1/salons/me/services/{service_id}`, DELETE `/v1/salons/me/staff/{staff_id}`, GET `/v1/salons/me`, GET `/v1/salons/me/blocks`, GET `/v1/salons/me/holidays` (+25 more)

### Community 66 - "test_payment_stage1_api.py"
Cohesion: 0.09
Nodes (14): CommissionBase, commission_reversal(), compute_commission(), test_zero_platform_commission_is_valid_in_the_commission_math(), FakeUseCases, load(), run(), test_0029_downgrade_restores_legacy_functions_and_drops_additions() (+6 more)

### Community 67 - "test_salon_ranking.py"
Cohesion: 0.19
Nodes (18): _actor(), add_salon(), ids(), ranked(), _subscribe(), test_admin_response_exposes_priority_and_audit_actor(), test_discovery_visibility_and_search_only(), test_hidden_salons_never_appear_even_with_top_priority() (+10 more)

### Community 68 - "pytest"
Cohesion: 0.09
Nodes (32): business_error(), infrastructure_error(), _PgError, _repository(), _Result, test_cancellation_owner_decision_releases_slot_only_when_approved(), test_closure_rejects_changed_impact_set(), test_cross_salon_decision_is_hidden() (+24 more)

### Community 69 - "Salon Owner App Backend API Contract"
Cohesion: 0.12
Nodes (16): Account deletion (owner), Audit result, Authentication, `GET /v1/salons/me/subscription/payments?limit=50&offset=0` (owner), `GET /v1/subscription-plans` (owner), `GET /v1/subscriptions/config` (no auth, always 200), Media upload flow, Payout account and setup checklist (+8 more)

### Community 70 - "routes/auth.py"
Cohesion: 0.07
Nodes (18): forgot_password(), me(), owner_access(), refresh(), ForgotPasswordRequest, ForgotPasswordResponse, ProfileResponse, RefreshRequest (+10 more)

### Community 71 - "notifications.py"
Cohesion: 0.09
Nodes (13): deactivate_device(), list_notifications(), mark_all_notifications_read(), mark_notification_read(), register_device(), _use_cases(), DeviceRegisterRequest, DeviceRegisterResponse (+5 more)

### Community 72 - "subscriptions.py"
Cohesion: 0.17
Nodes (23): cancel_subscription(), clear_salon_plan_price(), create_plan(), create_test_subscription(), deactivate_plan(), get_salon_subscription(), get_salon_trial(), list_events() (+15 more)

### Community 73 - "test_cashfree_subscription.py"
Cohesion: 0.13
Nodes (19): SubscriptionOrderRequest, adapter(), order(), request(), settings(), test_cancelled_refund_is_terminal_failure_in_api_and_webhook(), test_checkout_replay_and_server_verified_activation_use_existing_billing_flow(), handler() (+11 more)

### Community 74 - "routes/admin_insights.py"
Cohesion: 0.22
Nodes (9): BookingCounts, BulkPlanPriceResponse, MoneyTotals, MonthlyBookings, MonthlyMoney, SalonAnalyticsResponse, SalonSubscriptionRow, SalonSubscriptionSummary (+1 more)

### Community 76 - "FCMGateway"
Cohesion: 0.08
Nodes (9): FCMGateway, _is_permanent_fcm_error(), _token_ref(), test_expo_push_includes_notification_payload(), test_raw_fcm_receives_notification_payload_when_configured(), test_raw_fcm_without_credentials_records_failed_delivery(), test_provider_data_ignores_non_object_notification_data(), test_provider_data_merges_notification_data_as_strings() (+1 more)

### Community 77 - ".get_available_slots"
Cohesion: 0.05
Nodes (33): Customer booking window approval — 1 November 2026, B1 — Migration reconciliation and schema gap (BLOCKING), B2 — Shared staging/production database (BLOCKING), B3 — Bootstrap baseline incompatibility (BLOCKING), B4 — Old-client backward compatibility not certified (BLOCKING for 0042/0052), B5 — Erasure worker compatibility (BLOCKING for 0047/0048/0051), B6 — Production-environment readback and OIDC not live-verified, B7 — GitHub Free / private enforcement limitation (+25 more)

### Community 79 - "owner_setup.py"
Cohesion: 0.21
Nodes (6): build_setup_status(), _has_open_day(), mask_payout_account(), validate_payout_account(), test_setup_status_complete_and_partial_rules(), test_setup_status_fresh_owner_has_nothing_done()

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

### Community 86 - "test_plan_prices_sql.py"
Cohesion: 0.13
Nodes (15): _admin_id(), _apply_0049(), env(), _plans(), test_an_admin_edited_plan_price_is_not_overwritten_by_the_migration(), test_an_override_changes_only_that_salons_price_for_that_plan(), test_an_unknown_salon_or_plan_is_not_found(), test_clearing_goes_back_to_the_normal_price_and_is_idempotent() (+7 more)

### Community 87 - "Node/TypeScript MCP Server Implementation Guide"
Cohesion: 0.07
Nodes (27): Async/Await Best Practices, Building and Running, Character Limits and Truncation, Code Best Practices, Code Composability and Reusability, Complete Example, Error Handling, Key Imports (+19 more)

### Community 88 - "FakeWallet"
Cohesion: 0.08
Nodes (9): ask(), FakeWallet, owner(), settle(), TestCancel, TestMinimumPayout, TestRequestPayout, TestSummary (+1 more)

### Community 89 - "fastapi_testclient"
Cohesion: 0.13
Nodes (17): clear_salon_commission(), get_payment_settings(), get_salon_commission(), set_salon_commission(), _uc(), update_payment_settings(), PaymentSettingsResponse, PaymentSettingsUpdate (+9 more)

### Community 90 - "test_account_closure_steps.py"
Cohesion: 0.17
Nodes (21): closure_refund_provider_key(), phone_key_variants(), build(), FakeGateway, test_a_cache_failure_is_surfaced_not_swallowed(), test_a_provider_declining_the_refund_is_recorded_and_does_not_block(), test_a_provider_outage_retries_with_the_same_key_and_never_erases_early(), test_a_refund_that_cannot_be_issued_is_recorded_failed_after_the_cap() (+13 more)

### Community 91 - "test_api_input_bounds.py"
Cohesion: 0.12
Nodes (20): BookingCreateRequest, BlockedSlotCreateRequest, _booking(), _client(), test_action_request_total_price_stays_a_json_number(), test_blocked_slot_end_must_follow_start(), test_blocked_slot_requires_timezone_aware_datetimes(), test_blocked_slot_staff_id_is_uuid() (+12 more)

### Community 92 - "schemas/platform.py"
Cohesion: 0.05
Nodes (27): assign_staff_service(), create_service(), create_staff(), deactivate_service(), deactivate_staff(), get_staff_photo_upload_url(), list_services(), list_staff() (+19 more)

### Community 93 - "test_subscription.py"
Cohesion: 0.12
Nodes (18): ManualSubscriptionCreateRequest, SubscriptionStatus, is_subscription_promotion_active(), test_active_trialing_eligible_during_period(), test_active_trialing_ineligible_outside_period(), test_active_trialing_ineligible_with_null_dates(), test_cancelled_eligible_until_period_end(), test_cancelled_ineligible_after_period_end() (+10 more)

### Community 94 - "Website, customer app and owner app: developer handoff"
Cohesion: 0.10
Nodes (20): 1. Project and responsibility map, 2. Shared configuration and integration rules, 3. Shared customer workflows, 4. Website: screens and responsibilities, 5. Customer app: screens and responsibilities, 7. Shared notifications, profile, support and erasure, 8. Critical boundaries and release evidence, 9. Technical references (+12 more)

### Community 95 - "test_payment_settings_sql.py"
Cohesion: 0.12
Nodes (13): PaymentSettingsRepository, env(), _Reader, _reset(), test_a_change_of_rate_or_base_is_a_new_policy_version_but_the_minimum_is_not(), test_a_rate_without_a_base_or_a_base_without_a_rate_is_refused(), test_a_salon_rate_is_bounded_and_goes_with_the_salon(), test_a_salon_rate_is_read_next_to_the_platform_rate() (+5 more)

### Community 96 - "json"
Cohesion: 0.08
Nodes (19): get_redis_cache(), build_engines(), lifecycle_checks(), call(), create(), redis_control(), main(), bind() (+11 more)

### Community 97 - "Role"
Cohesion: 0.07
Nodes (34): GetMe, EnsureOwnerAccess, SubscriptionPlanUseCases, Role, profile(), FakeProfileRepository, _profile(), test_get_me_returns_active_actor() (+26 more)

### Community 98 - "booking_policy.py"
Cohesion: 0.09
Nodes (12): Booking, BookingLine, BookingSource, BookingStatus, PaymentStatus, allowed_status_transitions(), can_approve(), can_cancel() (+4 more)

### Community 99 - "page_bounds"
Cohesion: 0.06
Nodes (8): BookingActionRequestsMixin, NotificationsDevicesMixin, page_bounds(), _salon_actor_sql(), test_explicit_limit_is_kept_and_clamped_to_the_ceiling(), test_negative_offset_never_reaches_sql(), test_no_limit_applies_the_safety_ceiling(), test_offset_is_honoured_without_a_limit()

### Community 100 - "use_cases/subscription_billing.py"
Cohesion: 0.07
Nodes (20): SubscriptionEventKind, _body_amount(), SubscriptionBillingUseCases, SubscriptionWebhookHandler, IdempotencyKeyRequiredError, BillingInterval, BillingStatus, derive_entitlement() (+12 more)

### Community 101 - "SupabaseAuthGateway"
Cohesion: 0.11
Nodes (5): AuthTokens, channel_field(), SupabaseAuthGateway, test_password_reset_delegates_to_supabase_never_mints_tokens(), test_phone_otp_uses_supabase_verify_and_preserves_rejection()

### Community 102 - "test_public_discovery_contract.py"
Cohesion: 0.12
Nodes (14): add_salon(), catalog(), found(), test_a_paused_salon_offers_no_payment_method(), test_city_filter_is_exact_but_ignores_case_and_spaces(), test_filters_combine_with_and(), test_inactive_category_service_search_keeps_literal_wildcards(), test_nearby_supports_the_same_filters() (+6 more)

### Community 103 - "schemas/admin.py"
Cohesion: 0.11
Nodes (10): AdminCreateSalonRequest, AdminDeactivateSalonResponse, AdminRejectSalonRequest, AdminUpdateSalonRequest, CategoryCreateRequest, CategoryUpdateRequest, LanguageResponse, SubcategoryCreateRequest (+2 more)

### Community 104 - "test_accepting_bookings.py"
Cohesion: 0.05
Nodes (18): WalkInSalonResponse, WalkInServiceSummary, WalkInStaffSummary, WalkInVerifyPhoneRequest, WalkInVerifyPhoneResponse, SalonNotAcceptingBookingsError, test_migration_and_service_api_round_trip(), test_discovery_migration_review_and_qr_round_trip() (+10 more)

### Community 105 - "math"
Cohesion: 0.17
Nodes (15): analyse(), load(), main(), _money(), NumbersError, report(), sensitivity(), _sum() (+7 more)

### Community 106 - "PaymentGatewayResolver"
Cohesion: 0.08
Nodes (14): payment_webhook(), PaymentGateway, decorate(), timed(), load_adapter(), _adapter_module(), build_gateway(), PaymentGatewayResolver (+6 more)

### Community 107 - "config.py"
Cohesion: 0.05
Nodes (23): ProviderOrder, ProviderOrderState, ProviderPaymentState, ProviderRefund, PaymentOutcomeUnknownError, PaymentProviderError, Money, error_code_of() (+15 more)

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
Nodes (5): SalonApprovalRepository, WorkspaceRepository, AdminUseCases, CatalogAdminUseCases, UserNotifier

### Community 112 - "test_owner_finance_api.py"
Cohesion: 0.09
Nodes (77): make_owner(), env(), occurrence(), record(), rule(), test_a_retried_create_replays_and_a_different_body_with_the_same_key_is_refused(), test_a_retry_of_an_old_create_still_replays_after_its_start_date_left_the_window(), test_a_rule_may_start_in_the_future_or_up_to_a_month_back() (+69 more)

### Community 113 - "make_super_admin"
Cohesion: 0.06
Nodes (27): check_rate(), CommissionPolicy, resolve_commission_policy(), make_super_admin(), catalog_client(), FakeSettings, resolve(), TestResolve (+19 more)

### Community 114 - "test_booking_finance_sql.py"
Cohesion: 0.22
Nodes (19): Rules the build keeps, command(), finance(), outcome(), setup(), terminal(), test_admin_finance_requires_mfa_and_other_owner_cannot_read_statement(), test_checked_in_collection_capability_is_owner_scoped() (+11 more)

### Community 115 - "datetime"
Cohesion: 0.09
Nodes (9): SalonApprovalRequiredError, available_paise(), check_payout_day(), net_online_paise(), PayoutDateProblem, TestAvailable, TestNetOnline, TestPayoutDay (+1 more)

### Community 117 - "Changelog"
Cohesion: 0.10
Nodes (20): [0.1.3](https://github.com/supabase/agent-skills/compare/v0.1.2...v0.1.3) (2026-06-02), [0.1.4](https://github.com/supabase/agent-skills/compare/v0.1.3...v0.1.4) (2026-06-05), [0.1.5](https://github.com/supabase/agent-skills/compare/v0.1.4...v0.1.5) (2026-07-10), [0.1.6](https://github.com/supabase/agent-skills/compare/v0.1.5...supabase-v0.1.6) (2026-07-30), [0.1.7](https://github.com/supabase/agent-skills/compare/v0.1.6...supabase-v0.1.7) (2026-08-12), [0.1.8](https://github.com/supabase/agent-skills/compare/v0.1.7...supabase-v0.1.8) (2026-09-24), [0.1.9](https://github.com/supabase/agent-skills/compare/v0.1.8...supabase-v0.1.9) (2026-09-28), Bug Fixes (+12 more)

### Community 118 - "mumbai_browser.cjs"
Cohesion: 0.12
Nodes (12): { chromium }, fs, path, allowed, checks, {chromium}, data, errors (+4 more)

### Community 119 - "Any"
Cohesion: 0.12
Nodes (5): FakeExpoClient, FakeExpoResponse, FakeMappings, FakeResult, FakeSession

### Community 122 - "routes/finance.py"
Cohesion: 0.10
Nodes (41): add_adjustment(), add_expense(), add_expense_rule(), add_expenses_batch(), close_day(), daily_ledger(), expense_changes(), expense_summary() (+33 more)

### Community 123 - ".seed"
Cohesion: 0.08
Nodes (14): TestRuleCreatorErasure, TestRuleTable, adjustment(), cashbook_db(), close(), digest(), env(), expense() (+6 more)

### Community 124 - "WalkInUseCases"
Cohesion: 0.18
Nodes (5): WalkInUseCases, test_booking_context_rejects_cross_salon_and_keeps_qr_source(), test_booking_context_rejects_owner_before_database_lookup(), test_get_salon_by_qr_delegates(), test_get_salon_by_qr_not_found()

### Community 125 - "test_redis_recovery_sql.py"
Cohesion: 0.06
Nodes (20): get_probe_session(), get_session(), MeasuredAsyncSession, read_cache_snapshot(), save(), ask(), Gate, recovery() (+12 more)

### Community 126 - "Module Group 126"
Cohesion: 0.11
Nodes (19): 1.1 Understand Modern MCP Design, 1.2 Study MCP Protocol Documentation, 1.3 Study Framework Documentation, 1.4 Plan Your Implementation, 2.1 Set Up Project Structure, 2.2 Implement Core Infrastructure, 2.3 Implement Tools, 3.1 Code Quality (+11 more)

### Community 127 - "test_subscription_status_guard.py"
Cohesion: 0.45
Nodes (9): _admin(), test_cancel_allowed_from(), test_cancel_from_expired_conflicts(), test_missing_subscription_is_not_found(), test_repeat_cancel_is_idempotent_and_keeps_cancelled_at(), test_repeat_suspend_is_idempotent(), test_suspend_allowed_from(), test_suspend_from_terminal_conflicts() (+1 more)

### Community 129 - "Supabase"
Cohesion: 0.11
Nodes (15): Fix suggestion, Source, What happened, Skill Feedback, Steps, Core Principles, Debugging, Making and Committing Schema Changes (+7 more)

### Community 130 - "Admin"
Cohesion: 0.11
Nodes (18): Admin, GET `/v1/admin/catalog/categories`, GET `/v1/admin/catalog/categories/{category_id}/subcategories`, GET `/v1/admin/salons`, GET `/v1/admin/salons/{salon_id}`, GET `/v1/admin/salons/{salon_id}/onboarding`, PATCH `/v1/admin/catalog/categories/{category_id}`, PATCH `/v1/admin/catalog/subcategories/{subcategory_id}` (+10 more)

### Community 131 - "AccountErasureService"
Cohesion: 0.13
Nodes (3): AccountErasureService, ErasureVerificationError, RefundsPendingError

### Community 132 - "docs/README.md"
Cohesion: 0.11
Nodes (16): Checkout Safety and Verification Evidence, Account deletion (revision `0021_account_deletion`), Database plan, Payments and payout audit (migrations 0026, 0027), Folder structure, Account deletion contract (customer app, owner app, website), Frontend integration, Git workflow (+8 more)

### Community 133 - "test_image_families.py"
Cohesion: 0.08
Nodes (39): age_objects(), api_client(), _Clock, erasure_service(), gateway(), _grant(), key(), references() (+31 more)

### Community 134 - "test_booking_contract_sql.py"
Cohesion: 0.21
Nodes (18): AppError, _body(), _count(), _direct_book(), _qr_book(), _second_customer(), test_availability_after_sixty_local_days_is_empty(), test_customer_booking_later_than_sixty_local_days_is_rejected() (+10 more)

### Community 135 - "client_for"
Cohesion: 0.25
Nodes (6): client_for(), test_avatar_multipart_contract(), test_owner_gallery_serializes_database_uuid_ids(), test_owner_qr_does_not_require_storage(), test_owner_qr_repeated_clicks_keep_the_same_salon_identity(), test_report_frontend_contract_ignores_client_identity_and_timestamp()

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

### Community 140 - "schemas/booking.py"
Cohesion: 0.12
Nodes (8): AvailabilityResponse, BarberCancelBookingRequest, BookingLineResponse, CancelBookingRequest, DelayBookingRequest, NoShowBookingRequest, PaymentRequest, RejectBookingRequest

### Community 141 - "FinanceUseCases"
Cohesion: 0.06
Nodes (23): ExpenseRuleUseCases, FinanceUseCases, _paise(), fingerprint_of(), release_reservation(), require_idempotency_key(), _decode_cursor(), _encode_cursor() (+15 more)

### Community 142 - "schemas/platform.py"
Cohesion: 0.04
Nodes (45): LanguageResponse, PublicStaffResponse, ServiceCreateRequest, ServicePresentationRequest, ServiceResponse, ServiceUpdateRequest, StaffCreateRequest, StaffResponse (+37 more)

### Community 143 - "test_mumbai_forward_reconciliation.py"
Cohesion: 0.13
Nodes (9): canonical_sha256(), main(), normalized(), RecordingSession, test_both_columns_are_classified_as_scrubbed(), test_customer_clear_happens_before_profile_reference_detachment(), test_forward_chain_and_non_destructive_downgrade(), test_schema_adoption_preserves_both_values_and_rejects_definition_drift() (+1 more)

### Community 144 - "Env"
Cohesion: 0.11
Nodes (14): env(), Env, SubscriptionStateResponse, `GET /v1/salons/me/subscription` (owner), API, Design, Done when, Payment rules (do not skip) (+6 more)

### Community 145 - "Running Evaluations"
Cohesion: 0.12
Nodes (15): 1. Local STDIO Server, 2. Server-Sent Events (SSE), 3. HTTP (Streamable HTTP), Command-Line Options, Complete Example Workflow, Connection Errors, Evaluation File Format, Low Accuracy (+7 more)

### Community 146 - "Writing Guidelines for Postgres References"
Cohesion: 0.12
Nodes (15): 1. Concrete Transformation Patterns, 2. Error-First Structure, 3. Quantified Impact, 4. Self-Contained Examples, 5. Semantic Naming, Code Example Standards, Comments, Impact Level Guidelines (+7 more)

### Community 147 - "Customer App Backend API Contract"
Cohesion: 0.12
Nodes (17): Account deletion and closed salons, Audit result, Authentication, Availability, Avatar upload, Booking action requests, Booking list filters, Bulk notification read (+9 more)

### Community 148 - "ServiceUnavailableError"
Cohesion: 0.03
Nodes (21): get_auth_admin_gateway(), CreatedAuthUser, BookingSourceNotAllowedError, InsufficientBalanceError, OnlinePaymentUnavailableError, PayloadTooLargeError, PayoutAccountMissingError, PayoutBelowMinimumError (+13 more)

### Community 150 - "salon-backend"
Cohesion: 0.13
Nodes (14): Agents (`.claude/agents/`), Commands (run from `backend/`), Core backend agents, Founder skills (feature building and planning), graphify, Key rules, Layer map, Maintenance agents (+6 more)

### Community 151 - "Super-admin to owner review thread (spec; design, not built)"
Cohesion: 0.15
Nodes (15): resolved(), API (explicit `response_model`, status codes and `UUID` IDs), Authorization, Client impact (for the update lists), Data model (proposal), Decisions (from the interview), Erasure, Live status (+7 more)

### Community 152 - "Role"
Cohesion: 0.06
Nodes (27): require_role(), dependency(), BookingActionRequestUseCases, ClosureUseCases, ReportRepository, SubmitReport, AdminMFARequiredError, ForbiddenError (+19 more)

### Community 153 - "Progress: shifan"
Cohesion: 0.09
Nodes (23): 2026-10-24 continuation: lint/offline/live booking and fresh vendor check, 2026-10-31 — Gate B full-data rehearsal + owner production release authorization, Blockers, Cashfree verification continuation — 29 October 2026, Decisions, Decisions, Files touched, Files touched this session (+15 more)

### Community 154 - "RazorpayGateway"
Cohesion: 0.06
Nodes (18): RefundResult, SettlementAccount, SettlementAccountRequest, PaymentCapabilityError, measure_external(), CashfreeGateway, create_gateway(), _decimal() (+10 more)

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
Cohesion: 0.24
Nodes (8): analyse(), cross(), curves(), _f(), main(), PricingError, read(), report()

### Community 159 - "WalletUseCases"
Cohesion: 0.16
Nodes (5): _page_size(), _payout_entry(), WalletUseCases, can_cancel(), test_only_a_waiting_request_can_be_cancelled()

### Community 160 - "NotificationUseCases"
Cohesion: 0.33
Nodes (6): NotificationUseCases, test_deactivate_device_delegates_with_actor_id(), test_list_notifications_delegates(), test_mark_all_read_returns_updated_count(), test_mark_read_delegates(), test_register_device_passes_actor_id()

### Community 161 - "Progress: thameem/cloud-run-startup-investigation"
Cohesion: 0.15
Nodes (12): test_mumbai_validation_workflow_is_manual_and_has_no_scratch_service(), Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps (+4 more)

### Community 162 - "WalletAdminUseCases"
Cohesion: 0.17
Nodes (4): WalletAdminUseCases, PayoutAlreadyProcessedError, notify(), TestAdmin

### Community 163 - "Senior backend engineer"
Cohesion: 0.09
Nodes (23): 1. Start of every chat, 2. How a senior works, 3. When there is an error or failing test, 4. When improving or reviewing code, 5. Safe cleanup rules, 6. Database and money, 7. Security non-negotiables, 8. Definition of done (+15 more)

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
Cohesion: 0.11
Nodes (19): Access and availability notes, Catalog, Complete backend API reference for frontend teams, Customer, Errors and schema limitations, GET `/v1/catalog/categories`, GET `/v1/catalog/categories/{category_id}/subcategories`, GET `/v1/customer/profile` (+11 more)

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
Cohesion: 0.04
Nodes (49): portable_revisions(), require_mumbai_url(), require_unambiguous_url(), validate_evidence(), validate_migration_target(), validate_stamp_evidence(), 2. Is changing historical migration files safe?, Critical finding: the migration policy framework (+41 more)

### Community 174 - "collected_by_staff"
Cohesion: 0.19
Nodes (6): version(), collected_by_staff(), S1a — Staff earnings core (migration 0054, prepared only), S1b — Staff earnings API (owner only; staff get 403), S1c - Staff detail and the split (owner only; F19), TestCollectedByStaff

### Community 177 - "Database Reviewer"
Cohesion: 0.17
Nodes (11): 1. Query Performance (CRITICAL), 2. Schema Design (HIGH), 3. Security (CRITICAL), Anti-Patterns to Flag, Core Responsibilities, Database Reviewer, Diagnostic Commands, Key Principles (+3 more)

### Community 178 - "mcp-builder/SKILL.md"
Cohesion: 0.17
Nodes (8): Core MCP Documentation (Load First), 📚 Documentation Library, Evaluation Guide (Load During Phase 4), Language-Specific Implementation Guides (Load During Phase 2), MCP Server Development Guide, Overview, Reference Files, SDK Documentation (Load During Phase 1/2)

### Community 179 - "Progress: thameem/mumbai-forward-reconciliation"
Cohesion: 0.14
Nodes (14): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: thameem/mumbai-forward-reconciliation (+6 more)

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
Cohesion: 0.25
Nodes (8): test_custom_trial_limits_join_the_approval_transaction(), test_non_admin_cannot_read_or_modify_trial(), test_trial_http_response_and_no_anonymous_access(), test_trial_http_routes_reject_other_roles_before_repository_access(), session(), test_trial_inputs_reject_invalid_or_owner_supplied_fields(), test_trial_update_requires_both_limits_without_implicit_resets(), test_trial_update_uses_verified_admin_and_target_salon()

### Community 186 - "How to use the prompts"
Cohesion: 0.17
Nodes (11): Configuration: what belongs where, Critique and corrected product workflow, Frontend integration prompt pack, How to use the prompts, Model assignments and cost discipline, Prompt 0 — Backend readiness and corrected contract, Prompt 1 — Customer app, Prompt 2 — Owner app (+3 more)

### Community 187 - "test_cloud_run_auto.py"
Cohesion: 0.07
Nodes (23): require_verified_tls(), auto(), context(), health(), rollout(), patch(), state(), test_auto_refuses_unapproved_context() (+15 more)

### Community 189 - "test_release_configuration.py"
Cohesion: 0.07
Nodes (23): eligible(), forbidden(), modules(), saved_bundle(), test_actual_deploy_job_skips_when_authoritative_gate_is_false(), test_all_workflows_parse_and_actions_are_immutable(), test_artifact_substitution_is_rejected(), test_automatic_candidate_requires_tested_artifact_before_any_cloud_access() (+15 more)

### Community 190 - "routes/wallet.py"
Cohesion: 0.17
Nodes (19): _admin_use_cases(), cancel_payout(), list_payout_requests(), _owner_use_cases(), reject_payout(), request_payout(), reveal_payout_account(), wallet() (+11 more)

### Community 192 - "Pass 2 — Clean Architecture & Standards"
Cohesion: 0.20
Nodes (9): 1. Baseline before touching anything, 2. Review in three passes, 3. Apply or report, 4. Refactor one increment at a time, 5. Verify, then report, Pass 1 — Security, Pass 3 — Folder Structure, Salon Backend Code Refactorer (+1 more)

### Community 193 - "redis_recovery_browser.cjs"
Cohesion: 0.40
Nodes (3): {chromium}, readline, target

### Community 195 - "test_cloud_run_candidate.py"
Cohesion: 0.09
Nodes (18): attestation(), bootstrapped(), contract(), guarded(), schema_receipt(), test_attestation_target_and_paths_validated(), test_bootstrap_rejects_drift(), test_bootstrap_wrong_context_refused() (+10 more)

### Community 196 - "test_payment_ledger_sql.py"
Cohesion: 0.13
Nodes (16): _install_booking_window(), safety_db(), _alembic(), _build(), db_url(), _drop(), test_cash_and_online_capture_race_serialises_on_the_booking_lock(), test_earnings_use_the_snapshot_and_reversals() (+8 more)

### Community 197 - "WalletRepository"
Cohesion: 0.11
Nodes (4): decode_cursor(), encode_cursor(), _row(), WalletRepository

### Community 198 - "RedisCache"
Cohesion: 0.06
Nodes (23): RedisCache, validated_cache_reads(), test_database_health_returns_safe_503_when_database_is_unavailable(), test_redis_health_disabled_when_not_configured(), test_redis_health_ok_when_reachable(), test_redis_health_returns_503_when_ping_fails(), Store, test_booking_and_availability_never_read_or_write_payload_cache() (+15 more)

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

### Community 205 - "common.py"
Cohesion: 0.12
Nodes (8): update_salon_trial(), AdminApproveSalonRequest, _id_to_str(), _uuid_to_str(), SalonTrialResponse, TrialLimitsRequest, TrialUpdateRequest, test_approval_requires_a_booking_limit_and_has_no_default_for_it()

### Community 206 - "media/health.py"
Cohesion: 0.18
Nodes (12): heartbeat_path(), is_healthy(), main(), max_age_seconds(), touch(), setup_sweep(), test_dynamic_health_age(), test_heartbeat_missing_stale_failed_and_successful() (+4 more)

### Community 207 - "payments.py"
Cohesion: 0.27
Nodes (13): cancel_payment(), confirm_payment(), create_payment_intent(), get_settlement_account(), list_booking_payments(), my_earnings(), payment_config(), refresh_payment() (+5 more)

### Community 208 - "reconciliation_harness.py"
Cohesion: 0.16
Nodes (11): check_0042_destructive_ddl_applied(), check_alembic_version_at(), check_alembic_version_at_0050(), _check_project_confirmation(), _get_connection(), main(), print_stamp_manifest_inputs(), _require_env() (+3 more)

### Community 210 - "test_sql_bind_params.py"
Cohesion: 0.20
Nodes (5): _sql_string_literals(), test_no_bind_param_is_immediately_followed_by_a_pg_cast(), test_no_bind_param_null_check_is_untyped(), test_reference_cast_function_form_compiles_correctly(), test_reference_repro_of_the_broken_pattern()

### Community 211 - "source"
Cohesion: 0.15
Nodes (11): source(), AccessStateResponse, BookingCreateRequest, BookingResponse, GET `/v1/bookings`, Bookings, Closures and blocked time, Endpoint summary (+3 more)

### Community 212 - "Gate A — Isolated Full-Data Restore Evidence"
Cohesion: 0.07
Nodes (27): 0051 (owner_finance_cashbook), 0052 (booking_window_30_days), alembic current after each migration step, Backend test suite, Backup integrity (pre-restore), Destructive DDL confirmation, Gate A — Isolated Full-Data Restore Evidence, Gate B sequence executed on full-data Docker DB (+19 more)

### Community 213 - "booking_payments as Ledger Source of Truth"
Cohesion: 0.18
Nodes (8): Booking Lifecycle (pending/confirmed/completed/rejected/cancelled), Pausing New Bookings (accepting_bookings flag), Postgres Booking Functions (create_booking / get_available_slots), Salon Access State (trialing/soft_locked/subscribed_growth/subscribed_premium), Booking Masking for Locked Salons, Smart Slot Filler (Premium discount windows), SMS/Push Alert Circuit Breaker (Premium feature), Split Bill and Daily Ledger (commission rules)

### Community 215 - "test_closed_salon_statement.py"
Cohesion: 0.18
Nodes (8): client(), _month(), _Repo, test_only_super_admin_can_list_or_read_statements(), test_statement_derives_net_figures_and_totals_per_currency(), test_statement_of_a_salon_that_was_not_closed_by_deletion_is_not_found(), test_statement_with_no_transactions_is_empty_not_an_error(), _uc()

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
Cohesion: 0.11
Nodes (18): alembic current after each migration step, Destructive DDL reminder, For 0040_fastapi_only_access, For 0049_trial_salon_plan_prices (if applicable), Isolated Restore Evidence Template, Phase: 0049-equivalence, Phase: post-0041-0048 (optional mid-sequence check), Phase: post-0050 (+10 more)

### Community 223 - "OwnerPayoutAccountRequest"
Cohesion: 0.16
Nodes (5): put_payout_account(), _blank_to_none(), OwnerPayoutAccountRequest, _visible_photos(), PUT `/v1/salons/me/payout-account`

### Community 224 - "SalonSubscriptionUseCases"
Cohesion: 0.24
Nodes (5): _assert_admin(), SalonSubscriptionUseCases, test_cannot_create_subscription_with_terminal_status(), test_non_admin_cannot_manage_plans(), test_non_admin_cannot_manage_subscriptions()

### Community 226 - "Production Alembic baseline/bridge strategy — architecture review"
Cohesion: 0.06
Nodes (28): 10. Items requiring owner review before any bridge implementation begins, 1. Can Alembic safely begin at 0041 with no trustworthy baseline revision?, 3. Comparison of reconciliation approaches, 4. Recommended approach: A, with explicit stamp paradox resolution, 5. Truthfulness: how the bridge records production state without false claims, 6. How future upgrades reach 0051 and 0052 safely, 7. Destructive changes, incompatible signatures, and transformations requiring dedicated verification, 8. Restore-test evidence requirements beyond simple row counts (+20 more)

### Community 227 - "io"
Cohesion: 0.15
Nodes (8): get_qr_image(), _build_walkin_url(), make_qr_png(), make_qr_svg(), test_build_walkin_url_appends_token_to_route_prefix(), test_different_salon_tokens_produce_different_qr_images(), test_qr_render_is_deterministic_for_permanent_salon_identity(), test_printed_payload_is_the_web_route_plus_the_token()

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
Nodes (24): 0051 (owner_finance_cashbook), 0052 (booking_window_30_days), alembic current after each migration step, Backend test suite (step 11), Destructive DDL confirmation, Gate A — Isolated Restore Evidence, Gate B sequence executed on Docker DB, Gate C assessment (step 13) (+16 more)

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
Cohesion: 0.14
Nodes (21): cancellation_quote(), _remaining(), validate_customer_change(), validate_no_show(), test_actual_provider_cost_never_reduces_promised_refund(), test_aware_appointment_instants_are_required(), test_cancellation_exact_boundaries(), test_change_blocks_at_exactly_four_hours_and_later() (+13 more)

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
Cohesion: 0.14
Nodes (9): create_connection(), agent_loop(), evaluate_single_task(), extract_xml_content(), main(), parse_env_vars(), parse_evaluation_file(), parse_headers() (+1 more)

### Community 250 - "service"
Cohesion: 0.15
Nodes (16): service(), test_image_only_update_preserves_runtime(), Blockers and open questions, GET `/v1/salons`, GET `/v1/salons/nearby`, GET `/v1/salons/{salon_id}`, GET `/v1/salons/{salon_id}/services`, GET `/v1/salons/{salon_id}/staff` (+8 more)

### Community 251 - "test_messaging.py"
Cohesion: 0.07
Nodes (15): MessagingGateway, OutboundMessage, SendOutcome, _check_text(), render(), UnsafeMessageError, has_quota(), month_window() (+7 more)

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
Cohesion: 0.15
Nodes (11): preflight(), test_changed_trust_claim_fails_closed(), test_invalid_token_fails_closed(), test_jwt_decoder_never_logs_token(), token(), DeviceRegisterRequest, DeviceRegisterResponse, GET `/v1/media/results/{token}` (+3 more)

### Community 275 - "Operational Runbook (local setup, super-admin, workers)"
Cohesion: 0.11
Nodes (15): Operational Runbook (local setup, super-admin, workers), Architecture and cost boundary, Configuration, Cutover status, Resources and rollback, Shared production API domain migration — 27 October 2026, Verification so far, Backend README (+7 more)

### Community 277 - "test_reconciliation_finance_schema.py"
Cohesion: 0.17
Nodes (9): check_0049_subscription_plan_prices(), check_0051_finance_schema(), check_0052_booking_window_function(), Catalog, finance_tables(), test_booking_window_requires_both_exact_approved_function_bodies(), test_finance_schema_accepts_actual_migration_tables(), test_finance_schema_rejects_missing_day_close_table() (+1 more)

### Community 278 - "Mumbai reconciliation — least privilege — 2026-10-15"
Cohesion: 0.09
Nodes (19): 1. `supabase-schema-backup/` in Git, 2. Root `migration_mumbai_*.py` runners (13) - current split implemented, 3. Evidence note, Migration cleanup plan and execution record, Alembic migration, Checklist, Workflow, Authorized Local Cleanup 2026-10-15 (+11 more)

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

### Community 302 - "._scrub_owner_business"
Cohesion: 0.33
Nodes (4): Audit trail (migration `0027_payout_account_audit`), Owner payout accounts and setup checklist, Status, Storage and security

### Community 303 - "0015_salon_admin_approval.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_functions(), upgrade()

### Community 304 - "Production migration reconciliation — correction and safe path"
Cohesion: 0.07
Nodes (27): Approach A — New bridge migration (e.g., `0053_production_reconciliation_bridge`), Approach B — Idempotent forward repair (RECOMMENDED), Approach C — Compatibility release (hide endpoints until schema is ready), Approach D — Verified direct SQL with sequential Alembic stamps, Boundary 0: App-only release — NOT POSSIBLE, Boundary 1: Minimum schema release for core booking (0041–0045), Boundary 2: Schema compatibility release for erasure workers (add 0046, 0047, 0048), Boundary 3: Finance cashbook release (add 0049 idempotent, 0050 idempotent, 0051) (+19 more)

### Community 306 - "gcp-vm-release-compose.sh"
Cohesion: 0.50
Nodes (3): COMPOSE_ENV_FILE, COMPOSE_PROJECT_NAME, gcp-vm-release-compose.sh script

### Community 308 - "code-explorer.md"
Cohesion: 0.50
Nodes (3): Analysis Approach, Core Mission, Output Guidance

### Community 309 - "test_payout_proof_sql.py"
Cohesion: 0.21
Nodes (11): env(), mark_paid(), new_request(), record_payment(), test_a_file_that_is_not_an_allowed_type_or_whose_size_is_wrong_is_refused(), test_a_request_cannot_become_paid_without_a_recorded_payment(), test_deleting_the_admin_blanks_who_paid_but_keeps_the_record(), test_it_becomes_paid_once_the_payment_and_proof_exist_and_the_reference_matches() (+3 more)

### Community 310 - "Gate A for migrations 0053–0055 — 1 November 2026"
Cohesion: 0.12
Nodes (13): Completed retry with approved prices and 60-day window, Explicitly approved diagnostic retry, Gate A for migrations 0053–0055 — 1 November 2026, Local CI correction, Outstanding gates, Restore evidence, Retry after current catalog approval, Proposed production SQL execution — 0053 through 0055 (+5 more)

### Community 311 - "Clear Technical English"
Cohesion: 0.50
Nodes (3): Check the result, Clear Technical English, Write the explanation

### Community 312 - "CommissionPolicy"
Cohesion: 0.19
Nodes (7): CommissionPolicy, earned_commission(), half_up_div(), refund_reversals(), lines_for(), policy(), TestCommission

### Community 313 - "Payment integration: gap assessment and decision register"
Cohesion: 0.15
Nodes (11): PaymentConfirmRequest, Decisions made for the initial build, Decisions still needed from the business, Evidence levels used in this repo, Gap assessment (verified against source), Payment integration: gap assessment and decision register, Provider facts to re-verify in sandbox (not confirmed from official pages), Stage 1 build status (2026-10-12) (+3 more)

### Community 314 - "test_staff_earnings_domain.py"
Cohesion: 0.24
Nodes (4): earned_amount(), rule(), TestEarnedAmount, TestVersionsAndDates

### Community 318 - "subscription_billing_records table (purchase attempt tracking)"
Cohesion: 0.12
Nodes (19): Admin salon approval API endpoints, POST /v1/salons/me/complete-profile endpoint, Migration 0015 salon admin approval, Migration 0018 subscription foundation tables, Razorpay subscription webhook integration, subscription_billing_records table (purchase attempt tracking), Subscription entitlement states (active, grace, cancelled_paid_through, expired, none), payment-webhook-worker subscription reconciliation (reconcile_subscriptions_once) (+11 more)

### Community 319 - "Any"
Cohesion: 0.15
Nodes (8): check_0041_destructive_ddl_applied(), check_0049_primary_key(), check_0049_table_structure(), check_0050_column_exists(), check_baseline_0040_tables_exist(), check_empty_alembic_version(), check_fastapi_only_acl(), harness()

### Community 320 - "booking_finance_policy.py"
Cohesion: 0.15
Nodes (11): Allocation, _amount(), CancellationQuote, completed_service_allocation(), service_change_quote(), ServiceChangeQuote, test_completed_service_cost_shortfall_is_not_negative_salon_money(), test_completed_service_has_zero_platform_commission() (+3 more)

### Community 323 - "Production Release Execution Tracker — 2026-10-31"
Cohesion: 0.12
Nodes (16): Approved prices (owner confirmed 2026-10-31, Path A), Current production state (as of 2026-10-31 session), Execution sequence for next session, Full-data restore rehearsal (authoritative), Key evidence files, Permission change made, Phase 2 checklist — PREPARATION COMPLETE (restore verification pending), Phase 3 checklist — FULL-DATA RESTORE REHEARSAL COMPLETE (+8 more)

### Community 324 - "test_salon_approval.py"
Cohesion: 0.19
Nodes (11): test_admin_approval_routes_enforce_use_case_authorization(), test_admin_cannot_approve_inactive_or_incomplete_salon(), test_decisions_record_verified_admin_and_trim_reason_without_banning_owner(), test_http_returns_approval_code_for_pending_workspace(), session(), test_non_admin_cannot_reactivate_salon(), test_only_super_admin_can_review(), test_pending_owner_can_read_status_edit_setup_and_submit_onboarding() (+3 more)

### Community 325 - "_Result"
Cohesion: 0.18
Nodes (10): repo_with(), _Result, test_idempotency_first_use_reserves(), test_idempotency_mismatched_fingerprint_is_409(), test_idempotency_replays_completed_response(), test_idempotency_unfinished_original_is_in_progress(), test_observation_amount_mismatch_fails_row_and_never_captures(), test_observation_out_of_order_event_is_ignored() (+2 more)

### Community 327 - "AdminInsightsUseCases"
Cohesion: 0.16
Nodes (7): AdminInsightsUseCases, _assert_admin(), _counts(), _rollup_money(), test_a_bulk_offer_for_an_unknown_plan_is_a_clean_not_found(), get_plan(), test_no_payments_means_no_money_rows()

### Community 328 - "test_account_deletion_api.py"
Cohesion: 0.12
Nodes (4): client(), test_admin_ledger_is_super_admin_only_and_has_no_personal_fields(), test_deletion_blocked_409_body_contains_structured_counts(), test_domain_errors_map_to_documented_statuses()

### Community 333 - "reversal_due"
Cohesion: 0.20
Nodes (3): _half_up(), reversal_due(), TestReversalAfterRefund

### Community 334 - "Production Migration Execution Runbook"
Cohesion: 0.13
Nodes (14): Client compatibility requirements, Conditions for setting AUTO_DEPLOY_ENABLED=true (Gate C), Exact production commands (Gate B session, NOT AUTHORIZED YET), Finance endpoint checks (after Gate C: 0051), Gate A — backup + isolated restore test (required before any production step), Gate B — 0040→0050 production sequence, Gate C — 0051/0052 + AUTO_DEPLOY_ENABLED, Option 1: Maintenance window + write freeze (recommended for first release) (+6 more)

### Community 341 - "register_exception_handlers"
Cohesion: 0.10
Nodes (13): app_error_response(), _cors_headers(), register_exception_handlers(), app_error_handler(), http_exception_handler(), safe_validation_error_handler(), _sanitise(), unhandled_error_handler() (+5 more)

### Community 350 - "test_ci_registry_image.py"
Cohesion: 0.15
Nodes (6): registry(), command(), test_candidate_deploys_verified_digest_without_rebuild_or_repush(), test_changed_registry_image_rejected(), test_invalid_registry_provenance_rejected_without_network(), test_stale_main_never_pushes()

### Community 352 - "Owner finance: Phase 2 (local backend) implementation record"
Cohesion: 0.17
Nodes (12): A bug in Phase 2, found while designing this, and fixed, API additions since the Phase 1 contract (2026-10-29), Bug found by the tests and fixed in the migration, Deviations from the Phase 1 design (each deliberate), Erasure, Expense v2: custom name, batch push, change feed, month summary (2026-10-29), Gaps found while testing (read these), Not built yet (and why) (+4 more)

### Community 356 - "FakeRepo"
Cohesion: 0.14
Nodes (4): client(), FakeRepo, settings(), test_reconcile_applies_provider_truth_and_expires_unpaid_intents()

### Community 359 - "Payments"
Cohesion: 0.15
Nodes (13): booking_quote(), GET `/v1/bookings/{booking_id}/payments`, GET `/v1/payments/config`, GET `/v1/salons/me/earnings`, GET `/v1/salons/me/settlement-account`, Payments, POST `/v1/bookings/{booking_id}/payments/cancel`, POST `/v1/bookings/{booking_id}/payments/confirm` (+5 more)

### Community 396 - "cloud_run_candidate.py"
Cohesion: 0.10
Nodes (43): cleanup(), inspect_verified(), publish(), validate(), all_healthy(), api(), baseline(), cloud() (+35 more)

### Community 401 - "Progress: shifan-cloud-run-auto-deploy"
Cohesion: 0.08
Nodes (23): Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps, Progress: shifan-cloud-run-auto-deploy (+15 more)

### Community 408 - "routes/booking_finance.py"
Cohesion: 0.09
Nodes (12): admin_statement(), finance_command(), owner_statement(), AdminFinanceStatement, FinanceCommandRequest, OwnerPayoutStatement, BookingFinanceGateway, BookingFinanceUseCases (+4 more)

### Community 417 - "Rows"
Cohesion: 0.10
Nodes (6): execute_revision(), isolate(), migration_sql(), RollbackSession, Rows, test_upgrade_business_gates_owner_protection_and_downgrade()

### Community 418 - "Owner finance: Phase 0 discovery and approval request"
Cohesion: 0.10
Nodes (19): 10. Migration compatibility risks, 11. Proposed phases (unchanged from the brief), 1. Summary, 2. What exists today (verified in code), 3. Reuse, do not duplicate, 4.1 `salon_expenses` (append-only), 4.2 `salon_cash_adjustments` (append-only), 4.3 `salon_day_closes` (append-only revisions) (+11 more)

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
Cohesion: 0.15
Nodes (4): AuthUserContacts, FakeAdmin, FakeAuthAdmin, FakeAdmin

### Community 427 - "Latest main candidate — 2 November 2026"
Cohesion: 0.15
Nodes (11): Database, workers and remaining gate, Exact compatibility blocker, Immutable release identity, Latest main candidate — 2 November 2026, Promotion and rollback, Read-only verification, Evidence, Identity (+3 more)

### Community 429 - "test_staff_earnings_completion.py"
Cohesion: 0.08
Nodes (29): record_staff_earnings(), earnings(), finish(), test_a_booking_that_is_not_completed_earns_nothing(), test_a_completed_service_earns_its_staff_member_the_rule_in_force(), test_a_fixed_amount_above_the_price_is_capped_at_the_price(), test_a_problem_recording_earnings_never_stops_the_service_completing(), test_a_rule_made_after_completion_never_changes_the_earning() (+21 more)

### Community 431 - "expected_closing_cash"
Cohesion: 0.29
Nodes (3): expected_closing_cash(), TestExampleDay, TestCashFormula

### Community 432 - "Domain rules"
Cohesion: 0.20
Nodes (9): Account deletion, Booking, Cancellation, no-show and payout holds (owner-approved U08 target; not released), Domain rules, Migration state (31 October 2026 — Gate B COMPLETE), Payments, Public salon visibility, Roles (+1 more)

### Community 434 - "main"
Cohesion: 0.21
Nodes (9): erasure_probe(), call(), main(), actor_override(), selected_probe(), metadata(), probe(), record() (+1 more)

### Community 435 - "Owner finance: Phase 1 schema and API design (review only)"
Cohesion: 0.22
Nodes (9): 0. Assumptions used (the Phase 0 questions are not answered yet), 10. What still needs your decision before Phase 2, 1. Principles, 3. Reads that build the Daily Ledger (no new table), 4. Lock order (every write follows it, to avoid deadlock), 5. Audit events, 7. Privileges and row-level security, 9. Corrections and rollback (+1 more)

### Community 436 - "6. API contracts (all under `/v1`, JSON, paise, `Idempotency-Key` required on every write)"
Cohesion: 0.22
Nodes (9): 6. API contracts (all under `/v1`, JSON, paise, `Idempotency-Key` required on every write), `GET|POST /salons/me/commission-rules`, `GET /salons/me/ledger/daily?date=YYYY-MM-DD`, `GET /salons/me/ledger/range?from=&to=` (max 93 days), `GET /salons/me/staff-earnings?from=&to=`, `POST /salons/me/expenses`, `GET /salons/me/expenses?from=&to=&limit=&offset=`, `POST /salons/me/expenses/{id}/reverse`, `POST /salons/me/ledger/adjustments`, `POST /salons/me/ledger/days/{date}/close` (+1 more)

### Community 437 - "Cloud Run automatic-release gate fix — 1 November 2026"
Cohesion: 0.22
Nodes (7): Cloud Run automatic-release gate fix — 1 November 2026, Correction, Deployment safety retained, First automatic-run result, Proven skipped-release root cause, Verification scope, Main-merge Cloud Run configuration — 30 October 2026

### Community 438 - "salon_analytics"
Cohesion: 0.29
Nodes (5): bulk_set_plan_price(), list_salon_subscriptions(), salon_analytics(), salon_subscription_summary(), _uc()

### Community 439 - "public_api"
Cohesion: 0.25
Nodes (5): test_category_requires_service_assigned_to_active_staff(), test_category_uses_service_presentation_not_salon_business_label(), public_api(), database(), DatabaseHealthResponse

### Community 440 - "create_blocked_slot"
Cohesion: 0.18
Nodes (3): create_blocked_slot(), delete_blocked_slot(), list_blocked_slots()

### Community 441 - "_validate_not_production"
Cohesion: 0.18
Nodes (8): Backup, Gate A isolated restore evidence — 30 October 2026, Harness results, Isolated restore, Stop condition and cleanup, Safety checks (must all be confirmed before running harness), _validate_not_production(), test_production_url_blocked()

### Community 442 - "hmac"
Cohesion: 0.29
Nodes (5): verify_order_payment_signature(), hex_hmac(), test_decode_json_handles_text_and_python_values(), test_hex_hmac_matches_stdlib(), test_media_bucket_defaults_when_unset()

### Community 443 - "2. Proposed tables (text proposal, public schema, `salon_id uuid not null` everywhere)"
Cohesion: 0.25
Nodes (8): 2.1 `salon_expenses`, 2.2 `salon_cash_adjustments`, 2.3 `salon_day_closes` (one row per revision), 2.4 `booking_service_staff` (per-service attribution), 2.5 `staff_commission_rule_versions` (extends the approved G06 design), 2.6 `staff_earning_events` (append-only), 2.7 Premium messaging (built only at Phase 4; shown so the schema is reviewed once), 2. Proposed tables (text proposal, public schema, `salon_id uuid not null` everywhere)

### Community 444 - "Server-side WebP image families"
Cohesion: 0.17
Nodes (11): family_id(), Additive API contract, Admission and resource limits, Family retirement and account erasure, Keys, proof and compatibility, Local verification, 2026-10-19, Policy, Server-side WebP image families (+3 more)

### Community 445 - "CASHFREE_VERIFICATION_2026-10-29.md"
Cohesion: 0.25
Nodes (7): Activation finding, Activation prerequisites, Additional checks, Backend activation follow-up, Evidence, Local regression checks, Result

### Community 446 - "Canonical repository and Cloud Run CI/CD audit"
Cohesion: 0.22
Nodes (8): Approved IAM creation and readback, Canonical repository and Cloud Run CI/CD audit, GitHub configuration audit and changes, Implemented behavior, Local verification, Release hold, Repository and authentication, Verified GCP baseline

### Community 447 - "Production release preflight — 1 November 2026"
Cohesion: 0.25
Nodes (7): Candidate result, Current serving image, Fresh production observations, One-time supervised candidate — approved and verified, Outstanding release gates, Production promotion result, Production release preflight — 1 November 2026

### Community 448 - "Rows"
Cohesion: 0.18
Nodes (3): Rows, SQLiteSession, test_admin_list_selects_required_review_and_owner_fields()

### Community 449 - "BulkPlanPriceRequest"
Cohesion: 0.29
Nodes (4): BulkPlanPriceRequest, test_an_offer_end_without_a_timezone_is_refused_not_a_server_error(), test_the_bulk_request_needs_exactly_one_offer_input(), test_the_bulk_request_rejects_repeats_empty_and_oversized_lists_and_bad_ids()

### Community 450 - "install_database_metrics"
Cohesion: 0.32
Nodes (6): install_database_metrics(), after(), before(), PayoutHistoryEntryResponse, Payments and payee onboarding: stage 1 additions (backend only, dormant, not sandbox-tested), Payments and payout history (backend, dormant until a provider is configured)

### Community 451 - "create_walkin_booking"
Cohesion: 0.28
Nodes (3): create_walkin_booking(), _use_cases(), verify_phone()

### Community 452 - "Owner finance: Phase 3 (owner app) record"
Cohesion: 0.29
Nodes (5): Not verified, and why, Owner finance: Phase 3 (owner app) record, Still to do, Tests, What the owner sees

### Community 453 - "Local schema reconciliation rehearsal ? 29 October 2026"
Cohesion: 0.29
Nodes (7): Append-only correction, Local schema reconciliation rehearsal ? 29 October 2026, Offline OpenAPI release check, Rehearsed SQL order, Release gate, Results and retention impact, Source and recovery point

### Community 455 - "business_checks"
Cohesion: 0.20
Nodes (5): drain_notification_outbox(), run_forever(), business_checks(), create(), request()

### Community 459 - "PlanPriceSetRequest"
Cohesion: 0.33
Nodes (3): PlanPriceSetRequest, test_the_request_accepts_exactly_one_offer_input(), test_the_request_accepts_whole_rupees_and_paise()

### Community 463 - "Legacy Cloud Run baseline bootstrap"
Cohesion: 0.33
Nodes (5): Legacy Cloud Run baseline bootstrap, Migration gate, Other fixes, Verified baseline, Workflow selection after review

### Community 464 - "Cloud Run deployment gate audit — 1 November 2026"
Cohesion: 0.33
Nodes (5): Cloud Run deployment gate audit — 1 November 2026, Complete conditions and sources, One authoritative switch, Verification and activation, Verified defect

### Community 465 - "reseal_layout_evidence.py"
Cohesion: 0.33
Nodes (5): current_path(), digest(), main(), reseal(), rewrite()

### Community 466 - "Owner wallet and manual payouts"
Cohesion: 0.13
Nodes (13): 7. Safety, privacy and erasure, 8. Account erasure and retention, Admin routes (super admin + MFA), Model, Open decisions (not made in code), Owner routes (owner only; staff and customers get 403), Owner wallet and manual payouts, Payout proof (migration 0057, prepared, not applied) (+5 more)

### Community 469 - "schemas/support.py"
Cohesion: 0.39
Nodes (5): EmailEventResponse, SupportCreateRequest, SupportMessageResponse, SupportReplyRequest, SupportTicketResponse

### Community 471 - "6. Owner app and owner web: business workflows"
Cohesion: 0.33
Nodes (6): 6. Owner app and owner web: business workflows, Business resources, media and time off, Collections, payout and provider onboarding, Owner access, onboarding and review, Owner mobile subscription boundary, Owner screens and daily appointments

### Community 481 - "wif_claim_preflight.py"
Cohesion: 0.46
Nodes (5): decode_claims(), main(), request_claims(), require(), verify()

### Community 482 - "test_ci_artifact_cleanup.py"
Cohesion: 0.29
Nodes (3): cleanup(), test_other_artifact_never_deleted(), test_untrusted_context_never_deletes()

### Community 483 - "Features"
Cohesion: 0.67
Nodes (3): Account deletion (implemented, not yet production-verified), Features, Payment collection (backend)

### Community 484 - "Account Deletion"
Cohesion: 0.25
Nodes (8): Account Deletion, GET `/v1/account/deletion/{request_id}`, GET `/v1/admin/account-deletions`, GET `/v1/admin/deleted-salons`, GET `/v1/admin/deleted-salons/{salon_id}/statement`, POST `/v1/account/deletion`, POST `/v1/account/deletion/challenges`, POST `/v1/account/deletion/challenges/{challenge_id}/verify`

### Community 485 - "submit_report"
Cohesion: 0.33
Nodes (5): ReportRequest, ReportResponse, submit_report(), POST `/v1/reports`, Reports

### Community 486 - "Phase 3 — Docker prerequisites (complete before filling evidence below)"
Cohesion: 0.29
Nodes (7): 1. Download a fresh Supabase backup, 2. Start a local Docker PostgreSQL, 3. Restore the backup into Docker, 4. Set harness environment variables, 5. Run harness phases in sequence, Phase 3 — Docker prerequisites (complete before filling evidence below), Prerequisites checklist

### Community 487 - "test_list_bookings_scoping.py"
Cohesion: 0.43
Nodes (3): _list_sql(), test_customer_role_still_sees_only_own_bookings(), test_salon_roles_are_not_matched_on_their_personal_customer_bookings()

### Community 488 - "test_removed_profile_fields.py"
Cohesion: 0.38
Nodes (3): test_salon_cannot_clear_required_profile_details(), test_salon_rejects_removed_fields(), test_services_reject_optional_overrides()

### Community 489 - "Notifications"
Cohesion: 0.33
Nodes (6): DELETE `/v1/devices/{token}`, GET `/v1/notifications`, Notifications, POST `/v1/devices`, POST `/v1/notifications/{notification_id}/read`, POST `/v1/notifications/read-all`

### Community 492 - "Mumbai live catalog inspection (44 tables, 52 functions, empty Alembic history)"
Cohesion: 0.40
Nodes (5): Required owner approval decisions Q01-Q16 and A01-A06 before executable migration, Required 10-step forward-only reconciliation plan, Mumbai live catalog inspection (44 tables, 52 functions, empty Alembic history), RLS and privilege analysis (anon/authenticated zero rights, service_role broad rights), Minimum-rights contract (customer/owner/staff/finance/admin ceilings)

### Community 495 - "test_service_search_requires_active_category_and_subcategory"
Cohesion: 0.50
Nodes (3): _listed(), test_service_search_matches_what_the_services_list_shows(), test_service_search_requires_active_category_and_subcategory()

## Knowledge Gaps
- **28 isolated node(s):** `COMPOSE_ENV_FILE`, `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME`, `Footer – Making every appointment a little simpler`, `Our Founders Section – Ziyarad Huq CEO, Shifan NV CPO, Shoiball CMO` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 4245 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **196 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Profile` connect `Profile` to `NotFoundError`, `payments/booking.py`, `FeatureAccessRepository`, `require_super_admin`, `assert_approved_workspace`, `test_booking_contract_sql.py`, `use_cases/payout_proof.py`, `make_mock_repo`, `PlatformRepository`, `FinanceUseCases`, `ServiceUnavailableError`, `PaymentProviderNotConfiguredError`, `routes/admin.py`, `test_subscription_billing.py`, `routes/booking_finance.py`, `Role`, `test_checkout_email_telemetry.py`, `BookingPaymentUseCases`, `NotificationUseCases`, `ValidationError`, `SubscriptionProviderResolver`, `WalletAdminUseCases`, `WalletUseCases`, `AuthAdminGateway`, `test_booking_changes_sql.py`, `test_api_input_bounds.py`, `routes/payout_proof.py`, `unittest_mock`, `CacheGateway`, `use_cases/account_deletion.py`, `deps.py`, `routes/support.py`, `finance_ledger.py`, `routes/staff_earnings.py`, `salon_analytics`, `create_blocked_slot`, `post`, `routes/wallet.py`, `create_walkin_booking`, `test_salon_ranking.py`, `routes/auth.py`, `notifications.py`, `subscriptions.py`, `create_holiday`, `AdminInsightsUseCases`, `.list_notifications`, `SalonTrialUseCases`, `common.py`, `payments.py`, `ProfileRepository`, `fastapi_testclient`, `schemas/platform.py`, `BookingChangeGateway`, `test_subscription.py`, `OwnerPayoutAccountRequest`, `SalonSubscriptionUseCases`, `Role`, `booking_policy.py`, `use_cases/subscription_billing.py`, `submit_report`, `Payments`, `config.py`, `get_my_profile`, `AdminUseCases`, `test_owner_finance_api.py`, `make_super_admin`, `datetime`, `routes/finance.py`, `WalkInUseCases`, `test_subscription_status_guard.py`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Are the 243 inferred relationships involving `Profile` (e.g. with `get_authenticated_session()` and `get_current_actor()`) actually correct?**
  _`Profile` has 243 INFERRED edges - model-reasoned connections that need verification._
- **What connects `COMPOSE_ENV_FILE`, `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `NotFoundError` be split into smaller, more focused modules?**
  _Cohesion score 0.017588325652841783 - nodes in this community are weakly interconnected._
- **Why does `ValidationError` connect `ValidationError` to `NotFoundError`, `payments/booking.py`, `require_super_admin`, `assert_approved_workspace`, `test_booking_contract_sql.py`, `test_image_families.py`, `use_cases/payout_proof.py`, `test_admin_insights.py`, `make_mock_repo`, `PlatformRepository`, `FinanceUseCases`, `FakeRepo`, `test_cashfree_gateway.py`, `ServiceUnavailableError`, `PaymentProviderNotConfiguredError`, `BookingChangeRepository`, `test_payment_stage1_flows.py`, `RazorpayGateway`, `BookingPaymentUseCases`, `WalletUseCases`, `Rows`, `WalletAdminUseCases`, `unittest_mock`, `use_cases/account_deletion.py`, `deps.py`, `finance_ledger.py`, `AdminSalonsMixin`, `FinanceRepository`, `pytest`, `WalletRepository`, `test_salon_approval.py`, `AdminInsightsUseCases`, `test_cashfree_subscription.py`, `owner_setup.py`, `OwnerCatalogMixin`, `FakeWallet`, `test_subscription.py`, `SalonSubscriptionUseCases`, `Role`, `page_bounds`, `use_cases/subscription_billing.py`, `SupabaseAuthGateway`, `test_accepting_bookings.py`, `config.py`, `AdminUseCases`, `make_super_admin`, `datetime`, `ImageFamilies`, `WalkInUseCases`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 111 inferred relationships involving `ValidationError` (e.g. with `upload_avatar()` and `upload_signed_image()`) actually correct?**
  _`ValidationError` has 111 INFERRED edges - model-reasoned connections that need verification._
- **Should `payments/booking.py` be split into smaller, more focused modules?**
  _Cohesion score 0.04979570990806946 - nodes in this community are weakly interconnected._