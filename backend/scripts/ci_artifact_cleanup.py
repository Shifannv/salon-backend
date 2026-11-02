"""Delete only the exact CI image consumed by this successful main release."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

import cloud_run_candidate as release


def cleanup() -> dict:
    expected = {"GITHUB_REPOSITORY": release.REPOSITORY, "GITHUB_REF": "refs/heads/main",
                "GITHUB_EVENT_NAME": "push", "GITHUB_ACTOR_ID": "172572480"}
    release.require(all(os.environ.get(key) == value for key, value in expected.items()),
                    "Artifact cleanup requires the owner main-push release context")
    artifact_id = os.environ.get("CI_IMAGE_ARTIFACT_ID", "")
    commit = os.environ.get("GITHUB_SHA", "")
    run = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    release.require(artifact_id.isdigit() and run.isdigit() and attempt.isdigit()
                    and re.fullmatch(r"[0-9a-f]{40}", commit), "Invalid artifact cleanup identity")
    path = "actions/artifacts/" + artifact_id
    artifact = release.github(path)
    release.require(str(artifact.get("id")) == artifact_id
                    and artifact.get("name") == f"ci-image-{commit}-{run}-{attempt}"
                    and str(artifact.get("workflow_run", {}).get("id")) == run
                    and artifact.get("workflow_run", {}).get("head_sha") == commit,
                    "Refusing to delete an artifact from another image, commit or run")
    token = os.environ.get("GH_TOKEN", "")
    release.require(bool(token), "Artifact cleanup credential unavailable")
    request = urllib.request.Request(
        "https://api.github.com/repos/" + release.REPOSITORY + "/" + path,
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"},
        method="DELETE",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release.require(response.status == 204, "Artifact deletion did not succeed")
    return {"deleted_artifact_id": artifact_id, "commit": commit, "run_id": run}


if __name__ == "__main__":
    try:
        print(json.dumps(cleanup()))
    except Exception:
        print("Consumed-image cleanup failed; no broader deletion attempted; diagnostics suppressed", file=sys.stderr)
        sys.exit(1)
