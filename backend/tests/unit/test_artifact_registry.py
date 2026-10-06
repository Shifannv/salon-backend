"""Release registry selection must not guess among different repositories."""

import json
from subprocess import CompletedProcess

import pytest

from scripts import resolve_artifact_registry as registry


def repository(location="us-central1", **overrides):
    return {
        "name": f"projects/test-project/locations/{location}/repositories/salon-backend",
        "format": "DOCKER",
        "mode": "STANDARD_REPOSITORY",
        **overrides,
    }


def mock_gcloud(monkeypatch, responses):
    calls = []
    pending = iter(responses)

    def run(*args):
        calls.append(args)
        code, payload = next(pending)
        return CompletedProcess(
            args, code, json.dumps(payload), "permission denied" if code else ""
        )

    monkeypatch.setattr(registry, "gcloud", run)
    return calls


def test_verified_location_does_not_require_project_wide_discovery(monkeypatch):
    calls = mock_gcloud(monkeypatch, [(0, repository("us"))])
    assert registry.resolve_registry("test-project", "us") == (
        "us-docker.pkg.dev",
        "us-docker.pkg.dev/test-project/salon-backend",
    )
    assert len(calls) == 1
    assert calls[0][0] == "describe"


def test_vm_zone_falls_back_to_actual_repository_location(monkeypatch):
    calls = mock_gcloud(monkeypatch, [(1, {}), (0, [repository()])])
    host, path = registry.resolve_registry("test-project", "us-central1-a")
    assert host == "us-central1-docker.pkg.dev"
    assert path == "us-central1-docker.pkg.dev/test-project/salon-backend"
    assert calls[1] == ("list", "--project=test-project", "--location=all")


def test_ambiguous_locations_require_explicit_selection(monkeypatch):
    mock_gcloud(monkeypatch, [(0, [repository("us"), repository("eu")])])
    with pytest.raises(ValueError, match="Multiple salon-backend"):
        registry.resolve_registry("test-project", "")


def test_unrelated_repository_is_not_used(monkeypatch):
    mock_gcloud(
        monkeypatch,
        [(0, [repository(name="projects/test-project/locations/us/repositories/other")])],
    )
    with pytest.raises(ValueError, match="No accessible salon-backend"):
        registry.resolve_registry("test-project", "")


@pytest.mark.parametrize("overrides", [{"format": "MAVEN"}, {"mode": "REMOTE_REPOSITORY"}])
def test_only_writable_docker_repositories_are_accepted(monkeypatch, overrides):
    mock_gcloud(monkeypatch, [(0, repository(**overrides))])
    with pytest.raises(ValueError, match="standard Docker repository"):
        registry.resolve_registry("test-project", "us-central1")


def test_access_failure_does_not_guess_a_registry(monkeypatch):
    mock_gcloud(monkeypatch, [(1, {}), (1, {})])
    with pytest.raises(ValueError, match="repository read permissions"):
        registry.resolve_registry("test-project", "us-central1")


def test_empty_project_stops_before_cloud_requests(monkeypatch):
    calls = mock_gcloud(monkeypatch, [])
    with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
        registry.resolve_registry("", "us-central1")
    assert calls == []


def test_workflow_outputs_use_verified_location(monkeypatch, tmp_path):
    mock_gcloud(monkeypatch, [(1, {}), (0, [repository("us")])])
    output = tmp_path / "outputs"
    for name, value in {
        "GCP_PROJECT_ID": "test-project",
        "GCP_REGION": "us-central1-a",
        "IMAGE_NAME": "salon-platform-api",
        "GITHUB_SHA": "abc123",
        "GITHUB_OUTPUT": str(output),
    }.items():
        monkeypatch.setenv(name, value)
    assert registry.main() == 0
    assert output.read_text() == (
        "registry_host=us-docker.pkg.dev\n"
        "sha_tag=us-docker.pkg.dev/test-project/salon-backend/salon-platform-api:abc123\n"
    )
