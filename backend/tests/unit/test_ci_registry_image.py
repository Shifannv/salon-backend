"""Registry transport preserves the tested image without GitHub archive storage."""
import copy
import importlib.util
import json
import sys
from io import BytesIO
from pathlib import Path

import pytest


@pytest.fixture
def registry(monkeypatch, tmp_path):
    scripts = Path(__file__).parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    for name in ("cloud_run_candidate", "ci_registry_image"):
        spec = importlib.util.spec_from_file_location(name, scripts / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        monkeypatch.setitem(sys.modules, name, module)
    for key, value in {"GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1",
                       "GITHUB_OUTPUT": str(tmp_path / "output")}.items():
        monkeypatch.setenv(key, value)
    metadata = {"schema_version": 1, "repository": module.release.REPOSITORY, "commit": "a" * 40,
                "run_id": "123", "attempt": "1", "image": module.release.IMAGE_ROOT + "sha256:" + "b" * 64,
                "config_digest": "sha256:" + "c" * 64, "layer_diff_ids": ["sha256:" + "d" * 64]}
    state = {"Id": metadata["config_digest"], "RootFS": {"Layers": metadata["layer_diff_ids"]},
             "Config": {"Labels": {"org.opencontainers.image.revision": metadata["commit"],
                                   "org.opencontainers.image.source": "https://github.com/" + module.release.REPOSITORY}}}
    calls = []

    def command(*args):
        calls.append(args)
        if args[:3] == ("docker", "image", "inspect"):
            return json.dumps([state])
        if args[:3] == ("docker", "buildx", "imagetools"):
            return json.dumps({"config": {"digest": state["Id"]}, "layers": []})
        if args[:4] == ("gcloud", "artifacts", "docker", "images"):
            return json.dumps({"image_summary": {"digest": "sha256:" + "b" * 64}})
        return ""

    monkeypatch.setattr(module.release, "command", command)
    monkeypatch.setattr(module.release, "identity", lambda **kwargs: "a" * 40)
    monkeypatch.setattr(module.release, "latest_main", lambda: "a" * 40)
    return module, metadata, state, calls


def test_publish_once_without_rebuild_or_artifact_upload(registry, monkeypatch):
    module, metadata, _, calls = registry
    assert module.publish(f"salon-platform-api:sha-{'a' * 40}-123-1") == metadata
    assert sum(args[:2] == ("docker", "push") for args in calls) == 1
    assert not any(args[:2] == ("docker", "build") for args in calls)
    output = Path(module.os.environ["GITHUB_OUTPUT"]).read_text()
    assert json.loads(output.split("=", 1)[1]) == metadata


@pytest.mark.parametrize("key,value", [("commit", "e" * 40), ("repository", "other/repo"),
                                      ("run_id", "124"), ("attempt", "2"), ("schema_version", 2),
                                      ("image", "registry.invalid/api:latest"),
                                      ("config_digest", "latest"), ("layer_diff_ids", [])])
def test_invalid_registry_provenance_rejected_without_network(registry, key, value):
    module, metadata, _, calls = registry
    changed = copy.deepcopy(metadata)
    changed[key] = value
    with pytest.raises(RuntimeError):
        module.inspect_verified(changed)
    assert calls == []


@pytest.mark.parametrize("change", ["config", "layers", "commit", "repository"])
def test_changed_registry_image_rejected(registry, change):
    module, metadata, state, _ = registry
    if change == "config":
        metadata["config_digest"] = "sha256:" + "e" * 64
    elif change == "layers":
        state["RootFS"]["Layers"] = ["sha256:" + "e" * 64]
    else:
        label = "revision" if change == "commit" else "source"
        state["Config"]["Labels"]["org.opencontainers.image." + label] = "changed"
    with pytest.raises(RuntimeError, match="differs from the CI-tested image"):
        module.inspect_verified(metadata)


def test_stale_main_never_pushes(registry, monkeypatch):
    module, _, _, calls = registry
    def stale():
        raise RuntimeError("main advanced")
    monkeypatch.setattr(module.release, "latest_main", stale)
    with pytest.raises(RuntimeError, match="main advanced"):
        module.publish(f"salon-platform-api:sha-{'a' * 40}-123-1")
    assert not any(args[:2] == ("docker", "push") for args in calls)


def test_only_exact_ci_local_reference_can_publish(registry):
    module, _, _, calls = registry
    with pytest.raises(RuntimeError, match="Unexpected CI-tested image"):
        module.publish("salon-platform-api:latest")
    assert calls == []


def test_candidate_deploys_verified_digest_without_rebuild_or_repush(registry, monkeypatch, tmp_path):
    module, metadata, image_state, calls = registry
    release = module.release
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(release, "preflight", lambda **kwargs: metadata["commit"])
    monkeypatch.setattr(release, "SCHEMA_COMPATIBILITY", None)
    for key, value in {"GCP_PROJECT_ID": "saloon-505509", "GCP_REGION": "asia-south1",
                       "GCP_CLOUD_RUN_SERVICE": "salon-api-production", "BASELINE_COMMIT": metadata["commit"],
                       "GCP_ARTIFACT_REGISTRY_REPOSITORY": "salon-production", "BOOTSTRAP_BASELINE": "false"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    before = {"metadata": {"resourceVersion": "1"}, "spec": {"template": {"metadata": {},
              "spec": {"containers": [{"image": "previous", "env": [{"name": "UNCHANGED", "value": "synthetic"}]}]}}},
              "status": {"traffic": [{"revisionName": "salon-api-production-previous", "percent": 100}]}}
    after = copy.deepcopy(before)
    after["status"]["traffic"].append({"tag": "gh-123-1", "url": "https://review.run.app"})
    after["metadata"]["resourceVersion"] = "2"
    after["spec"]["template"]["spec"]["containers"][0]["image"] = metadata["image"]
    deployed = False
    original = release.command
    def command(*args):
        nonlocal deployed
        if args[:4] == ("gcloud", "run", "services", "describe"):
            return json.dumps(after if deployed else before)
        if args[:4] == ("gcloud", "run", "revisions", "describe"):
            return json.dumps({"status": {"imageDigest": metadata["image"],
                                          "conditions": [{"type": "Ready", "status": "True"}]}})
        if args[:3] == ("gcloud", "run", "deploy"):
            calls.append(args)
            assert "--image=" + metadata["image"] in args
            assert "--no-traffic" in args
            deployed = True
            return ""
        return original(*args)
    monkeypatch.setattr(release, "command", command)
    paths = {path: {"get": {}} for path in ["/health", "/health/db", "/health/redis", "/v1/salons", "/v1/subscription-plans"]}
    class Response(BytesIO):
        status = 200
    def response(url, **kwargs):
        body = ({"openapi": "3.1.0", "paths": paths} if url.endswith("openapi.json")
                else {"commit_sha": metadata["commit"], "version": "0.1.0"} if url.endswith("/version")
                else {"status": "ok"})
        return Response(json.dumps(body).encode())
    monkeypatch.setattr(release.urllib.request, "urlopen", response)
    result = release.candidate(automatic=True, tested_registry=metadata)
    assert result["status"] == "PASS_CANDIDATE_VERIFIED"
    assert result["image"] == metadata["image"] and result["production_traffic_promoted"] is False
    assert result["ci_registry_provenance"] == metadata
    assert all(row["pass"] for row in result["smoke"].values())
    assert not any(args[:2] in [("docker", "build"), ("docker", "push")] for args in calls)
    assert image_state["Config"]["Labels"]["org.opencontainers.image.revision"] == metadata["commit"]
