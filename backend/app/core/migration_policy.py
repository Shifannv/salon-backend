"""Explicit portable CI and reviewed Mumbai migration boundaries."""

import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

from alembic.script import ScriptDirectory
from alembic.util import CommandError
from sqlalchemy.engine import make_url

PORTABLE_CI_REVISION = "0037_customer_processing_charge"
PREPARED_MUMBAI_REVISION = "0040_fastapi_only_access"
MUMBAI_PROJECT = "wqjlgpnbiapcrlkxumcp"
PREPARED_REVISIONS = (
    "0038_cancellation_compatibility", "0039_promotion_search_path", PREPARED_MUMBAI_REVISION,
)
# Reconciliation chain: original immutable revisions authorized for straight-line replay
# after the 0040 baseline stamp.  Gate C (0051, 0052) authorized by owner 2026-10-31.
RECONCILIATION_REVISIONS = (
    "0041_salon_photo_limits",
    "0042_remove_business_category",
    "0043_no_show_attendance_guards",
    "0044_versioned_checkout_policy",
    "0045_customer_booking_changes",
    "0046_u08_financial_outcomes",
    "0047_booking_audit_erasure",
    "0048_support_billing_erasure",
    "0049_trial_salon_plan_prices",
    "0050_plan_price_valid_until",
    "0051_owner_finance_cashbook",
    "0052_booking_window_30_days",
)
# Only these two stamp targets are ever authorized; every other target is refused.
# 0040: baseline stamp from an empty alembic_version after structural proof.
# 0049: equivalence stamp after salon_plan_prices structure/data verification.
STAMP_ALLOWED_REVISIONS: frozenset[str] = frozenset({
    PREPARED_MUMBAI_REVISION,
    "0049_trial_salon_plan_prices",
})


def portable_revisions(script: ScriptDirectory) -> set[str]:
    """Resolve the portable ancestry; never reinterpret Alembic head as portable."""
    return {revision.revision for revision in script.iterate_revisions(PORTABLE_CI_REVISION, "base")}


def require_mumbai_url(database_url: str) -> None:
    url = make_url(database_url)
    require_unambiguous_url(database_url)
    direct = url.host == f"db.{MUMBAI_PROJECT}.supabase.co" and url.username == "postgres"
    pooled = url.host in {
        "aws-0-ap-south-1.pooler.supabase.com", "aws-1-ap-south-1.pooler.supabase.com",
    } and unquote(url.username or "") == f"postgres.{MUMBAI_PROJECT}"
    if not (direct or pooled) or url.database != "postgres" or url.port not in {5432, 6543}:
        raise CommandError("Mumbai policy requires the confirmed Mumbai Supabase database; scratch PostgreSQL, Sydney and other targets are refused")


def require_unambiguous_url(database_url: str) -> None:
    url = make_url(database_url)
    if url.drivername != "postgresql+asyncpg" or url.query:
        raise CommandError("Migration URLs require postgresql+asyncpg and no query overrides; host/user/database routing must be unambiguous")


def validate_evidence(
    manifest_path: str,
    approval_id: str,
    script: ScriptDirectory,
    *,
    target_revision: str | None = None,
) -> dict:
    """Verify explicit approval and exact reviewed sources without editing evidence.

    When target_revision is None (default), validates a baseline manifest targeting
    PREPARED_MUMBAI_REVISION and checks PREPARED_REVISIONS source files only.
    When target_revision names a RECONCILIATION_REVISIONS entry, also verifies
    source files for all RECONCILIATION_REVISIONS up to and including that target.
    """
    effective_target = target_revision or PREPARED_MUMBAI_REVISION
    try:
        path = Path(manifest_path)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (not approval_id or manifest["approval_id"] != approval_id
                or manifest["project_ref"] != MUMBAI_PROJECT
                or manifest["target_revision"] != effective_target
                or manifest["status"] != "approved" or not manifest["approved_by"]):
            raise ValueError("Approval identity/target mismatch")
        root = Path(script.dir).resolve()
        revisions_to_check = list(PREPARED_REVISIONS)
        if effective_target in RECONCILIATION_REVISIONS:
            for r in RECONCILIATION_REVISIONS:
                revisions_to_check.append(r)
                if r == effective_target:
                    break
        for revision in revisions_to_check:
            for source in (Path(script.get_revision(revision).path), root / "sql" / f"{revision}.sql"):
                if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["source_sha256"][source.name]:
                    raise ValueError("Reviewed source hash mismatch")
        for name in ("review", "preflight"):
            evidence = manifest[name]
            source = (path.parent / evidence["path"]).resolve()
            if hashlib.sha256(source.read_bytes()).hexdigest() != evidence["sha256"]:
                raise ValueError("Evidence checksum mismatch")
            if evidence["status"] != "passed":
                raise ValueError("Review/preflight is not passed")
        return manifest
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise CommandError("Mumbai requires an explicit approved manifest with matching source, review and preflight checksums; no evidence defaults are allowed") from error


def validate_stamp_evidence(
    manifest_path: str,
    approval_id: str,
    target_revision: str,
    script: ScriptDirectory,
) -> dict:
    """Verify explicit stamp approval: policy file hash, target migration source hash, and evidence docs.

    The stamp manifest must contain:
    - approval_id, project_ref, target_revision, status=approved, approved_by, stamp_authorized=true
    - source_sha256 with hashes of: migration_policy.py, <target>.py, <target>.sql
    - review and preflight evidence with sha256 and status=passed
    """
    try:
        path = Path(manifest_path)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (not approval_id or manifest["approval_id"] != approval_id
                or manifest["project_ref"] != MUMBAI_PROJECT
                or manifest["target_revision"] != target_revision
                or manifest["status"] != "approved" or not manifest["approved_by"]
                or manifest.get("stamp_authorized") is not True):
            raise ValueError("Stamp approval identity/target mismatch")
        policy_path = Path(__file__)
        if hashlib.sha256(policy_path.read_bytes()).hexdigest() != manifest["source_sha256"][policy_path.name]:
            raise ValueError("Policy file hash mismatch")
        root = Path(script.dir).resolve()
        rev = script.get_revision(target_revision)
        for source in (Path(rev.path), root / "sql" / f"{target_revision}.sql"):
            if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["source_sha256"][source.name]:
                raise ValueError("Reviewed source hash mismatch")
        for name in ("review", "preflight"):
            evidence = manifest[name]
            source = (path.parent / evidence["path"]).resolve()
            if hashlib.sha256(source.read_bytes()).hexdigest() != evidence["sha256"]:
                raise ValueError("Evidence checksum mismatch")
            if evidence["status"] != "passed":
                raise ValueError("Review/preflight is not passed")
        return manifest
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise CommandError(
            "Stamp requires an explicit approved manifest with stamp_authorized=true, "
            "matching policy file, target migration source, and review/preflight evidence checksums; "
            "no defaults are allowed"
        ) from error


def validate_migration_target(
    script: ScriptDirectory, destination: str | tuple | None, database_url: str,
    arguments: dict[str, str], *, command: str = "upgrade",
    starting_revision: str | None = None,
    offline: bool = False,
) -> None:
    """Refuse ambiguous targets and unapproved prepared revisions before connecting."""
    if command in {"stamp", "do_stamp"}:
        # Alembic 1.20 wraps destination in a single-element tuple; unwrap only for stamp.
        if isinstance(destination, (list, tuple)) and len(destination) == 1:
            destination = destination[0]

    if isinstance(destination, (tuple, list)):
        raise CommandError("Alembic stamp is not authorized by migration policy; history reconciliation requires separate review")

    if command in {"stamp", "do_stamp"}:
        if isinstance(destination, str) and destination in STAMP_ALLOWED_REVISIONS:
            require_unambiguous_url(database_url)
            require_mumbai_url(database_url)
            if arguments.get("mumbai_project") != MUMBAI_PROJECT:
                raise CommandError("Confirm Mumbai explicitly with -x mumbai_project=" + MUMBAI_PROJECT)
            validate_stamp_evidence(
                arguments.get("approval_manifest", ""),
                arguments.get("approval_id", ""),
                destination,
                script,
            )
            return
        raise CommandError(
            "Alembic stamp is not authorized by migration policy; "
            "only " + str(sorted(STAMP_ALLOWED_REVISIONS)) + " are approved stamp targets "
            "with a valid manifest; all other targets are refused"
        )

    policy = arguments.get("migration_policy")
    require_unambiguous_url(database_url)
    if command not in {"upgrade", "downgrade"}:
        raise CommandError("Only explicit reviewed upgrade/downgrade operations are supported; ensure_version and other mutations are refused")
    if policy == "portable-ci":
        if make_url(database_url).host not in {"localhost", "127.0.0.1", "::1"}:
            raise CommandError("portable-ci is restricted to disposable loopback PostgreSQL")
        if starting_revision is not None and starting_revision not in portable_revisions(script):
            raise CommandError("Portable CI cannot traverse prepared Mumbai starting revisions")
        if destination is None and command == "downgrade":
            return
        if destination not in portable_revisions(script):
            raise CommandError(f"Portable CI target must be an explicit revision at or before {PORTABLE_CI_REVISION}; head includes prepared Mumbai 0038-0040 and is refused")
        return
    if policy == "mumbai":
        if command != "upgrade":
            raise CommandError("Prepared Mumbai downgrades are not authorized; use a separately reviewed forward repair")
        require_mumbai_url(database_url)
        if arguments.get("mumbai_project") != MUMBAI_PROJECT:
            raise CommandError("Confirm Mumbai explicitly with -x mumbai_project=" + MUMBAI_PROJECT)
        validate_evidence(
            arguments.get("approval_manifest", ""),
            arguments.get("approval_id", ""),
            script,
            target_revision=destination,
        )
        if offline and starting_revision not in {PORTABLE_CI_REVISION, *PREPARED_REVISIONS, *RECONCILIATION_REVISIONS}:
            raise CommandError("Mumbai offline SQL requires an explicit reviewed starting revision; baseline/base rendering is refused")
        if destination not in (*PREPARED_REVISIONS, *RECONCILIATION_REVISIONS):
            raise CommandError("Mumbai execution must name a prepared revision explicitly and start from reviewed history")
        return
    raise CommandError("Migration execution requires an explicit policy: -x migration_policy=portable-ci for disposable tests through 0037, or -x migration_policy=mumbai with confirmed target and approved review/preflight manifest; no default approval exists")
