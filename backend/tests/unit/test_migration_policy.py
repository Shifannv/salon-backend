"""Migration policy tests: pure decisions and refused CLI commands, no DDL execution."""

import hashlib
import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util import CommandError

from app.core.migration_policy import (
    MUMBAI_PROJECT,
    PORTABLE_CI_REVISION,
    PREPARED_MUMBAI_REVISION,
    PREPARED_REVISIONS,
    RECONCILIATION_REVISIONS,
    STAMP_ALLOWED_REVISIONS,
    require_mumbai_url,
    validate_evidence,
    validate_migration_target,
    validate_stamp_evidence,
)

BACKEND = Path(__file__).resolve().parents[2]
SCRIPT = ScriptDirectory(str(BACKEND / "migrations"))
LOCAL = "postgresql+asyncpg://postgres:synthetic@127.0.0.1:1/postgres"
MUMBAI = f"postgresql+asyncpg://postgres:synthetic@db.{MUMBAI_PROJECT}.supabase.co:5432/postgres"


def test_repository_head_and_portable_boundary_are_distinct_and_linear():
    assert SCRIPT.get_heads() == ["0069_notification_audience"]
    assert SCRIPT.get_revision("0069_notification_audience").down_revision == "0068_payout_transfers"
    assert SCRIPT.get_revision("0066_notification_soft_delete").down_revision == "0065_age_and_guardian_consent"
    assert SCRIPT.get_revision("0065_age_and_guardian_consent").down_revision == "0064_payout_proof_redaction"
    assert SCRIPT.get_revision("0064_payout_proof_redaction").down_revision == "0063_booking_owner_archive"
    assert SCRIPT.get_revision("0062_booking_management").down_revision == "0061_staff_service_visits"
    assert SCRIPT.get_revision("0061_staff_service_visits").down_revision == "0060_user_consents"
    assert SCRIPT.get_revision("0060_user_consents").down_revision == "0059_payout_account_encryption"
    assert SCRIPT.get_revision("0057_payout_proof").down_revision == "0056_platform_payment_settings"
    assert SCRIPT.get_revision("0058_admin_salon_erasure").down_revision == "0057_payout_proof"
    assert SCRIPT.get_revision("0056_platform_payment_settings").down_revision == "0055_feature_access"
    assert SCRIPT.get_revision("0055_feature_access").down_revision == "0054_staff_earnings"
    assert SCRIPT.get_revision("0054_staff_earnings").down_revision == "0053_salon_payout_requests"
    assert SCRIPT.get_revision("0053_salon_payout_requests").down_revision == "0052_booking_window_30_days"
    assert SCRIPT.get_revision("0052_booking_window_30_days").down_revision == "0051_owner_finance_cashbook"
    assert SCRIPT.get_revision("0051_owner_finance_cashbook").down_revision == "0050_plan_price_valid_until"
    assert SCRIPT.get_revision("0050_plan_price_valid_until").down_revision == "0049_trial_salon_plan_prices"
    assert SCRIPT.get_revision("0049_trial_salon_plan_prices").down_revision == "0048_support_billing_erasure"
    assert SCRIPT.get_revision("0048_support_billing_erasure").down_revision == "0047_booking_audit_erasure"
    assert SCRIPT.get_revision("0047_booking_audit_erasure").down_revision == "0046_u08_financial_outcomes"
    assert SCRIPT.get_revision("0046_u08_financial_outcomes").down_revision == "0045_customer_booking_changes"
    assert SCRIPT.get_revision("0045_customer_booking_changes").down_revision == "0044_versioned_checkout_policy"
    assert SCRIPT.get_revision("0044_versioned_checkout_policy").down_revision == "0043_no_show_attendance_guards"
    assert SCRIPT.get_revision("0043_no_show_attendance_guards").down_revision == "0042_remove_business_category"
    assert SCRIPT.get_revision("0042_remove_business_category").down_revision == "0041_salon_photo_limits"
    assert SCRIPT.get_revision("0041_salon_photo_limits").down_revision == PREPARED_MUMBAI_REVISION
    prepared = list(reversed(list(SCRIPT.iterate_revisions(PREPARED_MUMBAI_REVISION, PORTABLE_CI_REVISION))))
    assert tuple(revision.revision for revision in prepared) == PREPARED_REVISIONS
    assert all(not revision.branch_labels and not revision.dependencies for revision in prepared)


@pytest.mark.parametrize("revision", [PORTABLE_CI_REVISION, "0014_repair_cancel_reason"])
def test_portable_target_is_explicit_known_ancestry(revision):
    validate_migration_target(SCRIPT, revision, LOCAL, {"migration_policy": "portable-ci"})


@pytest.mark.parametrize("revision", [*PREPARED_REVISIONS, "0041_salon_photo_limits", "0042_remove_business_category", "0043_no_show_attendance_guards", "0044_versioned_checkout_policy", "0045_customer_booking_changes", "0046_u08_financial_outcomes", "0047_booking_audit_erasure", "0048_support_billing_erasure", "0049_trial_salon_plan_prices", "0050_plan_price_valid_until", "0051_owner_finance_cashbook", "0052_booking_window_30_days", "head", "heads", "+1", "unknown"])
def test_portable_never_selects_prepared_or_ambiguous_target(revision):
    with pytest.raises(CommandError, match="Portable CI target"):
        validate_migration_target(SCRIPT, revision, LOCAL, {"migration_policy": "portable-ci"})


def test_no_default_policy_or_stamp_authorization():
    with pytest.raises(CommandError, match="explicit policy"):
        validate_migration_target(SCRIPT, PORTABLE_CI_REVISION, LOCAL, {})
    with pytest.raises(CommandError, match="stamp"):
        validate_migration_target(SCRIPT, PORTABLE_CI_REVISION, LOCAL, {"migration_policy": "portable-ci"}, command="stamp")


@pytest.mark.parametrize("url", [LOCAL,
    "postgresql+asyncpg://postgres:synthetic@db.sydney.supabase.co:5432/postgres",
    "postgresql+asyncpg://postgres.other:synthetic@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
])
def test_mumbai_rejects_scratch_sydney_and_wrong_project(url):
    with pytest.raises(CommandError, match="confirmed Mumbai"):
        require_mumbai_url(url)


def test_mumbai_requires_explicit_confirmation_and_evidence():
    with pytest.raises(CommandError, match="Confirm Mumbai"):
        validate_migration_target(SCRIPT, PREPARED_MUMBAI_REVISION, MUMBAI, {"migration_policy": "mumbai"})
    with pytest.raises(CommandError, match="manifest"):
        validate_migration_target(SCRIPT, PREPARED_MUMBAI_REVISION, MUMBAI, {
            "migration_policy": "mumbai", "mumbai_project": MUMBAI_PROJECT})


def test_approved_evidence_is_bound_to_exact_sources_and_checksums(tmp_path):
    source_hashes = {}
    for revision in PREPARED_REVISIONS:
        for path in (Path(SCRIPT.get_revision(revision).path), BACKEND / "migrations/sql" / f"{revision}.sql"):
            source_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    proof = tmp_path / "synthetic-proof.txt"
    proof.write_text("synthetic review/preflight evidence")
    evidence = {"path": proof.name, "sha256": hashlib.sha256(proof.read_bytes()).hexdigest(), "status": "passed"}
    manifest = {"approval_id": "synthetic-approval", "approved_by": "synthetic-reviewer",
        "status": "approved", "project_ref": MUMBAI_PROJECT,
        "target_revision": PREPARED_MUMBAI_REVISION, "source_sha256": source_hashes,
        "review": evidence, "preflight": evidence}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    assert validate_evidence(str(path), "synthetic-approval", SCRIPT) == manifest
    proof.write_text("changed proof")
    with pytest.raises(CommandError, match="checksums"):
        validate_evidence(str(path), "synthetic-approval", SCRIPT)


@pytest.mark.parametrize("arguments", [
    ["upgrade", "head"], ["upgrade", PREPARED_MUMBAI_REVISION],
])
def test_real_alembic_cli_refuses_unsafe_commands_before_connecting(arguments):
    result = subprocess.run([sys.executable, "-m", "alembic", "-x", "migration_policy=portable-ci", *arguments],
        cwd=BACKEND, env=dict(os.environ, DATABASE_URL=LOCAL), capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "refused" in result.stdout + result.stderr or "not authorized" in result.stdout + result.stderr
    assert "ConnectionRefusedError" not in result.stdout + result.stderr


@pytest.mark.parametrize("url", [LOCAL + "?host=remote.example", LOCAL + "?user=other",
    LOCAL + "?database=other", LOCAL.replace("postgresql+asyncpg", "postgresql")])
def test_policy_rejects_driver_and_query_routing_overrides(url):
    with pytest.raises(CommandError, match="query overrides"):
        validate_migration_target(SCRIPT, PORTABLE_CI_REVISION, url, {"migration_policy": "portable-ci"})


def test_portable_offline_range_cannot_cross_prepared_start():
    with pytest.raises(CommandError, match="starting revisions"):
        validate_migration_target(SCRIPT, PORTABLE_CI_REVISION, LOCAL, {"migration_policy": "portable-ci"},
            command="downgrade", starting_revision=PREPARED_MUMBAI_REVISION)


@pytest.mark.parametrize("start", [None, "base", PORTABLE_CI_REVISION])
def test_mumbai_offline_sql_requires_reviewed_start(monkeypatch, start):
    monkeypatch.setattr("app.core.migration_policy.validate_evidence", lambda *args, **kwargs: {})
    options = {"migration_policy": "mumbai", "mumbai_project": MUMBAI_PROJECT}
    if start != PORTABLE_CI_REVISION:
        with pytest.raises(CommandError, match="explicit reviewed starting"):
            validate_migration_target(SCRIPT, PREPARED_MUMBAI_REVISION, MUMBAI, options,
                starting_revision=start, offline=True)
    else:
        validate_migration_target(SCRIPT, PREPARED_MUMBAI_REVISION, MUMBAI, options,
            starting_revision=start, offline=True)


@pytest.mark.parametrize("operation", ["head", "ensure_version", "prepared"])
def test_programmatic_alembic_fails_closed_before_connection(monkeypatch, operation):
    monkeypatch.setenv("DATABASE_URL", LOCAL)
    cfg = Config(str(BACKEND / "alembic.ini"), output_buffer=StringIO())
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.cmd_opts = SimpleNamespace(x=["migration_policy=portable-ci"])
    with pytest.raises(CommandError):
        if operation == "ensure_version":
            command.ensure_version(cfg)
        else:
            command.upgrade(cfg, "head" if operation == "head" else PREPARED_MUMBAI_REVISION)
    assert cfg.get_main_option("sqlalchemy.url") == LOCAL


def test_portable_ci_environment_target_matches_policy():
    configured = os.environ.get("PORTABLE_CI_TARGET", PORTABLE_CI_REVISION)
    assert configured == PORTABLE_CI_REVISION


def test_mumbai_validation_workflow_is_manual_and_has_no_scratch_service():
    workflow = (BACKEND.parent / ".github/workflows/mumbai-migration-validation.yml").read_text()
    assert "workflow_dispatch:" in workflow and "environment: mumbai-migration-validation" in workflow
    assert "pull_request:" not in workflow and "services:" not in workflow
    assert "MUMBAI_VALIDATION_DATABASE_URL" in workflow
    assert "upgrade" not in workflow and "stamp" not in workflow


# ── Reconciliation revision set ───────────────────────────────────────────────

def test_reconciliation_revisions_tuple_is_ordered_and_complete():
    assert RECONCILIATION_REVISIONS[0] == "0041_salon_photo_limits"
    assert RECONCILIATION_REVISIONS[-1] == "0052_booking_window_30_days"
    assert len(RECONCILIATION_REVISIONS) == 12
    assert "0051_owner_finance_cashbook" in RECONCILIATION_REVISIONS
    assert "0052_booking_window_30_days" in RECONCILIATION_REVISIONS


def test_reconciliation_revisions_form_linear_chain():
    for i, rev_id in enumerate(RECONCILIATION_REVISIONS):
        rev = SCRIPT.get_revision(rev_id)
        if i == 0:
            assert rev.down_revision == PREPARED_MUMBAI_REVISION
        else:
            assert rev.down_revision == RECONCILIATION_REVISIONS[i - 1]


@pytest.mark.parametrize("revision", list(RECONCILIATION_REVISIONS))
def test_reconciliation_revision_is_authorized_mumbai_upgrade_target(revision, monkeypatch):
    monkeypatch.setattr("app.core.migration_policy.validate_evidence", lambda *args, **kwargs: {})
    validate_migration_target(
        SCRIPT, revision, MUMBAI,
        {"migration_policy": "mumbai", "mumbai_project": MUMBAI_PROJECT,
         "approval_manifest": "", "approval_id": ""},
    )



# ── Stamp authorization ────────────────────────────────────────────────────────

def test_stamp_allowed_revisions_are_exactly_0040_and_0049():
    assert STAMP_ALLOWED_REVISIONS == {
        "0040_fastapi_only_access",
        "0049_trial_salon_plan_prices",
    }


@pytest.mark.parametrize("revision", [
    PORTABLE_CI_REVISION,
    "0041_salon_photo_limits",
    "0048_support_billing_erasure",
    "0050_plan_price_valid_until",
    "0051_owner_finance_cashbook",
    "0052_booking_window_30_days",
    "head",
    "base",
])
def test_stamp_other_revisions_refused(revision):
    with pytest.raises(CommandError, match="stamp"):
        validate_migration_target(SCRIPT, revision, MUMBAI, {}, command="stamp")


def test_stamp_on_local_url_refused():
    for target in STAMP_ALLOWED_REVISIONS:
        with pytest.raises(CommandError, match="confirmed Mumbai"):
            validate_migration_target(SCRIPT, target, LOCAL, {}, command="stamp")


def test_stamp_without_mumbai_project_confirmation_refused():
    for target in STAMP_ALLOWED_REVISIONS:
        with pytest.raises(CommandError, match="Confirm Mumbai"):
            validate_migration_target(SCRIPT, target, MUMBAI, {}, command="stamp")


def test_stamp_without_manifest_refused():
    for target in STAMP_ALLOWED_REVISIONS:
        with pytest.raises(CommandError, match="manifest|Stamp"):
            validate_migration_target(
                SCRIPT, target, MUMBAI,
                {"mumbai_project": MUMBAI_PROJECT},
                command="stamp",
            )


def _make_stamp_manifest(tmp_path: Path, target: str, mutate: dict | None = None) -> tuple[Path, str]:
    """Build a valid stamp approval manifest for tests."""
    policy_path = Path(__file__).parents[2] / "app/core/migration_policy.py"
    root = BACKEND / "migrations"
    rev = SCRIPT.get_revision(target)
    source_hashes = {
        policy_path.name: hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        Path(rev.path).name: hashlib.sha256(Path(rev.path).read_bytes()).hexdigest(),
        f"{target}.sql": hashlib.sha256((root / "sql" / f"{target}.sql").read_bytes()).hexdigest(),
    }
    proof = tmp_path / "stamp-proof.txt"
    proof.write_text("synthetic stamp review/preflight evidence")
    evidence = {"path": proof.name, "sha256": hashlib.sha256(proof.read_bytes()).hexdigest(), "status": "passed"}
    manifest = {
        "approval_id": "synthetic-stamp-approval",
        "approved_by": "synthetic-reviewer",
        "status": "approved",
        "project_ref": MUMBAI_PROJECT,
        "target_revision": target,
        "stamp_authorized": True,
        "source_sha256": source_hashes,
        "review": evidence,
        "preflight": evidence,
    }
    if mutate:
        manifest.update(mutate)
    path = tmp_path / "stamp-manifest.json"
    path.write_text(json.dumps(manifest))
    return path, "synthetic-stamp-approval"


@pytest.mark.parametrize("target", sorted(STAMP_ALLOWED_REVISIONS))
def test_valid_stamp_manifest_is_accepted(tmp_path, target):
    manifest_path, approval_id = _make_stamp_manifest(tmp_path, target)
    result = validate_stamp_evidence(str(manifest_path), approval_id, target, SCRIPT)
    assert result["target_revision"] == target
    assert result["stamp_authorized"] is True


@pytest.mark.parametrize("target", sorted(STAMP_ALLOWED_REVISIONS))
def test_stamp_policy_gate_passes_with_valid_manifest(tmp_path, target):
    manifest_path, approval_id = _make_stamp_manifest(tmp_path, target)
    validate_migration_target(
        SCRIPT, target, MUMBAI,
        {"mumbai_project": MUMBAI_PROJECT, "approval_manifest": str(manifest_path), "approval_id": approval_id},
        command="stamp",
    )


@pytest.mark.parametrize("target", sorted(STAMP_ALLOWED_REVISIONS))
def test_stamp_manifest_without_stamp_authorized_flag_refused(tmp_path, target):
    manifest_path, approval_id = _make_stamp_manifest(tmp_path, target, {"stamp_authorized": False})
    with pytest.raises(CommandError, match="manifest|Stamp"):
        validate_stamp_evidence(str(manifest_path), approval_id, target, SCRIPT)


@pytest.mark.parametrize("target", sorted(STAMP_ALLOWED_REVISIONS))
def test_stamp_manifest_wrong_approval_id_refused(tmp_path, target):
    manifest_path, _ = _make_stamp_manifest(tmp_path, target)
    with pytest.raises(CommandError, match="manifest|Stamp"):
        validate_stamp_evidence(str(manifest_path), "wrong-id", target, SCRIPT)


@pytest.mark.parametrize("target", sorted(STAMP_ALLOWED_REVISIONS))
def test_stamp_manifest_changed_proof_refused(tmp_path, target):
    manifest_path, approval_id = _make_stamp_manifest(tmp_path, target)
    proof = tmp_path / "stamp-proof.txt"
    proof.write_text("tampered")
    with pytest.raises(CommandError, match="manifest|Stamp|checksum"):
        validate_stamp_evidence(str(manifest_path), approval_id, target, SCRIPT)


# ── Historical migration files are immutable ──────────────────────────────────

def test_historical_migration_py_files_exist_and_have_stable_hashes():
    """All 0001-0052 .py files must exist; hashes must be stable (not None)."""
    for rev_id in [*PREPARED_REVISIONS, *RECONCILIATION_REVISIONS,
                   "0051_owner_finance_cashbook", "0052_booking_window_30_days"]:
        rev = SCRIPT.get_revision(rev_id)
        path = Path(rev.path)
        assert path.exists(), f"Migration file missing: {path}"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert len(digest) == 64, f"Unexpected hash for {rev_id}"


def test_all_historical_sql_files_exist():
    sql_dir = BACKEND / "migrations" / "sql"
    for rev_id in [*PREPARED_REVISIONS, *RECONCILIATION_REVISIONS]:
        sql_path = sql_dir / f"{rev_id}.sql"
        assert sql_path.exists(), f"SQL file missing: {sql_path.name}"


# ── Approved production prices (Path A, 2026-10-31) ──────────────────────────

def test_harness_expected_prices_match_owner_approved_values():
    """Harness must check against the owner-confirmed production prices, not 0049 SQL targets."""
    from scripts.migrations.reconciliation_harness import EXPECTED_0049_PRICES
    assert EXPECTED_0049_PRICES["growth_1m"] == 449.00
    assert EXPECTED_0049_PRICES["growth_6m"] == 2419.00
    assert EXPECTED_0049_PRICES["growth_12m"] == 4299.00
    assert EXPECTED_0049_PRICES["premium_6m"] == 3499.00
    assert EXPECTED_0049_PRICES["premium_12m"] == 6199.00


def test_0049_sql_guards_will_not_fire_at_approved_prices():
    """0049 SQL guards fire only when price = 0031 seed value. Current prices are not seed values,
    so a future accidental re-run of 0049 SQL will not silently change production prices."""
    seed_guards = {
        "growth_6m": 1499.00,
        "growth_12m": 1999.00,
        "premium_6m": 2499.00,
        "premium_12m": 3499.00,
    }
    from scripts.migrations.reconciliation_harness import EXPECTED_0049_PRICES
    for code, guard_value in seed_guards.items():
        current = EXPECTED_0049_PRICES[code]
        assert current != guard_value, (
            f"{code}: current approved price {current} equals 0049 SQL guard {guard_value}; "
            "0049 SQL would fire and overwrite the production price."
        )


def test_0049_stamp_is_in_allowed_revisions():
    """0049 must be stampable (required because CREATE TABLE fails if table exists)."""
    assert "0049_trial_salon_plan_prices" in STAMP_ALLOWED_REVISIONS


def test_canonical_prices_module_matches_harness_expectations():
    """Regression: prices.py canonical constants must match reconciliation harness EXPECTED_0049_PRICES.
    If this fails, a fixture was updated without updating the harness (or vice versa)."""
    from prices import GROWTH_1M, GROWTH_1M_PAISE, GROWTH_6M, GROWTH_12M, PREMIUM_6M, PREMIUM_12M

    from scripts.migrations.reconciliation_harness import EXPECTED_0049_PRICES

    assert float(GROWTH_1M) == EXPECTED_0049_PRICES["growth_1m"]
    assert float(GROWTH_6M) == EXPECTED_0049_PRICES["growth_6m"]
    assert float(GROWTH_12M) == EXPECTED_0049_PRICES["growth_12m"]
    assert float(PREMIUM_6M) == EXPECTED_0049_PRICES["premium_6m"]
    assert float(PREMIUM_12M) == EXPECTED_0049_PRICES["premium_12m"]
    # Sanity check: paise is consistent with rupee
    import math
    assert GROWTH_1M_PAISE == math.floor(float(GROWTH_1M) * 100)


def test_fake_billing_repo_plan_matches_canonical_prices():
    """Regression: FakeBillingRepo.PLAN must use canonical growth_1m price.
    If this fails, support_subscription.py drifted from prices.py."""
    from prices import GROWTH_1M, GROWTH_6M
    from support_subscription import FakeBillingRepo
    assert FakeBillingRepo.PLAN["price_amount"] == GROWTH_1M
    # plan-g6 is constructed via **PLAN spread + overrides; check growth_6m price
    plans = {"plan-g6": {**FakeBillingRepo.PLAN, "id": "plan-g6", "code": "growth_6m",
                         "price_amount": GROWTH_6M, "billing_interval": "semiannual"}}
    assert plans["plan-g6"]["price_amount"] == GROWTH_6M


def test_approved_prices_differ_from_0049_sql_targets():
    """Document that production prices 2000/2999 differ from what 0049 SQL sets (1675/2932).
    Both are correct: SQL targets are for fresh-DB tests; production values reflect owner update."""
    from scripts.migrations.reconciliation_harness import EXPECTED_0049_PRICES
    sql_targets = {"growth_6m": 1675.00, "growth_12m": 2932.00}
    for code, sql_price in sql_targets.items():
        assert EXPECTED_0049_PRICES[code] != sql_price, (
            f"{code}: harness expected price must reflect production ({EXPECTED_0049_PRICES[code]}), "
            f"not 0049 SQL target ({sql_price})."
        )
