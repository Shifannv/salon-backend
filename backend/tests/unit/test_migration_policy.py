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
    require_mumbai_url,
    validate_evidence,
    validate_migration_target,
)

BACKEND = Path(__file__).resolve().parents[2]
SCRIPT = ScriptDirectory(str(BACKEND / "migrations"))
LOCAL = "postgresql+asyncpg://postgres:synthetic@127.0.0.1:1/postgres"
MUMBAI = f"postgresql+asyncpg://postgres:synthetic@db.{MUMBAI_PROJECT}.supabase.co:5432/postgres"


def test_repository_head_and_portable_boundary_are_distinct_and_linear():
    assert SCRIPT.get_heads() == ["0041_salon_photo_limits"]
    assert SCRIPT.get_revision("0041_salon_photo_limits").down_revision == PREPARED_MUMBAI_REVISION
    prepared = list(reversed(list(SCRIPT.iterate_revisions(PREPARED_MUMBAI_REVISION, PORTABLE_CI_REVISION))))
    assert tuple(revision.revision for revision in prepared) == PREPARED_REVISIONS
    assert all(not revision.branch_labels and not revision.dependencies for revision in prepared)


@pytest.mark.parametrize("revision", [PORTABLE_CI_REVISION, "0014_repair_cancel_reason"])
def test_portable_target_is_explicit_known_ancestry(revision):
    validate_migration_target(SCRIPT, revision, LOCAL, {"migration_policy": "portable-ci"})


@pytest.mark.parametrize("revision", [*PREPARED_REVISIONS, "0041_salon_photo_limits", "head", "heads", "+1", "unknown"])
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
    monkeypatch.setattr("app.core.migration_policy.validate_evidence", lambda *args: {})
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
