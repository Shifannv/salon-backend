"""Deployment guard regressions; these tests never access GitHub, Docker or GCP."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "cloud_run_candidate", Path(__file__).resolve().parents[2] / "scripts/cloud_run_candidate.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


@pytest.fixture
def guarded(monkeypatch):
    sha = "a" * 40
    variables = {"GITHUB_REPOSITORY": release.REPOSITORY, "GITHUB_REF": "refs/heads/main",
                 "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_SHA": sha, "BASELINE_COMMIT": "b" * 40,
                 "GITHUB_ACTOR_ID": "172572480", "APPROVE_DEPLOYMENT": "true", "REQUESTED_COMMIT": sha,
                 "DEPLOY_CONFIRMATION": "DEPLOY api.salones.in",
                 "BOOTSTRAP_BASELINE": "false", "BOOTSTRAP_CONFIRMATION": "",
                 "GCP_PROJECT_ID": "saloon-505509", "GCP_REGION": "asia-south1",
                 "GCP_CLOUD_RUN_SERVICE": "salon-api-production", "GCP_ARTIFACT_REGISTRY_REPOSITORY": "salon-production"}
    for key, value in variables.items():
        monkeypatch.setenv(key, value)
    responses = {"branches/main": {"protected": False, "commit": {"sha": sha}},
                 "environments/production": {"protection_rules": [{"type": "required_reviewers", "reviewers": [{"id": 1}]}],
                                             "deployment_branch_policy": {"custom_branch_policies": True}},
                 "environments/production/deployment-branch-policies": {"branch_policies": [{"name": "main", "type": "branch"}]}}
    monkeypatch.setattr(release, "github", lambda path: responses[path])
    monkeypatch.setattr(release, "command", lambda *args: sha if args[1:3] == ("rev-parse", "HEAD")
                        else "commit" if args[1:3] == ("cat-file", "-t") else "")
    return responses


def test_reviewed_main_with_no_migration_changes_passes(guarded):
    assert release.preflight() == "a" * 40


@pytest.mark.parametrize("key,value", [("GITHUB_REF", "refs/heads/feature"), ("GITHUB_EVENT_NAME", "push"),
                                      ("GITHUB_REPOSITORY", "Thameempp/salon-backend"), ("GCP_PROJECT_ID", "other"),
                                      ("GITHUB_ACTOR_ID", "other"), ("APPROVE_DEPLOYMENT", "false"),
                                      ("DEPLOY_CONFIRMATION", "deploy api.salones.in"), ("REQUESTED_COMMIT", "c" * 40)])
def test_wrong_context_refused(guarded, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError):
        release.preflight()


def test_superseded_main_refused(guarded):
    guarded["branches/main"]["commit"]["sha"] = "c" * 40
    with pytest.raises(RuntimeError, match="main advanced"):
        release.preflight()


def test_free_plan_without_reviewers_uses_explicit_actor_and_dispatch_guards(guarded):
    guarded["environments/production"]["protection_rules"] = []
    assert release.preflight() == "a" * 40


def test_wildcard_deployment_branch_refused(guarded):
    guarded["environments/production/deployment-branch-policies"]["branch_policies"][0]["name"] = "*"
    with pytest.raises(RuntimeError, match="main only"):
        release.preflight()


def test_any_migration_change_refused(guarded, monkeypatch):
    original = release.command
    monkeypatch.setattr(release, "command", lambda *args: "backend/migrations/sql/new.sql"
                        if args[1] == "diff" else original(*args))
    with pytest.raises(RuntimeError, match="Migration differences"):
        release.preflight()


@pytest.fixture
def schema_receipt(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    raw = (root / release.SCHEMA_RECEIPT_PATH).read_bytes()
    data = json.loads(raw)
    content = {path: (root / path).read_bytes().replace(b"\r\n", b"\n")
               for path in [*data["files"], *data["evidence"]]}
    monkeypatch.setattr(release, "command", lambda *args: "")
    monkeypatch.setattr(release, "git_blob", lambda commit, path: raw if path == release.SCHEMA_RECEIPT_PATH else content[path])
    return data, content


def test_applied_exact_schema_delta_requires_supervised_promotion(schema_receipt):
    data, _ = schema_receipt
    receipt = release.approved_schema_release(data["baseline_commit"], "a" * 40, list(data["files"]))
    assert receipt["requires_supervised_promotion"] is True
    assert receipt["migration_target"] == "0055_feature_access"


@pytest.mark.parametrize("change", ["other_baseline", "extra_migration", "changed_sql", "changed_revision", "changed_evidence"])
def test_schema_receipt_does_not_authorize_other_source_changes(schema_receipt, change):
    data, content = schema_receipt
    baseline = data["baseline_commit"]
    paths = list(data["files"])
    if change == "other_baseline":
        baseline = "f" * 40
    elif change == "extra_migration":
        paths.append("backend/migrations/sql/0056_unapproved.sql")
    else:
        path = (next(iter(data["evidence"])) if change == "changed_evidence" else
                next(path for path in paths if path.endswith(".py" if change == "changed_revision" else ".sql")))
        content[path] += b"\n-- changed\n"
    with pytest.raises(RuntimeError, match="Migration differences"):
        release.approved_schema_release(baseline, "a" * 40, paths)


@pytest.fixture
def schema_repair_receipt(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    source = "f26e8fd01c676702b9457330cf176e7a787ea40c"
    evidence_path = "backend/docs/verification/PRODUCTION_0067_0071_SCHEMA_REPAIR_2026-11-14.md"
    names = [
        "0067_working_hours_breaks", "0068_payout_transfers",
        "0069_notification_audience", "0070_booking_no_show_warnings",
        "0071_restore_working_hours_break_functions",
    ]
    paths = {f"backend/migrations/{folder}/{name}.{extension}"
             for name in names for folder, extension in [("sql", "sql"), ("versions", "py")]}
    files = {path: (root / path).read_bytes().replace(b"\r\n", b"\n") for path in paths}
    evidence = b"Production SQL verification evidence."
    data = {
        "schema_version": 1,
        "status": "PRODUCTION_SQL_VERIFIED",
        "repository": release.REPOSITORY,
        "gcp_project": "saloon-505509",
        "region": "asia-south1",
        "service": "salon-api-production",
        "database_project": "wqjlgpnbiapcrlkxumcp",
        "baseline_commit": "52197d54be9313ef6e1bdb5fdc6ca0792a5dd5a8",
        "sql_source_commit": source,
        "previous_revision": "salon-api-production-credential-v4-20261113",
        "previous_image": "asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:8ee466a3808d8077d332a8188d13f3e080ae69970334793938199b26d17d6418",
        "migration_target": "0071_restore_working_hours_break_functions",
        "release_mode": "owner-approved-auto-promotion",
        "files": {path: hashlib.sha256(content).hexdigest() for path, content in files.items()},
        "evidence": {evidence_path: hashlib.sha256(evidence).hexdigest()},
    }
    raw = json.dumps(data).encode()
    blobs = {**files, evidence_path: evidence}
    monkeypatch.setattr(release, "command", lambda *args: "")
    monkeypatch.setattr(release, "git_blob",
                        lambda commit, path: raw if path == release.SCHEMA_REPAIR_RECEIPT_PATH else blobs[path])
    return data


def test_exact_verified_repair_is_admitted_for_auto_promotion(schema_repair_receipt):
    data = schema_repair_receipt
    receipt = release.approved_schema_repair_release(
        data["baseline_commit"], "a" * 40, list(data["files"])
    )
    assert receipt["migration_target"] == "0071_restore_working_hours_break_functions"
    assert receipt["requires_supervised_promotion"] is False


@pytest.mark.parametrize("change", ["other_baseline", "extra_migration", "changed_sql", "changed_evidence"])
def test_schema_repair_receipt_refuses_unreviewed_differences(schema_repair_receipt, change, monkeypatch):
    data = schema_repair_receipt
    baseline = data["baseline_commit"]
    paths = list(data["files"])
    if change == "other_baseline":
        baseline = "f" * 40
    elif change == "extra_migration":
        paths.append("backend/migrations/sql/0072_unapproved.sql")
    else:
        path = next(iter(data["evidence"])) if change == "changed_evidence" else next(
            path for path in paths if path.endswith(".sql")
        )
        original = release.git_blob
        monkeypatch.setattr(release, "git_blob",
                            lambda commit, name: original(commit, name) + b"changed" if name == path
                            else original(commit, name))
    with pytest.raises(RuntimeError, match="Production schema receipt"):
        release.approved_schema_repair_release(baseline, "a" * 40, paths)


def service():
    return {"metadata": {"annotations": {"run.googleapis.com/maxScale": "1"}},
            "status": {"traffic": [{"revisionName": "previous", "percent": 100}]},
            "spec": {"template": {"metadata": {"name": "previous", "annotations": {}}, "spec": {
                "containers": [{"image": "old", "env": [{"name": "SETTING", "value": "synthetic"}]}],
                "serviceAccountName": "runtime"}}}}


def test_image_only_update_preserves_runtime():
    before = service()
    after = copy.deepcopy(before)
    after["spec"]["template"]["metadata"]["name"] = "candidate"
    after["spec"]["template"]["spec"]["containers"][0]["image"] = "new"
    after["status"]["traffic"].append({"revisionName": "candidate", "tag": "review"})
    release.verify_unchanged(before, after)


@pytest.mark.parametrize("change", ["traffic", "env", "service_account", "scaling"])
def test_unexpected_runtime_or_traffic_change_refused(change):
    before = service()
    after = copy.deepcopy(before)
    if change == "traffic":
        after["status"]["traffic"][0]["revisionName"] = "candidate"
    elif change == "env":
        after["spec"]["template"]["spec"]["containers"][0]["env"] = []
    elif change == "service_account":
        after["spec"]["template"]["spec"]["serviceAccountName"] = "other"
    else:
        after["metadata"]["annotations"]["run.googleapis.com/maxScale"] = "10"
    with pytest.raises(RuntimeError):
        release.verify_unchanged(before, after)


def contract():
    return {"openapi": "3.1.0", "paths": {path: {"get": {}} for path in
            ["/health", "/health/db", "/health/redis", "/v1/salons", "/v1/subscription-plans"]},
            "components": {"schemas": {"Plan": {"type": "object", "properties": {"price": {"type": "string"}}}}}}


def test_contract_additions_preserve_existing_routes_and_fields():
    before = contract()
    after = copy.deepcopy(before)
    after["paths"]["/v1/new"] = {"get": {}}
    release.verify_contract(before, after)


@pytest.mark.parametrize("change", ["route", "operation", "field", "type"])
def test_contract_regressions_refused(change):
    before = contract()
    after = copy.deepcopy(before)
    if change == "route":
        del after["paths"]["/v1/salons"]
    elif change == "operation":
        del after["paths"]["/v1/salons"]["get"]
    elif change == "field":
        del after["components"]["schemas"]["Plan"]["properties"]["price"]
    else:
        after["components"]["schemas"]["Plan"]["properties"]["price"]["type"] = "number"
    with pytest.raises(RuntimeError):
        release.verify_contract(before, after)


def attestation():
    return {"schema_version": 1, "source_kind": "hybrid-overlay", "revision": release.BOOTSTRAP_REVISION,
            "project": "saloon-505509", "region": "asia-south1", "service": "salon-api-production",
            "index_image": release.BOOTSTRAP_INDEX, "platform_image": release.BOOTSTRAP_PLATFORM,
            "overlay_reference_commit": "d" * 40,
            "files": {"requirements.txt": "a" * 64, "alembic.ini": "b" * 64,
                      "app/main.py": "c" * 64, "migrations/env.py": hashlib.sha256(b"original").hexdigest()}}


@pytest.fixture
def bootstrapped(guarded, monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_BASELINE", "true")
    monkeypatch.setenv("BASELINE_COMMIT", "")
    monkeypatch.setenv("BOOTSTRAP_CONFIRMATION", "BOOTSTRAP " + release.BOOTSTRAP_REVISION)
    monkeypatch.setattr(release, "bootstrap_manifest", attestation)
    monkeypatch.setattr(release, "bootstrap_migration_changes", lambda *args: [])


def test_bootstrap_does_not_require_a_fabricated_git_commit(bootstrapped):
    assert release.preflight() == "a" * 40


@pytest.mark.parametrize("key,value", [("BOOTSTRAP_CONFIRMATION", "BOOTSTRAP"),
                                      ("BASELINE_COMMIT", "b" * 40), ("GITHUB_ACTOR_ID", "other"),
                                      ("BOOTSTRAP_BASELINE", "yes")])
def test_bootstrap_wrong_context_refused(bootstrapped, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError):
        release.preflight()


def test_bootstrap_preserves_migration_gate(bootstrapped, monkeypatch):
    monkeypatch.setattr(release, "bootstrap_migration_changes", lambda *args: ["backend/migrations/sql/0051.sql"])
    with pytest.raises(RuntimeError, match="Migration differences"):
        release.preflight()


@pytest.mark.parametrize("change", ["revision", "image", "hash", "extra", "missing"])
def test_bootstrap_rejects_drift(change):
    data = attestation()
    files = dict(data["files"])
    revision, image = release.BOOTSTRAP_REVISION, release.BOOTSTRAP_PLATFORM
    if change == "revision":
        revision += "-other"
    elif change == "image":
        image = release.IMAGE_ROOT + "sha256:" + "d" * 64
    elif change == "hash":
        files["app/main.py"] = "d" * 64
    elif change == "extra":
        files["app/extra.py"] = "d" * 64
    else:
        del files["app/main.py"]
    with pytest.raises(RuntimeError):
        release.verify_bootstrap(data, revision, image, files)


def test_exact_bootstrap_inventory_passes():
    data = attestation()
    release.verify_bootstrap(data, release.BOOTSTRAP_REVISION, release.BOOTSTRAP_PLATFORM, data["files"])


@pytest.mark.parametrize("change", ["target", "path", "hash"])
def test_attestation_target_and_paths_validated(tmp_path, monkeypatch, change):
    data = attestation()
    if change == "target":
        data["service"] = "other"
    elif change == "path":
        data["files"]["app/../../.env"] = "a" * 64
    else:
        data["files"]["app/main.py"] = "not-a-hash"
    path = tmp_path / "attestation.json"
    path.write_text(json.dumps(data))
    monkeypatch.setattr(release, "BOOTSTRAP_MANIFEST", path)
    with pytest.raises(RuntimeError):
        release.bootstrap_manifest()


def test_migration_inventory_detects_new_changed_and_removed_files(monkeypatch):
    data = attestation()
    data["files"]["migrations/versions/old.py"] = "e" * 64
    monkeypatch.setattr(release, "command", lambda *args: "backend/migrations/env.py\nbackend/migrations/sql/0051.sql")
    monkeypatch.setattr(release, "git_blob", lambda *args: b"changed")
    assert release.bootstrap_migration_changes(data, "a" * 40) == [
        "backend/migrations/env.py", "backend/migrations/sql/0051.sql", "backend/migrations/versions/old.py"]


def test_migration_gate_ignores_checkout_line_endings_only(monkeypatch):
    data = attestation()
    data["files"]["migrations/env.py"] = hashlib.sha256(b"line\r\n").hexdigest()
    monkeypatch.setattr(release, "command", lambda *args: "backend/migrations/env.py" if args[1] == "ls-tree" else "")
    monkeypatch.setattr(release, "git_blob", lambda *args: b"line\n")
    assert release.bootstrap_migration_changes(data, "a" * 40) == []


def test_historical_review_changes_remain_a_gate(monkeypatch):
    data = attestation()
    monkeypatch.setattr(release, "command", lambda *args: "backend/migrations/env.py" if args[1] == "ls-tree"
                        else "backend/migrations/reviews/changed.json")
    monkeypatch.setattr(release, "git_blob", lambda *args: b"original")
    assert release.bootstrap_migration_changes(data, "a" * 40) == ["backend/migrations/reviews/changed.json"]


def test_registry_index_resolves_exact_amd64_platform():
    manifest = {"manifests": [{"platform": {"os": "linux", "architecture": "amd64"},
                               "digest": release.BOOTSTRAP_PLATFORM.split("@")[1]},
                              {"platform": {"os": "unknown", "architecture": "unknown"}, "digest": "sha256:" + "f" * 64}]}
    assert release.platform_image(release.BOOTSTRAP_INDEX, manifest) == release.BOOTSTRAP_PLATFORM


@pytest.mark.parametrize("count", [0, 2])
def test_registry_index_rejects_missing_or_ambiguous_platform(count):
    row = {"platform": {"os": "linux", "architecture": "amd64"}, "digest": "sha256:" + "a" * 64}
    with pytest.raises(RuntimeError):
        release.platform_image(release.BOOTSTRAP_INDEX, {"manifests": [row] * count})


def test_single_platform_manifest_keeps_digest():
    assert release.platform_image(release.BOOTSTRAP_PLATFORM, {"config": {}, "layers": []}) == release.BOOTSTRAP_PLATFORM


def test_registry_reference_requires_a_full_digest():
    with pytest.raises(RuntimeError):
        release.platform_image(release.IMAGE_ROOT + "sha256:bad", {"config": {}, "layers": []})
