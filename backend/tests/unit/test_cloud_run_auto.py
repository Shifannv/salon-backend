"""Automatic release failure/rollback regressions. No network or cloud writes."""
import copy
import importlib.util
import json
import subprocess
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def auto(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    spec = importlib.util.spec_from_file_location("cloud_run_candidate", scripts / "cloud_run_candidate.py")
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    monkeypatch.setitem(sys.modules, "cloud_run_candidate", release)
    spec = importlib.util.spec_from_file_location("cloud_run_auto", scripts / "cloud_run_auto.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def context(auto, monkeypatch):
    sha = "a" * 40
    for key, value in {"GITHUB_REPOSITORY": auto.release.REPOSITORY, "GITHUB_REF": "refs/heads/main",
                       "GITHUB_EVENT_NAME": "push", "GITHUB_SHA": sha, "REQUESTED_COMMIT": sha,
                       "GITHUB_ACTOR_ID": "172572480", "AUTO_DEPLOY_ENABLED": "true",
                       "BOOTSTRAP_BASELINE": "false", "BOOTSTRAP_CONFIRMATION": "", "BASELINE_COMMIT": "b" * 40,
                       "GCP_PROJECT_ID": "saloon-505509", "GCP_REGION": "asia-south1",
                       "GCP_CLOUD_RUN_SERVICE": "salon-api-production", "GCP_ARTIFACT_REGISTRY_REPOSITORY": "salon-production"}.items():
        monkeypatch.setenv(key, value)
    responses = {"branches/main": {"commit": {"sha": sha}},
                 "environments/production": {"deployment_branch_policy": {"custom_branch_policies": True}},
                 "environments/production/deployment-branch-policies": {"branch_policies": [{"name": "main", "type": "branch"}]}}
    monkeypatch.setattr(auto.release, "github", lambda key: responses[key])
    monkeypatch.setattr(auto.release, "command", lambda *args: sha if args[1:3] == ("rev-parse", "HEAD")
                        else "commit" if args[1:3] == ("cat-file", "-t") else "")
    return responses


def test_auto_main_push_passes_without_invented_manual_approval(auto, context, monkeypatch):
    monkeypatch.delenv("APPROVE_DEPLOYMENT", raising=False)
    monkeypatch.delenv("DEPLOY_CONFIRMATION", raising=False)
    assert auto.release.preflight(automatic=True) == "a" * 40
    with pytest.raises(RuntimeError, match="Manual dispatch"):
        auto.release.preflight()


def test_ordinary_owner_merge_passes_real_identity_and_merged_sha_admission(auto, context, monkeypatch):
    """The merge event actor is the approved owner; the PR author may differ."""
    sha = "a" * 40
    monkeypatch.setenv("GITHUB_ACTOR", "Shifannv")
    monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", "Shifannv")
    monkeypatch.setenv("PRODUCTION_AUTO_DEPLOY_ENABLED", "false")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    context[f"commits/{sha}/pulls?per_page=100"] = [{
        "merged_at": "2026-11-01T00:00:00Z", "merge_commit_sha": sha,
        "user": {"login": "different-contributor", "id": 42},
        "merged_by": {"login": "Shifannv", "id": 172572480},
        "base": {"ref": "main", "repo": {"full_name": auto.release.REPOSITORY}},
    }]
    assert auto.guard() is True


@pytest.mark.parametrize("key,value", [("GITHUB_REF", "refs/heads/feature"), ("GITHUB_EVENT_NAME", "pull_request"),
                                      ("GITHUB_EVENT_NAME", "workflow_dispatch"), ("GITHUB_ACTOR_ID", "other"),
                                      ("GITHUB_REPOSITORY", "other/repo"), ("AUTO_DEPLOY_ENABLED", "false"),
                                      ("AUTO_DEPLOY_ENABLED", ""), ("BOOTSTRAP_BASELINE", "true"),
                                      ("REQUESTED_COMMIT", "c" * 40), ("GCP_PROJECT_ID", "other")])
def test_auto_refuses_unapproved_context(auto, context, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError):
        auto.release.preflight(automatic=True)


def test_auto_still_refuses_migration_difference(auto, context, monkeypatch):
    original = auto.release.command
    monkeypatch.setattr(auto.release, "command", lambda *args: "backend/migrations/sql/0051.sql"
                        if args[1] == "diff" else original(*args))
    with pytest.raises(RuntimeError, match="Migration differences"):
        auto.release.preflight(automatic=True)


def test_auto_refuses_superseded_main(auto, context):
    context["branches/main"]["commit"]["sha"] = "c" * 40
    with pytest.raises(RuntimeError, match="main advanced"):
        auto.release.preflight(automatic=True)


def test_generated_receipt_does_not_break_clean_source_promotion(auto, context, monkeypatch, tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    root = Path(__file__).resolve().parents[3]
    (tmp_path / ".git/info/exclude").write_text((root / ".gitignore").read_text())
    (tmp_path / "candidate-result.json").write_text('{"status":"PASS_CANDIDATE_VERIFIED"}')
    original = auto.release.command
    monkeypatch.setattr(auto.release, "command", lambda *args: subprocess.check_output(
        ["git", "-C", str(tmp_path), "status", "--porcelain"], text=True).strip()
        if args[1:3] == ("status", "--porcelain") else original(*args))
    assert auto.release.identity(automatic=True) == "a" * 40
    (tmp_path / "unreviewed.py").write_text("unreviewed = True")
    with pytest.raises(RuntimeError, match="clean"):
        auto.release.identity(automatic=True)


def state(auto, revision="salon-api-production-old"):
    return {"name": auto.RESOURCE, "etag": "etag-1", "template": {"serviceAccount": "existing-runtime"},
            "traffic": [{"type": auto.REVISION, "revision": revision, "percent": 100},
                        {"type": auto.REVISION, "revision": "salon-api-production-tagged", "tag": "retain"}],
            "trafficStatuses": [{"revision": revision, "percent": 100}], "reconciling": False}


def health(auto, passed=True):
    return {host + path: {"status": 200 if passed else 503, "pass": passed} for host, path in auto.PUBLIC_CHECKS}


@pytest.fixture
def rollout(auto, monkeypatch):
    current = state(auto)
    calls = []
    monkeypatch.setattr(auto.release, "identity", lambda **kwargs: "a" * 40)
    monkeypatch.setattr(auto.release, "latest_main", lambda: "a" * 40)
    monkeypatch.setattr(auto, "verified_receipt", lambda receipt: None)
    monkeypatch.setattr(auto, "describe", lambda: {"metadata": {"resourceVersion": "v1"}})
    monkeypatch.setattr(auto, "api", lambda *args: copy.deepcopy(current))

    def patch(service, targets):
        calls.append(copy.deepcopy(targets))
        current["traffic"] = [{key: value for key, value in target.items() if key != "percent" or value}
                              for target in targets]  # Cloud Run omits default zero percentages.
        current["trafficStatuses"] = [{"revision": target["revision"], "percent": target["percent"]}
                                      for target in targets if target.get("percent")]
        current["etag"] = "etag-2"

    monkeypatch.setattr(auto, "patch_traffic", patch)
    monkeypatch.setattr(auto, "public_health", lambda **kwargs: health(auto))
    receipt = {"candidate_revision": "salon-api-production-new", "previous_revision": "salon-api-production-old",
               "verified_resource_version": "v1", "production_traffic_promoted": False, "commit": "a" * 40, "previous_commit": "b" * 40}
    return receipt, current, calls


def test_verified_candidate_promotes_and_keeps_existing_tags(auto, rollout):
    receipt, current, calls = rollout
    auto.promote(receipt)
    assert receipt["status"] == "PASS_PRODUCTION_PROMOTED"
    assert receipt["production_traffic_promoted"] is True
    assert auto.resolved(current) == [("salon-api-production-new", 100)]
    assert calls[0][0]["tag"] == "retain" and len(calls) == 1


@pytest.mark.parametrize("failure", ["health", "timeout_after_acceptance", "unhealthy_rollback"])
def test_health_or_ambiguous_patch_failure_rolls_back_same_revision(auto, rollout, monkeypatch, failure):
    receipt, current, calls = rollout
    checks = iter([health(auto, False), health(auto, failure != "unhealthy_rollback")])
    monkeypatch.setattr(auto, "public_health", lambda **kwargs: next(checks))
    if failure == "timeout_after_acceptance":
        original = auto.patch_traffic

        def patch(service, targets):
            original(service, targets)
            if len(calls) == 1:
                raise TimeoutError("synthetic timeout after patch accepted")

        monkeypatch.setattr(auto, "patch_traffic", patch)
        monkeypatch.setattr(auto, "public_health", lambda **kwargs: health(auto))
    with pytest.raises((RuntimeError, TimeoutError)):
        auto.promote(receipt)
    assert receipt["status"] == ("ROLLBACK_HEALTH_FAILED" if failure == "unhealthy_rollback" else "ROLLED_BACK")
    assert auto.resolved(current) == [("salon-api-production-old", 100)]
    assert len(calls) == 2 and receipt["production_traffic_promoted"] is False


def test_concurrent_external_change_is_not_overwritten(auto, rollout, monkeypatch):
    receipt, current, calls = rollout

    def changed_health(**kwargs):
        current["template"]["serviceAccount"] = "externally-changed"
        return health(auto, False)

    monkeypatch.setattr(auto, "public_health", changed_health)
    with pytest.raises(RuntimeError, match="Concurrent external edit"):
        auto.promote(receipt)
    assert receipt["status"] == "ROLLBACK_FAILED_OPERATOR_ACTION_REQUIRED" and len(calls) == 1


def test_superseded_candidate_does_not_change_traffic(auto, rollout, monkeypatch):
    receipt, _, calls = rollout
    monkeypatch.setattr(auto.release, "latest_main", lambda: (_ for _ in ()).throw(RuntimeError("main advanced")))
    with pytest.raises(RuntimeError, match="main advanced"):
        auto.promote(receipt)
    assert calls == []


def test_rejected_traffic_patch_keeps_previous_without_a_second_write(auto, rollout, monkeypatch):
    receipt, current, calls = rollout
    monkeypatch.setattr(auto, "patch_traffic", lambda *args: (_ for _ in ()).throw(RuntimeError("etag conflict")))
    with pytest.raises(RuntimeError, match="etag conflict"):
        auto.promote(receipt)
    assert receipt["status"] == "STOP_PREVIOUS_REVISION_RETAINED"
    assert auto.resolved(current) == [("salon-api-production-old", 100)] and calls == []


def test_failed_rollback_reports_unknown_live_traffic(auto, rollout, monkeypatch):
    receipt, _, calls = rollout
    original = auto.patch_traffic

    def patch(service, targets):
        if calls:
            raise RuntimeError("synthetic rollback denied")
        original(service, targets)

    monkeypatch.setattr(auto, "patch_traffic", patch)
    monkeypatch.setattr(auto, "public_health", lambda **kwargs: health(auto, False))
    with pytest.raises(RuntimeError, match="rollback denied"):
        auto.promote(receipt)
    assert receipt["status"] == "ROLLBACK_FAILED_OPERATOR_ACTION_REQUIRED"
    assert receipt["production_traffic_promoted"] is None


def test_traffic_patch_has_etag_and_only_traffic_mask(auto, monkeypatch):
    requests = []
    target = auto.targets(state(auto), "salon-api-production-new")
    current = state(auto, "salon-api-production-new")
    current["traffic"] = target
    monkeypatch.setattr(auto, "api", lambda *args: requests.append(args) or
                        ({"name": "must-not-poll-location-operation"} if args[0] == "PATCH" else current))
    auto.patch_traffic(state(auto), target)
    method, resource, body = requests[0]
    assert method == "PATCH" and resource == auto.RESOURCE
    assert set(body) == {"name", "etag", "traffic"} and body["etag"] == "etag-1"
    assert requests[1] == ("GET", auto.RESOURCE)


def test_public_health_failure_starts_rollback_without_waiting_for_remaining_urls(auto, monkeypatch):
    requests = []

    def failed(url, **kwargs):
        requests.append(url)
        raise urllib.error.HTTPError(url, 503, "synthetic", {}, None)

    monkeypatch.setattr(auto.urllib.request, "urlopen", failed)
    checks = auto.public_health()
    assert len(requests) == 1 and not auto.all_healthy(checks)
    assert next(iter(checks.values())) == {"status": 503, "pass": False}


@pytest.mark.parametrize("labels", [{}, {"org.opencontainers.image.revision": "a" * 40},
                                   {"org.opencontainers.image.revision": "a" * 40,
                                    "org.opencontainers.image.source": "https://github.com/other/repo"}])
def test_baseline_without_exact_source_label_is_refused(auto, monkeypatch, labels):
    monkeypatch.setattr(auto, "describe", lambda: {"status": {"traffic": [{"revisionName": "previous", "percent": 100}]}})
    monkeypatch.setattr(auto, "cloud", lambda *args: {"status": {"imageDigest": auto.release.IMAGE_ROOT + "sha256:" + "a" * 64}})
    monkeypatch.setattr(auto.release, "command", lambda *args: json.dumps([{"Config": {"Labels": labels}}])
                        if args[:3] == ("docker", "image", "inspect") else "")
    with pytest.raises(RuntimeError, match="proven Git source"):
        auto.baseline()


def valid_receipt(auto):
    return {"status": "PASS_CANDIDATE_VERIFIED", "ready": True, "api_identity": {"commit_sha": "a" * 40}, "commit": "a" * 40, "migration_differences": [],
            "smoke": {path: {"pass": True} for path in auto.SMOKES}, "openapi_sha256": "b" * 64,
            "openapi_contract_checks": "Expected routes and existing paths/operations/schema fields preserved",
            "image": auto.release.IMAGE_ROOT + "sha256:" + "c" * 64, "digest": "sha256:" + "c" * 64,
            "verified_resource_version": "v1", "previous_revision": "previous", "candidate_revision": "candidate"}


def test_complete_receipt_matches_current_service_and_ready_image(auto, monkeypatch):
    receipt = valid_receipt(auto)
    monkeypatch.setattr(auto.release, "latest_main", lambda: "a" * 40)
    monkeypatch.setattr(auto, "describe", lambda: {"metadata": {"resourceVersion": "v1"},
                                                   "status": {"traffic": [{"revisionName": "previous", "percent": 100}]}})
    monkeypatch.setattr(auto, "cloud", lambda *args: {"status": {"imageDigest": receipt["image"],
                                                                "conditions": [{"type": "Ready", "status": "True"}]}})
    auto.verified_receipt(receipt)


@pytest.mark.parametrize("change", ["missing_smoke", "failed_smoke", "migration", "status", "digest", "version", "ready"])
def test_promotion_requires_complete_same_candidate_evidence(auto, monkeypatch, change):
    receipt = valid_receipt(auto)
    monkeypatch.setattr(auto.release, "latest_main", lambda: "a" * 40)
    monkeypatch.setattr(auto, "describe", lambda: {"metadata": {"resourceVersion": "v1"},
                                                   "status": {"traffic": [{"revisionName": "previous", "percent": 100}]}})
    monkeypatch.setattr(auto, "cloud", lambda *args: {"status": {"imageDigest": receipt["image"],
                                                                "conditions": [{"type": "Ready", "status": "True"}]}})
    if change == "missing_smoke":
        receipt["smoke"].pop("/health/db")
    elif change == "failed_smoke":
        receipt["smoke"]["/health"]["pass"] = False
    elif change == "migration":
        receipt["migration_differences"] = ["new.sql"]
    elif change == "status":
        receipt["status"] = "PASS_AWAITING_EXPLICIT_TRAFFIC_APPROVAL"
    elif change == "digest":
        receipt["digest"] = "mutable-tag"
    elif change == "version":
        receipt["verified_resource_version"] = "older"
    else:
        receipt["ready"] = False
    with pytest.raises(RuntimeError):
        auto.verified_receipt(receipt)


def test_schema_candidate_cannot_be_promoted_automatically(auto):
    with pytest.raises(RuntimeError, match="separate explicit traffic approval"):
        auto.promote({"requires_supervised_promotion": True})


def test_verified_schema_deployment_stops_without_traffic_mutation(auto, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(auto, "guard", lambda: True)
    monkeypatch.setattr(auto, "baseline", lambda: "b" * 40)
    monkeypatch.setattr(auto, "public_health", lambda **kwargs: health(auto, True))
    monkeypatch.setitem(sys.modules, "ci_image_bundle", SimpleNamespace(download=lambda directory: None))
    receipt = {"requires_supervised_promotion": True, "production_traffic_promoted": False}
    monkeypatch.setattr(auto.release, "candidate", lambda **kwargs: receipt)
    def forbidden(receipt):
        pytest.fail("Schema deployment must never call automatic promotion")
    monkeypatch.setattr(auto, "promote", forbidden)
    auto.deploy()
    result = json.loads((tmp_path / "candidate-result.json").read_text())
    assert result["status"] == "PASS_AWAITING_EXPLICIT_TRAFFIC_APPROVAL"
    assert result["production_traffic_promoted"] is False
