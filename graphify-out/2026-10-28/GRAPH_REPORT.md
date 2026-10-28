# Graph Report - salon-backend  (2026-10-26)

## Corpus Check
- 697 files · ~790,384 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 17 file(s) not represented in the graph (top: (none) 9, .example 2, .csv 2)

## Summary
- 7489 nodes · 19519 edges · 415 communities (246 shown, 169 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2579 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `84bcc165`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- exceptions.py
- use_cases/payments.py
- PlatformRepository
- owner.py
- Role
- Profile
- test_media_admission_http.py
- Money
- json
- test_accepting_bookings.py
- booking_finance_policy.py
- Data models
- OwnerUseCases
- use_cases/platform.py
- test_checkout_safety_sql.py
- decimal
- Settings
- test_cashfree_gateway.py
- test_salon_approval_migration.py
- routes/payments.py
- CashfreeGateway
- AccountDeletionRepository
- routes/admin.py
- test_subscription_billing.py
- test_migration_policy.py
- test_payment_stage1_flows.py
- test_payment_flows.py
- ServiceUnavailableError
- verify_phone
- time
- deps.py
- BookingPaymentUseCases
- R2StorageGateway
- use_cases/subscription_billing.py
- SubscriptionProviderResolver
- test_subscription_billing_sql.py
- PaymentWebhookUseCases
- routes/account_deletion.py
- test_payments_foundation.py
- SQLAccountDeletionRepository
- test_booking_changes_sql.py
- routes/booking_actions.py
- test_account_deletion_use_cases.py
- ValidationError
- test_account_erasure.py
- provision_super_admin.py
- customer.py
- Module Group 47
- use_cases/account_deletion.py
- test_auth.py
- Module Group 50
- routes/support.py
- routes/booking_finance.py
- main.py
- CacheGateway
- panel.py
- test_payout_account.py
- test_account_deletion_sql.py
- RedisCache
- test_maintenance_job.py
- FakeBillingRepo
- bookings.py
- test_account_erasure_hardening.py
- SubscriptionBillingRepository
- connections.py
- Salon Owner
- test_payment_stage1_api.py
- test_salon_ranking.py
- ConflictError
- entities/subscription.py
- routes/auth.py
- notifications.py
- subscriptions.py
- media/health.py
- field_validator
- BookingActionRepository
- FCMGateway
- .get_available_slots
- Ledger
- SubscriptionWebhookHandler
- test_booking_finance_policy.py
- alembic
- architect.md
- MCP Server Best Practices
- UnauthorizedError
- PaymentRepository
- test_cache_recovery.py
- Node/TypeScript MCP Server Implementation Guide
- AccountErasureService
- Module Group 89
- test_account_closure_steps.py
- AdminUseCases
- schemas/admin.py
- test_subscription.py
- Website, customer app and owner app: developer handoff
- post
- asyncio
- test_fake_provider_flows.py
- pytest
- CatalogAdminUseCases
- SubscriptionBillingUseCases
- test_payment_fees_policy.py
- test_public_discovery_contract.py
- evaluation.py
- test_booking_error_classification.py
- math
- PaymentGatewayResolver
- migration_mumbai_runtime_20261015.py
- MCP Server Evaluation Guide
- Python MCP Server Implementation Guide
- test_docker_image_ids.py
- .reject_salon
- SubscriptionPlanRepo
- make_super_admin
- test_booking_finance_sql.py
- test_booking_contract_sql.py
- Changelog
- mumbai_browser.cjs
- Any
- redis.py
- ImageFamilies
- test_closed_salon_statement.py
- SalonSubscriptionUseCases
- WalkInUseCases
- test_public_http_and_playwright_refresh_after_lost_invalidation
- Module Group 126
- outbox_worker.py
- FakeRepo
- Supabase
- Admin
- round_money
- docs/README.md
- test_image_families.py
- FakeLedger
- test_account_deletion_api.py
- test_migration_tool_paths.py
- test_public_salon_visibility.py
- chief-of-staff.md
- Changelog
- AuthTokens
- PaymentProviderNotConfiguredError
- qr.py
- .erase_database
- Env
- Running Evaluations
- Writing Guidelines for Postgres References
- Customer App Backend API Contract
- SupabaseAuthAdminGateway
- BookingChangeRepository
- salon-backend
- Super-admin to owner review thread (spec; design, not built)
- repositories/account_deletion_repository.py
- Progress: shifan
- test_vm_release.py
- Review Priorities
- tdd-guide.md
- Rams Design Review
- van_westendorp.py
- Salon Owner App Backend API Contract
- Progress: thameem/cloud-run-startup-investigation
- Module Group 162
- Module Group 163
- Build Error Resolver
- Documentation & Codemap Specialist
- E2E Test Runner
- planner.md
- Refactor & Dead Code Cleaner
- Complete backend API reference for frontend teams
- Agent Instructions
- ProfileUpdateRequest
- Module Group 172
- Account Deletion
- Store
- family_id
- test_expo_push_includes_notification_payload
- Database Reviewer
- mcp-builder/SKILL.md
- Progress: thameem/mumbai-forward-reconciliation
- Progress: {branch}
- Progress: thameem/cloud-run-mumbai-staging
- Progress: thameem/local-docker-cold-start
- Progress: thameem/provider-agnostic-payments
- Progress: thameem/u08-verification-continuation
- Bookings
- How to use the prompts
- test_removed_profile_fields.py
- booking.py
- test_concurrent_avatar_commit_failure_and_cleanup_keep_committed_family
- Rows
- Pass 2 — Clean Architecture & Standards
- redis_recovery_browser.cjs
- get_cache
- get_image_family
- Env
- test_database_backup.py
- founder-board
- Module Group 200
- founder-ops
- Karpathy Guidelines
- Section Definitions
- Subscriptions
- upload_signed_image
- create_walkin_booking
- ports/__init__.py
- Module Group 208
- Module Group 209
- install_database_metrics
- source
- decode_json
- .insert_refund
- ._find_owner_salon_id
- reseal_layout_evidence.py
- test_account_deletion_migration.py
- public_api
- _Clock
- founder-marketing
- founder-offer
- BookingChangeGateway
- test_vendor_registration_state_machine_and_audit
- test_migration_and_service_api_round_trip
- test_notification_outbox_worker.py
- IntakeLedger
- .apply_payment_observation
- adapter
- Agent memory
- Booking and payments
- founder-brand
- founder-competitors
- founder-plan
- founder-pricing
- Quality Checklist
- Web Application Testing
- Domain rules
- get_my_profile
- Image integration review — 2026-10-10
- 0029_payment_monetary_policy.py
- 0030_subscription_billing.py
- 0033_payment_fee_snapshot.py
- test_list_bookings_scoping.py
- founder-cfo
- founder-launch
- Knex Migration Drift
- Quality Checklist
- Testing
- Workers and deploy
- Booking Actions
- Public discovery, QR and booking contract
- .delete
- image_family.py
- AuthUserContacts
- email_gateway.py
- Frontend Integration Prompt — Redis Feature Changes
- Module Group 257
- Module Group 258
- Module Group 259
- Module Group 260
- Module Group 261
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
- Notifications
- Salon Platform API
- ReportRepository
- .throttle
- Migration cleanup plan and execution record
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
- FakeAdmin
- test_account_deletion_blockers.py
- agent-sdk-verifier-py.md
- harness-optimizer.md
- loop-operator.md
- The three lenses
- Roadmap
- IdempotencyInProgressError
- .list_salons
- Owner payout accounts and setup checklist
- 0015_salon_admin_approval.py
- 0035_booking_checkout_safety.py
- gcp-vm-release-compose.sh
- test_service_search_requires_active_category_and_subcategory
- code-explorer.md
- Code reviewer (read-only)
- Migration reviewer (read-only)
- Clear Technical English
- Features
- phone_key_variants
- .settlement_model
- check-container.sh
- gcp-vm-deploy.sh
- code-architect.md
- start.md
- wrap.md
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
- schema-primary-keys.md
- security-privileges.md
- security-rls-basics.md
- security-rls-performance.md
- _template.md
- SESSIONS.md
- commands.md
- shared/README.md
- agent-skill-routing.md
- SALON_APPROVAL.md

## God Nodes (most connected - your core abstractions)
1. `Profile` - 367 edges
2. `PlatformRepository` - 263 edges
3. `ValidationError` - 185 edges
4. `Role` - 184 edges
5. `Settings` - 170 edges
6. `ForbiddenError` - 147 edges
7. `make_profile()` - 142 edges
8. `NotFoundError` - 138 edges
9. `Data models` - 138 edges
10. `make_mock_repo()` - 100 edges

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
- None detected.

## Hyperedges (group relationships)
- **Account Deletion End-to-End Flow (auth -> erasure -> financial purge)** — backend_docs_account_deletion_flow, backend_docs_account_deletion_erasure_worker, backend_docs_account_deletion_financial_purge_design_overview [EXTRACTED 1.00]
- **All Compose Workers Depend on Redis Health** — backend_docker_compose_api_service, backend_docker_compose_notification_worker, backend_docker_compose_media_cleanup, backend_docker_compose_account_deletion_worker, backend_docker_compose_payment_webhook_worker, backend_docker_compose_email_worker, backend_docker_compose_redis [EXTRACTED 1.00]
- **Booking Creation Idempotency Pattern (Postgres + Redis + use cases)** — backend_docs_booking_flow_postgres_functions, backend_docs_payments_idempotency, backend_docs_architecture_redis_caching [INFERRED 0.85]

## Communities (415 total, 169 thin omitted)

### Community 0 - "exceptions.py"
Cohesion: 0.04
Nodes (24): ReportRequest, ReportResponse, submit_report(), require_qr_token_format(), WalkInSalonResponse, WalkInServiceSummary, WalkInStaffSummary, WalkInVerifyPhoneRequest (+16 more)

### Community 1 - "use_cases/payments.py"
Cohesion: 0.04
Nodes (35): PaymentEvent, PaymentGateway, ProviderPayment, SettlementAccountRequest, apply_provider_payment(), _clean_code(), event_to_json(), observation_status() (+27 more)

### Community 2 - "PlatformRepository"
Cohesion: 0.02
Nodes (12): NotFoundError, _canonical_json_value(), PlatformRepository, _request_fingerprint(), test_profile_response_normalizes_uuid_id_for_api_schema(), test_gallery_attach_retry_returns_existing_row_without_duplicate_insert(), test_reference_query_fails_closed_on_rls_and_checks_every_media_table(), test_service_response_normalizes_uuid_ids_for_api_schema() (+4 more)

### Community 3 - "owner.py"
Cohesion: 0.03
Nodes (67): assign_staff_service(), complete_profile(), create_blocked_slot(), create_holiday(), create_image(), create_staff(), deactivate_service(), deactivate_staff() (+59 more)

### Community 4 - "Role"
Cohesion: 0.04
Nodes (83): BookingCreateRequest, BookingUseCases, NotificationUseCases, BookingSourceNotAllowedError, Role, make_booking(), make_mock_repo(), make_profile() (+75 more)

### Community 5 - "Profile"
Cohesion: 0.04
Nodes (23): BookingActionRequestUseCases, ClosureUseCases, mask_payout_account(), assert_approved_workspace(), ForbiddenError, SalonApprovalRequiredError, BookingSource, Profile (+15 more)

### Community 6 - "test_media_admission_http.py"
Cohesion: 0.05
Nodes (47): app_error_response(), _cors_headers(), register_exception_handlers(), app_error_handler(), http_exception_handler(), safe_validation_error_handler(), _sanitise(), unhandled_error_handler() (+39 more)

### Community 7 - "Money"
Cohesion: 0.04
Nodes (52): PaymentIntentRequest, RefundRequest, PayoutProvider, ProviderFeeReconciler, RefundProvider, WebhookVerifier, IdempotencyKeyReuseError, PaymentCapabilityError (+44 more)

### Community 8 - "json"
Cohesion: 0.06
Nodes (33): metric(), percentile(), run(), measure(), one(), run(), measure(), summary() (+25 more)

### Community 9 - "test_accepting_bookings.py"
Cohesion: 0.03
Nodes (38): get_authenticated_session(), get_current_actor(), require_role(), dependency(), AdminMFARequiredError, client(), _migration_statements(), _owner_salon() (+30 more)

### Community 10 - "booking_finance_policy.py"
Cohesion: 0.14
Nodes (10): Allocation, _amount(), CancellationQuote, completed_service_allocation(), _remaining(), ServiceChangeQuote, validate_no_show(), test_completed_service_cost_shortfall_is_not_negative_salon_money() (+2 more)

### Community 11 - "Data models"
Cohesion: 0.02
Nodes (126): AccountDeletionAcceptedResponse, AccountDeletionStatusResponse, AdminAccountDeletionResponse, AdminCreateSalonRequest, AdminDeactivateSalonResponse, AdminRejectSalonRequest, AdminSalonOnboardingResponse, AdminSalonResponse (+118 more)

### Community 12 - "OwnerUseCases"
Cohesion: 0.05
Nodes (35): OwnerUseCases, _upload_extension(), _upload_result(), make_owner(), test_staff_grant_requires_owned_staff_before_storage(), test_signed_workflow_processes_http_bytes_then_validates_saved_reference(), test_staff_replacement_preserves_shared_old_object_and_checks_new_namespace(), test_url_saving_calls_gateway_before_database_write() (+27 more)

### Community 13 - "use_cases/platform.py"
Cohesion: 0.03
Nodes (20): get_avatar_upload_url(), update_my_profile(), MediaReferences, StorageGateway, managed_media_path(), AvatarRepository, validate_media_reference(), CustomerUseCases (+12 more)

### Community 14 - "test_checkout_safety_sql.py"
Cohesion: 0.08
Nodes (60): PaymentCollectionRequiredError, set_actor_context(), changes(), changes_db(), install(), finance_db(), install(), SafetyEnv (+52 more)

### Community 15 - "decimal"
Cohesion: 0.19
Nodes (7): checkout_quote(), test_pay_at_salon_is_fee_free_with_exact_instructions(), test_adding_provider_credentials_cannot_activate_u08_online_money(), test_new_booking_policy_selection_does_not_reprice_legacy_payment(), test_policy_selection_is_explicit_and_rejects_unknown_versions(), test_u08_checkout_has_no_customer_surcharge_and_reports_its_version(), test_u08_quote_does_not_advertise_online_collection_before_held_funds_workflow()

### Community 16 - "Settings"
Cohesion: 0.06
Nodes (9): get_settings(), Settings, test_blank_account_deletion_secret_is_unconfigured(), test_explicit_r2_values_win_over_legacy_values(), test_settings_accept_legacy_r2_bucket_name(), test_settings_derives_r2_account_id_from_legacy_endpoint_url(), test_short_account_deletion_secret_is_rejected(), test_database_url_always_uses_asyncpg() (+1 more)

### Community 17 - "test_cashfree_gateway.py"
Cohesion: 0.07
Nodes (53): RefundStatus, ignored(), cf_settings(), event_body(), gateway(), intent_request(), order_handler(), pay() (+45 more)

### Community 18 - "test_salon_approval_migration.py"
Cohesion: 0.07
Nodes (11): execute_revision(), isolate(), migration_sql(), RollbackSession, Rows, test_upgrade_business_gates_owner_protection_and_downgrade(), _sql_string_literals(), test_no_bind_param_is_immediately_followed_by_a_pg_cast() (+3 more)

### Community 19 - "routes/payments.py"
Cohesion: 0.06
Nodes (47): booking_quote(), cancel_payment(), confirm_payment(), create_payment_intent(), get_settlement_account(), list_booking_payments(), my_earnings(), payment_config() (+39 more)

### Community 20 - "CashfreeGateway"
Cohesion: 0.06
Nodes (13): RefundResult, SettlementAccount, PaymentOutcomeUnknownError, PaymentProviderError, CashfreeGateway, _decimal(), dumps_json(), _phone() (+5 more)

### Community 22 - "routes/admin.py"
Cohesion: 0.07
Nodes (27): _admin_use_cases(), approve_salon(), _catalog_use_cases(), create_category(), create_salon(), create_subcategory(), deactivate_category(), deactivate_salon() (+19 more)

### Community 23 - "test_subscription_billing.py"
Cohesion: 0.09
Nodes (50): owner(), profile(), sub_settings(), handler_for(), http(), make(), normalized(), paid_flow() (+42 more)

### Community 24 - "test_migration_policy.py"
Cohesion: 0.08
Nodes (21): portable_revisions(), require_mumbai_url(), require_unambiguous_url(), validate_evidence(), validate_migration_target(), do_run_migrations(), guard_requested_migration(), run_migrations_offline() (+13 more)

### Community 25 - "test_payment_stage1_flows.py"
Cohesion: 0.08
Nodes (50): SettlementRegistrationDetails, PaymentAmountMismatchError, build(), capture(), details(), process_events(), claim(), settings() (+42 more)

### Community 26 - "test_payment_flows.py"
Cohesion: 0.06
Nodes (38): captured_body(), client(), FakeRepo, load(), make_processor(), repo_with(), _Result, run() (+30 more)

### Community 27 - "ServiceUnavailableError"
Cohesion: 0.06
Nodes (19): ServiceUnavailableError, set_request_id(), measure_external(), RequestMetrics, scrub_sentry(), ResendEmailGateway, channel_field(), SupabaseAuthGateway (+11 more)

### Community 28 - "verify_phone"
Cohesion: 0.16
Nodes (9): get_qr_image(), resolve_qr(), _use_cases(), verify_phone(), GET `/v1/walkin/{qr_token}`, GET `/v1/walkin/{qr_token}/qr`, POST `/v1/walkin/{qr_token}/bookings`, POST `/v1/walkin/{qr_token}/verify-phone` (+1 more)

### Community 29 - "time"
Cohesion: 0.07
Nodes (32): close_redis_cache(), main(), run_job(), export_backup(), gpg_path(), locate_tool(), main(), validate_destination() (+24 more)

### Community 30 - "deps.py"
Cohesion: 0.09
Nodes (8): get_auth_gateway(), get_payment_gateway_resolver(), get_subscription_provider_resolver(), process_in_background(), CreatedAuthUser, _adapter_module(), build_subscription_provider(), get_subscription_resolver()

### Community 31 - "BookingPaymentUseCases"
Cohesion: 0.10
Nodes (9): PaymentIntent, BookingPaymentUseCases, _fingerprint(), _json_default(), _ledger_row(), IdempotencyKeyRequiredError, PaymentInProgressError, PaymentOvercollectionError (+1 more)

### Community 32 - "R2StorageGateway"
Cohesion: 0.09
Nodes (13): R2StorageGateway, test_token_purposes_stay_cryptographically_separate(), test_assert_configured_passes_when_all_settings_present(), test_assert_configured_raises_when_settings_missing(), test_delete_object_calls_boto3_delete(), test_delete_object_raises_validation_error_on_boto3_failure(), test_delete_object_raises_when_r2_not_configured(), test_get_client_caches_boto3_client_across_calls() (+5 more)

### Community 33 - "use_cases/subscription_billing.py"
Cohesion: 0.05
Nodes (20): ProviderOrder, ProviderOrderState, ProviderPaymentObservation, ProviderPaymentState, ProviderRefund, ProviderSubscriptionEvent, SubscriptionClientConfig, SubscriptionEventKind (+12 more)

### Community 34 - "SubscriptionProviderResolver"
Cohesion: 0.10
Nodes (31): cancel(), checkout(), list_purchasable_plans(), my_access_state(), my_subscription(), payments(), subscription_config(), _uc() (+23 more)

### Community 35 - "test_subscription_billing_sql.py"
Cohesion: 0.08
Nodes (28): subscription_event_to_json(), _plans(), test_0030_statements_are_idempotent_and_plan_checks_exist(), subscription_side(), test_a_lapsed_active_row_within_stored_grace_keeps_the_benefit_without_a_sweep(), test_a_payment_that_lands_on_a_suspended_or_closed_salon_is_held_and_flagged(), test_a_suspended_salon_cannot_start_a_new_checkout(), test_account_deletion_blocks_a_live_subscription_and_rechecks_at_confirm() (+20 more)

### Community 36 - "PaymentWebhookUseCases"
Cohesion: 0.06
Nodes (11): get_payment_gateway(), payment_webhook(), PaymentWebhookUseCases, InvalidWebhookSignatureError, WebhookPayloadTooLargeError, get_payment_resolver(), drain_webhook_events(), reconcile_once() (+3 more)

### Community 37 - "routes/account_deletion.py"
Cohesion: 0.12
Nodes (21): closed_salon_statement(), confirm_account_deletion(), get_deletion_status(), list_account_deletions(), list_closed_salons(), start_deletion_challenge(), _use_cases(), verify_deletion_challenge() (+13 more)

### Community 38 - "test_payments_foundation.py"
Cohesion: 0.09
Nodes (18): derive_payment_state(), is_forward_transition(), build_gateway(), test_razorpay_booking_adapter_still_works_alongside(), hex_hmac(), make_settings(), test_callback_signature_vectors(), test_capabilities() (+10 more)

### Community 40 - "test_booking_changes_sql.py"
Cohesion: 0.10
Nodes (30): new_service(), reviewed(), setup_client(), test_booking_change_requires_key_and_rejects_key_reuse(), test_change_availability_excludes_only_own_booking_and_preserves_public_slots(), test_changed_catalog_quote_requires_reacceptance_and_time_only_keeps_booked_price(), test_cheaper_service_keeps_history_and_prepaid_money_but_reduces_unpaid_price(), test_concurrent_closure_is_rechecked_after_shared_salon_lock() (+22 more)

### Community 41 - "routes/booking_actions.py"
Cohesion: 0.10
Nodes (16): _action_use_cases(), apply_closure(), _closure_use_cases(), create_cancellation_request(), create_payment_confirmation_request(), list_booking_action_requests(), preview_closure(), respond_booking_action_request() (+8 more)

### Community 42 - "test_account_deletion_use_cases.py"
Cohesion: 0.13
Nodes (29): InvalidVerificationCodeError, TooManyRequestsError, build(), contacts(), FakeAuthGateway, test_a_subscription_bought_after_the_challenge_blocks_at_confirm(), test_active_subscription_blocks_only_with_a_real_provider(), test_admin_ledger_requires_super_admin() (+21 more)

### Community 43 - "ValidationError"
Cohesion: 0.04
Nodes (73): get_storage_gateway(), upload_avatar(), ImagePolicy, ImageProcessor, ProcessedImageFamily, ProcessedVariant, retire_unreferenced_media(), UploadAvatar (+65 more)

### Community 44 - "test_account_erasure.py"
Cohesion: 0.09
Nodes (17): FakeAdmin, FakeLedger, FakeStorage, make_request(), make_service(), test_already_missing_auth_user_is_not_banned_and_delete_is_idempotent(), test_auth_delete_failure_is_retryable_and_resumes_without_repeating_steps(), test_customer_erasure_skips_salon_cache_keys() (+9 more)

### Community 45 - "provision_super_admin.py"
Cohesion: 0.08
Nodes (21): _admin_base(), _assert_safe_existing_profile(), _AuthUser, _create_auth_user(), _FakeGateway, _find_user_by_email(), _get_profile_state(), main() (+13 more)

### Community 46 - "customer.py"
Cohesion: 0.10
Nodes (19): get_profile(), get_salon(), list_public_categories(), list_public_subcategories(), list_salon_services(), list_salon_staff(), list_salons(), nearby_salons() (+11 more)

### Community 47 - "Module Group 47"
Cohesion: 0.09
Nodes (40): Admin salon approval API endpoints, POST /v1/salons/me/complete-profile endpoint, Migration 0015 salon admin approval, Migration 0018 subscription foundation tables, Razorpay subscription webhook integration, subscription_billing_records table (purchase attempt tracking), Subscription entitlement states (active, grace, cancelled_paid_through, expired, none), payment-webhook-worker subscription reconciliation (reconcile_subscriptions_once) (+32 more)

### Community 48 - "use_cases/account_deletion.py"
Cohesion: 0.09
Nodes (13): AccountDeletionUseCases, deletion_stage(), mask_contact(), normalize_contact(), _statement_figures(), ContactMismatchError, DeletionBlockedError, digest() (+5 more)

### Community 49 - "test_auth.py"
Cohesion: 0.09
Nodes (12): MeOutput, GetMe, EnsureOwnerAccess, ProfileRepository, require_active(), FakeProfileRepository, _profile(), test_get_me_returns_active_actor() (+4 more)

### Community 50 - "Module Group 50"
Cohesion: 0.06
Nodes (28): Account Deletion Worker Service, API Service (Docker Compose), Email Worker Service, Media Cleanup Worker Service, Notification Worker Service, Payment Webhook Worker Service, Redis Service (Docker Compose), Erasure Worker (lock/cancel/notify/refund/settle/erase) (+20 more)

### Community 51 - "routes/support.py"
Cohesion: 0.09
Nodes (16): create_ticket(), email_event(), read_ticket(), reply_ticket(), EmailEventResponse, SupportCreateRequest, SupportMessageResponse, SupportReplyRequest (+8 more)

### Community 52 - "routes/booking_finance.py"
Cohesion: 0.09
Nodes (9): admin_statement(), finance_command(), owner_statement(), AdminFinanceStatement, FinanceCommandRequest, OwnerPayoutStatement, BookingFinanceGateway, BookingFinanceUseCases (+1 more)

### Community 53 - "main.py"
Cohesion: 0.04
Nodes (26): PayloadTooLargeError, RequestTimeoutError, UnsupportedMediaTypeError, _add_request_id(), configure_logging(), get_request_id(), init_sentry(), TimingMiddleware (+18 more)

### Community 54 - "CacheGateway"
Cohesion: 0.08
Nodes (13): database_health(), health(), readiness(), redis_health(), DatabaseHealthResponse, HealthResponse, RedisHealthResponse, CacheGateway (+5 more)

### Community 55 - "panel.py"
Cohesion: 0.11
Nodes (28): _answer_ok(), check(), deal(), init(), load_state(), main(), _num(), PanelError (+20 more)

### Community 56 - "test_payout_account.py"
Cohesion: 0.07
Nodes (12): build_setup_status(), FakeRepo, _migration(), _migration_named(), _sql(), test_0027_shape(), test_field_validation_rejects_bad_input(), test_migration_chain_and_security_shape() (+4 more)

### Community 57 - "test_account_deletion_sql.py"
Cohesion: 0.15
Nodes (26): confirm(), drain(), engine(), FakeAdmin, finish_ledger(), make_due(), make_service(), new_user() (+18 more)

### Community 58 - "RedisCache"
Cohesion: 0.13
Nodes (8): RedisCache, main(), test_auth_limit_fails_closed_on_backend_error(), test_auth_limit_fails_closed_without_redis_but_booking_fallback_stays_available(), test_late_cache_fill_cannot_enter_new_epoch(), test_unvalidated_or_failed_database_read_never_uses_cached_payload(), test_redis_cache_noop_when_client_is_none(), test_redis_cache_operations_with_mock_client()

### Community 59 - "test_maintenance_job.py"
Cohesion: 0.08
Nodes (22): drain_queue(), run_pass(), attempt_one(), checkpoint(), run_forever(), sweep_media(), media_fixture(), test_budget_does_not_cancel_in_flight_work_and_closes_resources() (+14 more)

### Community 61 - "bookings.py"
Cohesion: 0.10
Nodes (15): availability(), booking_change_availability(), change_booking(), list_bookings(), quote_booking_change(), BookingChangeCommitRequest, BookingChangeQuote, BookingChangeRequest (+7 more)

### Community 62 - "test_account_erasure_hardening.py"
Cohesion: 0.10
Nodes (18): drain_account_deletions(), run_forever(), storage_is_required(), validate_worker_configuration(), cascade_tables_in_migrations(), cfg(), load_0028(), run() (+10 more)

### Community 63 - "SubscriptionBillingRepository"
Cohesion: 0.11
Nodes (4): _row(), SubscriptionBillingRepository, test_concurrent_applications_extend_exactly_once(), racer()

### Community 64 - "connections.py"
Cohesion: 0.07
Nodes (5): MCPConnection, MCPConnectionHTTP, MCPConnectionSSE, MCPConnectionStdio, supabase

### Community 65 - "Salon Owner"
Cohesion: 0.06
Nodes (34): DELETE `/v1/salons/me/blocks/{block_id}`, DELETE `/v1/salons/me/holidays/{holiday_id}`, DELETE `/v1/salons/me/images/{image_id}`, DELETE `/v1/salons/me/services/{service_id}`, DELETE `/v1/salons/me/staff/{staff_id}`, GET `/v1/salons/me`, GET `/v1/salons/me/blocks`, GET `/v1/salons/me/holidays` (+26 more)

### Community 66 - "test_payment_stage1_api.py"
Cohesion: 0.09
Nodes (14): CommissionBase, commission_reversal(), compute_commission(), test_zero_platform_commission_is_valid_in_the_commission_math(), FakeUseCases, load(), run(), test_0029_downgrade_restores_legacy_functions_and_drops_additions() (+6 more)

### Community 67 - "test_salon_ranking.py"
Cohesion: 0.12
Nodes (26): AdminUpdateSalonRequest, _actor(), add_salon(), ids(), ranked(), _subscribe(), test_admin_request_validates_priority(), test_admin_response_exposes_priority_and_audit_actor() (+18 more)

### Community 68 - "ConflictError"
Cohesion: 0.17
Nodes (19): ConflictError, _repository(), _Result, test_cancellation_owner_decision_releases_slot_only_when_approved(), test_closure_rejects_changed_impact_set(), test_cross_salon_decision_is_hidden(), test_direct_payment_rejects_cancelled_booking(), test_duplicate_pending_request_is_rejected() (+11 more)

### Community 69 - "entities/subscription.py"
Cohesion: 0.08
Nodes (21): BillingInterval, BillingStatus, derive_entitlement(), EntitlementState, EventProcessingStatus, SalonSubscription, SubscriptionEvent, SubscriptionEventType (+13 more)

### Community 70 - "routes/auth.py"
Cohesion: 0.11
Nodes (14): forgot_password(), me(), owner_access(), refresh(), ForgotPasswordRequest, ForgotPasswordResponse, ProfileResponse, RefreshRequest (+6 more)

### Community 71 - "notifications.py"
Cohesion: 0.11
Nodes (13): deactivate_device(), list_notifications(), mark_all_notifications_read(), mark_notification_read(), register_device(), _use_cases(), DeviceRegisterRequest, DeviceRegisterResponse (+5 more)

### Community 72 - "subscriptions.py"
Cohesion: 0.18
Nodes (20): cancel_subscription(), create_plan(), create_test_subscription(), deactivate_plan(), get_salon_subscription(), list_events(), list_plans(), _plan_uc() (+12 more)

### Community 73 - "media/health.py"
Cohesion: 0.11
Nodes (20): heartbeat_path(), is_healthy(), main(), max_age_seconds(), touch(), heartbeat_path(), is_healthy(), main() (+12 more)

### Community 74 - "field_validator"
Cohesion: 0.10
Nodes (3): _blank_to_none(), OwnerPayoutAccountRequest, _visible_photos()

### Community 76 - "FCMGateway"
Cohesion: 0.11
Nodes (4): FCMGateway, test_provider_data_ignores_non_object_notification_data(), test_provider_data_merges_notification_data_as_strings(), test_provider_data_still_works_for_notifications_without_data()

### Community 77 - ".get_available_slots"
Cohesion: 0.07
Nodes (17): Database And Booking Rules, Look for, Output, Performance analyst (read-only), Refactorer, Alembic migration, Checklist, Workflow (+9 more)

### Community 79 - "SubscriptionWebhookHandler"
Cohesion: 0.11
Nodes (4): SubscriptionReconciler, SubscriptionSettlement, SubscriptionWebhookHandler, reconcile_subscriptions_once()

### Community 80 - "test_booking_finance_policy.py"
Cohesion: 0.14
Nodes (22): cancellation_quote(), service_change_quote(), validate_customer_change(), test_actual_provider_cost_never_reduces_promised_refund(), test_aware_appointment_instants_are_required(), test_cancellation_exact_boundaries(), test_change_blocks_at_exactly_four_hours_and_later(), test_change_is_permitted_only_above_four_hours() (+14 more)

### Community 82 - "architect.md"
Cohesion: 0.07
Nodes (27): 1. Current State Analysis, 1. Modularity & Separation of Concerns, 2. Requirements Gathering, 2. Scalability, 3. Design Proposal, 3. Maintainability, 4. Security, 4. Trade-Off Analysis (+19 more)

### Community 83 - "MCP Server Best Practices"
Cohesion: 0.07
Nodes (28): Authentication and Authorization, DNS Rebinding Protection, Documentation Requirements, Error Handling, Error Handling, Input Validation, JSON Format (`response_format="json"`), Markdown Format (`response_format="markdown"`, typically default) (+20 more)

### Community 84 - "UnauthorizedError"
Cohesion: 0.13
Nodes (9): UnauthorizedError, SupabaseJWTVerifier, test_deactivated_account_jwt_returns_401_on_deletion_endpoints(), _raise_unauthorized(), test_concurrent_unknown_keys_share_one_cold_refresh(), refresh(), test_failed_fetch_attempts_are_also_bounded(), test_rotation_refresh_is_allowed_after_bounded_cooldown() (+1 more)

### Community 86 - "test_cache_recovery.py"
Cohesion: 0.13
Nodes (12): validated_cache_reads(), read_cache_snapshot(), test_snapshot_changes_on_commit_with_older_transaction_still_open(), worker(), test_booking_and_availability_never_read_or_write_payload_cache(), test_disconnected_reader_recovers_before_serving_payload(), test_erasure_worker_probes_retained_client_before_destructive_work(), test_explicit_invalidation_failure_is_logged_and_retried() (+4 more)

### Community 87 - "Node/TypeScript MCP Server Implementation Guide"
Cohesion: 0.07
Nodes (27): Async/Await Best Practices, Building and Running, Character Limits and Truncation, Code Best Practices, Code Composability and Reusability, Complete Example, Error Handling, Key Imports (+19 more)

### Community 88 - "AccountErasureService"
Cohesion: 0.13
Nodes (3): AccountErasureService, ErasureVerificationError, RefundsPendingError

### Community 89 - "Module Group 89"
Cohesion: 0.09
Nodes (13): Mumbai staging readiness review — 2026-10-16, Payment, subscription and booking domain specification, Provider-independent payments: mock implementation — 2026-10-18, Mumbai staging readiness audit — 2026-10-15, Mumbai forward revisions — prepared only — 2026-10-15, Mumbai reconciliation — least privilege — 2026-10-15, Alembic history reconciliation plan — no execution, Rollback / recovery plan — Mumbai (+5 more)

### Community 90 - "test_account_closure_steps.py"
Cohesion: 0.19
Nodes (19): closure_refund_provider_key(), build(), FakeGateway, test_a_cache_failure_is_surfaced_not_swallowed(), test_a_provider_declining_the_refund_is_recorded_and_does_not_block(), test_a_provider_outage_retries_with_the_same_key_and_never_erases_early(), test_a_refund_that_cannot_be_issued_is_recorded_failed_after_the_cap(), test_after_the_retry_cap_unsettled_refunds_are_logged_and_erasure_proceeds() (+11 more)

### Community 91 - "AdminUseCases"
Cohesion: 0.13
Nodes (6): AdminUseCases, UserNotifier, test_admin_deactivate_salon_requires_super_admin(), test_admin_list_salons_requires_super_admin(), test_admin_list_salons_super_admin_ok(), test_onboarding_requires_admin_before_reading_private_data()

### Community 92 - "schemas/admin.py"
Cohesion: 0.11
Nodes (9): AdminApproveSalonRequest, AdminSalonOnboardingResponse, CategoryCreateRequest, CategoryUpdateRequest, SubcategoryCreateRequest, SubcategoryUpdateRequest, HostedMediaRequest, ServiceResponse (+1 more)

### Community 93 - "test_subscription.py"
Cohesion: 0.13
Nodes (17): SubscriptionStatus, is_subscription_promotion_active(), test_active_trialing_eligible_during_period(), test_active_trialing_ineligible_outside_period(), test_active_trialing_ineligible_with_null_dates(), test_cancelled_eligible_until_period_end(), test_cancelled_ineligible_after_period_end(), test_cancelled_ineligible_with_null_period_end() (+9 more)

### Community 94 - "Website, customer app and owner app: developer handoff"
Cohesion: 0.08
Nodes (26): 1. Project and responsibility map, 2. Shared configuration and integration rules, 3. Shared customer workflows, 4. Website: screens and responsibilities, 5. Customer app: screens and responsibilities, 6. Owner app and owner web: business workflows, 7. Shared notifications, profile, support and erasure, 8. Critical boundaries and release evidence (+18 more)

### Community 95 - "post"
Cohesion: 0.21
Nodes (14): approve_booking(), barber_cancel_booking(), cancel_booking(), check_in(), complete_booking(), create_booking(), delay_booking(), get_booking() (+6 more)

### Community 96 - "asyncio"
Cohesion: 0.04
Nodes (30): build_engines(), get_probe_session(), get_session(), MeasuredAsyncSession, downgrade(), upgrade(), backup(), statements() (+22 more)

### Community 97 - "test_fake_provider_flows.py"
Cohesion: 0.10
Nodes (8): ClientConfig, PaymentCallback, PaymentProvider, build(), test_existing_customer_authorization_is_enforced_with_fake_provider(), test_fake_payment_and_refund_use_existing_intake_worker_and_replay_gate(), test_http_intake_rejects_tampering_and_cashfree_path_without_storing_effects(), test_sdk_callback_never_marks_a_mock_payment_paid()

### Community 98 - "pytest"
Cohesion: 0.17
Nodes (15): validate_salon_photo_write(), visible_salon_photos(), test_online_first_then_cash_receipt_is_refused_by_the_database(), test_inline_images_cannot_enter_media_records_or_cached_responses(), test_create_booking_request_accepts_new_preferences(), photo(), test_cover_replacement_keeps_slide_capacity(), test_legacy_duplicate_allows_metadata_updates_and_unique_replacement() (+7 more)

### Community 100 - "SubscriptionBillingUseCases"
Cohesion: 0.19
Nodes (5): _body_amount(), SubscriptionBillingUseCases, Entitlement, test_cancel_is_idempotent_keeps_paid_through_and_works_with_billing_off(), test_config_never_allows_native_purchase_and_exposes_only_the_public_key()

### Community 101 - "test_payment_fees_policy.py"
Cohesion: 0.14
Nodes (17): cancellation_deduction(), gateway_fee_amount(), payee_share(), _settings(), test_deduction_never_exceeds_amount_paid_and_never_negative(), test_flat_and_percent_rules_are_both_accepted_and_percent_is_capped(), test_flat_deduction(), test_gateway_fee_is_percent_rounded_half_up_to_paise() (+9 more)

### Community 102 - "test_public_discovery_contract.py"
Cohesion: 0.12
Nodes (14): add_salon(), catalog(), found(), test_a_paused_salon_offers_no_payment_method(), test_city_filter_is_exact_but_ignores_case_and_spaces(), test_filters_combine_with_and(), test_inactive_category_service_search_keeps_literal_wildcards(), test_nearby_supports_the_same_filters() (+6 more)

### Community 103 - "evaluation.py"
Cohesion: 0.14
Nodes (9): create_connection(), agent_loop(), evaluate_single_task(), extract_xml_content(), main(), parse_env_vars(), parse_evaluation_file(), parse_headers() (+1 more)

### Community 104 - "test_booking_error_classification.py"
Cohesion: 0.18
Nodes (12): business_error(), infrastructure_error(), _PgError, _session(), test_business_not_accepting_error_keeps_its_code(), test_business_slot_error_maps_to_slot_unavailable(), test_checkout_guard_trigger_errors_keep_their_codes(), test_database_error_without_sqlstate_is_re_raised() (+4 more)

### Community 105 - "math"
Cohesion: 0.17
Nodes (15): analyse(), load(), main(), _money(), NumbersError, report(), sensitivity(), _sum() (+7 more)

### Community 106 - "PaymentGatewayResolver"
Cohesion: 0.16
Nodes (9): decorate(), timed(), WebhookDomain, PaymentGatewayResolver, test_resolver_registry_never_substitutes_a_provider(), test_webhook_gateways_are_per_enabled_provider(), test_cashfree_disabled_never_builds_adapter_or_calls_provider(), test_disabled_cashfree_requires_no_credentials_and_has_no_new_capabilities() (+1 more)

### Community 107 - "migration_mumbai_runtime_20261015.py"
Cohesion: 0.13
Nodes (12): SQLProfileRepository, rollback_checks(), erasure_probe(), call(), main(), actor_override(), selected_probe(), metadata() (+4 more)

### Community 108 - "MCP Server Evaluation Guide"
Cohesion: 0.09
Nodes (23): Answer Guidelines, Complexity and Depth, Core Requirements, Diversity, Evaluation Examples, Evaluation Overview, Evaluation Requirements, Good Questions (+15 more)

### Community 109 - "Python MCP Server Implementation Guide"
Cohesion: 0.09
Nodes (23): Async/Await Best Practices, Code Best Practices, Code Composability and Reusability, Complete Example, Error Handling, Key Imports, MCP Python SDK and FastMCP, Overview (+15 more)

### Community 110 - "test_docker_image_ids.py"
Cohesion: 0.33
Nodes (6): digest(), image_ids(), archive_fixture(), test_accepts_equivalent_ids_from_verified_archive(), test_legacy_archive_keeps_config_id(), test_rejects_unrelated_or_corrupt_metadata()

### Community 111 - ".reject_salon"
Cohesion: 0.13
Nodes (3): SalonApprovalRepository, WorkspaceRepository, test_decisions_record_verified_admin_and_trim_reason_without_banning_owner()

### Community 112 - "SubscriptionPlanRepo"
Cohesion: 0.14
Nodes (3): SalonSubscriptionRepo, SubscriptionEventRepo, SubscriptionPlanRepo

### Community 113 - "make_super_admin"
Cohesion: 0.20
Nodes (16): make_super_admin(), catalog_client(), _migration(), test_admin_route_notifier_enqueues_without_booking_and_forwards_data(), test_admin_routes_hand_a_background_task_runner_to_the_use_case(), test_approve_notifies_owner_with_status_payload(), test_background_push_failure_is_swallowed(), test_enqueue_persists_data_json_and_allows_no_booking() (+8 more)

### Community 114 - "test_booking_finance_sql.py"
Cohesion: 0.23
Nodes (18): command(), finance(), outcome(), setup(), terminal(), test_admin_finance_requires_mfa_and_other_owner_cannot_read_statement(), test_checked_in_collection_capability_is_owner_scoped(), test_completed_prepaid_has_zero_commission_and_only_actual_provider_cost() (+10 more)

### Community 115 - "test_booking_contract_sql.py"
Cohesion: 0.24
Nodes (17): AppError, _body(), _count(), _direct_book(), _qr_book(), _second_customer(), test_direct_booking_persists_source_app(), test_direct_route_cannot_claim_qr_walkin() (+9 more)

### Community 117 - "Changelog"
Cohesion: 0.10
Nodes (20): [0.1.3](https://github.com/supabase/agent-skills/compare/v0.1.2...v0.1.3) (2026-06-02), [0.1.4](https://github.com/supabase/agent-skills/compare/v0.1.3...v0.1.4) (2026-06-05), [0.1.5](https://github.com/supabase/agent-skills/compare/v0.1.4...v0.1.5) (2026-07-10), [0.1.6](https://github.com/supabase/agent-skills/compare/v0.1.5...supabase-v0.1.6) (2026-07-30), [0.1.7](https://github.com/supabase/agent-skills/compare/v0.1.6...supabase-v0.1.7) (2026-08-12), [0.1.8](https://github.com/supabase/agent-skills/compare/v0.1.7...supabase-v0.1.8) (2026-09-24), [0.1.9](https://github.com/supabase/agent-skills/compare/v0.1.8...supabase-v0.1.9) (2026-09-28), Bug Fixes (+12 more)

### Community 118 - "mumbai_browser.cjs"
Cohesion: 0.12
Nodes (12): { chromium }, fs, path, allowed, checks, {chromium}, data, errors (+4 more)

### Community 119 - "Any"
Cohesion: 0.14
Nodes (4): FakeExpoClient, FakeExpoResponse, FakeMappings, FakeResult

### Community 120 - "redis.py"
Cohesion: 0.16
Nodes (9): get_redis_cache(), init_redis_cache(), _redacted_target(), test_startup_outage_retains_client_and_retries_epoch_after_reconnect(), test_redacted_target_never_contains_the_password(), test_redis_cache_create_handles_connection_failure(), test_redis_cache_create_returns_noop_on_none_or_empty_url(), test_redis_cache_delete_prefix_with_mock_client() (+1 more)

### Community 122 - "test_closed_salon_statement.py"
Cohesion: 0.17
Nodes (9): client(), _month(), _Repo, test_only_super_admin_can_list_or_read_statements(), test_routes_are_super_admin_only(), test_statement_derives_net_figures_and_totals_per_currency(), test_statement_of_a_salon_that_was_not_closed_by_deletion_is_not_found(), test_statement_with_no_transactions_is_empty_not_an_error() (+1 more)

### Community 123 - "SalonSubscriptionUseCases"
Cohesion: 0.24
Nodes (6): _assert_admin(), SalonSubscriptionUseCases, SubscriptionPlanUseCases, test_cannot_create_subscription_with_terminal_status(), test_non_admin_cannot_manage_plans(), test_non_admin_cannot_manage_subscriptions()

### Community 124 - "WalkInUseCases"
Cohesion: 0.18
Nodes (5): WalkInUseCases, test_booking_context_rejects_cross_salon_and_keeps_qr_source(), test_booking_context_rejects_owner_before_database_lookup(), test_get_salon_by_qr_delegates(), test_get_salon_by_qr_not_found()

### Community 125 - "test_public_http_and_playwright_refresh_after_lost_invalidation"
Cohesion: 0.15
Nodes (8): save(), ask(), Gate, test_concurrent_http_booking_and_idempotent_retry_during_redis_outage(), authenticated_session(), session(), test_public_http_and_playwright_refresh_after_lost_invalidation(), test_two_processes_mutation_outage_reconnect_never_returns_stale()

### Community 126 - "Module Group 126"
Cohesion: 0.11
Nodes (19): 1.1 Understand Modern MCP Design, 1.2 Study MCP Protocol Documentation, 1.3 Study Framework Documentation, 1.4 Plan Your Implementation, 2.1 Set Up Project Structure, 2.2 Implement Core Infrastructure, 2.3 Implement Tools, 3.1 Code Quality (+11 more)

### Community 127 - "outbox_worker.py"
Cohesion: 0.13
Nodes (6): drain_notification_outbox(), enqueue_and_deliver_notification(), run_forever(), business_checks(), create(), request()

### Community 129 - "Supabase"
Cohesion: 0.11
Nodes (15): Fix suggestion, Source, What happened, Skill Feedback, Steps, Core Principles, Debugging, Making and Committing Schema Changes (+7 more)

### Community 130 - "Admin"
Cohesion: 0.11
Nodes (18): Admin, GET `/v1/admin/catalog/categories`, GET `/v1/admin/catalog/categories/{category_id}/subcategories`, GET `/v1/admin/catalog/languages`, GET `/v1/admin/salons`, GET `/v1/admin/salons/{salon_id}`, GET `/v1/admin/salons/{salon_id}/onboarding`, PATCH `/v1/admin/catalog/categories/{category_id}` (+10 more)

### Community 131 - "round_money"
Cohesion: 0.12
Nodes (12): round_money(), test_round_money_is_half_up_and_coerces(), 1. Start of every chat, 2. How a senior works, 3. When there is an error or failing test, 4. When improving or reviewing code, 5. Safe cleanup rules, 6. Database and money (+4 more)

### Community 132 - "docs/README.md"
Cohesion: 0.19
Nodes (6): Folder structure, Account deletion contract (customer app, owner app, website), Frontend integration, Git workflow, Project documentation, Technology stack

### Community 133 - "test_image_families.py"
Cohesion: 0.15
Nodes (28): age_objects(), erasure_service(), key(), references(), test_any_reference_protects_entire_family(), test_bad_ack_requires_matching_head_not_an_unchecked_success(), test_distinct_grants_share_immutable_keys_but_accounts_do_not(), test_duplicate_and_concurrent_uploads_reuse_identical_members() (+20 more)

### Community 135 - "test_account_deletion_api.py"
Cohesion: 0.12
Nodes (5): client(), test_admin_ledger_is_super_admin_only_and_has_no_personal_fields(), test_deletion_blocked_409_body_contains_structured_counts(), test_domain_errors_map_to_documented_statuses(), test_status_is_authenticated_by_header_token_not_jwt()

### Community 136 - "test_migration_tool_paths.py"
Cohesion: 0.12
Nodes (6): tmp_path(), offline_tools(), test_offline_bundle_matches_sealed_files(), test_revision_review_preserves_sealed_evidence(), test_runner_imports_without_network_or_credentials(), Gotchas

### Community 137 - "test_public_salon_visibility.py"
Cohesion: 0.21
Nodes (6): test_cached_walkin_requires_current_database_qr_validation(), test_detail_visibility_on_miss_and_stale_cache(), test_hidden_public_catalog_miss_stops_before_catalog_read(), test_list_sources_only_return_approved_active_complete(), test_public_catalog_miss_avoids_unused_photo_query(), test_revocation_blocks_existing_and_late_cache_fills()

### Community 138 - "chief-of-staff.md"
Cohesion: 0.12
Nodes (16): 1. skip (auto-archive), 2. info_only (summary only), 3. meeting_info (calendar cross-reference), 4. action_required (draft reply), 4-Tier Classification System, Briefing Output Format, Example Invocations, Key Design Principles (+8 more)

### Community 139 - "Changelog"
Cohesion: 0.12
Nodes (16): [1.2.0](https://github.com/supabase/agent-skills/compare/v1.1.1...v1.2.0) (2026-06-02), [1.3.0](https://github.com/supabase/agent-skills/compare/v1.2.0...v1.3.0) (2026-06-05), [1.4.0](https://github.com/supabase/agent-skills/compare/v1.3.0...v1.4.0) (2026-07-10), [1.5.0](https://github.com/supabase/agent-skills/compare/supabase-postgres-best-practices-v1.4.0...supabase-postgres-best-practices-v1.5.0) (2026-07-30), [1.6.0](https://github.com/supabase/agent-skills/compare/supabase-postgres-best-practices-v1.5.0...supabase-postgres-best-practices-v1.6.0) (2026-07-30), Bug Fixes, Bug Fixes, Bug Fixes (+8 more)

### Community 140 - "AuthTokens"
Cohesion: 0.19
Nodes (3): AuthTokens, RefreshInput, Refresh

### Community 141 - "PaymentProviderNotConfiguredError"
Cohesion: 0.23
Nodes (3): PaymentProviderNotConfiguredError, NullPaymentGateway, test_null_gateway_implements_every_abstract_method_and_refuses_all()

### Community 142 - "qr.py"
Cohesion: 0.20
Nodes (7): _build_walkin_url(), make_qr_png(), make_qr_svg(), test_build_walkin_url_appends_token_to_route_prefix(), test_different_salon_tokens_produce_different_qr_images(), test_qr_render_is_deterministic_for_permanent_salon_identity(), test_printed_payload_is_the_web_route_plus_the_token()

### Community 144 - "Env"
Cohesion: 0.23
Nodes (3): env(), Env, SubscriptionStateResponse

### Community 145 - "Running Evaluations"
Cohesion: 0.12
Nodes (15): 1. Local STDIO Server, 2. Server-Sent Events (SSE), 3. HTTP (Streamable HTTP), Command-Line Options, Complete Example Workflow, Connection Errors, Evaluation File Format, Low Accuracy (+7 more)

### Community 146 - "Writing Guidelines for Postgres References"
Cohesion: 0.12
Nodes (15): 1. Concrete Transformation Patterns, 2. Error-First Structure, 3. Quantified Impact, 4. Self-Contained Examples, 5. Semantic Naming, Code Example Standards, Comments, Impact Level Guidelines (+7 more)

### Community 147 - "Customer App Backend API Contract"
Cohesion: 0.12
Nodes (16): Account deletion and closed salons, Audit result, Authentication, Availability, Avatar upload, Booking list filters, Bulk notification read, Create booking (+8 more)

### Community 150 - "salon-backend"
Cohesion: 0.13
Nodes (14): Agents (`.claude/agents/`), Commands (run from `backend/`), Core backend agents, Founder skills (feature building and planning), graphify, Key rules, Layer map, Maintenance agents (+6 more)

### Community 151 - "Super-admin to owner review thread (spec; design, not built)"
Cohesion: 0.13
Nodes (14): API (explicit `response_model`, status codes and `UUID` IDs), Authorization, Client impact (for the update lists), Data model (proposal), Decisions (from the interview), Erasure, Live status, Migration outline (not a migration file) (+6 more)

### Community 152 - "repositories/account_deletion_repository.py"
Cohesion: 0.22
Nodes (3): authored_quote_pattern(), personal_text_pattern(), quoted_text_pattern()

### Community 153 - "Progress: shifan"
Cohesion: 0.14
Nodes (13): test_a_customer_in_the_chair_is_blocked(), test_closed_salon_statement_keeps_money_totals_after_owner_erasure(), 2026-10-24 continuation: lint/offline/live booking and fresh vendor check, Blockers and open questions, Decisions, Files touched, Goal, In progress (+5 more)

### Community 154 - "test_vm_release.py"
Cohesion: 0.25
Nodes (10): release(), run_release(), test_containerd_manifest_id_is_accepted_from_verified_allowlist(), test_failed_readiness_does_not_promote_release(), test_migration_failure_preserves_previous_release_record(), test_missing_runtime_env_stops_before_migrations(), test_pre_deploy_failure_never_replaces_services(), test_release_rejects_implicit_head_before_any_docker_operation() (+2 more)

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

### Community 159 - "Salon Owner App Backend API Contract"
Cohesion: 0.14
Nodes (14): Account deletion (owner), Audit result, Authentication, Bookings, Closures and blocked time, Endpoint summary, Images, services, and staff, Media upload flow (+6 more)

### Community 161 - "Progress: thameem/cloud-run-startup-investigation"
Cohesion: 0.15
Nodes (12): test_mumbai_validation_workflow_is_manual_and_has_no_scratch_service(), Blockers and open questions, Decisions, Done, Files touched, Goal, In progress, Next steps (+4 more)

### Community 162 - "Module Group 162"
Cohesion: 0.29
Nodes (7): Cloud Run Deployment Assessment 2026-10-22, Mumbai Cloud Run Staging Deployment 2026-10-16, Mumbai Staging Startup Investigation 2026-10-16, Startup Profile Baseline and Import Review 2026-10-20, Local Docker Cold Start Measurement 2026-10-16, Infrastructure Ownership and Cost Audit 2026-10-16, Local Mumbai Database Health Recovery 2026-10-16

### Community 163 - "Module Group 163"
Cohesion: 0.29
Nodes (7): Authorized Local Cleanup 2026-10-15, Mumbai Execution Preflight and Hold 2026-10-15, Final Mumbai Local Staging Acceptance 2026-10-15, Mumbai Local Refresh Implementation and Verification 2026-10-15, Redis Recovery Verification 2026-10-16, Mumbai Customer and Owner Refresh Audit 2026-10-15, Mumbai Refresh Designs 2026-10-15

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
Cohesion: 0.15
Nodes (13): Access and availability notes, Complete backend API reference for frontend teams, Customer, Errors and schema limitations, GET `/v1/customer/profile`, How to use this reference, Inventory, PATCH `/v1/customer/profile` (+5 more)

### Community 170 - "Agent Instructions"
Cohesion: 0.17
Nodes (11): Agent Instructions, Auth Rules, Backend Architecture Rules, Code Ownership, Dependency And Setup Files, Deployment Rules, Secrets And Environment, Source of Truth (+3 more)

### Community 171 - "ProfileUpdateRequest"
Cohesion: 0.33
Nodes (9): ProfileUpdateRequest, test_profile_name_cannot_be_cleared(), test_profile_name_is_trimmed_and_omitted_fields_stay_omitted(), test_profile_update_accepts_plus_91_storage_format(), test_profile_update_allows_repeated_digits_inside_valid_mobile(), test_profile_update_normalizes_indian_mobile(), test_profile_update_preserves_bundled_avatar_references(), test_profile_update_rejects_fake_or_invalid_mobile() (+1 more)

### Community 172 - "Module Group 172"
Cohesion: 0.40
Nodes (6): For Customers / For Salons Dual Audience Section, Footer – Making every appointment a little simpler, Our Founders Section – Ziyarad Huq CEO, Shifan NV CPO, Shoiball CMO, Hero Section – Becoming your best aesthetic, Salon BRQ Marketing Landing Page, QR Code Scan-to-Book Customer Flow

### Community 173 - "Account Deletion"
Cohesion: 0.14
Nodes (8): Account Deletion, GET `/v1/account/deletion/{request_id}`, GET `/v1/admin/account-deletions`, GET `/v1/admin/deleted-salons`, GET `/v1/admin/deleted-salons/{salon_id}/statement`, POST `/v1/account/deletion`, POST `/v1/account/deletion/challenges`, POST `/v1/account/deletion/challenges/{challenge_id}/verify`

### Community 175 - "family_id"
Cohesion: 0.17
Nodes (11): family_id(), Additive API contract, Admission and resource limits, Family retirement and account erasure, Keys, proof and compatibility, Local verification, 2026-10-19, Policy, Server-side WebP image families (+3 more)

### Community 176 - "test_expo_push_includes_notification_payload"
Cohesion: 0.26
Nodes (4): FakeSession, test_expo_push_includes_notification_payload(), test_raw_fcm_receives_notification_payload_when_configured(), test_raw_fcm_without_credentials_records_failed_delivery()

### Community 177 - "Database Reviewer"
Cohesion: 0.17
Nodes (11): 1. Query Performance (CRITICAL), 2. Schema Design (HIGH), 3. Security (CRITICAL), Anti-Patterns to Flag, Core Responsibilities, Database Reviewer, Diagnostic Commands, Key Principles (+3 more)

### Community 178 - "mcp-builder/SKILL.md"
Cohesion: 0.17
Nodes (8): Core MCP Documentation (Load First), 📚 Documentation Library, Evaluation Guide (Load During Phase 4), Language-Specific Implementation Guides (Load During Phase 2), MCP Server Development Guide, Overview, Reference Files, SDK Documentation (Load During Phase 1/2)

### Community 179 - "Progress: thameem/mumbai-forward-reconciliation"
Cohesion: 0.17
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

### Community 185 - "Bookings"
Cohesion: 0.17
Nodes (12): Bookings, GET `/v1/bookings/{booking_id}`, POST `/v1/bookings`, POST `/v1/bookings/{booking_id}/approve`, POST `/v1/bookings/{booking_id}/cancel`, POST `/v1/bookings/{booking_id}/cancel/barber`, POST `/v1/bookings/{booking_id}/check-in`, POST `/v1/bookings/{booking_id}/complete` (+4 more)

### Community 186 - "How to use the prompts"
Cohesion: 0.17
Nodes (11): Configuration: what belongs where, Critique and corrected product workflow, Frontend integration prompt pack, How to use the prompts, Model assignments and cost discipline, Prompt 0 — Backend readiness and corrected contract, Prompt 1 — Customer app, Prompt 2 — Owner app (+3 more)

### Community 187 - "test_removed_profile_fields.py"
Cohesion: 0.27
Nodes (5): OwnerSalonUpdateRequest, test_partial_salon_updates_preserve_omitted_fields_and_trim_details(), test_salon_cannot_clear_required_profile_details(), test_salon_rejects_removed_fields(), test_services_reject_optional_overrides()

### Community 188 - "booking.py"
Cohesion: 0.20
Nodes (5): Booking, BookingLine, BookingStatus, PaymentStatus, allowed_status_transitions()

### Community 190 - "test_concurrent_avatar_commit_failure_and_cleanup_keep_committed_family"
Cohesion: 0.18
Nodes (4): api_client(), gateway(), test_concurrent_avatar_commit_failure_and_cleanup_keep_committed_family(), cleanup_committing_family()

### Community 191 - "Rows"
Cohesion: 0.18
Nodes (3): Rows, SQLiteSession, test_admin_list_selects_required_review_and_owner_fields()

### Community 192 - "Pass 2 — Clean Architecture & Standards"
Cohesion: 0.18
Nodes (10): 1. Baseline before touching anything, 2. Review in three passes, 3. Apply or report, 4. Refactor one increment at a time, 5. Verify, then report, Pass 1 — Security, Pass 2 — Clean Architecture & Standards, Pass 3 — Folder Structure (+2 more)

### Community 193 - "redis_recovery_browser.cjs"
Cohesion: 0.40
Nodes (3): {chromium}, readline, target

### Community 194 - "get_cache"
Cohesion: 0.27
Nodes (5): get_cache(), test_database_health_returns_safe_503_when_database_is_unavailable(), test_redis_health_disabled_when_not_configured(), test_redis_health_ok_when_reachable(), test_redis_health_returns_503_when_ping_fails()

### Community 195 - "get_image_family"
Cohesion: 0.20
Nodes (5): get_image_family(), GET `/v1/media/results/{token}`, Media, POST `/v1/customer/profile/avatar`, PUT `/v1/media/uploads/{token}`

### Community 197 - "test_database_backup.py"
Cohesion: 0.22
Nodes (4): test_encrypted_pipeline_only_records_complete_exports(), test_private_keys_must_not_live_in_checkout(), test_unignored_checkout_destination_is_rejected(), test_unsafe_source_cannot_start_any_export()

### Community 199 - "founder-board"
Cohesion: 0.20
Nodes (9): founder-board, Output, Rules, Step 0: the idea file, Step 1: brief the board, Step 2: convene, Step 3: the chair's summary, The rule about the three names (+1 more)

### Community 200 - "Module Group 200"
Cohesion: 0.67
Nodes (4): Frontend API Usage Matrix 2026-10-22, Frontend Update Lists 2026-10-22, Full API Architecture Audit 2026-10-21, Image Variants Review and Staging Gate 2026-10-19

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

### Community 210 - "install_database_metrics"
Cohesion: 0.28
Nodes (6): install_database_metrics(), after(), before(), PayoutHistoryEntryResponse, Payments and payee onboarding: stage 1 additions (backend only, dormant, not sandbox-tested), Payments and payout history (backend, dormant until a provider is configured)

### Community 211 - "source"
Cohesion: 0.22
Nodes (7): can_cancel(), source(), AccessStateResponse, BookingCreateRequest, BookingResponse, GET `/v1/bookings`, Booking action requests

### Community 213 - ".insert_refund"
Cohesion: 0.33
Nodes (3): test_commission_snapshot_is_immutable_and_reversal_is_bounded(), test_earnings_use_the_snapshot_and_reversals(), test_excess_refund_via_refund_rows_leaves_booking_paid()

### Community 215 - "reseal_layout_evidence.py"
Cohesion: 0.33
Nodes (5): current_path(), digest(), main(), reseal(), rewrite()

### Community 216 - "test_account_deletion_migration.py"
Cohesion: 0.50
Nodes (7): load(), run(), test_audit_trigger_escape_hatch_and_erasure_helper(), test_downgrade_restores_baseline_audit_trigger_and_drops_everything(), test_revision_chain_is_linear_after_media_guards(), test_upgrade_creates_bound_challenges_and_a_pii_free_ledger(), test_upgrade_relaxes_only_the_not_null_columns_erasure_must_clear()

### Community 217 - "public_api"
Cohesion: 0.25
Nodes (5): test_category_requires_service_assigned_to_active_staff(), test_category_uses_service_presentation_not_salon_business_label(), public_api(), database(), DatabaseHealthResponse

### Community 218 - "_Clock"
Cohesion: 0.25
Nodes (5): _Clock, _grant(), test_expiry_crossed_during_processing_stores_nothing_and_reports_the_failure(), test_expiry_crossed_during_storage_still_returns_204_and_extends_nothing(), test_put_with_query_string_commits_and_returns_204_with_the_result_link()

### Community 219 - "founder-marketing"
Cohesion: 0.22
Nodes (8): founder-marketing, Output, Rules, Step 1: read the evidence, Step 2: positioning, Step 3: channels, Step 4: the 30-day campaign, Step 5: budget and numbers

### Community 220 - "founder-offer"
Cohesion: 0.22
Nodes (8): founder-offer, Output, Rules, Step 1: read what is already known, Step 2: the problem list, Step 3: solutions, trimmed and stacked, Step 4: score it, Step 5: re-test it

### Community 227 - "adapter"
Cohesion: 0.32
Nodes (6): adapter(), test_create_order_rejects_long_receipt_and_zero_amount(), test_create_order_sends_paise_receipt_and_basic_auth(), handler(), test_fetches_map_states_and_404_is_none(), test_refund_is_sent_in_paise_with_an_idempotency_header()

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

### Community 236 - "Domain rules"
Cohesion: 0.25
Nodes (7): Account deletion, Booking, Cancellation, no-show and payout holds (owner-approved U08 target; not released), Domain rules, Payments, Public salon visibility, Roles

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

### Community 242 - "test_list_bookings_scoping.py"
Cohesion: 0.43
Nodes (3): _list_sql(), test_customer_role_still_sees_only_own_bookings(), test_salon_roles_are_not_matched_on_their_personal_customer_bookings()

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

### Community 249 - "Booking Actions"
Cohesion: 0.29
Nodes (7): Booking Actions, GET `/v1/booking-action-requests`, POST `/v1/booking-action-requests/{request_id}/respond`, POST `/v1/bookings/{booking_id}/cancellation-requests`, POST `/v1/bookings/{booking_id}/payment-confirmation-requests`, POST `/v1/salons/me/closures`, POST `/v1/salons/me/closures/preview`

### Community 250 - "Public discovery, QR and booking contract"
Cohesion: 0.29
Nodes (7): 1. Search salons by name, area and service, 3. QR contract, 4. Booking directly by salon id, 5. Error codes, 6. Client follow-ups, 7. What was verified, and how, Public discovery, QR and booking contract

### Community 252 - "image_family.py"
Cohesion: 0.47
Nodes (3): AvatarResponse, ImageFamilyResponse, ImageVariantResponse

### Community 256 - "Frontend Integration Prompt — Redis Feature Changes"
Cohesion: 0.33
Nodes (5): Error Envelope Reference, Frontend Integration Prompt — Redis Feature Changes, Prompt — Customer App, Prompt — Owner App, UUID Generation — Language Quick Reference

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

### Community 274 - "Notifications"
Cohesion: 0.33
Nodes (6): DELETE `/v1/devices/{token}`, GET `/v1/notifications`, Notifications, POST `/v1/devices`, POST `/v1/notifications/{notification_id}/read`, POST `/v1/notifications/read-all`

### Community 275 - "Salon Platform API"
Cohesion: 0.33
Nodes (5): Checks, Docker, Documentation, Local development, Salon Platform API

### Community 277 - ".throttle"
Cohesion: 0.40
Nodes (3): Checklist, Output, Security reviewer (read-only)

### Community 278 - "Migration cleanup plan and execution record"
Cohesion: 0.40
Nodes (4): 1. `supabase-schema-backup/` in Git, 2. Root `migration_mumbai_*.py` runners (13) - current split implemented, 3. Evidence note, Migration cleanup plan and execution record

### Community 287 - "0011_holiday_soft_delete.py"
Cohesion: 0.60
Nodes (3): downgrade(), _replace_database_functions(), upgrade()

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

### Community 298 - "Roadmap"
Cohesion: 0.40
Nodes (4): Built, Dormant, Not built, Roadmap

### Community 302 - "Owner payout accounts and setup checklist"
Cohesion: 0.50
Nodes (4): Audit trail (migration `0027_payout_account_audit`), Owner payout accounts and setup checklist, Status, Storage and security

### Community 303 - "0015_salon_admin_approval.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_functions(), upgrade()

### Community 306 - "gcp-vm-release-compose.sh"
Cohesion: 0.50
Nodes (3): COMPOSE_ENV_FILE, COMPOSE_PROJECT_NAME, gcp-vm-release-compose.sh script

### Community 307 - "test_service_search_requires_active_category_and_subcategory"
Cohesion: 0.50
Nodes (3): _listed(), test_service_search_matches_what_the_services_list_shows(), test_service_search_requires_active_category_and_subcategory()

### Community 308 - "code-explorer.md"
Cohesion: 0.50
Nodes (3): Analysis Approach, Core Mission, Output Guidance

### Community 309 - "Code reviewer (read-only)"
Cohesion: 0.50
Nodes (3): Check the diff against, Code reviewer (read-only), Output

### Community 310 - "Migration reviewer (read-only)"
Cohesion: 0.50
Nodes (3): Check, Migration reviewer (read-only), Output

### Community 311 - "Clear Technical English"
Cohesion: 0.50
Nodes (3): Check the result, Clear Technical English, Write the explanation

### Community 312 - "Features"
Cohesion: 0.50
Nodes (3): Account deletion (implemented, not yet production-verified), Features, Payment collection (backend)

## Knowledge Gaps
- **42 isolated node(s):** `COMPOSE_ENV_FILE`, `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME`, `Footer – Making every appointment a little simpler`, `Our Founders Section – Ziyarad Huq CEO, Shifan NV CPO, Shoiball CMO` (+37 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3172 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **169 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Profile` connect `Profile` to `exceptions.py`, `use_cases/payments.py`, `owner.py`, `Role`, `test_accepting_bookings.py`, `OwnerUseCases`, `use_cases/platform.py`, `routes/payments.py`, `routes/admin.py`, `test_subscription_billing.py`, `deps.py`, `BookingPaymentUseCases`, `use_cases/subscription_billing.py`, `SubscriptionProviderResolver`, `routes/account_deletion.py`, `test_booking_changes_sql.py`, `routes/booking_actions.py`, `ValidationError`, `customer.py`, `use_cases/account_deletion.py`, `test_auth.py`, `routes/support.py`, `routes/booking_finance.py`, `bookings.py`, `test_salon_ranking.py`, `routes/auth.py`, `notifications.py`, `subscriptions.py`, `create_walkin_booking`, `source`, `AdminUseCases`, `test_subscription.py`, `post`, `CatalogAdminUseCases`, `SubscriptionBillingUseCases`, `SalonSubscriptionUseCases`, `migration_mumbai_runtime_20261015.py`, `get_my_profile`, `.reject_salon`, `make_super_admin`, `test_booking_contract_sql.py`, `.delete`, `WalkInUseCases`, `.authorize`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Are the 173 inferred relationships involving `Profile` (e.g. with `get_authenticated_session()` and `get_current_actor()`) actually correct?**
  _`Profile` has 173 INFERRED edges - model-reasoned connections that need verification._
- **What connects `COMPOSE_ENV_FILE`, `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME` to the rest of the system?**
  _42 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `exceptions.py` be split into smaller, more focused modules?**
  _Cohesion score 0.03903693314633006 - nodes in this community are weakly interconnected._
- **Why does `PlatformRepository` connect `PlatformRepository` to `exceptions.py`, `owner.py`, `Role`, `Profile`, `test_media_admission_http.py`, `Money`, `test_accepting_bookings.py`, `OwnerUseCases`, `use_cases/platform.py`, `test_checkout_safety_sql.py`, `Env`, `test_salon_approval_migration.py`, `routes/payments.py`, `BookingChangeRepository`, `routes/admin.py`, `test_payment_flows.py`, `ServiceUnavailableError`, `verify_phone`, `BookingPaymentUseCases`, `SubscriptionProviderResolver`, `test_subscription_billing_sql.py`, `routes/booking_actions.py`, `ValidationError`, `.list_salons`, `customer.py`, `test_payout_account.py`, `.list_bookings`, `test_maintenance_job.py`, `bookings.py`, `test_account_erasure_hardening.py`, `Rows`, `ConflictError`, `notifications.py`, `.get_available_slots`, `create_walkin_booking`, `schemas/admin.py`, `PaymentRepository`, `._find_owner_salon_id`, `.deactivate_device`, `AdminUseCases`, `.deactivate_device_for_actor`, `.get_qr_image_url`, `.__init__`, `post`, `.list_due_notification_outbox_ids`, `test_migration_and_service_api_round_trip`, `.lock_media_url`, `CatalogAdminUseCases`, `.mark_all_notifications_read`, `.mark_notification_outbox_processed`, `.mark_notification_outbox_retry`, `.media_reference_guards_installed`, `.media_url_is_referenced`, `.notification_has_failed_delivery`, `.set_qr_image_url`, `.validate_qr_token`, `asyncio`, `test_booking_error_classification.py`, `make_super_admin`, `test_list_bookings_scoping.py`, `test_booking_contract_sql.py`, `WalkInUseCases`, `outbox_worker.py`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `PlatformRepository` (e.g. with `list_public_categories()` and `list_public_subcategories()`) actually correct?**
  _`PlatformRepository` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Should `use_cases/payments.py` be split into smaller, more focused modules?**
  _Cohesion score 0.04021879021879022 - nodes in this community are weakly interconnected._