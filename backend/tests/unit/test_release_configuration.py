"""Offline policy/CI artifact regression tests. All external operations are mocked."""
import copy
import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import urllib.error
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "backend/scripts"


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    loaded = []
    for name in ["cloud_run_candidate", "cloud_run_auto", "ci_image_bundle"]:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        loaded.append(module)
    return loaded


def forbidden(*args, **kwargs):
    raise AssertionError("External command/request forbidden during local verification")


@pytest.mark.parametrize("value", ["", "false", "True", "TRUE", "true ", "1"])
def test_disabled_gate_has_no_external_side_effects(modules, monkeypatch, value):
    release, auto, _ = modules
    for key, content in {"AUTO_DEPLOY_ENABLED": value, "PRODUCTION_AUTO_DEPLOY_ENABLED": "true",
                         "GITHUB_REPOSITORY": release.REPOSITORY, "GITHUB_EVENT_NAME": "push",
                         "GITHUB_REF": "refs/heads/main", "GITHUB_ACTOR_ID": "172572480"}.items():
        monkeypatch.setenv(key, content)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setattr(release, "github", forbidden)
    monkeypatch.setattr(release, "command", forbidden)
    monkeypatch.setattr(auto, "cloud", forbidden)
    assert auto.gate() is False
    assert auto.guard() is False
    auto.deploy()


@pytest.fixture
def eligible(modules, monkeypatch):
    release, auto, bundle = modules
    sha = "a" * 40
    for key, content in {"AUTO_DEPLOY_ENABLED": "true",
                         "GITHUB_REPOSITORY": release.REPOSITORY,
                         "GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/main",
                         "GITHUB_ACTOR_ID": "172572480", "GITHUB_SHA": sha,
                         "GITHUB_ACTOR": "Shifannv", "GITHUB_TRIGGERING_ACTOR": "Shifannv"}.items():
        monkeypatch.setenv(key, content)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setattr(release, "identity", lambda **kwargs: sha)
    monkeypatch.setattr(release, "command", forbidden)
    monkeypatch.setattr(auto, "cloud", forbidden)
    pulls = [{"merged_at": "synthetic", "merge_commit_sha": sha,
              "base": {"ref": "main", "repo": {"full_name": release.REPOSITORY}}}]
    monkeypatch.setattr(release, "github", lambda path: pulls)
    return release, auto, bundle, pulls


def test_exact_merged_main_is_eligible(eligible):
    _, auto, _, _ = eligible
    assert auto.guard() is True


@pytest.mark.parametrize("value", [None, "", "false", "true", "True", "FALSE", "1"])
def test_stale_secret_cannot_change_enabled_gate(eligible, monkeypatch, value):
    _, auto, _, _ = eligible
    if value is None:
        monkeypatch.delenv("PRODUCTION_AUTO_DEPLOY_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PRODUCTION_AUTO_DEPLOY_ENABLED", value)
    assert auto.guard() is True


def test_single_variable_gate_emits_enabled_output_and_reason(eligible, monkeypatch, tmp_path, capsys):
    _, auto, _, _ = eligible
    output = tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.delenv("PRODUCTION_AUTO_DEPLOY_ENABLED", raising=False)
    assert auto.gate() is True
    assert output.read_text().strip() == "enabled=true"
    assert "Deployment gate: enabled=true; blocked_by=none" in capsys.readouterr().out
    monkeypatch.setenv("AUTO_DEPLOY_ENABLED", "false")
    assert auto.gate() is False
    assert output.read_text().splitlines()[-1] == "enabled=false"
    assert "Deployment gate: enabled=false; blocked_by=auto_deploy_enabled" in capsys.readouterr().out


def test_missing_authoritative_variable_fails_closed(eligible, monkeypatch, capsys):
    _, auto, _, _ = eligible
    monkeypatch.delenv("AUTO_DEPLOY_ENABLED")
    monkeypatch.setenv("PRODUCTION_AUTO_DEPLOY_ENABLED", "true")
    assert auto.gate() is False
    assert "blocked_by=auto_deploy_enabled" in capsys.readouterr().out


@pytest.mark.parametrize("key,value,reason", [
    ("GITHUB_REF", "refs/heads/shifan", "ref_main"),
    ("GITHUB_EVENT_NAME", "pull_request", "event_push"),
    ("GITHUB_EVENT_NAME", "pull_request_target", "event_push"),
    ("GITHUB_EVENT_NAME", "workflow_dispatch", "event_push"),
    ("GITHUB_REPOSITORY", "other/repo", "repository"),
    ("GITHUB_ACTOR_ID", "untrusted", "actor_id"),
])
def test_ineligible_context_prints_exact_reason_before_identity(eligible, monkeypatch, capsys, key, value, reason):
    release, auto, _, _ = eligible
    monkeypatch.setenv(key, value)
    monkeypatch.setattr(release, "identity", forbidden)
    assert auto.guard() is False
    assert f"Deployment gate: enabled=false; blocked_by={reason}" in capsys.readouterr().out


@pytest.mark.parametrize("change", ["unmerged", "different_sha", "different_base", "different_repo", "direct_push"])
def test_direct_push_or_wrong_merge_is_refused(eligible, change):
    _, auto, _, pulls = eligible
    if change == "direct_push":
        pulls.clear()
    elif change == "unmerged":
        pulls[0]["merged_at"] = None
    elif change == "different_sha":
        pulls[0]["merge_commit_sha"] = "b" * 40
    elif change == "different_base":
        pulls[0]["base"]["ref"] = "shifan"
    else:
        pulls[0]["base"]["repo"]["full_name"] = "other/repo"
    with pytest.raises(RuntimeError, match="merged PR"):
        auto.guard()


def test_stale_queue_is_skipped_before_cloud_auth(eligible, monkeypatch):
    release, auto, _, _ = eligible
    monkeypatch.setattr(release, "identity", lambda **kwargs: (_ for _ in ()).throw(
        RuntimeError("main advanced; run again for latest main")))
    monkeypatch.setattr(release, "github", forbidden)
    assert auto.guard() is False


def test_different_retry_actor_is_refused(eligible, monkeypatch):
    _, auto, _, _ = eligible
    monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", "other-user")
    with pytest.raises(RuntimeError, match="retry"):
        auto.guard()


def test_new_main_does_not_interrupt_started_release(modules, monkeypatch):
    release, _, _ = modules
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setattr(release, "latest_main", forbidden)
    release.DEPLOYMENT_STARTED = True
    assert release.deployment_commit() == "a" * 40


def test_automatic_candidate_requires_tested_artifact_before_any_cloud_access(modules, monkeypatch):
    release, _, _ = modules
    monkeypatch.setattr(release, "command", forbidden)
    monkeypatch.setattr(release, "github", forbidden)
    with pytest.raises(RuntimeError, match="CI-tested image"):
        release.candidate(automatic=True)


def workflow(name):
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


def test_all_workflows_parse_and_actions_are_immutable():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        data = workflow(path.name)
        assert isinstance(data["jobs"], dict)
        for job in data["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step:
                    assert len(step["uses"].rsplit("@", 1)[-1]) == 40


def test_feature_pr_ci_and_exact_check_names_have_no_deployment_permissions():
    ci = workflow("backend.yml")
    assert {"push", "pull_request"} <= ci["on"].keys()
    assert ci["jobs"]["test"]["name"] == "Lint and tests"
    assert ci["jobs"]["image"]["name"] == "Build and smoke test image"
    assert ci["jobs"]["image"]["needs"] == "test"
    assert ci["permissions"] == {"contents": "read"}
    assert all("environment" not in job for job in ci["jobs"].values())


def test_actual_deploy_job_skips_when_authoritative_gate_is_false():
    data = workflow("cloud-run-auto.yml")
    assert data["on"] == {"push": {"branches": ["main"]}}
    # Concurrency must be at the workflow level so that an older commit whose CI finishes
    # later cannot preempt a newer commit's pending release slot (P1 queue-ordering fix).
    assert data["concurrency"] == {"group": "production-cloud-run", "cancel-in-progress": "false"}
    assert data["jobs"]["gate"]["environment"] == "production"
    activation = next(step for step in data["jobs"]["gate"]["steps"] if step.get("id") == "activation")
    assert activation["env"]["AUTO_DEPLOY_ENABLED"] == "${{ vars.AUTO_DEPLOY_ENABLED }}"
    assert "AUTO_DEPLOY_ENABLED" not in data["jobs"]["gate"]["env"]
    job = data["jobs"]["release"]
    assert set(job["needs"]) == {"ci", "gate"}
    assert "needs.gate.outputs.enabled == 'true'" in job["if"]
    assert "concurrency" not in job  # serialization is at workflow level, not release-job level
    assert all("if" in step for step in job["steps"] if step.get("uses", "").startswith("google-github-actions/"))
    claim_step = next(step for step in job["steps"] if step.get("run") == "python3 backend/scripts/wif_claim_preflight.py")
    auth_index = next(index for index, step in enumerate(job["steps"])
                      if step.get("uses", "").startswith("google-github-actions/auth@"))
    assert claim_step["if"] == "steps.admit.outputs.eligible == 'true'"
    assert job["steps"].index(claim_step) < auth_index
    workflow_text = (ROOT / ".github/workflows/cloud-run-auto.yml").read_text()
    assert "PRODUCTION_AUTO_DEPLOY_ENABLED" not in workflow_text
    assert "AUTO_DEPLOY_ENABLED" not in job["env"]
    for step in job["steps"]:
        if step.get("run", "").endswith(("cloud_run_auto.py guard", "cloud_run_auto.py deploy")):
            assert step["env"]["AUTO_DEPLOY_ENABLED"] == "${{ vars.AUTO_DEPLOY_ENABLED }}"
    manual = workflow("cloud-run-candidate.yml")
    assert manual["permissions"] == {"contents": "read"} and set(manual["jobs"]) == {"disabled"}


def test_queue_ab_older_commit_skips_newer_main_stays_eligible(eligible, monkeypatch):
    """Regression for P1 queue-ordering: A (older) reaches release after B is already on main.
    A must skip before any cloud auth. B (current main) remains eligible."""
    release, auto, _, _ = eligible
    # A is an older commit; main has advanced to B (the eligible fixture SHA).
    monkeypatch.setattr(release, "identity", lambda **kwargs: (_ for _ in ()).throw(
        RuntimeError("main advanced; run again for latest main")))
    assert auto.guard() is False  # A skips without touching cloud resources


def test_queue_abc_only_newest_eligible_c_deploys(eligible, monkeypatch):
    """Regression: A and B are both older than C (current main). Both skip; C is eligible.
    Workflow-level concurrency guarantees C holds the pending slot, not A or B."""
    release, auto, _, _ = eligible
    # A skips
    monkeypatch.setattr(release, "identity", lambda **kwargs: (_ for _ in ()).throw(
        RuntimeError("main advanced; run again for latest main")))
    assert auto.guard() is False
    # B also skips
    assert auto.guard() is False
    # C is main — restore identity to return the eligible SHA
    sha = "a" * 40
    monkeypatch.setattr(release, "identity", lambda **kwargs: sha)
    assert auto.guard() is True  # C is eligible and deploys


@pytest.fixture
def saved_bundle(modules, monkeypatch, tmp_path):
    _, _, bundle = modules
    for key, value in {"GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2"}.items():
        monkeypatch.setenv(key, value)
    image = "ci:tested"
    config = {"config": {"Labels": {"org.opencontainers.image.revision": "a" * 40,
                                    "org.opencontainers.image.source": "https://github.com/Shifannv/salon-backend"}},
              "rootfs": {"diff_ids": ["sha256:" + "b" * 64]}}
    raw = json.dumps(config).encode()
    config_id = "sha256:" + hashlib.sha256(raw).hexdigest()
    with tarfile.open(tmp_path / "image.tar", "w") as archive:
        for name, data in {"config.json": raw, "manifest.json": json.dumps([
            {"RepoTags": [image], "Config": "config.json", "Layers": []}]).encode()}.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    metadata = {"schema_version": 1, "repository": "Shifannv/salon-backend", "commit": "a" * 40,
                "run_id": "123", "attempt": "2", "image_ref": image, "tested_image_id": config_id,
                "config_digest": config_id, "layer_diff_ids": config["rootfs"]["diff_ids"],
                "archive_sha256": bundle.sha256(tmp_path / "image.tar"), "verified_image_ids": [config_id]}
    (tmp_path / "provenance.json").write_text(json.dumps(metadata))
    return bundle, tmp_path, metadata


def test_tested_image_archive_source_and_content_verify(saved_bundle):
    bundle, path, metadata = saved_bundle
    assert bundle.validate(path) == metadata


@pytest.mark.parametrize("field", ["commit", "repository", "run_id", "attempt", "config_digest", "layer_diff_ids", "archive_sha256"])
def test_artifact_substitution_is_rejected(saved_bundle, field):
    bundle, path, metadata = saved_bundle
    corrupted = copy.deepcopy(metadata)
    corrupted[field] = [] if field == "layer_diff_ids" else "different"
    (path / "provenance.json").write_text(json.dumps(corrupted))
    with pytest.raises(RuntimeError):
        bundle.validate(path)


def test_changed_image_archive_is_rejected(saved_bundle):
    bundle, path, _ = saved_bundle
    with (path / "image.tar").open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(RuntimeError, match="archive changed"):
        bundle.validate(path)


def test_automatic_pipeline_uses_tested_image_and_finishes_after_new_main(modules, monkeypatch, tmp_path):
    release, _, bundle = modules
    sha, baseline = "a" * 40, "b" * 40
    previous_image = release.IMAGE_ROOT + "sha256:" + "b" * 64
    immutable = release.IMAGE_ROOT + "sha256:" + "c" * 64
    for key, value in {"BASELINE_COMMIT": baseline, "GITHUB_SHA": sha, "GITHUB_RUN_ID": "123",
                       "GITHUB_RUN_ATTEMPT": "2", "GCP_PROJECT_ID": "saloon-505509",
                       "GCP_REGION": "asia-south1", "GCP_CLOUD_RUN_SERVICE": "salon-api-production",
                       "GCP_ARTIFACT_REGISTRY_REPOSITORY": "salon-production", "BOOTSTRAP_BASELINE": "false",
                       "GITHUB_ACTOR_ID": "172572480"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.chdir(tmp_path)
    metadata = {"image_ref": "ci:tested", "config_digest": "sha256:" + "d" * 64,
                "layer_diff_ids": ["sha256:" + "e" * 64]}
    monkeypatch.setattr(bundle, "load", lambda directory: metadata)
    monkeypatch.setattr(release, "preflight", lambda **kwargs: sha)
    latest_calls = []

    def latest():
        latest_calls.append(True)
        assert len(latest_calls) == 1, "Newer main must not abort a started release"
        return sha

    monkeypatch.setattr(release, "latest_main", latest)
    before = {"metadata": {"resourceVersion": "1", "annotations": {}},
              "spec": {"template": {"metadata": {"name": "previous", "annotations": {}},
                                     "spec": {"containers": [{"image": previous_image}]}}},
              "status": {"traffic": [{"revisionName": "previous", "percent": 100}]}}
    after = copy.deepcopy(before)
    after["metadata"]["resourceVersion"] = "2"
    after["status"]["traffic"].append({"tag": "gh-123-2", "url": "https://candidate.run.app"})
    services = iter([before, before, after, after])
    commands = []

    def command(*args):
        commands.append(args)
        assert args[:2] != ("docker", "build"), "Deployment must not rebuild CI image"
        if args[:4] == ("gcloud", "run", "services", "describe"):
            return json.dumps(next(services))
        if args[:4] == ("gcloud", "run", "revisions", "describe"):
            if args[4] == "previous":
                return json.dumps({"status": {"imageDigest": previous_image}})
            return json.dumps({"status": {"imageDigest": immutable, "conditions": [{"type": "Ready", "status": "True"}]}})
        if args[:3] == ("docker", "image", "inspect"):
            commit = baseline if args[3] == previous_image else sha
            return json.dumps([{"Config": {"Labels": {"org.opencontainers.image.revision": commit,
                                  "org.opencontainers.image.source": "https://github.com/" + release.REPOSITORY}},
                               "RootFS": {"Layers": metadata["layer_diff_ids"]}}])
        if args[:4] == ("gcloud", "artifacts", "docker", "images"):
            return json.dumps({"image_summary": {"digest": "sha256:" + "c" * 64}})
        if args[:4] == ("docker", "buildx", "imagetools", "inspect"):
            return json.dumps({"config": {"digest": metadata["config_digest"]}, "layers": []})
        return ""

    monkeypatch.setattr(release, "command", command)
    contract = {"openapi": "3.1.0", "paths": {path: {"get": {}} for path in
                ["/health", "/health/db", "/health/redis", "/v1/salons", "/v1/subscription-plans"]}}

    class Reply(io.BytesIO):
        status = 200

    def response(url, **kwargs):
        value = contract if url.endswith("/openapi.json") else {"version": "0.1.0", "commit_sha": sha}
        if url.endswith("/health/ready"):
            value = {"status": "ok"}
        return Reply(json.dumps(value).encode())

    monkeypatch.setattr(release.urllib.request, "urlopen", response)
    result = release.candidate(automatic=True, tested_bundle=tmp_path)
    assert result["status"] == "PASS_CANDIDATE_VERIFIED"
    assert result["api_identity"]["commit_sha"] == sha
    assert set(result["smoke"]) == {"/health/ready", "/version", "/health", "/health/db", "/health/redis", "/docs", "/openapi.json"}
    assert any(args[:2] == ("docker", "tag") for args in commands)
    deploy = next(args for args in commands if args[:3] == ("gcloud", "run", "deploy"))
    assert "--image=" + immutable in deploy and "--no-traffic" in deploy


def test_signed_artifact_download_verifies_digest_without_forwarding_auth(saved_bundle, monkeypatch, tmp_path):
    bundle, directory, metadata = saved_bundle
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name in ["image.tar", "provenance.json"]:
            archive.write(directory / name, name)
    payload = data.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    for key, value in {"CI_IMAGE_ARTIFACT_ID": "42", "CI_IMAGE_ARTIFACT_DIGEST": digest,
                       "GH_TOKEN": "synthetic-unit-only"}.items():
        monkeypatch.setenv(key, value)
    artifact = {"expired": False, "name": bundle.artifact_name(), "digest": "sha256:" + digest,
                "workflow_run": {"id": 123, "head_sha": "a" * 40}}
    monkeypatch.setattr(bundle.release, "github", lambda path: artifact)
    signed_url = "https://synthetic.blob.core.windows.net/artifact.zip?sig=synthetic"
    requests = []

    class Opener:
        def open(self, request, **kwargs):
            assert request.full_url.startswith("https://api.github.com/repos/Shifannv/salon-backend/")
            assert request.get_header("Authorization") == "Bearer synthetic-unit-only"
            raise urllib.error.HTTPError(request.full_url, 302, "redirect", {"Location": signed_url}, None)

    monkeypatch.setattr(bundle.urllib.request, "build_opener", lambda handler: Opener())

    def storage(url, **kwargs):
        assert isinstance(url, str) and url == signed_url  # No Authorization-bearing Request forwarded.
        requests.append(url)
        return io.BytesIO(payload)

    monkeypatch.setattr(bundle.urllib.request, "urlopen", storage)
    assert bundle.download(tmp_path / "restored") == metadata
    assert len(requests) == 1


@pytest.mark.parametrize("change", ["run", "sha", "digest", "name", "expired"])
def test_wrong_artifact_rejected_before_download(saved_bundle, monkeypatch, tmp_path, change):
    bundle, _, _ = saved_bundle
    digest = "a" * 64
    monkeypatch.setenv("CI_IMAGE_ARTIFACT_ID", "42")
    monkeypatch.setenv("CI_IMAGE_ARTIFACT_DIGEST", digest)
    artifact = {"expired": False, "name": bundle.artifact_name(), "digest": "sha256:" + digest,
                "workflow_run": {"id": 123, "head_sha": "a" * 40}}
    if change == "run":
        artifact["workflow_run"]["id"] = 999
    elif change == "sha":
        artifact["workflow_run"]["head_sha"] = "b" * 40
    elif change == "expired":
        artifact["expired"] = True
    else:
        artifact[change] = "other"
    monkeypatch.setattr(bundle.release, "github", lambda path: artifact)
    monkeypatch.setattr(bundle.urllib.request, "build_opener", forbidden)
    with pytest.raises(RuntimeError, match="Artifact belongs"):
        bundle.download(tmp_path / "never-created")


def test_public_http_200_with_wrong_commit_is_failed_and_stops_smoke(modules, monkeypatch):
    _, auto, _ = modules
    requests = []

    class Reply(io.BytesIO):
        status = 200

    def response(url, **kwargs):
        requests.append(url)
        body = {"status": "ok"} if url.endswith("/health/ready") else {"version": "0.1.0", "commit_sha": "b" * 40}
        return Reply(json.dumps(body).encode())

    monkeypatch.setattr(auto.urllib.request, "urlopen", response)
    checks = auto.public_health(expected_commit="a" * 40)
    assert len(requests) == 2 and not auto.all_healthy(checks)
    assert checks[requests[-1]] == {"status": 200, "pass": False}
