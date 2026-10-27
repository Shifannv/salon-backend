# Graph Report - backend  (2026-10-26)

## Corpus Check
- Large corpus: 508 files · ~653,644 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 5957 nodes · 17724 edges · 274 communities (148 shown, 126 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 2400 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Auth & API Wiring
- Payment Gateway Ports
- Salon Approval & Workspace
- Owner Profile & Staff
- Subscription Providers
- Owner Use Cases
- Booking & Webhook Routes
- Payout Provider Logic
- Image Processing
- Role & Permission Guards
- Booking Finance Policy
- Admin Catalog Routes
- Payment Error Types
- Cashfree Webhook Tests
- Booking Payment Use Cases
- Booking Lifecycle Routes
- Subscription Reconciler
- Admin Salon Use Cases
- Privacy & Erasure
- Subscription Billing Tests
- Module Group 20
- Module Group 21
- Module Group 22
- Module Group 23
- Module Group 24
- Module Group 25
- Module Group 26
- Module Group 27
- Module Group 28
- Module Group 29
- Module Group 30
- Module Group 31
- Module Group 32
- Module Group 33
- Module Group 34
- Module Group 35
- Module Group 36
- Module Group 37
- Module Group 38
- Module Group 39
- Module Group 40
- Module Group 41
- Module Group 42
- Module Group 43
- Module Group 44
- Module Group 45
- Module Group 46
- Module Group 47
- Module Group 48
- Module Group 49
- Module Group 50
- Module Group 51
- Module Group 52
- Module Group 53
- Module Group 54
- Module Group 55
- Module Group 56
- Module Group 57
- Module Group 58
- Module Group 59
- Module Group 60
- Module Group 61
- Module Group 62
- Module Group 63
- Module Group 64
- Module Group 65
- Module Group 66
- Module Group 67
- Module Group 68
- Module Group 69
- Module Group 70
- Module Group 71
- Module Group 72
- Module Group 73
- Module Group 74
- Module Group 75
- Module Group 76
- Module Group 77
- Module Group 78
- Module Group 79
- Module Group 80
- Module Group 81
- Module Group 82
- Module Group 83
- Module Group 84
- Module Group 85
- Module Group 86
- Module Group 87
- Module Group 88
- Module Group 89
- Module Group 90
- Module Group 91
- Module Group 92
- Module Group 93
- Module Group 94
- Module Group 95
- Module Group 96
- Module Group 97
- Module Group 98
- Module Group 99
- Module Group 100
- Module Group 101
- Module Group 103
- Module Group 104
- Module Group 105
- Module Group 106
- Module Group 107
- Module Group 108
- Module Group 109
- Module Group 110
- Module Group 111
- Module Group 112
- Module Group 113
- Module Group 114
- Module Group 115
- Module Group 116
- Module Group 117
- Module Group 118
- Module Group 119
- Module Group 120
- Module Group 121
- Module Group 122
- Module Group 123
- Module Group 124
- Module Group 125
- Module Group 126
- Module Group 127
- Module Group 128
- Module Group 129
- Module Group 130
- Module Group 132
- Module Group 133
- Module Group 134
- Module Group 135
- Module Group 136
- Module Group 137
- Module Group 138
- Module Group 139
- Module Group 140
- Module Group 141
- Module Group 142
- Module Group 143
- Module Group 145
- Module Group 146
- Module Group 147
- Module Group 149
- Module Group 150
- Module Group 151
- Module Group 152
- Module Group 154
- Module Group 155
- Module Group 156
- Module Group 157
- Module Group 158
- Module Group 159
- Module Group 160
- Module Group 161
- Module Group 162
- Module Group 163
- Module Group 164
- Module Group 165
- Module Group 166
- Module Group 168
- Module Group 169
- Module Group 170
- Module Group 171
- Module Group 172
- Module Group 173
- Module Group 174
- Module Group 175
- Module Group 176
- Module Group 177
- Module Group 178
- Module Group 179
- Module Group 180
- Module Group 181
- Module Group 182
- Module Group 183
- Module Group 184
- Module Group 185
- Module Group 186
- Module Group 187
- Module Group 188
- Module Group 189
- Module Group 190
- Module Group 191
- Module Group 192
- Module Group 193
- Module Group 194
- Module Group 195
- Module Group 196
- Module Group 197
- Module Group 198
- Module Group 199
- Module Group 200
- Module Group 201
- Module Group 203
- Module Group 204
- Module Group 205
- Module Group 206
- Module Group 207
- Module Group 208
- Module Group 209
- Module Group 228
- Module Group 229
- Module Group 230
- Module Group 231
- Module Group 257
- Module Group 258
- Module Group 259
- Module Group 260
- Module Group 261
- Module Group 262
- Module Group 263
- Module Group 265
- Module Group 268
- Module Group 269
- Module Group 270
- Module Group 271
- Module Group 272

## God Nodes (most connected - your core abstractions)
1. `Profile` - 367 edges
2. `PlatformRepository` - 262 edges
3. `ValidationError` - 184 edges
4. `Role` - 184 edges
5. `Settings` - 167 edges
6. `ForbiddenError` - 146 edges
7. `make_profile()` - 138 edges
8. `NotFoundError` - 137 edges
9. `Money` - 97 edges
10. `make_mock_repo()` - 97 edges

## Surprising Connections (you probably didn't know these)
- `handler()` --indirect_call--> `payments()`  [INFERRED]
  tests/unit/test_cashfree_gateway.py → app/api/v1/routes/subscription_billing.py
- `test_admin_response_exposes_priority_and_audit_actor()` --uses--> `AdminSalonResponse`  [INFERRED]
  tests/unit/test_salon_ranking.py → app/api/v1/schemas/admin.py
- `test_public_salon_response_has_no_subscription_fields()` --uses--> `SalonSummaryResponse`  [INFERRED]
  tests/unit/test_subscription.py → app/api/v1/schemas/platform.py
- `test_naive_start_datetime_is_rejected_not_reinterpreted()` --uses--> `BookingCreateRequest`  [INFERRED]
  tests/unit/test_walkin_qr_contract.py → app/api/v1/schemas/platform.py
- `test_the_request_carries_no_price_duration_or_end_time()` --uses--> `BookingCreateRequest`  [INFERRED]
  tests/unit/test_walkin_qr_contract.py → app/api/v1/schemas/platform.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **All Compose Workers Depend on Redis Health** — docker_compose_api_service, docker_compose_notification_worker, docker_compose_media_cleanup, docker_compose_account_deletion_worker, docker_compose_payment_webhook_worker, docker_compose_email_worker, docker_compose_redis [EXTRACTED 1.00]
- **Booking Creation Idempotency Pattern (Postgres + Redis + use cases)** — docs_booking_flow_postgres_functions, docs_payments_idempotency, docs_architecture_redis_caching [INFERRED 0.85]
- **Account Deletion End-to-End Flow (auth -> erasure -> financial purge)** — docs_account_deletion_flow, docs_account_deletion_erasure_worker, docs_account_deletion_financial_purge_design_overview [EXTRACTED 1.00]

## Communities (274 total, 126 thin omitted)

### Community 0 - "Auth & API Wiring"
Cohesion: 0.03
Nodes (24): get_authenticated_session(), get_cache(), get_current_actor(), get_payment_gateway(), get_payment_gateway_resolver(), get_storage_gateway(), process_in_background(), BookingChangeError (+16 more)

### Community 1 - "Payment Gateway Ports"
Cohesion: 0.05
Nodes (30): ClientConfig, PaymentEvent, ProviderPayment, RefundRequest, RefundResult, measure_external(), GatewayCapability, is_forward_transition() (+22 more)

### Community 2 - "Salon Approval & Workspace"
Cohesion: 0.04
Nodes (23): SalonApprovalRepository, WorkspaceRepository, BookingActionRequestUseCases, ClosureUseCases, _extract_r2_object_key(), assert_approved_workspace(), ForbiddenError, OnlinePaymentUnavailableError (+15 more)

### Community 3 - "Owner Profile & Staff"
Cohesion: 0.05
Nodes (45): assign_staff_service(), complete_profile(), create_blocked_slot(), create_holiday(), create_image(), create_service(), create_staff(), deactivate_service() (+37 more)

### Community 4 - "Subscription Providers"
Cohesion: 0.05
Nodes (20): ProviderOrder, ProviderOrderState, ProviderPaymentObservation, ProviderPaymentState, ProviderRefund, ProviderSubscriptionEvent, SubscriptionClientConfig, SubscriptionEventKind (+12 more)

### Community 5 - "Owner Use Cases"
Cohesion: 0.05
Nodes (15): build_setup_status(), _has_open_day(), mask_payout_account(), OwnerUseCases, _upload_extension(), _upload_result(), validate_payout_account(), Profile (+7 more)

### Community 6 - "Booking & Webhook Routes"
Cohesion: 0.05
Nodes (45): payment_webhook(), app_error_response(), AppError, PayloadTooLargeError, app_error_handler(), RequestTimeoutError, TooManyRequestsError, UnsupportedMediaTypeError (+37 more)

### Community 7 - "Payout Provider Logic"
Cohesion: 0.06
Nodes (35): PayoutProvider, IdempotencyKeyReuseError, EvidenceSource, PayoutRequest, PayoutStatus, ProviderFeeReconciliation, ProviderFees, ProviderPayout (+27 more)

### Community 8 - "Image Processing"
Cohesion: 0.05
Nodes (33): _canonical_json_value(), _request_fingerprint(), build_engines(), get_probe_session(), family_id(), namespace_for(), audit(), distribution() (+25 more)

### Community 9 - "Role & Permission Guards"
Cohesion: 0.05
Nodes (50): require_role(), dependency(), SubmitReport, AdminMFARequiredError, Role, make_profile(), test_post_booking_returns_distinct_409_when_not_accepting(), test_walkin_qr_booking_returns_same_409() (+42 more)

### Community 10 - "Booking Finance Policy"
Cohesion: 0.05
Nodes (51): Allocation, _amount(), cancellation_quote(), CancellationQuote, completed_service_allocation(), _remaining(), service_change_quote(), ServiceChangeQuote (+43 more)

### Community 11 - "Admin Catalog Routes"
Cohesion: 0.06
Nodes (34): _admin_use_cases(), approve_salon(), _catalog_use_cases(), create_category(), create_salon(), create_subcategory(), deactivate_category(), deactivate_salon() (+26 more)

### Community 12 - "Payment Error Types"
Cohesion: 0.06
Nodes (51): PaymentAmountMismatchError, PaymentOutcomeUnknownError, PaymentProviderError, build(), capture(), details(), FakeGateway, process_events() (+43 more)

### Community 13 - "Cashfree Webhook Tests"
Cohesion: 0.06
Nodes (52): ignored(), both_client(), cf_settings(), event_body(), gateway(), IntakeRepo, intent_request(), order_handler() (+44 more)

### Community 14 - "Booking Payment Use Cases"
Cohesion: 0.07
Nodes (20): apply_provider_payment(), BookingPaymentUseCases, _clean_code(), event_to_json(), _fingerprint(), _json_default(), _ledger_row(), observation_status() (+12 more)

### Community 15 - "Booking Lifecycle Routes"
Cohesion: 0.07
Nodes (32): approve_booking(), availability(), barber_cancel_booking(), booking_change_availability(), cancel_booking(), change_booking(), check_in(), complete_booking() (+24 more)

### Community 16 - "Subscription Reconciler"
Cohesion: 0.04
Nodes (20): SubscriptionReconciler, SubscriptionSettlement, get_settings(), Settings, reconcile_subscriptions_once(), test_auto_release_cannot_be_enabled_it_is_not_built(), test_blank_env_values_mean_unset_not_zero(), test_provider_defaults_stay_none() (+12 more)

### Community 17 - "Admin Salon Use Cases"
Cohesion: 0.06
Nodes (11): AdminUseCases, CatalogAdminUseCases, UserNotifier, test_admin_deactivate_salon_requires_super_admin(), test_admin_list_categories_requires_super_admin(), test_admin_list_categories_super_admin_ok(), test_admin_list_salons_requires_super_admin(), test_admin_list_salons_super_admin_ok() (+3 more)

### Community 18 - "Privacy & Erasure"
Cohesion: 0.04
Nodes (29): authored_quote_pattern(), personal_text_pattern(), quoted_text_pattern(), build(), write(), validate(), canonical_sha256(), main() (+21 more)

### Community 19 - "Subscription Billing Tests"
Cohesion: 0.07
Nodes (56): owner(), profile(), sub_settings(), adapter(), ent(), handler_for(), http(), make() (+48 more)

### Community 20 - "Module Group 20"
Cohesion: 0.04
Nodes (6): SQLAccountDeletionRepository, erasure_probe(), _statuses(), test_customer_open_booking_blocker_includes_checked_in(), RecordingSession, test_customer_clear_happens_before_profile_reference_detachment()

### Community 21 - "Module Group 21"
Cohesion: 0.08
Nodes (40): make_mock_repo(), make_owner(), client(), _migration_statements(), _owner_salon(), test_migration_adds_column_and_gates_both_db_functions(), test_migration_downgrade_restores_functions_then_drops_column(), test_non_owner_cannot_toggle() (+32 more)

### Community 22 - "Module Group 22"
Cohesion: 0.06
Nodes (24): _row(), SubscriptionBillingRepository, _plans(), test_0030_statements_are_idempotent_and_plan_checks_exist(), test_a_lapsed_active_row_within_stored_grace_keeps_the_benefit_without_a_sweep(), test_a_payment_that_lands_on_a_suspended_or_closed_salon_is_held_and_flagged(), test_a_suspended_salon_cannot_start_a_new_checkout(), test_account_deletion_blocks_a_live_subscription_and_rechecks_at_confirm() (+16 more)

### Community 23 - "Module Group 23"
Cohesion: 0.12
Nodes (44): set_actor_context(), create_app(), install(), install(), SafetyEnv, test_api_quote_auth_ownership_support_idempotency_and_safe_disabled_config(), actor(), session() (+36 more)

### Community 24 - "Module Group 24"
Cohesion: 0.06
Nodes (26): portable_revisions(), require_mumbai_url(), require_unambiguous_url(), validate_evidence(), validate_migration_target(), do_run_migrations(), guard_requested_migration(), run_migrations_offline() (+18 more)

### Community 25 - "Module Group 25"
Cohesion: 0.05
Nodes (8): get_image_family(), upload_avatar(), upload_signed_image(), MediaReferences, StorageGateway, managed_media_path(), retire_unreferenced_media(), validate_media_reference()

### Community 27 - "Module Group 27"
Cohesion: 0.08
Nodes (26): BookingUseCases, BookingSourceNotAllowedError, enqueue_and_deliver_notification(), make_booking(), test_approve_as_owner(), test_approve_requires_owner(), test_availability_delegates_to_repo(), test_booking_response_can_cancel_only_before_start_time() (+18 more)

### Community 28 - "Module Group 28"
Cohesion: 0.06
Nodes (22): create_walkin_booking(), get_qr_image(), require_qr_token_format(), resolve_qr(), _use_cases(), verify_phone(), CustomerAvailabilityResponse, WalkInSalonResponse (+14 more)

### Community 29 - "Module Group 29"
Cohesion: 0.08
Nodes (30): heartbeat_path(), is_healthy(), main(), max_age_seconds(), touch(), distribution(), docker(), inventory() (+22 more)

### Community 30 - "Module Group 30"
Cohesion: 0.07
Nodes (18): PaymentGateway, ProviderFeeReconciler, RefundProvider, WebhookVerifier, decorate(), timed(), WebhookDomain, _adapter_module() (+10 more)

### Community 31 - "Module Group 31"
Cohesion: 0.09
Nodes (14): R2StorageGateway, test_token_purposes_stay_cryptographically_separate(), test_r2_media_resume_skips_previous_prefixes_and_uses_start_after(), test_assert_configured_passes_when_all_settings_present(), test_assert_configured_raises_when_settings_missing(), test_delete_object_calls_boto3_delete(), test_delete_object_raises_validation_error_on_boto3_failure(), test_delete_object_raises_when_r2_not_configured() (+6 more)

### Community 32 - "Module Group 32"
Cohesion: 0.05
Nodes (24): HostedMediaRequest, BlockedSlotCreateRequest, BookingLineResponse, HolidayCreateRequest, OwnerSalonCompleteProfileRequest, OwnerSalonSettingsRequest, OwnerSalonUpdateRequest, OwnerSetupStatusResponse (+16 more)

### Community 33 - "Module Group 33"
Cohesion: 0.08
Nodes (16): _body_amount(), subscription_event_to_json(), SubscriptionBillingUseCases, BillingInterval, BillingStatus, derive_entitlement(), Entitlement, EntitlementState (+8 more)

### Community 34 - "Module Group 34"
Cohesion: 0.10
Nodes (33): checkpoint(), age_objects(), api_client(), erasure_service(), family(), gateway(), key(), references() (+25 more)

### Community 35 - "Module Group 35"
Cohesion: 0.10
Nodes (28): booking_quote(), cancel_payment(), confirm_payment(), create_payment_intent(), get_settlement_account(), list_booking_payments(), my_earnings(), payment_config() (+20 more)

### Community 36 - "Module Group 36"
Cohesion: 0.09
Nodes (12): PaymentIntent, PaymentIntentRequest, PaymentProvider, PaymentCapabilityError, CashfreeGateway, create_gateway(), _decimal(), dumps_json() (+4 more)

### Community 38 - "Module Group 38"
Cohesion: 0.07
Nodes (24): derive_payment_state(), header(), hex_hmac(), gateway_with(), hex_hmac(), make_settings(), test_callback_signature_vectors(), test_configured_provider_needs_credentials() (+16 more)

### Community 39 - "Module Group 39"
Cohesion: 0.09
Nodes (16): get_profile(), get_salon(), list_public_categories(), list_public_subcategories(), list_salon_services(), list_salon_staff(), list_salons(), nearby_salons() (+8 more)

### Community 40 - "Module Group 40"
Cohesion: 0.11
Nodes (22): get_auth_admin_gateway(), closed_salon_statement(), confirm_account_deletion(), get_deletion_status(), list_account_deletions(), list_closed_salons(), start_deletion_challenge(), _use_cases() (+14 more)

### Community 41 - "Module Group 41"
Cohesion: 0.10
Nodes (25): ImagePolicy, ProcessedVariant, PillowImageProcessor, source(), test_integrated_multipart_rejects_multiple_files_before_processing(), test_result_token_is_read_only_and_upload_token_is_not_a_result_token(), photo(), test_bounded_retry_rejects_when_no_output_can_meet_limit() (+17 more)

### Community 42 - "Module Group 42"
Cohesion: 0.13
Nodes (32): InvalidVerificationCodeError, build(), contacts(), FakeAuthGateway, test_a_subscription_bought_after_the_challenge_blocks_at_confirm(), test_active_subscription_blocks_only_with_a_real_provider(), test_admin_ledger_requires_super_admin(), test_challenge_and_token_cannot_authorize_another_account() (+24 more)

### Community 43 - "Module Group 43"
Cohesion: 0.07
Nodes (12): run_forever(), get_payment_resolver(), drain_webhook_events(), run_forever(), drain_notification_outbox(), run_forever(), config_values(), run() (+4 more)

### Community 44 - "Module Group 44"
Cohesion: 0.09
Nodes (17): _action_use_cases(), apply_closure(), _closure_use_cases(), create_cancellation_request(), create_payment_confirmation_request(), list_booking_action_requests(), preview_closure(), respond_booking_action_request() (+9 more)

### Community 45 - "Module Group 45"
Cohesion: 0.09
Nodes (20): _admin_base(), _assert_safe_existing_profile(), _AuthUser, _create_auth_user(), _FakeGateway, _find_user_by_email(), _get_profile_state(), main() (+12 more)

### Community 46 - "Module Group 46"
Cohesion: 0.09
Nodes (24): heartbeat_path(), is_healthy(), main(), max_age_seconds(), touch(), storage_is_required(), validate_worker_configuration(), cascade_tables_in_migrations() (+16 more)

### Community 47 - "Module Group 47"
Cohesion: 0.09
Nodes (40): app/core/migration_policy.py (Alembic env guard), Mumbai migration target (0040_fastapi_only_access, guarded approval required), Portable CI migration policy (target 0037, disposable loopback only), Cancellation reason field erasure (bookings.cancellation_reason_text/code), Mumbai Supabase project (wqjlgpnbiapcrlkxumcp, ap-south-1), Prepared revisions 0038-0040 (cancellation_compatibility, promotion_search_path, fastapi_only_access), Required owner approval decisions Q01-Q16 and A01-A06 before executable migration, Required 10-step forward-only reconciliation plan (+32 more)

### Community 48 - "Module Group 48"
Cohesion: 0.10
Nodes (12): AccountDeletionUseCases, deletion_stage(), mask_contact(), normalize_contact(), ContactMismatchError, DeletionBlockedError, digest(), digests_match() (+4 more)

### Community 49 - "Module Group 49"
Cohesion: 0.09
Nodes (24): drain_account_deletions(), run_forever(), init_redis_cache(), drain_queue(), main(), run_job(), run_pass(), attempt_one() (+16 more)

### Community 50 - "Module Group 50"
Cohesion: 0.06
Nodes (28): Account Deletion Worker Service, API Service (Docker Compose), Email Worker Service, Media Cleanup Worker Service, Notification Worker Service, Payment Webhook Worker Service, Redis Service (Docker Compose), Erasure Worker (lock/cancel/notify/refund/settle/erase) (+20 more)

### Community 51 - "Module Group 51"
Cohesion: 0.15
Nodes (29): confirm(), drain(), engine(), FakeAdmin, finish_ledger(), make_due(), make_service(), new_user() (+21 more)

### Community 52 - "Module Group 52"
Cohesion: 0.14
Nodes (21): get_subscription_provider_resolver(), cancel(), checkout(), list_purchasable_plans(), my_access_state(), my_subscription(), payments(), subscription_config() (+13 more)

### Community 53 - "Module Group 53"
Cohesion: 0.07
Nodes (9): _add_request_id(), configure_logging(), get_request_id(), set_request_id(), install_database_metrics(), RequestMetrics, TimingMiddleware, deliver_once() (+1 more)

### Community 55 - "Module Group 55"
Cohesion: 0.12
Nodes (14): create_ticket(), email_event(), read_ticket(), reply_ticket(), EmailEventResponse, SupportCreateRequest, SupportMessageResponse, SupportReplyRequest (+6 more)

### Community 56 - "Module Group 56"
Cohesion: 0.08
Nodes (7): _blank_to_none(), HolidayResponse, OwnerPayoutAccountRequest, ServicePresentationRequest, ServiceUpdateRequest, _visible_photos(), test_holiday_response_converts_database_uuid_ids_to_strings()

### Community 57 - "Module Group 57"
Cohesion: 0.08
Nodes (3): NotFoundError, PayAtSalonDailyLimitError, BookingChangeRepository

### Community 58 - "Module Group 58"
Cohesion: 0.11
Nodes (12): PaymentWebhookUseCases, SubscriptionWebhookHandler, InvalidWebhookSignatureError, test_fake_payment_and_refund_use_existing_intake_worker_and_replay_gate(), test_a_forged_signature_stores_nothing_and_both_providers_work_simultaneously(), subscription_side(), test_duplicate_delayed_and_out_of_order_webhooks_never_extend_twice(), deliver() (+4 more)

### Community 59 - "Module Group 59"
Cohesion: 0.08
Nodes (11): CustomerUseCases, test_update_profile_allows_customer(), test_update_profile_allows_owner_personal_profile(), test_update_profile_rejects_staff_customer_surface(), gateway(), test_avatar_grants_have_distinct_keys(), test_profile_write_failure_preserves_previous_image(), test_staff_grant_requires_owned_staff_before_storage() (+3 more)

### Community 60 - "Module Group 60"
Cohesion: 0.11
Nodes (9): admin_statement(), finance_command(), owner_statement(), AdminFinanceStatement, FinanceCommandRequest, OwnerPayoutStatement, BookingFinanceGateway, BookingFinanceUseCases (+1 more)

### Community 61 - "Module Group 61"
Cohesion: 0.16
Nodes (19): cancel_subscription(), create_plan(), create_test_subscription(), deactivate_plan(), get_salon_subscription(), list_events(), list_plans(), _plan_uc() (+11 more)

### Community 63 - "Module Group 63"
Cohesion: 0.12
Nodes (11): MeOutput, GetMe, EnsureOwnerAccess, require_active(), FakeProfileRepository, _profile(), test_get_me_returns_active_actor(), test_owner_access_fails_when_the_promotion_matches_no_row() (+3 more)

### Community 65 - "Module Group 65"
Cohesion: 0.07
Nodes (5): QrCodeNotFoundError, test_description_removal_photo_cleanup_constraints_and_concurrent_uploads(), test_gallery_attach_retry_returns_existing_row_without_duplicate_insert(), test_a_cached_salon_is_revalidated_so_an_expired_token_stops_working(), test_unknown_expired_or_unpublished_token_is_one_machine_readable_404()

### Community 66 - "Module Group 66"
Cohesion: 0.08
Nodes (10): test_admin_ledger_is_super_admin_only_and_has_no_personal_fields(), test_domain_errors_map_to_documented_statuses(), test_status_is_authenticated_by_header_token_not_jwt(), client_for(), test_avatar_multipart_contract(), test_avatar_rejects_invalid_images_before_upload(), test_owner_gallery_serializes_database_uuid_ids(), test_owner_qr_does_not_require_storage() (+2 more)

### Community 67 - "Module Group 67"
Cohesion: 0.08
Nodes (9): FakeRepo, _migration(), _migration_named(), _sql(), test_0027_shape(), test_field_validation_rejects_bad_input(), test_migration_chain_and_security_shape(), test_only_owner_can_read_or_write() (+1 more)

### Community 68 - "Module Group 68"
Cohesion: 0.11
Nodes (13): deactivate_device(), list_notifications(), mark_all_notifications_read(), mark_notification_read(), register_device(), _use_cases(), DeviceRegisterRequest, DeviceRegisterResponse (+5 more)

### Community 69 - "Module Group 69"
Cohesion: 0.14
Nodes (24): ValidationError, test_failure_to_derive_the_link_never_turns_a_stored_upload_into_an_error(), broken(), gateway(), test_gateway_rejects_bad_metadata_keys_and_buckets(), test_gateway_rejects_expiry_tampering_and_wrong_mime_before_r2(), test_raw_storage_helper_is_not_exposed_and_family_type_is_required(), stored_head() (+16 more)

### Community 70 - "Module Group 70"
Cohesion: 0.14
Nodes (16): SalonNotAcceptingBookingsError, SlotUnavailableError, business_error(), infrastructure_error(), _PgError, test_repository_maps_db_error_to_distinct_error_before_generic_slot_match(), test_repository_still_maps_slot_errors_as_before(), _session() (+8 more)

### Community 71 - "Module Group 71"
Cohesion: 0.11
Nodes (4): FCMGateway, test_provider_data_ignores_non_object_notification_data(), test_provider_data_merges_notification_data_as_strings(), test_provider_data_still_works_for_notifications_without_data()

### Community 72 - "Module Group 72"
Cohesion: 0.13
Nodes (7): RedisCache, test_auth_limit_fails_closed_on_backend_error(), test_auth_limit_fails_closed_without_redis_but_booking_fallback_stays_available(), test_strict_erasure_invalidation_propagates_failure(), test_redis_cache_delete_prefix_with_mock_client(), test_redis_cache_noop_when_client_is_none(), test_redis_cache_operations_with_mock_client()

### Community 73 - "Module Group 73"
Cohesion: 0.12
Nodes (13): export_backup(), gpg_path(), locate_tool(), main(), validate_destination(), validate_source(), command(), compare() (+5 more)

### Community 75 - "Module Group 75"
Cohesion: 0.11
Nodes (17): add_salon(), catalog(), found(), _listed(), test_a_paused_salon_offers_no_payment_method(), test_city_filter_is_exact_but_ignores_case_and_spaces(), test_filters_combine_with_and(), test_inactive_category_service_search_keeps_literal_wildcards() (+9 more)

### Community 76 - "Module Group 76"
Cohesion: 0.10
Nodes (4): AuthUserContacts, CreatedAuthUser, SupabaseAuthAdminGateway, FakeAuthAdmin

### Community 77 - "Module Group 77"
Cohesion: 0.18
Nodes (17): _repository(), _Result, test_cancellation_owner_decision_releases_slot_only_when_approved(), test_closure_rejects_changed_impact_set(), test_cross_salon_decision_is_hidden(), test_direct_payment_rejects_cancelled_booking(), test_duplicate_pending_request_is_rejected(), test_immediate_cancel_rejects_late_request() (+9 more)

### Community 78 - "Module Group 78"
Cohesion: 0.13
Nodes (9): UnauthorizedError, SupabaseJWTVerifier, test_deactivated_account_jwt_returns_401_on_deletion_endpoints(), _raise_unauthorized(), test_concurrent_unknown_keys_share_one_cold_refresh(), refresh(), test_failed_fetch_attempts_are_also_bounded(), test_rotation_refresh_is_allowed_after_bounded_cooldown() (+1 more)

### Community 79 - "Module Group 79"
Cohesion: 0.09
Nodes (12): Booking, BookingLine, BookingSource, BookingStatus, PaymentStatus, allowed_status_transitions(), can_approve(), can_cancel() (+4 more)

### Community 80 - "Module Group 80"
Cohesion: 0.13
Nodes (18): SubscriptionStatus, is_subscription_promotion_active(), test_active_trialing_eligible_during_period(), test_active_trialing_ineligible_outside_period(), test_active_trialing_ineligible_with_null_dates(), test_cancelled_eligible_until_period_end(), test_cancelled_ineligible_after_period_end(), test_cancelled_ineligible_with_null_period_end() (+10 more)

### Community 82 - "Module Group 82"
Cohesion: 0.12
Nodes (9): forgot_password(), me(), refresh(), get_my_profile(), ForgotPasswordRequest, ForgotPasswordResponse, ProfileResponse, RefreshRequest (+1 more)

### Community 83 - "Module Group 83"
Cohesion: 0.11
Nodes (4): SettlementAccount, SettlementAccountRequest, NullPaymentGateway, test_null_gateway_implements_every_abstract_method_and_refuses_all()

### Community 84 - "Module Group 84"
Cohesion: 0.19
Nodes (19): closure_refund_provider_key(), build(), FakeGateway, test_a_cache_failure_is_surfaced_not_swallowed(), test_a_provider_declining_the_refund_is_recorded_and_does_not_block(), test_a_provider_outage_retries_with_the_same_key_and_never_erases_early(), test_a_refund_that_cannot_be_issued_is_recorded_failed_after_the_cap(), test_after_the_retry_cap_unsettled_refunds_are_logged_and_erasure_proceeds() (+11 more)

### Community 85 - "Module Group 85"
Cohesion: 0.13
Nodes (3): SalonSubscriptionRepo, SubscriptionEventRepo, SubscriptionPlanRepo

### Community 86 - "Module Group 86"
Cohesion: 0.14
Nodes (12): validated_cache_reads(), main(), test_booking_and_availability_never_read_or_write_payload_cache(), test_disconnected_reader_recovers_before_serving_payload(), test_erasure_worker_probes_retained_client_before_destructive_work(), test_explicit_invalidation_failure_is_logged_and_retried(), test_late_cache_fill_cannot_enter_new_epoch(), test_overlapping_request_contexts_do_not_share_cache_fill_versions() (+4 more)

### Community 88 - "Module Group 88"
Cohesion: 0.13
Nodes (3): AccountErasureService, ErasureVerificationError, RefundsPendingError

### Community 89 - "Module Group 89"
Cohesion: 0.09
Nodes (13): Mumbai staging readiness review — 2026-10-16, Payment, subscription and booking domain specification, Provider-independent payments: mock implementation — 2026-10-18, Mumbai staging readiness audit — 2026-10-15, Mumbai forward revisions — prepared only — 2026-10-15, Mumbai reconciliation — least privilege — 2026-10-15, Alembic history reconciliation plan — no execution, Rollback / recovery plan — Mumbai (+5 more)

### Community 90 - "Module Group 90"
Cohesion: 0.11
Nodes (8): metric(), percentile(), run(), measure(), one(), run(), measure(), summary()

### Community 91 - "Module Group 91"
Cohesion: 0.12
Nodes (14): changes(), changes_db(), safety(), safety_db(), _alembic(), _build(), db_url(), _drop() (+6 more)

### Community 92 - "Module Group 92"
Cohesion: 0.12
Nodes (7): database_health(), health(), readiness(), redis_health(), DatabaseHealthResponse, HealthResponse, RedisHealthResponse

### Community 93 - "Module Group 93"
Cohesion: 0.12
Nodes (12): rollback_checks(), business_checks(), create(), request(), main(), actor_override(), selected_probe(), metadata() (+4 more)

### Community 94 - "Module Group 94"
Cohesion: 0.22
Nodes (19): command(), finance(), finance_db(), outcome(), setup(), terminal(), test_admin_finance_requires_mfa_and_other_owner_cannot_read_statement(), test_checked_in_collection_capability_is_owner_scoped() (+11 more)

### Community 95 - "Module Group 95"
Cohesion: 0.16
Nodes (3): AuthTokens, RefreshInput, Refresh

### Community 96 - "Module Group 96"
Cohesion: 0.13
Nodes (10): BookingCheckoutUseCases, checkout_quote(), test_invalid_money_is_rejected(), test_online_charge_uses_decimal_half_up(), test_pay_at_salon_is_fee_free_with_exact_instructions(), test_adding_provider_credentials_cannot_activate_u08_online_money(), test_new_booking_policy_selection_does_not_reprice_legacy_payment(), test_policy_selection_is_explicit_and_rejects_unknown_versions() (+2 more)

### Community 98 - "Module Group 98"
Cohesion: 0.12
Nodes (11): save(), ask(), Gate, test_concurrent_http_booking_and_idempotent_retry_during_redis_outage(), authenticated_session(), session(), test_independent_customers_compete_for_same_slot_without_serialized_fixture(), book() (+3 more)

### Community 99 - "Module Group 99"
Cohesion: 0.20
Nodes (16): make_super_admin(), catalog_client(), _migration(), test_admin_route_notifier_enqueues_without_booking_and_forwards_data(), test_admin_routes_hand_a_background_task_runner_to_the_use_case(), test_approve_notifies_owner_with_status_payload(), test_background_push_failure_is_swallowed(), test_enqueue_persists_data_json_and_allows_no_booking() (+8 more)

### Community 100 - "Module Group 100"
Cohesion: 0.21
Nodes (3): ProcessedImageFamily, ImageFamilies, member_path()

### Community 101 - "Module Group 101"
Cohesion: 0.16
Nodes (6): NotificationUseCases, test_deactivate_device_delegates_with_actor_id(), test_list_notifications_delegates(), test_mark_all_read_returns_updated_count(), test_mark_read_delegates(), test_register_device_passes_actor_id()

### Community 103 - "Module Group 103"
Cohesion: 0.16
Nodes (11): get_avatar_upload_url(), update_my_profile(), ProfileUpdateRequest, test_profile_name_cannot_be_cleared(), test_profile_name_is_trimmed_and_omitted_fields_stay_omitted(), test_profile_update_accepts_plus_91_storage_format(), test_profile_update_allows_repeated_digits_inside_valid_mobile(), test_profile_update_normalizes_indian_mobile() (+3 more)

### Community 104 - "Module Group 104"
Cohesion: 0.17
Nodes (9): client(), _month(), _Repo, test_only_super_admin_can_list_or_read_statements(), test_routes_are_super_admin_only(), test_statement_derives_net_figures_and_totals_per_currency(), test_statement_of_a_salon_that_was_not_closed_by_deletion_is_not_found(), test_statement_with_no_transactions_is_empty_not_an_error() (+1 more)

### Community 105 - "Module Group 105"
Cohesion: 0.15
Nodes (16): captured_body(), make_processor(), sign(), test_amount_mismatch_fails_event_loudly_without_retry(), test_bad_signature_is_rejected_and_writes_nothing(), test_exception_schedules_backoff_retry(), test_overcollection_fails_event_without_retry(), test_oversized_body_is_rejected() (+8 more)

### Community 106 - "Module Group 106"
Cohesion: 0.12
Nodes (3): owner_access(), ProfileRepository, SQLProfileRepository

### Community 107 - "Module Group 107"
Cohesion: 0.24
Nodes (6): _assert_admin(), SalonSubscriptionUseCases, SubscriptionPlanUseCases, test_cannot_create_subscription_with_terminal_status(), test_non_admin_cannot_manage_plans(), test_non_admin_cannot_manage_subscriptions()

### Community 108 - "Module Group 108"
Cohesion: 0.18
Nodes (5): WalkInUseCases, test_booking_context_rejects_cross_salon_and_keeps_qr_source(), test_booking_context_rejects_owner_before_database_lookup(), test_get_salon_by_qr_delegates(), test_get_salon_by_qr_not_found()

### Community 109 - "Module Group 109"
Cohesion: 0.14
Nodes (5): BookingIdempotencyKeyReusedError, ConflictError, PayAtSalonBlockedError, PaymentCollectionRequiredError, _is_business_error()

### Community 110 - "Module Group 110"
Cohesion: 0.19
Nodes (6): digest(), image_ids(), archive_fixture(), test_accepts_equivalent_ids_from_verified_archive(), test_legacy_archive_keeps_config_id(), test_rejects_unrelated_or_corrupt_metadata()

### Community 111 - "Module Group 111"
Cohesion: 0.25
Nodes (16): add_salon(), ids(), _subscribe(), test_admin_request_validates_priority(), test_admin_response_exposes_priority_and_audit_actor(), test_discovery_visibility_and_search_only(), test_hidden_salons_never_appear_even_with_top_priority(), test_higher_priority_first_then_distance_then_name_then_id() (+8 more)

### Community 112 - "Module Group 112"
Cohesion: 0.25
Nodes (16): new_service(), reviewed(), setup_client(), test_booking_change_requires_key_and_rejects_key_reuse(), test_change_availability_excludes_only_own_booking_and_preserves_public_slots(), test_changed_catalog_quote_requires_reacceptance_and_time_only_keeps_booked_price(), test_cheaper_service_keeps_history_and_prepaid_money_but_reduces_unpaid_price(), test_concurrent_closure_is_rechecked_after_shared_salon_lock() (+8 more)

### Community 113 - "Module Group 113"
Cohesion: 0.17
Nodes (12): _customer(), attendance_guard(), local_app(), session(), test_booking_check_in_collection_completion_journey(), test_checked_in_booking_cannot_be_marked_absent_by_either_path(), test_no_show_grace_reason_notification_and_replay(), test_sql_exact_no_show_boundary_and_same_state_erasure() (+4 more)

### Community 114 - "Module Group 114"
Cohesion: 0.14
Nodes (5): get_auth_gateway(), channel_field(), SupabaseAuthGateway, test_password_reset_delegates_to_supabase_never_mints_tokens(), test_phone_otp_uses_supabase_verify_and_preserves_rejection()

### Community 115 - "Module Group 115"
Cohesion: 0.13
Nodes (7): ImageProcessor, AvatarRepository, UploadAvatar, test_failed_avatar_publication_defers_cleanup_until_committed_reference_check(), test_avatar_provider_failure_does_not_update_profile(), test_avatar_upload_persists_only_actor_profile(), test_avatar_replacement_and_failed_replacement_never_eagerly_delete_shared_media()

### Community 116 - "Module Group 116"
Cohesion: 0.24
Nodes (11): validate_salon_photo_write(), visible_salon_photos(), photo(), test_cover_replacement_keeps_slide_capacity(), test_legacy_duplicate_allows_metadata_updates_and_unique_replacement(), test_legacy_excess_does_not_allow_a_role_change_that_adds_capacity(), test_legacy_third_slide_does_not_block_replacing_a_visible_slide(), test_legacy_three_slides_cannot_add_a_fourth_photo_as_cover() (+3 more)

### Community 117 - "Module Group 117"
Cohesion: 0.19
Nodes (9): ServiceUnavailableError, init_sentry(), scrub_sentry(), ResendEmailGateway, test_only_resend_key_without_verified_sender_makes_no_network_call(), test_resend_provider_key_is_server_only_and_retries_keep_same_idempotency_key(), test_resend_send_has_an_overall_deadline_and_cancels_slow_transport(), test_sentry_removes_credentials_pii_sql_parameters_and_breadcrumbs() (+1 more)

### Community 118 - "Module Group 118"
Cohesion: 0.12
Nodes (12): { chromium }, fs, path, allowed, checks, {chromium}, data, errors (+4 more)

### Community 119 - "Module Group 119"
Cohesion: 0.14
Nodes (4): FakeExpoClient, FakeExpoResponse, FakeMappings, FakeResult

### Community 121 - "Module Group 121"
Cohesion: 0.12
Nodes (5): client(), FakeRepo, settings(), test_reconcile_applies_provider_truth_and_expires_unpaid_intents(), fetch_payment()

### Community 122 - "Module Group 122"
Cohesion: 0.13
Nodes (6): _init_cache(), lifespan(), _warm_database(), test_lifespan_warms_database_and_cache_concurrently(), step(), test_one_failed_warm_up_does_not_stop_the_other()

### Community 125 - "Module Group 125"
Cohesion: 0.33
Nodes (14): _body(), _count(), _direct_book(), _qr_book(), _second_customer(), test_direct_booking_persists_source_app(), test_direct_route_cannot_claim_qr_walkin(), test_online_payment_is_refused_without_any_side_effect() (+6 more)

### Community 126 - "Module Group 126"
Cohesion: 0.39
Nodes (13): make_request(), make_service(), test_already_missing_auth_user_is_not_banned_and_delete_is_idempotent(), test_auth_delete_failure_is_retryable_and_resumes_without_repeating_steps(), test_customer_erasure_skips_salon_cache_keys(), test_lock_is_released_even_when_storage_fails(), test_missing_storage_configuration_fails_instead_of_skipping_media(), test_nothing_due_returns_false() (+5 more)

### Community 127 - "Module Group 127"
Cohesion: 0.18
Nodes (10): repo_with(), _Result, test_idempotency_first_use_reserves(), test_idempotency_mismatched_fingerprint_is_409(), test_idempotency_replays_completed_response(), test_idempotency_unfinished_original_is_in_progress(), test_observation_amount_mismatch_fails_row_and_never_captures(), test_observation_out_of_order_event_is_ignored() (+2 more)

### Community 130 - "Module Group 130"
Cohesion: 0.18
Nodes (7): load(), run(), test_0029_downgrade_restores_legacy_functions_and_drops_additions(), test_0029_shape_chain_and_idempotent_statements(), test_a_case_expression_never_sits_inside_a_plpgsql_if_condition(), test_commission_snapshot_arithmetic(), test_register_422_never_echoes_submitted_values_or_logs_them()

### Community 132 - "Module Group 132"
Cohesion: 0.21
Nodes (7): close_redis_cache(), _redacted_target(), test_startup_outage_retains_client_and_retries_epoch_after_reconnect(), test_redacted_target_never_contains_the_password(), test_redis_cache_create_handles_connection_failure(), test_redis_cache_create_returns_noop_on_none_or_empty_url(), test_redis_cache_global_lifecycle()

### Community 133 - "Module Group 133"
Cohesion: 0.18
Nodes (4): FakeR2Client, storage_error(), test_media_does_not_use_redis(), test_transient_head_failure_is_reported_not_silently_classed_as_legacy()

### Community 135 - "Module Group 135"
Cohesion: 0.15
Nodes (5): test_category_requires_service_assigned_to_active_staff(), test_category_uses_service_presentation_not_salon_business_label(), public_api(), SQLiteSession, test_admin_list_selects_required_review_and_owner_fields()

### Community 136 - "Module Group 136"
Cohesion: 0.25
Nodes (10): release(), run_release(), test_containerd_manifest_id_is_accepted_from_verified_allowlist(), test_failed_readiness_does_not_promote_release(), test_migration_failure_preserves_previous_release_record(), test_missing_runtime_env_stops_before_migrations(), test_pre_deploy_failure_never_replaces_services(), test_release_rejects_implicit_head_before_any_docker_operation() (+2 more)

### Community 137 - "Module Group 137"
Cohesion: 0.21
Nodes (6): test_cached_walkin_requires_current_database_qr_validation(), test_detail_visibility_on_miss_and_stale_cache(), test_hidden_public_catalog_miss_stops_before_catalog_read(), test_list_sources_only_return_approved_active_complete(), test_public_catalog_miss_avoids_unused_photo_query(), test_revocation_blocks_existing_and_late_cache_fills()

### Community 140 - "Module Group 140"
Cohesion: 0.15
Nodes (3): offline_tools(), test_revision_review_preserves_sealed_evidence(), test_runner_imports_without_network_or_credentials()

### Community 141 - "Module Group 141"
Cohesion: 0.23
Nodes (5): PaymentCallback, build(), test_existing_customer_authorization_is_enforced_with_fake_provider(), test_http_intake_rejects_tampering_and_cashfree_path_without_storing_effects(), test_sdk_callback_never_marks_a_mock_payment_paid()

### Community 142 - "Module Group 142"
Cohesion: 0.21
Nodes (3): _statement_figures(), can_read_own_profile(), is_super_admin()

### Community 143 - "Module Group 143"
Cohesion: 0.17
Nodes (6): _cors_headers(), register_exception_handlers(), safe_validation_error_handler(), _sanitise(), unhandled_error_handler(), test_oversized_gateway_body_never_creates_object()

### Community 145 - "Module Group 145"
Cohesion: 0.23
Nodes (7): app_factory(), get_user(), phone_verify(), session(), sign_in(), user(), fixture_manifest()

### Community 146 - "Module Group 146"
Cohesion: 0.26
Nodes (4): FakeSession, test_expo_push_includes_notification_payload(), test_raw_fcm_receives_notification_payload_when_configured(), test_raw_fcm_without_credentials_records_failed_delivery()

### Community 151 - "Module Group 151"
Cohesion: 0.33
Nodes (3): test_commission_snapshot_is_immutable_and_reversal_is_bounded(), test_earnings_use_the_snapshot_and_reversals(), test_excess_refund_via_refund_rows_leaves_booking_paid()

### Community 154 - "Module Group 154"
Cohesion: 0.36
Nodes (3): MeasuredAsyncSession, test_failed_commit_does_not_invalidate_read_models(), test_successful_commit_invalidates_after_database_commit()

### Community 156 - "Module Group 156"
Cohesion: 0.25
Nodes (5): _Clock, _grant(), test_expiry_crossed_during_processing_stores_nothing_and_reports_the_failure(), test_expiry_crossed_during_storage_still_returns_204_and_extends_nothing(), test_put_with_query_string_commits_and_returns_204_with_the_result_link()

### Community 162 - "Module Group 162"
Cohesion: 0.29
Nodes (7): Cloud Run Deployment Assessment 2026-10-22, Mumbai Cloud Run Staging Deployment 2026-10-16, Mumbai Staging Startup Investigation 2026-10-16, Startup Profile Baseline and Import Review 2026-10-20, Local Docker Cold Start Measurement 2026-10-16, Infrastructure Ownership and Cost Audit 2026-10-16, Local Mumbai Database Health Recovery 2026-10-16

### Community 163 - "Module Group 163"
Cohesion: 0.29
Nodes (7): Authorized Local Cleanup 2026-10-15, Mumbai Execution Preflight and Hold 2026-10-15, Final Mumbai Local Staging Acceptance 2026-10-15, Mumbai Local Refresh Implementation and Verification 2026-10-15, Redis Recovery Verification 2026-10-16, Mumbai Customer and Owner Refresh Audit 2026-10-15, Mumbai Refresh Designs 2026-10-15

### Community 164 - "Module Group 164"
Cohesion: 0.38
Nodes (3): downgrade(), _sql(), upgrade()

### Community 165 - "Module Group 165"
Cohesion: 0.43
Nodes (4): downgrade(), _sql(), upgrade(), _validate()

### Community 166 - "Module Group 166"
Cohesion: 0.38
Nodes (3): downgrade(), _sql(), upgrade()

### Community 168 - "Module Group 168"
Cohesion: 0.43
Nodes (3): _list_sql(), test_customer_role_still_sees_only_own_bookings(), test_salon_roles_are_not_matched_on_their_personal_customer_bookings()

### Community 169 - "Module Group 169"
Cohesion: 0.47
Nodes (3): AvatarResponse, ImageFamilyResponse, ImageVariantResponse

### Community 172 - "Module Group 172"
Cohesion: 0.40
Nodes (6): For Customers / For Salons Dual Audience Section, Footer – Making every appointment a little simpler, Our Founders Section – Ziyarad Huq CEO, Shifan NV CPO, Shoiball CMO, Hero Section – Becoming your best aesthetic, Salon BRQ Marketing Landing Page, QR Code Scan-to-Book Customer Flow

### Community 173 - "Module Group 173"
Cohesion: 0.47
Nodes (3): downgrade(), _replace_functions(), upgrade()

### Community 174 - "Module Group 174"
Cohesion: 0.47
Nodes (3): downgrade(), _sql(), upgrade()

### Community 175 - "Module Group 175"
Cohesion: 0.47
Nodes (3): downgrade(), _sql(), upgrade()

### Community 176 - "Module Group 176"
Cohesion: 0.53
Nodes (6): load(), run(), test_0026_chain_tables_and_security_shape(), test_0026_does_not_widen_the_enums(), test_0026_downgrade_restores_narrow_check_and_drops_everything(), test_0027_chain_and_hardening_shape()

### Community 178 - "Module Group 178"
Cohesion: 0.50
Nodes (3): ReportRequest, ReportResponse, submit_report()

### Community 189 - "Module Group 189"
Cohesion: 0.60
Nodes (3): downgrade(), _replace_database_functions(), upgrade()

### Community 193 - "Module Group 193"
Cohesion: 0.40
Nodes (3): {chromium}, readline, target

### Community 200 - "Module Group 200"
Cohesion: 0.67
Nodes (4): Frontend API Usage Matrix 2026-10-22, Frontend Update Lists 2026-10-22, Full API Architecture Audit 2026-10-21, Image Variants Review and Staging Gate 2026-10-19

### Community 201 - "Module Group 201"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_functions(), upgrade()

### Community 204 - "Module Group 204"
Cohesion: 0.50
Nodes (3): COMPOSE_ENV_FILE, COMPOSE_PROJECT_NAME, gcp-vm-release-compose.sh script

## Knowledge Gaps
- **42 isolated node(s):** `COMPOSE_ENV_FILE`, `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME`, `Backend README`, `API Service (Docker Compose)` (+37 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2079 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **126 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PlatformRepository` connect `Module Group 26` to `Auth & API Wiring`, `Module Group 129`, `Salon Approval & Workspace`, `Owner Profile & Staff`, `Owner Use Cases`, `Booking & Webhook Routes`, `Payout Provider Logic`, `Module Group 135`, `Admin Catalog Routes`, `Booking Payment Use Cases`, `Booking Lifecycle Routes`, `Admin Salon Use Cases`, `Privacy & Erasure`, `Module Group 21`, `Module Group 22`, `Module Group 23`, `Module Group 152`, `Module Group 25`, `Module Group 153`, `Module Group 27`, `Module Group 28`, `Module Group 35`, `Module Group 37`, `Module Group 39`, `Module Group 168`, `Module Group 43`, `Module Group 44`, `Module Group 49`, `Module Group 178`, `Module Group 52`, `Module Group 54`, `Module Group 57`, `Module Group 59`, `Module Group 65`, `Module Group 67`, `Module Group 68`, `Module Group 69`, `Module Group 70`, `Module Group 77`, `Module Group 207`, `Module Group 87`, `Module Group 93`, `Module Group 97`, `Module Group 98`, `Module Group 99`, `Module Group 101`, `Module Group 103`, `Module Group 105`, `Module Group 108`, `Module Group 109`, `Module Group 117`, `Module Group 124`, `Module Group 125`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 173 inferred relationships involving `Profile` (e.g. with `get_authenticated_session()` and `get_current_actor()`) actually correct?**
  _`Profile` has 173 INFERRED edges - model-reasoned connections that need verification._
- **What connects `COMPOSE_ENV_FILE`, `COMPOSE_ENV_FILE`, `COMPOSE_PROJECT_NAME` to the rest of the system?**
  _42 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Auth & API Wiring` be split into smaller, more focused modules?**
  _Cohesion score 0.03457854406130268 - nodes in this community are weakly interconnected._
- **Why does `Profile` connect `Owner Use Cases` to `Auth & API Wiring`, `Salon Approval & Workspace`, `Owner Profile & Staff`, `Subscription Providers`, `Role & Permission Guards`, `Admin Catalog Routes`, `Module Group 142`, `Booking Lifecycle Routes`, `Booking Payment Use Cases`, `Admin Salon Use Cases`, `Subscription Billing Tests`, `Module Group 21`, `Module Group 25`, `Module Group 27`, `Module Group 28`, `Module Group 161`, `Module Group 33`, `Module Group 35`, `Module Group 39`, `Module Group 40`, `Module Group 44`, `Module Group 48`, `Module Group 178`, `Module Group 52`, `Module Group 55`, `Module Group 59`, `Module Group 60`, `Module Group 61`, `Module Group 63`, `Module Group 68`, `Module Group 79`, `Module Group 80`, `Module Group 82`, `Module Group 85`, `Module Group 95`, `Module Group 99`, `Module Group 101`, `Module Group 103`, `Module Group 231`, `Module Group 106`, `Module Group 107`, `Module Group 108`, `Module Group 111`, `Module Group 113`, `Module Group 115`, `Module Group 125`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Are the 54 inferred relationships involving `PlatformRepository` (e.g. with `list_public_categories()` and `list_public_subcategories()`) actually correct?**
  _`PlatformRepository` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Should `Payment Gateway Ports` be split into smaller, more focused modules?**
  _Cohesion score 0.04611650485436893 - nodes in this community are weakly interconnected._