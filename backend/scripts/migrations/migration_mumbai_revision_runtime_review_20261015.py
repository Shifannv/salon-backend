"""Read-only local per-revision final-state review; never import/run upgrade functions."""

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
# Selected final-state requirements for EVERY revision, plus the complete final
# catalog comparison below. Earlier function/policy definitions may be superseded.
REQUIREMENTS = {
    1: {"tables": ["profiles", "salons", "staff", "services", "bookings", "booking_services", "blocked_slots"]},
    2: {"columns": ["notifications.read_at"], "functions": ["stamp_notification_read_at"]},
    3: {"functions": ["handle_new_user"]},
    4: {"functions": ["get_available_slots"]},
    5: {"columns": ["staff.experience"]},
    6: {"tables": ["bookings", "blocked_slots"]},
    7: {"columns": ["salons.qr_image_url"]},
    8: {"columns": ["salon_images.is_active"], "indexes": ["idx_salon_images_active"]},
    9: {"columns": ["bookings.cancellation_reason"]},
    10: {"tables": ["salon_reports"]},
    11: {"columns": ["salon_holidays.is_active"], "indexes": ["uq_salon_holidays_active_date"]},
    12: {"columns": ["bookings.estimated_end_datetime"]},
    13: {"tables": ["booking_action_requests", "notification_outbox"], "columns": ["bookings.payment_preference"]},
    14: {"columns": ["bookings.cancellation_reason"]},
    15: {"columns": ["salons.approval_status", "salons.approved_at", "salons.approved_by", "salons.rejection_reason"], "functions": ["guard_salon_approval", "guard_booking_salon_approval"]},
    16: {"columns": ["services.category_name", "services.subcategory_name", "services.photo_url"]},
    17: {"columns": ["salons.display_priority"], "functions": ["guard_salon_display_priority"]},
    18: {"tables": ["subscription_plans", "subscription_provider_accounts", "salon_subscriptions", "subscription_events"], "functions": ["guard_subscription_admin", "is_subscription_promotion_active"]},
    19: {"columns": ["salons.discovery_visibility", "salons.home_placement"], "functions": ["guard_salon_discovery_placement"]},
    20: {"functions": ["guard_media_reference"]},
    21: {"tables": ["account_deletion_challenges", "account_deletion_requests"], "functions": ["erase_profile_references"]},
    22: {"columns": ["salons.accepting_bookings"]},
    23: {"columns": ["notifications.data"]},
    24: {"functions": ["handle_new_user", "get_active_tokens", "create_booking", "register_device_token", "deactivate_device_token"]},
    25: {"tables": ["salon_payout_accounts"]},
    26: {"tables": ["booking_payments", "payment_refunds", "payment_webhook_events", "payment_idempotency_keys", "payment_provider_accounts"], "functions": ["recompute_booking_payment_state"]},
    27: {"tables": ["salon_payout_account_history"], "functions": ["salon_payout_account_masked", "tg_salon_payout_account_history"]},
    28: {"functions": ["erase_profile_references"], "indexes": ["idx_account_deletion_requests_open_age"]},
    29: {"tables": ["payment_anomalies", "payment_provider_account_audit"], "columns": ["booking_payments.platform_commission_amount", "booking_payments.overcollected_amount", "payment_refunds.commission_reversal_amount"]},
    30: {"tables": ["subscription_billing_records"], "functions": ["apply_subscription_billing_record", "cancel_salon_subscription_renewal", "sweep_lapsed_subscriptions"]},
    31: {"tables": ["subscription_plans"]},
    32: {"tables": ["salon_access"], "functions": ["start_salon_trial", "recompute_salon_trial", "salon_booking_eligible"]},
    33: {"columns": ["booking_payments.gateway_fee_percent", "booking_payments.gateway_fee_amount", "payment_refunds.kind", "payment_refunds.deduction_amount", "payment_refunds.attempts"]},
    34: {"enums": ["booking_status"]},
    35: {"tables": ["booking_audit_events", "customer_booking_restrictions"], "functions": ["guard_booking_checkout", "stamp_booking_lifecycle", "guard_collection_snapshot"]},
    36: {"tables": ["support_messages", "email_events", "api_rate_limits"], "functions": ["enqueue_booking_email", "enqueue_verified_payment_receipt"]},
    37: {"columns": ["bookings.checkout_policy_version", "booking_payments.service_amount", "booking_payments.online_processing_charge", "booking_payments.provider_session_id"], "functions": ["stamp_checkout_policy", "guard_collection_snapshot"]},
}
NOTES = {
    1: "Consolidated baseline overlap documented; compare final objects, not a replay recipe.",
    3: "Final signup body is superseded/hardened by 0024; user metadata is display-only.",
    6: "Replica FULL checked; current publication membership separately refreshed by scoped MCP.",
    9: "0014 repeats repair idempotently; two extra reason_code/reason_text columns are not this migration's cancellation_reason.",
    18: "Function replaced by 0030; compare final body, not obsolete intermediate body.",
    21: "Erasure function superseded by 0028. No destructive erasure job executed.",
    24: "Destination denies client register/deactivate EXECUTE despite historical authenticated grants. Promotion function search_path retained beyond 0030. Not an exact ACL match.",
    26: "Ledger function/guards subsequently replaced by 0029,0033,0035,0037; final-state comparison applies.",
    29: "Historical data backfill execution cannot be inferred from schema. No production rows imported.",
    30: "Promotion function body matches final head; Mumbai search_path hardening differs. Provider lifecycle not exercised.",
    31: "Six non-personal seed plan codes checked separately; this is not historical execution proof.",
    34: "checked_in and no_show must exist in booking_status.",
    35: "Compare referenced 0035 SQL as well as revision Python; 0037 replaces some financial guards.",
    37: "Compare referenced 0037 SQL plus columns/final guard body. Checkout/collection tested via API.",
}


def normalized(value):
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return [normalized(v) for v in value]
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()}
    return value


def canonical_sha256(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main():
    current = json.loads((ROOT / "backend/migrations/reviews/migration-mumbai-forward-catalog-2026-10-15.json").read_text())
    previous = json.loads((ROOT / "backend/migrations/reviews/migration-mumbai-completion-audit-2026-10-15.json").read_text())["catalog"]
    comparison = json.loads((ROOT / "backend/migrations/reviews/migration-mumbai-head-comparison-2026-10-15.json").read_text())
    # This bridge retains all previous known head mismatches; it never invents a new
    # clean expected catalog or silently normalizes away actual ACL differences.
    fresh_changes = {category: {"missing": sorted(set(old) - set(current[category])),
        "extra": sorted(set(current[category]) - set(old)),
        "changed": sorted(k for k in old.keys() & current[category].keys()
                          if normalized(old[k]) != normalized(current[category][k]))}
        for category, old in previous.items()}
    rows = []
    revision_files = [p for p in sorted((ROOT / "backend/migrations/versions").glob("*.py"))
                      if p.name[:4].isdigit() and int(p.name[:4]) <= 37]
    assert len(revision_files) == 37
    for path in revision_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        number = int(path.name[:4])
        checks = []
        for category, names in REQUIREMENTS[number].items():
            keys = {k.split("(")[0] for k in current[category]} if category == "functions" else set(current[category])
            checks += [{"category": category, "object": name, "present": name in keys} for name in names]
        if number == 6:
            checks += [{"category": "replica_identity", "object": name,
                        "present": current["tables"][name]["replica_identity"] == "f"}
                       for name in ("bookings", "blocked_slots")]
        if number == 34:
            checks += [{"category": "enum_value", "object": value,
                        "present": value in current["enums"]["booking_status"]}
                       for value in ("checked_in", "no_show")]
        external = []
        for sql_path in (ROOT / "backend/migrations/sql").glob("*.sql"):
            if sql_path.name in path.read_text(encoding="utf-8"):
                external.append({"file": sql_path.relative_to(ROOT).as_posix(),
                                 "sha256": canonical_sha256(sql_path)})
        rows.append({"revision": path.stem, "source_sha256": canonical_sha256(path),
            "summary": (ast.get_docstring(tree) or "").splitlines()[0], "checks": checks,
            "status": "selected final-state requirements present" if all(c["present"] for c in checks) else "missing selected requirement",
            "external_SQL_sources": external, "notes": NOTES.get(number, "Final structural effect covered by catalog/head comparison; execution history not inferred.")})
    artifact = {"destination": "wqjlgpnbiapcrlkxumcp", "head": comparison["head"],
        "prepared_repository_head_not_applied": "0040_fastapi_only_access",
        "revision_count": len(rows), "revisions": rows, "fresh_catalog_drift_since_prior_audit": fresh_changes,
        "known_head_differences": comparison["differences"],
        "limitations": "All revisions inventoried with selected final-state assertions and full current catalog bridge. Does not prove intermediate revision execution, arbitrary historical backfills, or reproduce effective clean-head ACLs. No revision imported/executed."}
    (ROOT / "backend/migrations/reviews/migration-mumbai-runtime-revision-review-2026-10-15.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps({"revisions": len(rows), "missing_requirements": [r["revision"] for r in rows if r["status"].startswith("missing")],
                      "fresh_drift": {k: v for k, v in fresh_changes.items() if any(v.values())}}))


if __name__ == "__main__":
    main()
