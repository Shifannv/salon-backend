"""Cleanup cannot delete evidence or another workflow's image."""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def cleanup(monkeypatch):
    scripts = Path(__file__).parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("ci_artifact_cleanup", scripts / "ci_artifact_cleanup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for key, value in {"GITHUB_REPOSITORY": "Shifannv/salon-backend", "GITHUB_REF": "refs/heads/main",
                       "GITHUB_EVENT_NAME": "push", "GITHUB_ACTOR_ID": "172572480", "GITHUB_SHA": "a" * 40,
                       "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1", "CI_IMAGE_ARTIFACT_ID": "456",
                       "GH_TOKEN": "synthetic-test-only"}.items():
        monkeypatch.setenv(key, value)
    artifact = {"id": 456, "name": f"ci-image-{'a' * 40}-123-1",
                "workflow_run": {"id": 123, "head_sha": "a" * 40}}
    monkeypatch.setattr(module.release, "github", lambda path: artifact)
    request = MagicMock()
    request.return_value.__enter__.return_value.status = 204
    monkeypatch.setattr(module.urllib.request, "urlopen", request)
    return module, artifact, request


def test_only_own_consumed_image_can_be_deleted(cleanup):
    module, _, request = cleanup
    assert module.cleanup()["deleted_artifact_id"] == "456"
    sent = request.call_args.args[0]
    assert sent.method == "DELETE" and sent.full_url.endswith("/actions/artifacts/456")


@pytest.mark.parametrize("key,value", [("GITHUB_REF", "refs/heads/shifan"),
                                      ("GITHUB_EVENT_NAME", "pull_request"),
                                      ("GITHUB_ACTOR_ID", "other"), ("CI_IMAGE_ARTIFACT_ID", "../other")])
def test_untrusted_context_never_deletes(cleanup, monkeypatch, key, value):
    module, _, request = cleanup
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError):
        module.cleanup()
    request.assert_not_called()


@pytest.mark.parametrize("change", ["name", "commit", "run", "id"])
def test_other_artifact_never_deleted(cleanup, change):
    module, artifact, request = cleanup
    if change == "name":
        artifact["name"] = "cloud-run-evidence"
    elif change == "commit":
        artifact["workflow_run"]["head_sha"] = "b" * 40
    elif change == "run":
        artifact["workflow_run"]["id"] = 789
    else:
        artifact["id"] = 999
    with pytest.raises(RuntimeError):
        module.cleanup()
    request.assert_not_called()
