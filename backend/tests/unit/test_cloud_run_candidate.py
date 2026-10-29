"""Deployment guard regressions; these tests never access GitHub, Docker or GCP."""
import copy
import importlib.util
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
