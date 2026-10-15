# All 37 revisions ? final-state review

No migration function was imported or executed. These are selected per-revision final-state assertions plus a complete fresh catalog bridge to the prior verified head comparison; they do not prove historical execution or every backfill. Known head differences and missing expected-head ACL reproduction remain explicit.

| Revision | Current structural evidence | Notes |
| --- | --- | --- |
| 0001_baseline | profiles, salons, staff, services, bookings, booking_services, blocked_slots ? present | Consolidated baseline overlap documented; compare final objects, not a replay recipe. |
| 0002_notifications_read_at | notifications.read_at, stamp_notification_read_at ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0003_google_oauth_profile_metadata | handle_new_user ? present | Final signup body is superseded/hardened by 0024; user metadata is display-only. |
| 0004_service_duration_slot_steps | get_available_slots ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0005_staff_experience | staff.experience ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0006_enable_realtime | bookings, blocked_slots, bookings, blocked_slots ? present | Replica FULL checked; current publication membership separately refreshed by scoped MCP. |
| 0007_salon_qr_image_url | salons.qr_image_url ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0008_salon_images_soft_delete | salon_images.is_active, idx_salon_images_active ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0009_booking_cancellation_reason | bookings.cancellation_reason ? present | 0014 repeats repair idempotently; two extra reason_code/reason_text columns are not this migration's cancellation_reason. |
| 0010_salon_reports | salon_reports ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0011_holiday_soft_delete | salon_holidays.is_active, uq_salon_holidays_active_date ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0012_booking_delay | bookings.estimated_end_datetime ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0013_booking_action_requests | booking_action_requests, notification_outbox, bookings.payment_preference ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0014_repair_cancel_reason | bookings.cancellation_reason ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0015_salon_admin_approval | salons.approval_status, salons.approved_at, salons.approved_by, salons.rejection_reason, guard_salon_approval, guard_booking_salon_approval ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0016_service_presentation | services.category_name, services.subcategory_name, services.photo_url ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0017_salon_display_priority | salons.display_priority, guard_salon_display_priority ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0018_subscription_foundation | subscription_plans, subscription_provider_accounts, salon_subscriptions, subscription_events, guard_subscription_admin, is_subscription_promotion_active ? present | Function replaced by 0030; compare final body, not obsolete intermediate body. |
| 0019_discovery_placement | salons.discovery_visibility, salons.home_placement, guard_salon_discovery_placement ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0020_media_reference_guards | guard_media_reference ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0021_account_deletion | account_deletion_challenges, account_deletion_requests, erase_profile_references ? present | Erasure function superseded by 0028. No destructive erasure job executed. |
| 0022_salon_accepting_bookings | salons.accepting_bookings ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0023_notification_data | notifications.data ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0024_secure_new_user_role | handle_new_user, get_active_tokens, create_booking, register_device_token, deactivate_device_token ? present | Destination denies client register/deactivate EXECUTE despite historical authenticated grants. Promotion function search_path retained beyond 0030. Not an exact ACL match. |
| 0025_salon_payout_accounts | salon_payout_accounts ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0026_booking_payments | booking_payments, payment_refunds, payment_webhook_events, payment_idempotency_keys, payment_provider_accounts, recompute_booking_payment_state ? present | Ledger function/guards subsequently replaced by 0029,0033,0035,0037; final-state comparison applies. |
| 0027_payout_account_audit | salon_payout_account_history, salon_payout_account_masked, tg_salon_payout_account_history ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0028_account_erasure_hardening | erase_profile_references, idx_account_deletion_requests_open_age ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0029_payment_monetary_policy | payment_anomalies, payment_provider_account_audit, booking_payments.platform_commission_amount, booking_payments.overcollected_amount, payment_refunds.commission_reversal_amount ? present | Historical data backfill execution cannot be inferred from schema. No production rows imported. |
| 0030_subscription_billing | subscription_billing_records, apply_subscription_billing_record, cancel_salon_subscription_renewal, sweep_lapsed_subscriptions ? present | Promotion function body matches final head; Mumbai search_path hardening differs. Provider lifecycle not exercised. |
| 0031_seed_subscription_plans | subscription_plans ? present | Six non-personal seed plan codes checked separately; this is not historical execution proof. |
| 0032_salon_access_state | salon_access, start_salon_trial, recompute_salon_trial, salon_booking_eligible ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0033_payment_fee_snapshot | booking_payments.gateway_fee_percent, booking_payments.gateway_fee_amount, payment_refunds.kind, payment_refunds.deduction_amount, payment_refunds.attempts ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0034_booking_lifecycle_states | booking_status, checked_in, no_show ? present | checked_in and no_show must exist in booking_status. |
| 0035_booking_checkout_safety | booking_audit_events, customer_booking_restrictions, guard_booking_checkout, stamp_booking_lifecycle, guard_collection_snapshot ? present | Compare referenced 0035 SQL as well as revision Python; 0037 replaces some financial guards. |
| 0036_support_email_outbox | support_messages, email_events, api_rate_limits, enqueue_booking_email, enqueue_verified_payment_receipt ? present | Final structural effect covered by catalog/head comparison; execution history not inferred. |
| 0037_customer_processing_charge | bookings.checkout_policy_version, booking_payments.service_amount, booking_payments.online_processing_charge, booking_payments.provider_session_id, stamp_checkout_policy, guard_collection_snapshot ? present | Compare referenced 0037 SQL plus columns/final guard body. Checkout/collection tested via API. |
