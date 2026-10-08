"""Resolve the release registry from an existing Google Cloud repository."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPOSITORY = "salon-backend"


def gcloud(*args):
    return subprocess.run(
        ["gcloud", "artifacts", "repositories", *args, "--format=json", "--quiet"],
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_registry(project, location):
    if not project or any(char.isspace() or char == "/" for char in project):
        raise ValueError("Set GCP_PROJECT_ID to the Google Cloud project ID.")

    repository = None
    if location:
        result = gcloud("describe", REPOSITORY, f"--project={project}", f"--location={location}")
        if result.returncode == 0:
            repository = json.loads(result.stdout)

    if repository is None:
        result = gcloud("list", f"--project={project}", "--location=all")
        if result.returncode:
            raise ValueError(
                "Cannot discover the Artifact Registry repository. Check GCP_PROJECT_ID, "
                "GCP_REGION (repository location, not VM zone), and the runner service "
                "account's repository read permissions.\n" + result.stderr.strip()
            )
        matches = [
            item
            for item in json.loads(result.stdout)
            if item["name"].endswith(f"/repositories/{REPOSITORY}")
        ]
        if not matches:
            raise ValueError(
                f"No accessible {REPOSITORY} repository exists in GCP_PROJECT_ID. "
                "Create a standard Docker repository named salon-backend in Artifact "
                "Registry and set GCP_REGION to its location before deploying."
            )
        if len(matches) != 1:
            raise ValueError(
                "Multiple salon-backend repositories exist. Set GCP_REGION to the "
                "intended repository location."
            )
        repository = matches[0]

    if (
        repository.get("format") != "DOCKER"
        or repository.get("mode", "STANDARD_REPOSITORY") != "STANDARD_REPOSITORY"
    ):
        raise ValueError("salon-backend must be a standard Docker repository to accept pushes.")

    parts = repository["name"].split("/")
    if len(parts) != 6 or parts[2] != "locations" or parts[4:] != ["repositories", REPOSITORY]:
        raise ValueError("Artifact Registry returned an unexpected repository resource name.")
    actual_location = parts[3]
    if location != actual_location:
        print(
            f"Using verified Artifact Registry location {actual_location}; "
            "set GCP_REGION to this repository location.",
            file=sys.stderr,
        )
    host = f"{actual_location}-docker.pkg.dev"
    return host, f"{host}/{project}/{REPOSITORY}"


def main():
    try:
        host, registry = resolve_registry(
            os.environ.get("GCP_PROJECT_ID", "").strip(),
            os.environ.get("GCP_REGION", "").strip(),
        )
        tag = f"{registry}/{os.environ['IMAGE_NAME']}:{os.environ['GITHUB_SHA']}"
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            output.write(f"registry_host={host}\nsha_tag={tag}\n")
    except (ValueError, KeyError, OSError) as error:
        print(f"Artifact Registry configuration failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
