# Graph Report - salon-backend  (2026-10-21)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 7305 nodes · 18314 edges · 353 communities (245 shown, 108 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2342 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `54c09ff0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- OwnerUseCases
- json
- exceptions.py
- Money
- owner.py
- RedisCache
- Role
- Profile
- routes/admin.py
- test_booking_contract_sql.py
- ForbiddenError
- AdminUseCases
- test_subscription_billing_sql.py
- StorageGateway
- test_payment_stage1_flows.py
- main.py
- use_cases/payments.py
- test_subscription_billing.py
- PillowImageProcessor
- FCMGateway
- platform_repository.py
- test_image_families.py
- time
- PaymentProviderError
- test_cashfree_gateway.py
- CashfreeGateway
- routes/payments.py
- test_walkin_qr_contract.py
- PaymentRepository
- test_payments_foundation.py
- CacheGateway
- routes/walkin.py
- BookingPaymentUseCases
- AuthAdminGateway
- ValidationError
- unittest_mock
- Settings
- PaymentGatewayResolver
- test_checkout_safety_sql.py
- deps.py
- post
- Any
- docs/README.md
- test_payment_flows.py
- alembic
- routes/booking_actions.py
- test_media_publication_safety.py
- use_cases/platform.py
- provision_super_admin.py
- test_migration_policy.py
- schemas/platform.py
- PaymentProviderNotConfiguredError
- use_cases/account_deletion.py
- pytest
- SQLAccountDeletionRepository
- panel.py
- PlatformRepository
- test_payout_account.py
- field_validator
- test_redis_recovery_sql.py
- SubscriptionProviderResolver
- test_account_deletion_api.py
- FakeBillingRepo
- connections.py
- Mumbai staging readiness audit — 2026-10-15
- BookingActionRepository
- use_cases/subscription_billing.py
- NotFoundError
- booking_policy.py
- 1. Business decisions Q01-Q30
- test_account_deletion_sql.py
- test_media_integration.py
- .create_booking
- MUMBAI_FORWARD_RECONCILIATION.md
- test_public_salon_visibility.py
- .get_available_slots
- .complete_owner_salon
- Ledger
- test_public_discovery_contract.py
- .get_owner_salon
- architect.md
- MCP Server Best Practices
- test_payment_fees_policy.py
- Node/TypeScript MCP Server Implementation Guide
- AuthGateway
- test_account_closure_steps.py
- SubscriptionWebhookHandler
- test_subscription.py
- config.py
- cleanup_worker.py
- evaluation.py
- AccountErasureService
- Salon Owner App Backend API Contract
- SupabaseAuthGateway
- routes/auth.py
- routes/support.py
- SubscriptionPlanRepo
- WalkInUseCases
- test_checkout_email_telemetry.py
- Checkout safety, email and verification
- Round 2: probe type, runtime and code change
- MCP Server Evaluation Guide
- Python MCP Server Implementation Guide
- readiness
- CustomerUseCases
- ConflictError
- test_upgrade_business_gates_owner_protection_and_downgrade
- test_media_admission_http.py
- G09: Slot-hold and concurrency support
- test_salon_ranking.py
- notifications.py
- ImageFamilies
- Changelog
- .apply_payment_observation
- Server-side WebP image families
- webhook_worker.py
- subscriptions.py
- Mumbai staging startup investigation — 16–17 October 2026 (IST)
- Payment, subscription and booking domain specification
- 🚀 High-Level Workflow
- test_account_erasure_hardening.py
- payment-subscription-booking-spec.md
- docs/migrations/README.md
- mumbai_browser.cjs
- Supabase
- test_payment_stage1_api.py
- FakeLedger
- FakeRepo
- chief-of-staff.md
- Changelog
- Customer App Backend API Contract
- entities/subscription.py
- account_deletion/worker.py
- Mumbai schema/history reconciliation — 2026-10-18
- API latency investigation — 2026-10-14
- importlib_util
- test_account_erasure.py
- Running Evaluations
- Writing Guidelines for Postgres References
- test_mumbai_forward_reconciliation.py
- ProfileUpdateRequest
- schemas/subscription.py
- Payment, subscription and booking migration designs
- Mumbai migration inspection — 2026-10-15
- Env
- test_vm_release.py
- salon-backend
- Any
- Env
- .get_public_salon
- G03: Cancellation policy and refund obligations
- Subscription & Promotion Foundation
- Image variants review and staging gate — 19 October 2026
- Review Priorities
- tdd-guide.md
- Rams Design Review
- unit_economics.py
- van_westendorp.py
- Owner billing (stage 2)
- .update_owner_staff
- SupportRepository
- G08: Closure/reschedule support
- test_docker_image_ids.py
- Rows
- FakeLedger
- Progress: thameem/cloud-run-startup-investigation
- Build Error Resolver
- Documentation & Codemap Specialist
- E2E Test Runner
- planner.md
- Refactor & Dead Code Cleaner
- Agent Instructions
- get_avatar_upload_url
- AccountDeletionRepository
- compute_commission
- account_deletion/health.py
- ._scrub_owner_business
- SupabaseAuthAdminGateway
- Marketplace model: API contract (single source for backend, apps and website)
- G01: Audit and authority foundation
- Approval decision register
- test_sql_bind_params.py
- Database Reviewer
- mcp-builder/SKILL.md
- Progress: {branch}
- Progress: thameem/cloud-run-mumbai-staging
- Progress: thameem/local-docker-cold-start
- Progress: thameem/provider-agnostic-payments
- How to use the prompts
- field_validator
- Account Deletion
- Final technical approval defaults - recommendations only
- Runbook
- Provider-independent payments: mock implementation
- Senior backend engineer
- Progress: thameem/mumbai-forward-reconciliation
- FakeStorage
- .paid
- G07: Subscription lifecycle
- 5. Mumbai migration-history decisions
- Stage 1 additions (Cashfree, multi-provider routing, monetary policy)
- Mumbai runtime validation — 2026-10-15
- ._w
- adapter
- Salon Backend Code Refactorer
- founder-board
- founder-ops
- Karpathy Guidelines
- Section Definitions
- Progress: shifan
- decode_json
- G04: Payout/dispute records
- G06: Staff commission ledger
- 4. Runtime privilege decisions
- 6. Redis concurrency decisions
- Mumbai destination migration — 2026-10-15
- reseal_layout_evidence.py
- FakeRepo
- founder-marketing
- founder-offer
- AuthUserContacts
- test_migration_and_service_api_round_trip
- test_notification_outbox_worker.py
- G02: Provider-fee reconciliation
- G05: Payout schedules
- Phase 1 decision sheet
- Authorized local cleanup - 2026-10-15
- Redis recovery verification — 2026-10-16
- lifecycle_checks
- IntakeLedger
- Agent memory
- Booking and payments
- founder-brand
- founder-competitors
- founder-plan
- founder-pricing
- Quality Checklist
- Web Application Testing
- Domain rules
- install_database_metrics
- 2. Cashfree/provider decisions P01-P06
- 3. Legal/accounting decisions L01-L05
- CI migration policy verification — 2026-10-16
- Mumbai Cloud Run staging deployment — 16 October 2026
- Local Docker cold-start measurement — 16 October 2026
- Mumbai staging readiness review — 2026-10-16
- 6. Money examples and snapshots
- 0029_payment_monetary_policy.py
- 0030_subscription_billing.py
- 0033_payment_fee_snapshot.py
- test_list_bookings_scoping.py
- client
- founder-cfo
- founder-launch
- Knex Migration Drift
- Quality Checklist
- Testing
- Workers and deploy
- email_gateway.py
- Frontend Integration Prompt — Redis Feature Changes
- 13. Exact questions requiring owner approval
- 2. Decision classification and confirmed rules
- 0022_salon_accepting_bookings.py
- 0026_booking_payments.py
- 0027_payout_account_audit.py
- run
- Evaluation Process
- Advanced MCP Features
- Advanced FastMCP Features
- Supabase Postgres Best Practices
- Migration cleanup plan and execution record
- Proposed treatment of the 43 unresolved fields
- CI password regression ? 2026-10-14
- 0001_baseline.py
- 0002_notifications_read_at.py
- 0003_google_oauth_profile_metadata.py
- 0004_service_duration_slot_steps.py
- 0005_staff_experience.py
- 0006_enable_realtime.py
- 0008_salon_images_soft_delete.py
- 0009_booking_cancellation_reason.py
- 0011_holiday_soft_delete.py
- 0024_secure_new_user_role.py
- 0025_salon_payout_accounts.py
- 0035_booking_checkout_safety.py
- gcp-vm-release-compose.sh
- FakeAuthGateway
- test_unchanged_legacy_avatar_is_compared_under_lock_before_save
- Performance analyst (read-only)
- Clear Technical English
- QrCodeUrlResponse
- phone_key_variants
- 0016_service_presentation.py
- 0018_subscription_foundation.py
- 0034_booking_lifecycle_states.py
- 0039_promotion_search_path.py
- check-container.sh
- gcp-vm-deploy.sh
- engine
- test_database_url_scheme.py
- code-architect.md
- start.md
- wrap.md
- schemas/__init__.py
- .begin_verify_attempt
- .cancel_open_bookings
- .claim_due_request
- .complete_request
- .confirm_deletion
- .count_blockers
- .count_closure_impact
- .count_recent_challenges
- .create_challenge
- .expire_challenge
- .expire_live_challenge
- .fail_request
- .finish_closure_refund
- .get_live_challenge
- .list_requests
- .list_unsettled_closure_refunds
- .profile_exists
- auth/__init__.py

## God Nodes (most connected - your core abstractions)
1. `Profile` - 346 edges
2. `PlatformRepository` - 244 edges
3. `Role` - 167 edges
4. `ValidationError` - 162 edges
5. `Settings` - 161 edges
6. `make_profile()` - 138 edges
7. `ForbiddenError` - 133 edges
8. `NotFoundError` - 123 edges
9. `make_mock_repo()` - 100 edges
10. `Money` - 97 edges

## Surprising Connections (you probably didn't know these)
- `1. Search salons by name, area and service` --references--> `SalonSummaryResponse`  [INFERRED]
  docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md → backend/app/api/v1/schemas/platform.py
- `Roles` --references--> `owner()`  [INFERRED]
  docs/agent-memory/shared/domain-rules.md → backend/tests/support_subscription.py
- `Where checks go` --references--> `require_role()`  [INFERRED]
  .claude/skills/auth-and-roles/SKILL.md → backend/app/api/deps.py
- `Status flow` --references--> `no_show()`  [INFERRED]
  .claude/skills/booking-and-payments/SKILL.md → backend/app/api/v1/routes/bookings.py
- `Payout account and setup checklist` --references--> `payout()`  [INFERRED]
  docs/Salon-Owner-App-Backend-API-Document.md → backend/tests/unit/test_fake_provider.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Cancellation money and slot policy (U03-U07)** — backend_docs_verification_payment_subscription_booking_spec_cancellation_bands, backend_docs_verification_payment_subscription_booking_spec_c28_cancellation_money, backend_docs_verification_payment_subscription_booking_spec_payout_hold_u07, backend_docs_verification_payment_subscription_booking_spec_slot_release_u04 [EXTRACTED 1.00]
- **Client-facing API contract documents** — docs_customer_app_backend_api_document_customer_app_backend_api_contract, docs_salon_owner_app_backend_api_document_salon_owner_app_backend_api_contract, docs_public_discovery_and_booking_contract, docs_frontend_integration_prompts [EXTRACTED 1.00]
- **Payment/subscription/booking design groups G01-G09** — backend_docs_migrations_payment_subscription_booking_designs_0048_admin_financial_audit, backend_docs_migrations_payment_subscription_booking_designs_0041_provider_fee_reconciliation, backend_docs_migrations_payment_subscription_booking_designs_0042_cancellation_policy_versions, backend_docs_migrations_payment_subscription_booking_designs_0043_payout_dispute_records, backend_docs_migrations_payment_subscription_booking_designs_0044_payout_schedules, backend_docs_migrations_payment_subscription_booking_designs_0045_staff_commission_ledger, backend_docs_migrations_payment_subscription_booking_designs_0046_subscription_lifecycle, backend_docs_migrations_payment_subscription_booking_designs_0047_business_closure_reschedule, backend_docs_migrations_payment_subscription_booking_designs_09_slot_hold_concurrency_support [EXTRACTED 1.00]
- **Shared agent-memory knowledge files** — docs_agent_memory_shared_architecture, docs_agent_memory_shared_gotchas_gotchas, docs_agent_memory_shared_domain_rules_domain_rules, docs_agent_memory_shared_conventions, docs_agent_memory_shared_decisions, docs_agent_memory_shared_commands, docs_agent_memory_shared_roadmap [EXTRACTED 1.00]
- **Cancellation money and hold policy approval chain** — backend_docs_migrations_payment_subscription_booking_designs_approval_register_policy_approval_record_u06, backend_docs_migrations_payment_subscription_booking_designs_approval_register_u07, backend_docs_migrations_payment_subscription_booking_designs_phase1_decision_sheet_phase_1_decision_sheet, backend_docs_migrations_payment_subscription_booking_designs_0042_cancellation_policy_versions_u03_bands [INFERRED 0.85]
- **Cloud Run and Docker cold-start measurement series** — backend_docs_verification_docker_cold_start_2026_10_16, backend_docs_verification_cloud_run_mumbai_staging_2026_10_16, backend_docs_verification_cloud_run_startup_investigation_2026_10_16, backend_docs_verification_cloud_run_startup_profile_2026_10_20 [INFERRED 0.85]
- **Cold-start measurement progress tracks** — docs_agent_memory_progress_thameem_local_docker_cold_start, docs_agent_memory_progress_thameem_cloud_run_mumbai_staging, docs_agent_memory_progress_thameem_cloud_run_startup_investigation [INFERRED 0.85]
- **Deployment and explicit migration policy** — backend_docs_ci_cd, backend_docs_docker_deployment_docker_deployment, backend_docs_migrations_migration_policy, backend_docs_migrations_mumbai_forward_reconciliation [INFERRED 0.85]
- **Image and media pipeline** — backend_docs_image_media, backend_docs_image_variants, backend_docs_image_integration_report, backend_docs_image_media_cleanup_worker [INFERRED 0.85]
- **Mumbai local staging evidence chain** — backend_docs_verification_mumbai_final_acceptance_2026_10_15, backend_docs_verification_mumbai_local_refresh_results_2026_10_15, backend_docs_verification_mumbai_redis_recovery_2026_10_16, backend_docs_verification_mumbai_staging_readiness_review_2026_10_16 [INFERRED 0.85]
- **Payment and subscription design docs** — backend_docs_payments_payments, backend_docs_payment_decisions, backend_docs_subscriptions, backend_docs_payout_accounts, backend_docs_runbook_payment_operations [INFERRED 0.85]

## Communities (353 total, 108 thin omitted)

### Community 0 - "OwnerUseCases"
Cohesion: 0.02
Nodes (12): NotFoundError, _canonical_json_value(), PlatformRepository, _request_fingerprint(), test_discovery_migration_review_and_qr_round_trip(), test_profile_response_normalizes_uuid_id_for_api_schema(), test_gallery_attach_retry_returns_existing_row_without_duplicate_insert(), test_service_response_normalizes_uuid_ids_for_api_schema() (+4 more)

### Community 1 - "json"
Cohesion: 0.05
Nodes (44): OwnerUseCases, _upload_extension(), _upload_result(), make_mock_repo(), make_owner(), test_non_owner_cannot_toggle(), test_patch_settings_forbidden_for_customer_and_pending_salon(), test_patch_settings_toggles_and_invalidates_salon_and_walkin_cache() (+36 more)

### Community 2 - "exceptions.py"
Cohesion: 0.05
Nodes (22): ProviderOrder, ProviderOrderState, ProviderPaymentObservation, ProviderPaymentState, ProviderRefund, ProviderSubscriptionEvent, SubscriptionClientConfig, SubscriptionOrderRequest (+14 more)

### Community 3 - "Money"
Cohesion: 0.05
Nodes (25): get_session(), run_forever(), metric(), main(), run(), measure(), summary(), rollback_checks() (+17 more)

### Community 4 - "owner.py"
Cohesion: 0.05
Nodes (41): assign_staff_service(), complete_profile(), create_blocked_slot(), create_holiday(), create_image(), create_service(), create_staff(), deactivate_service() (+33 more)

### Community 5 - "RedisCache"
Cohesion: 0.04
Nodes (31): get_authenticated_session(), get_cache(), get_current_actor(), test_migration_and_service_api_round_trip(), client(), _migration_statements(), _owner_salon(), test_migration_adds_column_and_gates_both_db_functions() (+23 more)

### Community 6 - "Role"
Cohesion: 0.05
Nodes (30): close_redis_cache(), _redacted_target(), RedisCache, validated_cache_reads(), read_cache_snapshot(), main(), test_snapshot_changes_on_commit_with_older_transaction_still_open(), test_redis_health_disabled_when_not_configured() (+22 more)

### Community 7 - "Profile"
Cohesion: 0.05
Nodes (35): _admin_use_cases(), approve_salon(), _catalog_use_cases(), create_category(), create_salon(), create_subcategory(), deactivate_category(), deactivate_salon() (+27 more)

### Community 8 - "routes/admin.py"
Cohesion: 0.04
Nodes (20): _extract_r2_object_key(), mask_payout_account(), validate_payout_account(), assert_approved_workspace(), Booking, BookingLine, BookingSource, BookingStatus (+12 more)

### Community 9 - "test_booking_contract_sql.py"
Cohesion: 0.07
Nodes (36): SettlementAccountRequest, PayoutProvider, IdempotencyKeyReuseError, EvidenceSource, PayoutRequest, PayoutStatus, ProviderFeeReconciliation, ProviderFees (+28 more)

### Community 10 - "ForbiddenError"
Cohesion: 0.04
Nodes (28): _add_request_id(), configure_logging(), get_request_id(), set_request_id(), init_sentry(), RequestMetrics, scrub_sentry(), TimingMiddleware (+20 more)

### Community 11 - "AdminUseCases"
Cohesion: 0.06
Nodes (56): AppError, OnlinePaymentUnavailableError, set_actor_context(), Cause and fix, CI password regression ? 2026-10-14, Masked SQLAlchemy URL password test defect, Repository and Docker cleanup, Verification (+48 more)

### Community 12 - "test_subscription_billing_sql.py"
Cohesion: 0.06
Nodes (51): PaymentOutcomeUnknownError, PaymentProviderError, build(), capture(), details(), FakeGateway, process_events(), claim() (+43 more)

### Community 13 - "StorageGateway"
Cohesion: 0.05
Nodes (27): portable_revisions(), require_mumbai_url(), require_unambiguous_url(), validate_evidence(), validate_migration_target(), do_run_migrations(), guard_requested_migration(), run_migrations_offline() (+19 more)

### Community 14 - "test_payment_stage1_flows.py"
Cohesion: 0.04
Nodes (12): get_storage_gateway(), get_image_family(), upload_avatar(), upload_signed_image(), AvatarResponse, ImageFamilyResponse, ImageVariantResponse, MediaReferences (+4 more)

### Community 15 - "main.py"
Cohesion: 0.07
Nodes (57): owner(), profile(), sub_settings(), adapter(), ent(), handler_for(), http(), make() (+49 more)

### Community 16 - "use_cases/payments.py"
Cohesion: 0.04
Nodes (23): SubscriptionReconciler, SubscriptionSettlement, get_settings(), Settings, reconcile_subscriptions_once(), Worker, test_auto_release_cannot_be_enabled_it_is_not_built(), test_blank_env_values_mean_unset_not_zero() (+15 more)

### Community 17 - "test_subscription_billing.py"
Cohesion: 0.06
Nodes (49): RefundStatus, both_client(), cf_settings(), event_body(), gateway(), IntakeRepo, intent_request(), order_handler() (+41 more)

### Community 18 - "PillowImageProcessor"
Cohesion: 0.05
Nodes (31): _row(), SubscriptionBillingRepository, _alembic(), _build(), db_url(), _drop(), recovery_db(), db_url() (+23 more)

### Community 19 - "FCMGateway"
Cohesion: 0.06
Nodes (16): SalonApprovalRepository, WorkspaceRepository, BookingIdempotencyKeyReusedError, ConflictError, IdempotencyInProgressError, PayAtSalonBlockedError, PayAtSalonDailyLimitError, PaymentAmountMismatchError (+8 more)

### Community 20 - "platform_repository.py"
Cohesion: 0.03
Nodes (5): downgrade(), upgrade(), downgrade(), upgrade(), downgrade()

### Community 21 - "test_image_families.py"
Cohesion: 0.07
Nodes (36): distribution(), docker(), inventory(), main(), remove_owned(), poll(), request(), stamp_ns() (+28 more)

### Community 22 - "time"
Cohesion: 0.05
Nodes (18): MeOutput, GetMe, EnsureOwnerAccess, ProfileRepository, can_read_own_profile(), is_customer(), is_staff(), is_super_admin() (+10 more)

### Community 23 - "PaymentProviderError"
Cohesion: 0.05
Nodes (12): FCMGateway, FakeExpoClient, FakeExpoResponse, FakeMappings, FakeResult, FakeSession, test_expo_push_includes_notification_payload(), test_raw_fcm_receives_notification_payload_when_configured() (+4 more)

### Community 24 - "test_cashfree_gateway.py"
Cohesion: 0.05
Nodes (27): HostedMediaRequest, BlockedSlotCreateRequest, BlockedSlotResponse, BookingLineResponse, CustomerAvailabilityResponse, DelayBookingRequest, HolidayCreateRequest, ImageUploadUrlResponse (+19 more)

### Community 25 - "CashfreeGateway"
Cohesion: 0.08
Nodes (26): ImagePolicy, ImageProcessor, ProcessedImageFamily, ProcessedVariant, PillowImageProcessor, namespace_for(), test_integrated_multipart_rejects_multiple_files_before_processing(), test_result_token_is_read_only_and_upload_token_is_not_a_result_token() (+18 more)

### Community 27 - "test_walkin_qr_contract.py"
Cohesion: 0.06
Nodes (3): AdminUseCases, CatalogAdminUseCases, UserNotifier

### Community 28 - "PaymentRepository"
Cohesion: 0.07
Nodes (22): PaymentEvent, ProviderPayment, apply_provider_payment(), _clean_code(), event_to_json(), observation_status(), derive_payment_state(), is_forward_transition() (+14 more)

### Community 29 - "test_payments_foundation.py"
Cohesion: 0.06
Nodes (12): get_auth_admin_gateway(), database_health(), health(), readiness(), redis_health(), DatabaseHealthResponse, HealthResponse, RedisHealthResponse (+4 more)

### Community 30 - "CacheGateway"
Cohesion: 0.11
Nodes (40): InvalidVerificationCodeError, make_profile(), build(), contacts(), FakeAuthGateway, test_a_subscription_bought_after_the_challenge_blocks_at_confirm(), test_active_subscription_blocks_only_with_a_real_provider(), test_admin_ledger_requires_super_admin() (+32 more)

### Community 31 - "routes/walkin.py"
Cohesion: 0.09
Nodes (36): age_objects(), api_client(), _Clock, erasure_service(), family(), gateway(), _grant(), key() (+28 more)

### Community 32 - "BookingPaymentUseCases"
Cohesion: 0.08
Nodes (22): require_role(), dependency(), BookingActionRequestUseCases, ClosureUseCases, AdminMFARequiredError, ForbiddenError, SalonApprovalRequiredError, Role (+14 more)

### Community 33 - "AuthAdminGateway"
Cohesion: 0.09
Nodes (26): BookingUseCases, BookingSourceNotAllowedError, make_booking(), test_approve_as_owner(), test_approve_requires_owner(), test_availability_delegates_to_repo(), test_booking_response_can_cancel_only_before_start_time(), test_booking_response_exposes_late_cancellation_and_cash_claim_eligibility() (+18 more)

### Community 35 - "unittest_mock"
Cohesion: 0.08
Nodes (18): _body_amount(), subscription_event_to_json(), SubscriptionBillingUseCases, BillingInterval, BillingStatus, derive_entitlement(), Entitlement, EntitlementState (+10 more)

### Community 36 - "Settings"
Cohesion: 0.07
Nodes (22): get_redis_cache(), build_engines(), get_probe_session(), MeasuredAsyncSession, lifecycle_checks(), call(), create(), bind() (+14 more)

### Community 37 - "PaymentGatewayResolver"
Cohesion: 0.10
Nodes (40): Deployment, Explicit migration policy, Mumbai validation and approval, Portable CI, Mumbai schema/history reconciliation 2026-10-18, Pre-migration approvals A01-A06, Forward-only reconciliation plan, 43 proposed financial tables absent in Mumbai (+32 more)

### Community 38 - "test_checkout_safety_sql.py"
Cohesion: 0.08
Nodes (17): PaymentGateway, PaymentCapabilityError, PaymentProviderNotConfiguredError, ignored(), NullPaymentGateway, _adapter_module(), build_gateway(), PaymentGatewayResolver (+9 more)

### Community 39 - "deps.py"
Cohesion: 0.06
Nodes (3): SQLAccountDeletionRepository, RecordingSession, test_customer_clear_happens_before_profile_reference_detachment()

### Community 40 - "post"
Cohesion: 0.09
Nodes (13): R2StorageGateway, test_token_purposes_stay_cryptographically_separate(), test_assert_configured_passes_when_all_settings_present(), test_assert_configured_raises_when_settings_missing(), test_delete_object_calls_boto3_delete(), test_delete_object_raises_validation_error_on_boto3_failure(), test_delete_object_raises_when_r2_not_configured(), test_get_client_caches_boto3_client_across_calls() (+5 more)

### Community 41 - "Any"
Cohesion: 0.07
Nodes (21): create_walkin_booking(), get_qr_image(), require_qr_token_format(), resolve_qr(), _use_cases(), verify_phone(), BookingCreateRequest, WalkInServiceSummary (+13 more)

### Community 42 - "docs/README.md"
Cohesion: 0.08
Nodes (14): RefundResult, SettlementAccount, measure_external(), decorate(), timed(), CashfreeGateway, create_gateway(), _decimal() (+6 more)

### Community 43 - "test_payment_flows.py"
Cohesion: 0.05
Nodes (40): Account Deletion, Account lock and session revocation, Admin visibility, Blockers (409 `deletion_blocked`), Boundaries (what is NOT erased), Deletion challenge/verify/confirm flow, Data-deletion matrix, Deployment (+32 more)

### Community 44 - "alembic"
Cohesion: 0.04
Nodes (35): Database And Booking Rules, Account-deletion behavior, Downgrade safety and rollback plan, Final technical approval defaults - recommendations only, G08: Closure/reschedule support, Indexes and constraints, PostgreSQL function and concurrency design, Purpose and compatibility (+27 more)

### Community 45 - "routes/booking_actions.py"
Cohesion: 0.05
Nodes (39): Deletion blockers (409 deletion_blocked), Closure refunds (salon_closed idempotency key), Access state (trial, soft wall, entitlements), Cancellation and refund quote, Masked bookings for locked salons, SMS alert fallback circuit breaker, Split-bill commission rules and daily ledger, Decisions made for the initial build (+31 more)

### Community 46 - "test_media_publication_safety.py"
Cohesion: 0.05
Nodes (43): Checkout safety, email and verification, Email and observability configuration, Email outbox worker (Resend), Evidence and outstanding verification, Implemented API contract, Reproducible local verification, Schema prepared for review, User story and boundaries (+35 more)

### Community 47 - "use_cases/platform.py"
Cohesion: 0.08
Nodes (26): heartbeat_path(), is_healthy(), main(), max_age_seconds(), touch(), run_forever(), storage_is_required(), validate_worker_configuration() (+18 more)

### Community 48 - "provision_super_admin.py"
Cohesion: 0.07
Nodes (23): header(), hex_hmac(), gateway_with(), hex_hmac(), make_settings(), test_configured_provider_needs_credentials(), test_create_intent_sends_paise_receipt_and_transfers(), handler() (+15 more)

### Community 49 - "test_migration_policy.py"
Cohesion: 0.05
Nodes (40): CI migration policy verification — 2026-10-16, Clean result and failures investigated, Exact verification commands, Migration readiness, Mumbai latency, Manual Mumbai migration validation workflow, Policy and changed paths, Redis and fresh Mumbai acceptance (+32 more)

### Community 50 - "schemas/platform.py"
Cohesion: 0.05
Nodes (41): Public discovery gate (approved, active, profile_completed), Smart slot filler (Premium), Mumbai empty Alembic history (restored schema), Database migrations, Layout, Portable CI target 0037 vs prepared Mumbai head 0040, Approval gate (awaiting_admin_approval 403), Owner push on decision (+33 more)

### Community 51 - "PaymentProviderNotConfiguredError"
Cohesion: 0.12
Nodes (21): approve_booking(), availability(), barber_cancel_booking(), cancel_booking(), check_in(), complete_booking(), create_booking(), delay_booking() (+13 more)

### Community 52 - "use_cases/account_deletion.py"
Cohesion: 0.09
Nodes (20): closure_refund_provider_key(), build(), FakeGateway, FakeLedger, test_a_cache_failure_is_surfaced_not_swallowed(), test_a_provider_declining_the_refund_is_recorded_and_does_not_block(), test_a_provider_outage_retries_with_the_same_key_and_never_erases_early(), test_a_refund_that_cannot_be_issued_is_recorded_failed_after_the_cap() (+12 more)

### Community 53 - "pytest"
Cohesion: 0.05
Nodes (38): account-deletion-worker erasure order (lock, cancel, notify, refund, settle, erase), Failed deployment and rollback, GitHub Actions to the GCP VM, GitHub configuration, One-time VM setup, Operate the deployed release, Release wrapper and rollback procedure, What runs (+30 more)

### Community 54 - "SQLAccountDeletionRepository"
Cohesion: 0.05
Nodes (38): Mumbai validation and approval manifest, Erasure classification and behavior, History reconciliation, Mumbai forward reconciliation — prepared, not executed, Prepared chain and expected schema, Rollback / execution gate, Backend skipped-test audit (14 skips, 5 fail when enabled), Backup evidence (+30 more)

### Community 55 - "panel.py"
Cohesion: 0.06
Nodes (21): add_salon(), catalog(), found(), _listed(), test_a_paused_salon_offers_no_payment_method(), test_city_filter_is_exact_but_ignores_case_and_spaces(), test_filters_combine_with_and(), test_inactive_category_service_search_keeps_literal_wildcards() (+13 more)

### Community 56 - "PlatformRepository"
Cohesion: 0.07
Nodes (29): _as(), client(), session(), _fingerprint(), _qr_booking_client(), test_a_real_slot_conflict_is_the_only_409_slot_unavailable(), test_different_instant_has_a_different_fingerprint(), test_direct_booking_over_http_is_recorded_as_app() (+21 more)

### Community 57 - "test_payout_account.py"
Cohesion: 0.05
Nodes (38): can_cancel(), Evidence and re-run, Final Mumbai local staging acceptance - 2026-10-15, Final result, Isolation, concurrency limits and cleanup, Redis failure and decision, Blocked gate 2: provider payment failure and refund settlement, Cashfree confirmation gates P01-P06 (+30 more)

### Community 58 - "field_validator"
Cohesion: 0.09
Nodes (20): _admin_base(), _assert_safe_existing_profile(), _AuthUser, _create_auth_user(), _FakeGateway, _find_user_by_email(), _get_profile_state(), main() (+12 more)

### Community 59 - "test_redis_recovery_sql.py"
Cohesion: 0.09
Nodes (32): captured_body(), load(), make_processor(), repo_with(), _Result, run(), sign(), test_0026_chain_tables_and_security_shape() (+24 more)

### Community 60 - "SubscriptionProviderResolver"
Cohesion: 0.10
Nodes (11): AccountDeletionUseCases, deletion_stage(), mask_contact(), normalize_contact(), ContactMismatchError, DeletionBlockedError, digest(), digests_match() (+3 more)

### Community 61 - "test_account_deletion_api.py"
Cohesion: 0.09
Nodes (15): create_ticket(), email_event(), read_ticket(), reply_ticket(), EmailEventResponse, SupportCreateRequest, SupportMessageResponse, SupportReplyRequest (+7 more)

### Community 62 - "FakeBillingRepo"
Cohesion: 0.14
Nodes (6): BookingPaymentUseCases, _fingerprint(), _json_default(), _ledger_row(), test_cashfree_disabled_never_builds_adapter_or_calls_provider(), test_refresh_requires_an_idempotency_key_and_a_provider()

### Community 63 - "connections.py"
Cohesion: 0.05
Nodes (37): test_mumbai_validation_workflow_is_manual_and_has_no_scratch_service(), Blockers and open questions, Mumbai staging cold-start audit (10 samples), Decisions, Done, Files touched, Goal, In progress (+29 more)

### Community 64 - "Mumbai staging readiness audit — 2026-10-15"
Cohesion: 0.05
Nodes (39): 10. Security, audit and account deletion, 11. Rollback and release risks, 12. Frontend handoff requirements, 13.1 Additional U02 approval questions, 13.2 Additional U03 monetary decisions, 13.3 U04 cancellation and recovery review, 13.4 U05 remaining review decisions, 13.5 Final technical approval defaults - recommendations only (+31 more)

### Community 65 - "BookingActionRepository"
Cohesion: 0.11
Nodes (28): _answer_ok(), check(), deal(), init(), load_state(), main(), _num(), PanelError (+20 more)

### Community 66 - "use_cases/subscription_billing.py"
Cohesion: 0.15
Nodes (27): confirm(), drain(), engine(), FakeAdmin, finish_ledger(), make_due(), make_service(), new_user() (+19 more)

### Community 67 - "NotFoundError"
Cohesion: 0.10
Nodes (23): FakeR2Client, storage_error(), gateway(), test_gateway_rejects_bad_metadata_keys_and_buckets(), test_gateway_rejects_expiry_tampering_and_wrong_mime_before_r2(), test_media_does_not_use_redis(), test_raw_storage_helper_is_not_exposed_and_family_type_is_required(), test_transient_head_failure_is_reported_not_silently_classed_as_legacy() (+15 more)

### Community 68 - "booking_policy.py"
Cohesion: 0.11
Nodes (12): get_profile(), get_salon(), list_public_categories(), list_public_subcategories(), list_salon_services(), list_salon_staff(), list_salons(), nearby_salons() (+4 more)

### Community 69 - "1. Business decisions Q01-Q30"
Cohesion: 0.08
Nodes (12): _blank_to_none(), HolidayResponse, ImageUploadUrlRequest, OwnerPayoutAccountRequest, ServiceCreateRequest, ServicePresentationRequest, ServiceUpdateRequest, Commands to run only after review (+4 more)

### Community 70 - "test_account_deletion_sql.py"
Cohesion: 0.08
Nodes (8): AccountErasureService, ErasureVerificationError, managed_media_path(), phone_key_variants(), RefundsPendingError, drain_account_deletions(), Account deletion worker, test_phone_key_variants_cover_every_spelling_and_ignore_junk()

### Community 71 - "test_media_integration.py"
Cohesion: 0.15
Nodes (22): get_subscription_provider_resolver(), cancel(), checkout(), list_purchasable_plans(), my_access_state(), my_subscription(), payments(), subscription_config() (+14 more)

### Community 72 - ".create_booking"
Cohesion: 0.12
Nodes (15): _action_use_cases(), apply_closure(), _closure_use_cases(), create_cancellation_request(), create_payment_confirmation_request(), list_booking_action_requests(), preview_closure(), respond_booking_action_request() (+7 more)

### Community 74 - "test_public_salon_visibility.py"
Cohesion: 0.11
Nodes (10): SubscriptionEventKind, PaymentWebhookUseCases, SubscriptionWebhookHandler, InvalidWebhookSignatureError, test_a_forged_signature_stores_nothing_and_both_providers_work_simultaneously(), subscription_side(), test_duplicate_delayed_and_out_of_order_webhooks_never_extend_twice(), deliver() (+2 more)

### Community 75 - ".get_available_slots"
Cohesion: 0.08
Nodes (10): CustomerUseCases, test_update_profile_allows_customer(), test_update_profile_allows_owner_personal_profile(), test_update_profile_rejects_staff_customer_surface(), gateway(), test_avatar_grants_have_distinct_keys(), test_inline_images_cannot_enter_media_records_or_cached_responses(), test_upload_capability_cannot_overwrite_a_published_object() (+2 more)

### Community 76 - ".complete_owner_salon"
Cohesion: 0.07
Nodes (5): MCPConnection, MCPConnectionHTTP, MCPConnectionSSE, MCPConnectionStdio, supabase

### Community 77 - "Ledger"
Cohesion: 0.08
Nodes (9): get_avatar_upload_url(), get_my_profile(), update_my_profile(), ReportRequest, ReportResponse, submit_report(), ReportRepository, SubmitReport (+1 more)

### Community 78 - "test_public_discovery_contract.py"
Cohesion: 0.09
Nodes (18): UploadAvatar, _cors_headers(), register_exception_handlers(), safe_validation_error_handler(), _sanitise(), unhandled_error_handler(), test_avatar_database_rollback_preserves_prior_reference_and_does_not_delete(), test_failed_avatar_publication_defers_cleanup_until_committed_reference_check() (+10 more)

### Community 79 - ".get_owner_salon"
Cohesion: 0.06
Nodes (31): 1. Business decisions Q01-Q30, Q01 - Approved cancellation bands; monetary finalization open, Q02 - Confirmed no-show process and remaining financial scope, Q03 - Exact 48/12/4-hour boundaries, Q04 - Fee bearers, reserves and deficits, Q05 - Completion hold and admin-controlled cancellation settlement, Q06 - Trial activation, cap and calendar, Q07 - Expiry, grace, receipts and late capture (+23 more)

### Community 80 - "architect.md"
Cohesion: 0.11
Nodes (13): deactivate_device(), list_notifications(), mark_all_notifications_read(), mark_notification_read(), register_device(), _use_cases(), DeviceRegisterRequest, DeviceRegisterResponse (+5 more)

### Community 81 - "MCP Server Best Practices"
Cohesion: 0.18
Nodes (20): cancel_subscription(), create_plan(), create_test_subscription(), deactivate_plan(), get_salon_subscription(), list_events(), list_plans(), _plan_uc() (+12 more)

### Community 83 - "Node/TypeScript MCP Server Implementation Guide"
Cohesion: 0.08
Nodes (13): build_setup_status(), _has_open_day(), _migration(), _migration_named(), _sql(), test_0027_shape(), test_field_validation_rejects_bad_input(), test_history_is_owner_only() (+5 more)

### Community 84 - "AuthGateway"
Cohesion: 0.11
Nodes (8): GatewayCapability, create_gateway(), from_paise(), RazorpayGateway, to_paise(), test_razorpay_booking_adapter_still_works_alongside(), test_capabilities(), test_paise_rounding()

### Community 86 - "SubscriptionWebhookHandler"
Cohesion: 0.12
Nodes (18): SalonSummaryResponse, SubscriptionStatus, is_subscription_promotion_active(), test_active_trialing_eligible_during_period(), test_active_trialing_ineligible_outside_period(), test_active_trialing_ineligible_with_null_dates(), test_cancelled_eligible_until_period_end(), test_cancelled_ineligible_after_period_end() (+10 more)

### Community 87 - "test_subscription.py"
Cohesion: 0.10
Nodes (7): RefundRequest, ProviderFeeReconciler, RefundProvider, WebhookVerifier, Implemented with mock provider, FakeGateway, test_refund_timeout_is_recovered_without_a_second_operation()

### Community 88 - "config.py"
Cohesion: 0.14
Nodes (21): make_super_admin(), catalog_client(), test_record_payment_requires_can_record_payment(), _migration(), test_admin_route_notifier_enqueues_without_booking_and_forwards_data(), test_admin_routes_hand_a_background_task_runner_to_the_use_case(), test_approve_notifies_owner_with_status_payload(), test_background_push_failure_is_swallowed() (+13 more)

### Community 89 - "cleanup_worker.py"
Cohesion: 0.07
Nodes (27): 1. Current State Analysis, 1. Modularity & Separation of Concerns, 2. Requirements Gathering, 2. Scalability, 3. Design Proposal, 3. Maintainability, 4. Security, 4. Trade-Off Analysis (+19 more)

### Community 90 - "evaluation.py"
Cohesion: 0.07
Nodes (28): Authentication and Authorization, DNS Rebinding Protection, Documentation Requirements, Error Handling, Error Handling, Input Validation, JSON Format (`response_format="json"`), Markdown Format (`response_format="markdown"`, typically default) (+20 more)

### Community 91 - "AccountErasureService"
Cohesion: 0.14
Nodes (4): refresh(), RefreshInput, AuthGateway, Refresh

### Community 92 - "Salon Owner App Backend API Contract"
Cohesion: 0.11
Nodes (13): BookingPaymentResponse, BookingQuoteRequest, BookingQuoteResponse, EarningsResponse, PaymentConfigResponse, PaymentConfirmRequest, PaymentIntentRequest, PaymentIntentResponse (+5 more)

### Community 93 - "SupabaseAuthGateway"
Cohesion: 0.11
Nodes (4): ClientConfig, PaymentIntent, PaymentIntentRequest, PaymentProvider

### Community 94 - "routes/auth.py"
Cohesion: 0.07
Nodes (27): Async/Await Best Practices, Building and Running, Character Limits and Truncation, Code Best Practices, Code Composability and Reusability, Complete Example, Error Handling, Key Imports (+19 more)

### Community 95 - "routes/support.py"
Cohesion: 0.18
Nodes (7): ValidationError, family_id(), ImageFamilies, member_path(), test_failure_to_derive_the_link_never_turns_a_stored_upload_into_an_error(), broken(), validate_context()

### Community 96 - "SubscriptionPlanRepo"
Cohesion: 0.08
Nodes (24): Migrations 0038-0040 (prepared, held, unapplied), Acceptance gate NOT READY for migrations, Blockers and open questions, Decisions, Done, Files touched, Goal, In progress (+16 more)

### Community 97 - "WalkInUseCases"
Cohesion: 0.08
Nodes (24): Cross-process Redis cache coherence failure, Read-model epoch cache invalidation after commit, QR booking durable PostgreSQL idempotency ledger, U06 cancellation money: captured minus penalty, 70/30 salon/platform pool, U03 customer cancellation bands (48h flat, 12h 5%, 4h 35%, under 4h zero refund), U07 payout hold formulas and 48h completed-service hold, U05 Redis outage fallback and durable outbox invalidation, U04 immediate slot release after committed cancellation (+16 more)

### Community 98 - "test_checkout_email_telemetry.py"
Cohesion: 0.08
Nodes (19): WebP image variants (commit 28bf921), U06/U07 cancellation and payout approvals, Commands, Decisions, Booking, Booking rules (create_booking, get_available_slots), Cancellation penalty bands and payout holds, Cancellation, no-show and payout holds (owner-approved U06/U07, not yet implemented) (+11 more)

### Community 99 - "Checkout safety, email and verification"
Cohesion: 0.12
Nodes (6): get_auth_gateway(), AuthTokens, channel_field(), SupabaseAuthGateway, test_password_reset_delegates_to_supabase_never_mints_tokens(), test_phone_otp_uses_supabase_verify_and_preserves_rejection()

### Community 100 - "Round 2: probe type, runtime and code change"
Cohesion: 0.14
Nodes (17): cancellation_deduction(), gateway_fee_amount(), payee_share(), _settings(), test_deduction_never_exceeds_amount_paid_and_never_negative(), test_flat_and_percent_rules_are_both_accepted_and_percent_is_capped(), test_flat_deduction(), test_gateway_fee_is_percent_rounded_half_up_to_paise() (+9 more)

### Community 101 - "MCP Server Evaluation Guide"
Cohesion: 0.14
Nodes (9): create_connection(), agent_loop(), evaluate_single_task(), extract_xml_content(), main(), parse_env_vars(), parse_evaluation_file(), parse_headers() (+1 more)

### Community 102 - "Python MCP Server Implementation Guide"
Cohesion: 0.16
Nodes (16): TooManyRequestsError, app_factory(), build(), forbidden_dependency(), assert_error(), oversized(), request_asgi(), test_allowed_origin_oversized_upload_has_shared_error_cors_and_timing() (+8 more)

### Community 103 - "readiness"
Cohesion: 0.18
Nodes (19): _actor(), add_salon(), ids(), ranked(), _subscribe(), test_admin_request_validates_priority(), test_admin_response_exposes_priority_and_audit_actor(), test_discovery_visibility_and_search_only() (+11 more)

### Community 104 - "CustomerUseCases"
Cohesion: 0.21
Nodes (15): FakeStorage, make_request(), make_service(), test_already_missing_auth_user_is_not_banned_and_delete_is_idempotent(), test_auth_delete_failure_is_retryable_and_resumes_without_repeating_steps(), test_customer_erasure_skips_salon_cache_keys(), test_lock_is_released_even_when_storage_fails(), test_missing_storage_configuration_fails_instead_of_skipping_media() (+7 more)

### Community 105 - "ConflictError"
Cohesion: 0.29
Nodes (17): test_actual_gps_exif_is_removed_from_every_variant(), test_grant_json_is_bounded_before_parsing(), test_metadata_gets_share_admission_and_reject_request_bodies(), Downstream, invoke(), scope(), test_ambiguous_framing_rejected(), test_binary_oversize_and_svg_rejected() (+9 more)

### Community 106 - "test_upgrade_business_gates_owner_protection_and_downgrade"
Cohesion: 0.21
Nodes (15): get_payment_gateway_resolver(), cancel_payment(), confirm_payment(), create_payment_intent(), get_settlement_account(), list_booking_payments(), my_earnings(), payment_config() (+7 more)

### Community 107 - "test_media_admission_http.py"
Cohesion: 0.23
Nodes (14): confirm_account_deletion(), get_deletion_status(), list_account_deletions(), start_deletion_challenge(), _use_cases(), verify_deletion_challenge(), AccountDeletionAcceptedResponse, AccountDeletionStatusResponse (+6 more)

### Community 108 - "G09: Slot-hold and concurrency support"
Cohesion: 0.13
Nodes (3): SalonSubscriptionRepo, SubscriptionEventRepo, SubscriptionPlanRepo

### Community 109 - "test_salon_ranking.py"
Cohesion: 0.09
Nodes (5): deliver_notification_outbox_event(), drain_notification_outbox(), enqueue_and_deliver_notification(), run_forever(), test_outbox_worker_marks_delivery_or_retry()

### Community 110 - "notifications.py"
Cohesion: 0.10
Nodes (19): Architecture, Caching and Idempotency, Redis caching and snapshot-validated read model, accepting_bookings pause switch, Action requests, Booking flow, Postgres create_booking / get_available_slots, Pausing new bookings (+11 more)

### Community 111 - "ImageFamilies"
Cohesion: 0.09
Nodes (23): Answer Guidelines, Complexity and Depth, Core Requirements, Diversity, Evaluation Examples, Evaluation Overview, Evaluation Requirements, Good Questions (+15 more)

### Community 112 - "Changelog"
Cohesion: 0.09
Nodes (23): Async/Await Best Practices, Code Best Practices, Code Composability and Reusability, Complete Example, Error Handling, Key Imports, MCP Python SDK and FastMCP, Overview (+15 more)

### Community 113 - ".apply_payment_observation"
Cohesion: 0.14
Nodes (8): save(), ask(), Gate, test_concurrent_http_booking_and_idempotent_retry_during_redis_outage(), session(), test_public_http_and_playwright_refresh_after_lost_invalidation(), test_two_processes_mutation_outage_reconnect_never_returns_stale(), worker()

### Community 114 - "Server-side WebP image families"
Cohesion: 0.09
Nodes (22): Account-deletion behavior, Atomic hold protocol and conflict behavior, Atomic intent and delivery identity, Audited operator repair, Authoritative availability and booking races, Commit, durable intent and idempotent invalidation, Downgrade safety and rollback plan, Final technical approval defaults - recommendations only (+14 more)

### Community 115 - "webhook_worker.py"
Cohesion: 0.15
Nodes (11): build(), write(), validate(), analyse(), cross(), curves(), _f(), main() (+3 more)

### Community 116 - "subscriptions.py"
Cohesion: 0.12
Nodes (6): get_payment_gateway(), get_payment_resolver(), drain_webhook_events(), reconcile_once(), run_forever(), test_drain_processes_each_due_event_once()

### Community 117 - "Mumbai staging startup investigation — 16–17 October 2026 (IST)"
Cohesion: 0.12
Nodes (8): forgot_password(), me(), owner_access(), ForgotPasswordRequest, ForgotPasswordResponse, ProfileResponse, RefreshRequest, TokenResponse

### Community 118 - "Payment, subscription and booking domain specification"
Cohesion: 0.18
Nodes (13): sweep_media(), heartbeat_path(), is_healthy(), main(), max_age_seconds(), touch(), setup_sweep(), test_dynamic_health_age() (+5 more)

### Community 119 - "🚀 High-Level Workflow"
Cohesion: 0.10
Nodes (20): [0.1.3](https://github.com/supabase/agent-skills/compare/v0.1.2...v0.1.3) (2026-06-02), [0.1.4](https://github.com/supabase/agent-skills/compare/v0.1.3...v0.1.4) (2026-06-05), [0.1.5](https://github.com/supabase/agent-skills/compare/v0.1.4...v0.1.5) (2026-07-10), [0.1.6](https://github.com/supabase/agent-skills/compare/v0.1.5...supabase-v0.1.6) (2026-07-30), [0.1.7](https://github.com/supabase/agent-skills/compare/v0.1.6...supabase-v0.1.7) (2026-08-12), [0.1.8](https://github.com/supabase/agent-skills/compare/v0.1.7...supabase-v0.1.8) (2026-09-24), [0.1.9](https://github.com/supabase/agent-skills/compare/v0.1.8...supabase-v0.1.9) (2026-09-28), Bug Fixes (+12 more)

### Community 120 - "test_account_erasure_hardening.py"
Cohesion: 0.17
Nodes (6): NotificationUseCases, test_deactivate_device_delegates_with_actor_id(), test_list_notifications_delegates(), test_mark_all_read_returns_updated_count(), test_mark_read_delegates(), test_register_device_passes_actor_id()

### Community 121 - "payment-subscription-booking-spec.md"
Cohesion: 0.17
Nodes (6): WalkInUseCases, QrSalonMismatchError, test_booking_context_rejects_cross_salon_and_keeps_qr_source(), test_booking_context_rejects_owner_before_database_lookup(), test_get_salon_by_qr_delegates(), test_get_salon_by_qr_not_found()

### Community 122 - "docs/migrations/README.md"
Cohesion: 0.26
Nodes (12): _repository(), _Result, test_cancellation_owner_decision_releases_slot_only_when_approved(), test_closure_rejects_changed_impact_set(), test_cross_salon_decision_is_hidden(), test_direct_payment_rejects_cancelled_booking(), test_duplicate_pending_request_is_rejected(), test_immediate_cancel_rejects_late_request() (+4 more)

### Community 123 - "mumbai_browser.cjs"
Cohesion: 0.14
Nodes (3): test_commission_snapshot_is_immutable_and_reversal_is_bounded(), test_earnings_use_the_snapshot_and_reversals(), test_excess_refund_via_refund_rows_leaves_booking_paid()

### Community 124 - "Supabase"
Cohesion: 0.11
Nodes (16): API latency investigation — 2026-10-14, Backend skipped-test audit, Changed files and reasons, E2E and safety status, Finding and evidence, Local Docker API connected to remote Supabase, sequential read-only health, Local synthetic API, 20 concurrent safe reads, Local synthetic API, sequential (+8 more)

### Community 125 - "test_payment_stage1_api.py"
Cohesion: 0.13
Nodes (7): app_factory(), get_user(), phone_verify(), session(), sign_in(), user(), fixture_manifest()

### Community 126 - "FakeLedger"
Cohesion: 0.11
Nodes (19): 1.1 Understand Modern MCP Design, 1.2 Study MCP Protocol Documentation, 1.3 Study Framework Documentation, 1.4 Plan Your Implementation, 2.1 Set Up Project Structure, 2.2 Implement Core Infrastructure, 2.3 Implement Tools, 3.1 Code Quality (+11 more)

### Community 127 - "FakeRepo"
Cohesion: 0.14
Nodes (4): AuthUserContacts, FakeAdmin, FakeAuthAdmin, FakeAdmin

### Community 128 - "chief-of-staff.md"
Cohesion: 0.26
Nodes (6): _assert_admin(), SalonSubscriptionUseCases, SubscriptionPlanUseCases, test_cannot_create_subscription_with_terminal_status(), test_non_admin_cannot_manage_plans(), test_non_admin_cannot_manage_subscriptions()

### Community 129 - "Changelog"
Cohesion: 0.17
Nodes (4): UnauthorizedError, SupabaseJWTVerifier, test_deactivated_account_jwt_returns_401_on_deletion_endpoints(), _raise_unauthorized()

### Community 130 - "Customer App Backend API Contract"
Cohesion: 0.12
Nodes (12): { chromium }, fs, path, allowed, checks, {chromium}, data, errors (+4 more)

### Community 132 - "account_deletion/worker.py"
Cohesion: 0.11
Nodes (15): Fix suggestion, Source, What happened, Skill Feedback, Steps, Core Principles, Debugging, Making and Committing Schema Changes (+7 more)

### Community 133 - "Mumbai schema/history reconciliation — 2026-10-18"
Cohesion: 0.12
Nodes (5): client(), FakeRepo, settings(), test_reconcile_applies_provider_truth_and_expires_unpaid_intents(), fetch_payment()

### Community 134 - "API latency investigation — 2026-10-14"
Cohesion: 0.17
Nodes (9): CommissionBase, commission_reversal(), compute_commission(), round_money(), test_zero_platform_commission_is_valid_in_the_commission_math(), test_commission_rejects_out_of_range_rate_and_never_exceeds_payment(), test_reversal_is_proportional_and_the_last_refund_absorbs_rounding(), test_round_money_is_half_up_and_coerces() (+1 more)

### Community 135 - "importlib_util"
Cohesion: 0.12
Nodes (16): 1. skip (auto-archive), 2. info_only (summary only), 3. meeting_info (calendar cross-reference), 4. action_required (draft reply), 4-Tier Classification System, Briefing Output Format, Example Invocations, Key Design Principles (+8 more)

### Community 136 - "test_account_erasure.py"
Cohesion: 0.12
Nodes (16): [1.2.0](https://github.com/supabase/agent-skills/compare/v1.1.1...v1.2.0) (2026-06-02), [1.3.0](https://github.com/supabase/agent-skills/compare/v1.2.0...v1.3.0) (2026-06-05), [1.4.0](https://github.com/supabase/agent-skills/compare/v1.3.0...v1.4.0) (2026-07-10), [1.5.0](https://github.com/supabase/agent-skills/compare/supabase-postgres-best-practices-v1.4.0...supabase-postgres-best-practices-v1.5.0) (2026-07-30), [1.6.0](https://github.com/supabase/agent-skills/compare/supabase-postgres-best-practices-v1.5.0...supabase-postgres-best-practices-v1.6.0) (2026-07-30), Bug Fixes, Bug Fixes, Bug Fixes (+8 more)

### Community 137 - "Running Evaluations"
Cohesion: 0.17
Nodes (7): load(), run(), test_0029_downgrade_restores_legacy_functions_and_drops_additions(), test_0029_shape_chain_and_idempotent_statements(), test_a_case_expression_never_sits_inside_a_plpgsql_if_condition(), test_commission_snapshot_arithmetic(), test_register_422_never_echoes_submitted_values_or_logs_them()

### Community 138 - "Writing Guidelines for Postgres References"
Cohesion: 0.12
Nodes (16): 10. Exact approvals before executable migration preparation, 1. Actual Mumbai migration/history state, 2. Differences from repository head 0040, 3. Existing objects reusable by the proposed designs, 4. Missing proposed objects, 5. Conflicting objects and semantics, 6. RLS and privilege risks, 7. Account-deletion and retention risks (+8 more)

### Community 139 - "test_mumbai_forward_reconciliation.py"
Cohesion: 0.12
Nodes (15): 1. Local STDIO Server, 2. Server-Sent Events (SSE), 3. HTTP (Streamable HTTP), Command-Line Options, Complete Example Workflow, Connection Errors, Evaluation File Format, Low Accuracy (+7 more)

### Community 140 - "ProfileUpdateRequest"
Cohesion: 0.12
Nodes (15): 1. Concrete Transformation Patterns, 2. Error-First Structure, 3. Quantified Impact, 4. Self-Contained Examples, 5. Semantic Naming, Code Example Standards, Comments, Impact Level Guidelines (+7 more)

### Community 141 - "schemas/subscription.py"
Cohesion: 0.18
Nodes (7): canonical_sha256(), main(), normalized(), test_both_columns_are_classified_as_scrubbed(), test_forward_chain_and_non_destructive_downgrade(), test_schema_adoption_preserves_both_values_and_rejects_definition_drift(), test_security_has_no_positive_default_or_future_client_grants()

### Community 142 - "Payment, subscription and booking migration designs"
Cohesion: 0.21
Nodes (9): ProfileUpdateRequest, StaffUpdateRequest, test_existing_hosted_media_urls_and_clearing_remain_supported(), test_profile_update_accepts_plus_91_storage_format(), test_profile_update_allows_repeated_digits_inside_valid_mobile(), test_profile_update_normalizes_indian_mobile(), test_profile_update_preserves_bundled_avatar_references(), test_profile_update_rejects_fake_or_invalid_mobile() (+1 more)

### Community 143 - "Mumbai migration inspection — 2026-10-15"
Cohesion: 0.13
Nodes (15): Design-review record and remaining approvals, Foundation, integration and activation order, Locking, compatibility and future verification, Minimum-rights contract, Payment, subscription and booking migration designs, Privacy and account erasure, Provider provenance contract, Readiness and approval gates (+7 more)

### Community 144 - "Env"
Cohesion: 0.13
Nodes (14): Alembic, Backup integrity and object inventory, Canonical mapping before edits, Commands run / not run, Continuation results after reconnection request, Cutover and rollback, Environment inventory (values omitted), Exact files inspected / changed (+6 more)

### Community 146 - "salon-backend"
Cohesion: 0.24
Nodes (10): release(), run_release(), test_containerd_manifest_id_is_accepted_from_verified_allowlist(), test_failed_readiness_does_not_promote_release(), test_migration_failure_preserves_previous_release_record(), test_missing_runtime_env_stops_before_migrations(), test_pre_deploy_failure_never_replaces_services(), test_release_rejects_implicit_head_before_any_docker_operation() (+2 more)

### Community 147 - "Any"
Cohesion: 0.13
Nodes (14): Agents (`.claude/agents/`), Commands (run from `backend/`), Core backend agents, Founder skills (feature building and planning), graphify, Key rules, Layer map, Maintenance agents (+6 more)

### Community 148 - "Env"
Cohesion: 0.14
Nodes (14): Account-deletion behavior, Admin and owner projection boundary under U03, Downgrade safety and rollback plan, Final technical approval defaults - recommendations only, G03: Cancellation policy and refund obligations, Historical U02 split and shared refund-cap invariants, Indexes and constraints, Purpose and compatibility (+6 more)

### Community 149 - ".get_public_salon"
Cohesion: 0.14
Nodes (14): Admin API contract, Config boundary, Current state (foundation, 0018), Events, Payment provider decision (shared or separate), Plans, Promotion eligibility, Public discovery ordering (+6 more)

### Community 150 - "G03: Cancellation policy and refund obligations"
Cohesion: 0.14
Nodes (13): Blockers that remain, Compose healthcheck: risk documented, behaviour not verified, Files changed after review entry (in addition to the entry list), New defect found by the partition review: `result_url` was an upload capability, Post-review update — 19 October 2026 (later session), Test results in this update, Blocked pending Cashfree account / requiring provider verification, Feature flags and isolation (+5 more)

### Community 151 - "Subscription & Promotion Foundation"
Cohesion: 0.19
Nodes (10): erasure_probe(), call(), main(), actor_override(), selected_probe(), metadata(), probe(), record() (+2 more)

### Community 152 - "Image variants review and staging gate — 19 October 2026"
Cohesion: 0.14
Nodes (13): Approval Criteria, CRITICAL — Error Handling, CRITICAL — Security, Diagnostic Commands, Framework Checks, HIGH — Code Quality, HIGH — Concurrency, HIGH — Pythonic Patterns (+5 more)

### Community 153 - "Review Priorities"
Cohesion: 0.14
Nodes (13): 1. Write Test First (RED), 2. Run Test -- Verify it FAILS, 3. Write Minimal Implementation (GREEN), 4. Run Test -- Verify it PASSES, 5. Refactor (IMPROVE), 6. Verify Coverage, Edge Cases You MUST Test, Quality Checklist (+5 more)

### Community 154 - "tdd-guide.md"
Cohesion: 0.14
Nodes (13): 1. Accessibility Review (WCAG 2.1), 2. Visual Design Review, Color & Contrast, Components, Critical (Must Fix), Guidelines, Layout & Spacing, Mode (+5 more)

### Community 156 - "unit_economics.py"
Cohesion: 0.19
Nodes (6): app_error_response(), PayloadTooLargeError, app_error_handler(), RequestTimeoutError, UnsupportedMediaTypeError, Admission findings 1 and 2: resolved, verified by tests

### Community 157 - "van_westendorp.py"
Cohesion: 0.33
Nodes (6): digest(), image_ids(), archive_fixture(), test_accepts_equivalent_ids_from_verified_archive(), test_legacy_archive_keeps_config_id(), test_rejects_unrelated_or_corrupt_metadata()

### Community 160 - "SupportRepository"
Cohesion: 0.15
Nodes (12): 1. Collect All Errors, 2. Fix Strategy (MINIMAL CHANGES), 3. Common Fixes, Build Error Resolver, Core Responsibilities, Diagnostic Commands, DO and DON'T, Priority Levels (+4 more)

### Community 161 - "G08: Closure/reschedule support"
Cohesion: 0.15
Nodes (12): 1. Analyze Repository, 2. Analyze Modules, 3. Generate Codemaps, 4. Codemap Format, Analysis Commands, Codemap Workflow, Core Responsibilities, Documentation & Codemap Specialist (+4 more)

### Community 162 - "test_docker_image_ids.py"
Cohesion: 0.15
Nodes (12): 1. Plan, 2. Create, 3. Execute, Core Responsibilities, E2E Test Runner, Fallback: Playwright, Flaky Test Handling, Key Principles (+4 more)

### Community 163 - "Rows"
Cohesion: 0.15
Nodes (12): 1. Requirements Analysis, 2. Architecture Review, 3. Step Breakdown, 4. Implementation Order, Best Practices, Plan Format, Planning Process, Red Flags to Check (+4 more)

### Community 164 - "FakeLedger"
Cohesion: 0.15
Nodes (12): 1. Analyze, 2. Verify, 3. Remove Safely, 4. Consolidate Duplicates, Core Responsibilities, Detection Commands, Key Principles, Refactor & Dead Code Cleaner (+4 more)

### Community 165 - "Progress: thameem/cloud-run-startup-investigation"
Cohesion: 0.17
Nodes (11): Agent Instructions, Auth Rules, Backend Architecture Rules, Code Ownership, Dependency And Setup Files, Deployment Rules, Secrets And Environment, Source of Truth (+3 more)

### Community 167 - "Documentation & Codemap Specialist"
Cohesion: 0.26
Nodes (7): PaymentCallback, build(), test_existing_customer_authorization_is_enforced_with_fake_provider(), test_fake_payment_and_refund_use_existing_intake_worker_and_replay_gate(), test_http_intake_rejects_tampering_and_cashfree_path_without_storing_effects(), test_sdk_callback_never_marks_a_mock_payment_paid(), test_callback_signature_vectors()

### Community 168 - "E2E Test Runner"
Cohesion: 0.17
Nodes (10): Account deletion / salon closure, Adding another subscription provider, Configuration, Endpoints, Entitlement (backend-derived), Flow, Mode and store-policy posture, Operator recovery (+2 more)

### Community 169 - "planner.md"
Cohesion: 0.18
Nodes (9): 1. `supabase-schema-backup/` in Git, 2. Root `migration_mumbai_*.py` runners (13) - current split implemented, 3. Evidence note, Migration cleanup plan and execution record, Authorized local cleanup - 2026-10-15, Backup preservation, Runner relocation, Verification and exact image removal (+1 more)

### Community 170 - "Refactor & Dead Code Cleaner"
Cohesion: 0.17
Nodes (12): Account-deletion behavior, Approval stage and before/after references, Downgrade safety and rollback plan, Financial identity, actor and command contract, G01: Audit and authority foundation, Immutable finalization and failure durability, Indexes and constraints, Later typed integration ownership (+4 more)

### Community 171 - "Agent Instructions"
Cohesion: 0.20
Nodes (5): _sql_string_literals(), test_no_bind_param_is_immediately_followed_by_a_pg_cast(), test_no_bind_param_null_check_is_untyped(), test_reference_cast_function_form_compiles_correctly(), test_reference_repro_of_the_broken_pattern()

### Community 172 - "get_avatar_upload_url"
Cohesion: 0.17
Nodes (3): offline_tools(), test_revision_review_preserves_sealed_evidence(), test_runner_imports_without_network_or_credentials()

### Community 173 - "AccountDeletionRepository"
Cohesion: 0.17
Nodes (11): 1. Query Performance (CRITICAL), 2. Schema Design (HIGH), 3. Security (CRITICAL), Anti-Patterns to Flag, Core Responsibilities, Database Reviewer, Diagnostic Commands, Key Principles (+3 more)

### Community 174 - "compute_commission"
Cohesion: 0.17
Nodes (8): Core MCP Documentation (Load First), 📚 Documentation Library, Evaluation Guide (Load During Phase 4), Language-Specific Implementation Guides (Load During Phase 2), MCP Server Development Guide, Overview, Reference Files, SDK Documentation (Load During Phase 1/2)

### Community 175 - "account_deletion/health.py"
Cohesion: 0.20
Nodes (4): What the database erasure does (step 5, one transaction, re-runnable), Appendix A. Live object inventory and comparison fingerprints, Activation, renewal, overlap (the SQL function), Tables (migration 0030)

### Community 176 - "._scrub_owner_business"
Cohesion: 0.18
Nodes (11): 0. Conventions, 1. Access state (trial, soft wall, entitlements), 2. Masked bookings (owner and staff views), 3. Payment modes, 4. Cancellation and refund quote (Pay Online), 5. Split-bill: commission rules and daily ledger, 6. Smart slot filler (Premium), 7. Alerts: delivery acknowledgement, session and settings (+3 more)

### Community 177 - "SupabaseAuthAdminGateway"
Cohesion: 0.18
Nodes (11): Approval decision register, Historical policy approval record U01, Policy approval record U02, Policy approval record U03, Policy approval record U04, Policy approval record U07, Policy review record U05, Recommended approval order (+3 more)

### Community 178 - "Marketplace model: API contract (single source for backend, apps and website)"
Cohesion: 0.18
Nodes (11): Final technical approval defaults - recommendations only, TA01 - Checked-in monetary remedy, TA02 - Owner/admin cancellation authority, TA03 - Retry count/backoff, TA04 - Outbox lease, TA05 - Dead-letter, TA06 - Alert targets, TA07 - Repair authorization (+3 more)

### Community 179 - "G01: Audit and authority foundation"
Cohesion: 0.18
Nodes (11): Cleanup, Cloud Run cold trials, Excluded trials and the pooler limit, Import review, Local baseline, Profiler, Recommended next steps, Result (+3 more)

### Community 180 - "Approval decision register"
Cohesion: 0.18
Nodes (11): Cleanup, Cloud Run A/B (TCP probe, gen1, 8 trials each, alternating), Code change, Combined effect, Garbage collection paused during startup (rc2), Infrastructure variants (production image, profiler with library phases), Measured cost on Cloud Run (6 trials, medians), Production configuration candidate (+3 more)

### Community 181 - "test_sql_bind_params.py"
Cohesion: 0.18
Nodes (7): Mumbai reconciliation — least privilege, Privilege decisions, Remaining gates, Alembic history reconciliation — no execution, Rollback / recovery, Exact grant evidence and limits, Exact known differences

### Community 183 - "Database Reviewer"
Cohesion: 0.22
Nodes (4): test_cached_walkin_requires_current_database_qr_validation(), test_detail_visibility_on_miss_and_stale_cache(), test_list_sources_only_return_approved_active_complete(), test_revocation_blocks_existing_and_late_cache_fills()

### Community 184 - "mcp-builder/SKILL.md"
Cohesion: 0.20
Nodes (10): Account-deletion behavior, Downgrade safety and rollback plan, Existing-schema compatibility and rollout, G07: Subscription lifecycle, Indexes and constraints, Purpose and compatibility, RLS/security impact, Tables and columns (+2 more)

### Community 185 - "Progress: {branch}"
Cohesion: 0.20
Nodes (10): 5. Mumbai migration-history decisions, MH01 - Restoration provenance and backfill uncertainty, MH02 - Independent PG17 reference strategy, MH03 - Full equivalence and accepted differences, MH04 - No-op compatibility versus forward repair, MH05 - Independent restored-history recording strategy, MH06 - Bounded executable preparation scope, MH07 - Final graph, IDs and target policy (+2 more)

### Community 186 - "Progress: thameem/cloud-run-mumbai-staging"
Cohesion: 0.20
Nodes (9): Addendum — independent review blockers fixed (19 October 2026), Admission middleware bypasses CORS and error envelope, Complete-diff scope and safety checks, Exact image-related files at review entry, Findings requiring correction, Image variants review and staging gate — 19 October 2026, Remaining risks and commit recommendation, Staging target and blocked prerequisites (+1 more)

### Community 187 - "Progress: thameem/local-docker-cold-start"
Cohesion: 0.20
Nodes (8): Blocked / untested, Evidence, Extra columns and Alembic, Failed attempts and SQL errors, Mumbai runtime validation — 2026-10-15, Passed, Rollback and scope proof, All 37 revisions ? final-state review

### Community 189 - "How to use the prompts"
Cohesion: 0.20
Nodes (9): founder-board, Output, Rules, Step 0: the idea file, Step 1: brief the board, Step 2: convene, Step 3: the chair's summary, The rule about the three names (+1 more)

### Community 190 - "field_validator"
Cohesion: 0.20
Nodes (9): founder-ops, Output, Step 1: what the business has to do every day, Step 2: suppliers, Step 3: people, Step 4: routines (SOPs), Step 5: tools, Step 6: licences, permits and insurance (+1 more)

### Community 191 - "Account Deletion"
Cohesion: 0.20
Nodes (9): 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution, 5. Don't Hide Confusion, 6. Question Assumptions, 7. Define Tests Upfront, 8. When in Doubt, Simplify (+1 more)

### Community 192 - "Final technical approval defaults - recommendations only"
Cohesion: 0.20
Nodes (9): 1. Start of every chat, 2. How a senior works, 3. When there is an error or failing test, 4. When improving or reviewing code, 5. Safe cleanup rules, 7. Security non-negotiables, 8. Definition of done, 9. Which tool for which job (+1 more)

### Community 193 - "Runbook"
Cohesion: 0.20
Nodes (9): 1. Query Performance (query), 2. Connection Management (conn), 3. Security & RLS (security), 4. Schema Design (schema), 5. Concurrency & Locking (lock), 6. Data Access Patterns (data), 7. Monitoring & Diagnostics (monitor), 8. Advanced Features (advanced) (+1 more)

### Community 194 - "Provider-independent payments: mock implementation"
Cohesion: 0.20
Nodes (10): Blockers and open questions, Decisions, Files touched, Goal, In progress, Next steps, Progress: shifan, Review findings (+2 more)

### Community 196 - "Progress: thameem/mumbai-forward-reconciliation"
Cohesion: 0.22
Nodes (9): Account-deletion behavior, Downgrade safety and rollback plan, G04: Payout/dispute records, Indexes and constraints, Purpose and compatibility, RLS/security impact, Tables and columns, U03 cancellation and no-show payout boundary (+1 more)

### Community 197 - "FakeStorage"
Cohesion: 0.22
Nodes (9): Account-deletion behavior, Canonical earning and formula enforcement, Downgrade safety and rollback plan, G06: Staff commission ledger, Indexes and constraints, Purpose and compatibility, RLS/security impact, Tables and columns (+1 more)

### Community 198 - ".paid"
Cohesion: 0.22
Nodes (9): 4. Runtime privilege decisions, RP01 - Effective identity and principal separation, RP02 - Object ACLs and function/publication boundaries, RP03 - Authority bootstrap and stages, RP04 - Rollback-safe audit and availability, RP05 - Canonical identity, attestation and key rotation, RP06 - Erasure powers, immutable guards and handoff, RP07 - Shared lock ranks and implicit-lock review (+1 more)

### Community 199 - "G07: Subscription lifecycle"
Cohesion: 0.22
Nodes (9): 6. Redis concurrency decisions, RC01 - Healthy/outage admission modes, RC02 - Atomic interval/resource representation, RC03 - Actor limits, renewal and transfer, RC04 - Expiry, cleanup and memory bounds, RC05 - Proof, API compatibility and privacy, RC06 - Commit, replay and invalidation, RC07 - Canonical SQL and buffer integration (+1 more)

### Community 200 - "5. Mumbai migration-history decisions"
Cohesion: 0.22
Nodes (8): Authenticated cold-start method and results, Configuration and secrets, Evidence, costs and verification limits, Existing Upstash validation, Final deployment, Mumbai Cloud Run staging deployment — 16 October 2026, salon-api-mumbai-staging Cloud Run service configuration, Upstash Redis validation (Mumbai)

### Community 201 - "Stage 1 additions (Cashfree, multi-provider routing, monetary policy)"
Cohesion: 0.22
Nodes (9): Completed cold-start results, Evidence and scope, Final verification and infrastructure separation, Findings before any configuration change, Individual natural cold requests, Inspected startup components, Local timing-only profiles, Mumbai staging startup investigation — 16–17 October 2026 (IST) (+1 more)

### Community 202 - "Mumbai runtime validation — 2026-10-15"
Cohesion: 0.22
Nodes (9): Backup and restore details, Clean-head comparison and stamping gate, Continuation after the user supplied the Session pooler, Customer Vercel browser continuation, Local artifacts, Local configuration and remaining inputs, Mumbai destination migration — 2026-10-15, Seeds and test accounts (+1 more)

### Community 204 - "adapter"
Cohesion: 0.33
Nodes (5): current_path(), digest(), main(), reseal(), rewrite()

### Community 205 - "Salon Backend Code Refactorer"
Cohesion: 0.50
Nodes (7): load(), run(), test_audit_trigger_escape_hatch_and_erasure_helper(), test_downgrade_restores_baseline_audit_trigger_and_drops_everything(), test_revision_chain_is_linear_after_media_guards(), test_upgrade_creates_bound_challenges_and_a_pii_free_ledger(), test_upgrade_relaxes_only_the_not_null_columns_erasure_must_clear()

### Community 206 - "founder-board"
Cohesion: 0.25
Nodes (4): receive(), send(), test_ingress_capacity_is_nonblocking_and_released(), test_total_receive_deadline_and_slot_release()

### Community 207 - "founder-ops"
Cohesion: 0.22
Nodes (8): founder-marketing, Output, Rules, Step 1: read the evidence, Step 2: positioning, Step 3: channels, Step 4: the 30-day campaign, Step 5: budget and numbers

### Community 208 - "Karpathy Guidelines"
Cohesion: 0.22
Nodes (8): founder-offer, Output, Rules, Step 1: read what is already known, Step 2: the problem list, Step 3: solutions, trimmed and stacked, Step 4: score it, Step 5: re-test it

### Community 211 - "decode_json"
Cohesion: 0.25
Nodes (8): Account-deletion behavior, Downgrade safety and rollback plan, G02: Provider-fee reconciliation, Indexes and constraints, Purpose and compatibility, RLS/security impact, Tables and columns, Unresolved approval and readiness

### Community 212 - "G04: Payout/dispute records"
Cohesion: 0.25
Nodes (8): Account-deletion behavior, Downgrade safety and rollback plan, G05: Payout schedules, Indexes and constraints, Purpose and compatibility, RLS/security impact, Tables and columns, Unresolved approval and readiness

### Community 213 - "G06: Staff commission ledger"
Cohesion: 0.29
Nodes (4): Dominant cold-start span precedes application lifespan, Supabase pooler 15-client limit equals production connection budget, Startup probe period adds about 3s to cold start, scripts/startup_profile.py profiler

### Community 214 - "4. Runtime privilege decisions"
Cohesion: 0.25
Nodes (8): Cleanup plan — commands for later review, not executed, Cost risk and free allowances, Evidence, Infrastructure ownership and cost audit — 16–17 October 2026 (IST), Upstash status and limits of verification, Verified inventory, VM and production path, What the current work is doing

### Community 215 - "6. Redis concurrency decisions"
Cohesion: 0.25
Nodes (8): Auth, Storage and staging contract, Connection and latency, Evidence, Mumbai staging readiness audit — 2026-10-15, Permissions, ownership and business tests, Phase ledger, Required actions and next approval, Schema inventory and reconciliation

### Community 218 - "FakeRepo"
Cohesion: 0.25
Nodes (7): Agent memory, Layout, Privacy, Progress file sections, Promote progress -> shared, SESSIONS.md row, Writing rules

### Community 219 - "founder-marketing"
Cohesion: 0.25
Nodes (7): founder-brand, Output, Rules, Step 1: read the brief, Step 2: name candidates, Step 3: voice and promise, Step 4: the look, as a brief

### Community 220 - "founder-offer"
Cohesion: 0.25
Nodes (7): founder-competitors, Output, Step 1: who is there, Step 2: the facts, Step 3: what their customers say, Step 4: the map and the gap, The rules

### Community 221 - "AuthUserContacts"
Cohesion: 0.25
Nodes (7): founder-plan, Output, Rules, Step 1: see what is there, Step 2: the summary, Step 3: compile, Step 4: the one-pager

### Community 222 - "test_migration_and_service_api_round_trip"
Cohesion: 0.25
Nodes (7): founder-pricing, Output, Rules, Step 1: what buyers said, Step 2: what competitors charge, Step 3: what the business needs, Step 4: decide

### Community 223 - "test_notification_outbox_worker.py"
Cohesion: 0.25
Nodes (8): Advanced Features (where applicable), Code Quality, Implementation Quality, Project Configuration, Quality Checklist, Strategic Design, Testing and Build, TypeScript Quality

### Community 224 - "G02: Provider-fee reconciliation"
Cohesion: 0.25
Nodes (7): Best Practices, Common Pitfall, Decision Tree: Choosing Your Approach, Example: Using with_server.py, Reconnaissance-Then-Action Pattern, Reference Files, Web Application Testing

### Community 225 - "G05: Payout schedules"
Cohesion: 0.33
Nodes (5): install_database_metrics(), after(), before(), Payments and payee onboarding: stage 1 additions (backend only, dormant, not sandbox-tested), Payments and payout history (backend, dormant until a provider is configured)

### Community 226 - "Phase 1 decision sheet"
Cohesion: 0.29
Nodes (7): 2. Cashfree/provider decisions P01-P06, P01 - Actual charges and canonical economic identity, P02 - Withholding and release feasibility, P03 - Schedule/calendar capabilities, P04 - KYC and destination lifecycle, P05 - Signatures, finality, retries and recovery, P06 - Funding and cross-method transfer identity

### Community 227 - "Authorized local cleanup - 2026-10-15"
Cohesion: 0.29
Nodes (7): 3. Legal/accounting decisions L01-L05, L01 - Customer terms and dispute rights, L02 - Tax, invoices, recognition and chart of accounts, L03 - Permitted custody, reserves and recovery, L04 - Staff recognition and lawful correction/recovery, L05 field-level subdecisions, L05 - Retention, anonymization and evidence access

### Community 228 - "Redis recovery verification — 2026-10-16"
Cohesion: 0.29
Nodes (7): A. Handoff rules, B. Money rules, C. Technical defaults TA01 to TA10, D. Still needing a decision, E. Items that can stay unresolved (ship inert, disabled by flag), F. What happens next, Phase 1 decision sheet

### Community 229 - "lifecycle_checks"
Cohesion: 0.29
Nodes (3): Alembic migration, Checklist, Workflow

### Community 230 - "IntakeLedger"
Cohesion: 0.29
Nodes (7): Deliverables and schema before/after, Erasure behavior, Evidence, Exact baseline, comparison and history, Mumbai forward revisions — prepared only, Rollback and exact remaining risks, Validation

### Community 231 - "Agent memory"
Cohesion: 0.38
Nodes (3): downgrade(), _sql(), upgrade()

### Community 232 - "Booking and payments"
Cohesion: 0.43
Nodes (4): downgrade(), _sql(), upgrade(), _validate()

### Community 233 - "founder-brand"
Cohesion: 0.38
Nodes (3): downgrade(), _sql(), upgrade()

### Community 234 - "founder-competitors"
Cohesion: 0.33
Nodes (3): business_checks(), create(), request()

### Community 235 - "founder-plan"
Cohesion: 0.43
Nodes (3): _list_sql(), test_customer_role_still_sees_only_own_bookings(), test_salon_roles_are_not_matched_on_their_personal_customer_bookings()

### Community 236 - "founder-pricing"
Cohesion: 0.29
Nodes (6): founder-cfo, Output, Rules, Step 1: gather the inputs, Step 2: run it, Step 3: the CFO's note

### Community 237 - "Quality Checklist"
Cohesion: 0.29
Nodes (6): founder-launch, Output, Step 1: test before you spend, Step 2: the countdown, Step 3: launch day, Step 4: the first 30 days

### Community 238 - "Web Application Testing"
Cohesion: 0.29
Nodes (6): Diagnostic steps, Fix, Knex Migration Drift, Related anti-patterns to flag in review, Root cause to suspect, When this pattern applies

### Community 239 - "Domain rules"
Cohesion: 0.29
Nodes (7): Advanced Features (where applicable), Code Quality, Implementation Quality, Quality Checklist, Strategic Design, Testing, Tool Configuration

### Community 240 - "install_database_metrics"
Cohesion: 0.29
Nodes (6): Before finishing, Booking concurrency test, Real DB vs fakes, Role matrix, Rules, Testing

### Community 241 - "2. Cashfree/provider decisions P01-P06"
Cohesion: 0.29
Nodes (6): Checks, Compose services, Deploy flow, Health, Worker rules, Workers and deploy

### Community 244 - "Mumbai Cloud Run staging deployment — 16 October 2026"
Cohesion: 0.33
Nodes (3): QrCodeNotFoundError, test_a_cached_salon_is_revalidated_so_an_expired_token_stops_working(), test_unknown_expired_or_unpublished_token_is_one_machine_readable_404()

### Community 245 - "Local Docker cold-start measurement — 16 October 2026"
Cohesion: 0.33
Nodes (6): Evidence and reproduction, Inspected startup configuration, Isolation and method, Local Docker cold-start measurement — 16 October 2026, Results, Verification and cleanup

### Community 246 - "Mumbai staging readiness review — 2026-10-16"
Cohesion: 0.47
Nodes (3): downgrade(), _replace_functions(), upgrade()

### Community 247 - "6. Money examples and snapshots"
Cohesion: 0.47
Nodes (3): downgrade(), _sql(), upgrade()

### Community 248 - "0029_payment_monetary_policy.py"
Cohesion: 0.47
Nodes (3): downgrade(), _sql(), upgrade()

### Community 249 - "0030_subscription_billing.py"
Cohesion: 0.40
Nodes (4): percentile(), run(), measure(), one()

### Community 250 - "0033_payment_fee_snapshot.py"
Cohesion: 0.33
Nodes (6): Evaluation Process, Step 1: Documentation Inspection, Step 2: Tool Inspection, Step 3: Developing Understanding, Step 4: Read-Only Content Inspection, Step 5: Task Generation

### Community 251 - "test_list_bookings_scoping.py"
Cohesion: 0.33
Nodes (6): Advanced MCP Features, Notification Support, Resource Registration, stdio (For Local Integrations), Streamable HTTP (Recommended for Remote Servers), Transport Options

### Community 252 - "client"
Cohesion: 0.33
Nodes (6): Advanced FastMCP Features, Context Parameter Injection, Lifespan Management, Resource Registration, Structured Output Types, Transport Options

### Community 253 - "founder-cfo"
Cohesion: 0.33
Nodes (5): How to Use, References, Rule Categories by Priority, Supabase Postgres Best Practices, When to Apply

### Community 255 - "Knex Migration Drift"
Cohesion: 0.40
Nodes (5): Category meanings, Exact field-by-field classification, Future verification and readiness, Proposed treatment of the 43 unresolved fields, Retention, erasure and immutable snapshots

### Community 263 - "0022_salon_accepting_bookings.py"
Cohesion: 0.60
Nodes (3): downgrade(), _replace_database_functions(), upgrade()

### Community 267 - "Evaluation Process"
Cohesion: 0.40
Nodes (3): {chromium}, readline, target

### Community 269 - "Advanced FastMCP Features"
Cohesion: 0.40
Nodes (4): Verification Focus, Verification Process, Verification Report Format, What NOT to Focus On

### Community 270 - "Supabase Postgres Best Practices"
Cohesion: 0.40
Nodes (4): Constraints, Mission, Output, Workflow

### Community 271 - "Migration cleanup plan and execution record"
Cohesion: 0.40
Nodes (4): Escalation, Mission, Required Checks, Workflow

### Community 272 - "Proposed treatment of the 43 unresolved fields"
Cohesion: 0.40
Nodes (4): The Monopoly lens, The Offers lens, The Product lens, The three lenses

### Community 277 - "0001_baseline.py"
Cohesion: 0.50
Nodes (4): Audit trail (migration `0027_payout_account_audit`), Owner payout accounts and setup checklist, Status, Storage and security

### Community 278 - "0002_notifications_read_at.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_functions(), upgrade()

### Community 279 - "0003_google_oauth_profile_metadata.py"
Cohesion: 0.50
Nodes (3): COMPOSE_ENV_FILE, COMPOSE_PROJECT_NAME, gcp-vm-release-compose.sh script

### Community 280 - "0004_service_duration_slot_steps.py"
Cohesion: 0.50
Nodes (3): Analysis Approach, Core Mission, Output Guidance

### Community 281 - "0005_staff_experience.py"
Cohesion: 0.50
Nodes (3): Check the result, Clear Technical English, Write the explanation

## Knowledge Gaps
- **44 isolated node(s):** `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME`, `COMPOSE_ENV_FILE`, `Masked SQLAlchemy URL password test defect`, `accepting_bookings pause switch` (+39 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3251 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **108 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PlatformRepository` connect `OwnerUseCases` to `json`, `Money`, `owner.py`, `RedisCache`, `Profile`, `routes/admin.py`, `test_booking_contract_sql.py`, `AdminUseCases`, `StorageGateway`, `test_payment_stage1_flows.py`, `test_vm_release.py`, `CI password regression ? 2026-10-14`, `FCMGateway`, `PillowImageProcessor`, `test_walkin_qr_contract.py`, `0007_salon_qr_image_url.py`, `AuthAdminGateway`, `ValidationError`, `harness-optimizer.md`, `loop-operator.md`, `Adding an endpoint`, `Any`, `The three lenses`, `playwright_sync_api`, `alembic`, `Roadmap`, `IdempotencyInProgressError`, `use_cases/platform.py`, `Decimal`, `PaymentProviderNotConfiguredError`, `panel.py`, `test_redis_recovery_sql.py`, `test_account_deletion_api.py`, `Senior backend engineer`, `booking_policy.py`, `NotFoundError`, `test_account_deletion_sql.py`, `test_media_integration.py`, `.create_booking`, `.get_available_slots`, `Ledger`, `architect.md`, `Node/TypeScript MCP Server Implementation Guide`, `config.py`, `routes/support.py`, `test_upgrade_business_gates_owner_protection_and_downgrade`, `founder-competitors`, `founder-plan`, `test_salon_ranking.py`, `.apply_payment_observation`, `Mumbai Cloud Run staging deployment — 16 October 2026`, `Payment, subscription and booking domain specification`, `test_account_erasure_hardening.py`, `payment-subscription-booking-spec.md`, `docs/migrations/README.md`, `founder-launch`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Are the 163 inferred relationships involving `Profile` (e.g. with `get_authenticated_session()` and `get_current_actor()`) actually correct?**
  _`Profile` has 163 INFERRED edges - model-reasoned connections that need verification._
- **What connects `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME`, `COMPOSE_ENV_FILE` to the rest of the system?**
  _44 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `OwnerUseCases` be split into smaller, more focused modules?**
  _Cohesion score 0.021021313954055505 - nodes in this community are weakly interconnected._
- **Why does `Profile` connect `routes/admin.py` to `chief-of-staff.md`, `json`, `exceptions.py`, `owner.py`, `RedisCache`, `Profile`, `AdminUseCases`, `test_payment_stage1_flows.py`, `main.py`, `CI password regression ? 2026-10-14`, `FCMGateway`, `time`, `test_walkin_qr_contract.py`, `PaymentRepository`, `test_payments_foundation.py`, `CacheGateway`, `BookingPaymentUseCases`, `AuthAdminGateway`, `unittest_mock`, `Any`, `PaymentProviderNotConfiguredError`, `test_payout_account.py`, `SubscriptionProviderResolver`, `test_account_deletion_api.py`, `FakeBillingRepo`, `booking_policy.py`, `test_media_integration.py`, `.create_booking`, `.get_available_slots`, `Ledger`, `test_public_discovery_contract.py`, `architect.md`, `MCP Server Best Practices`, `SubscriptionWebhookHandler`, `config.py`, `AccountErasureService`, `SupabaseAuthGateway`, `readiness`, `test_upgrade_business_gates_owner_protection_and_downgrade`, `test_media_admission_http.py`, `Mumbai staging startup investigation — 16–17 October 2026 (IST)`, `test_account_erasure_hardening.py`, `payment-subscription-booking-spec.md`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `PlatformRepository` (e.g. with `list_public_categories()` and `list_public_subcategories()`) actually correct?**
  _`PlatformRepository` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Should `json` be split into smaller, more focused modules?**
  _Cohesion score 0.051209341117598 - nodes in this community are weakly interconnected._