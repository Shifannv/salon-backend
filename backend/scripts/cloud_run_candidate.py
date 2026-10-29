"""Fail-closed, read-only smoke checks around an image-only, zero-traffic release.

Runtime configuration and command output stay in memory. This program never reads
Secret Manager, runs migrations, or assigns production traffic.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY = "Shifannv/salon-backend"
SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def command(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    require(result.returncode == 0, f"{args[0]} operation failed; raw output suppressed")
    return result.stdout.strip()


def github(path: str) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/{path}",
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub preflight denied (HTTP {error.code}); do not bypass protection") from None


def latest_main() -> str:
    branch = github("branches/main")
    commit = os.environ["GITHUB_SHA"]
    require(branch["commit"]["sha"] == commit, "main advanced; run again for latest main")
    return commit


def preflight() -> str:
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "Wrong repository")
    require(os.environ.get("GITHUB_REF") == "refs/heads/main", "Only main can deploy")
    require(os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "Manual dispatch required")
    require(os.environ.get("GITHUB_ACTOR_ID") == "172572480", "Only the approved actor can deploy")
    require(os.environ.get("APPROVE_DEPLOYMENT") == "true", "Explicit candidate approval required")
    require(os.environ.get("DEPLOY_CONFIRMATION") == "DEPLOY api.salones.in", "Exact typed confirmation required")
    commit = latest_main()
    require(os.environ.get("REQUESTED_COMMIT") == commit, "Supplied commit must equal workflow SHA")
    require(SHA.fullmatch(commit) is not None, "Full source SHA required")
    require(command("git", "rev-parse", "HEAD") == commit, "Checkout differs from selected commit")
    require(not command("git", "status", "--porcelain"), "Working tree must be clean")
    baseline = os.environ["BASELINE_COMMIT"]
    require(SHA.fullmatch(baseline) is not None, "Full proven deployed source SHA required")
    require(command("git", "cat-file", "-t", baseline) == "commit", "Baseline commit missing")
    require(not command("git", "diff", "--name-only", baseline, commit, "--", "backend/migrations"),
            "Migration differences require separate reviewed backup, target and approval; candidate refused")
    environment = github("environments/production")
    policy = environment.get("deployment_branch_policy") or {}
    require(policy.get("custom_branch_policies") is True, "Production must allow main only")
    allowed = github("environments/production/deployment-branch-policies").get("branch_policies", [])
    require(len(allowed) == 1 and allowed[0].get("name") == "main"
            and allowed[0].get("type", "branch") == "branch", "Production branch policy must be main only")
    expected = {"GCP_PROJECT_ID": "saloon-505509", "GCP_REGION": "asia-south1",
                "GCP_CLOUD_RUN_SERVICE": "salon-api-production", "GCP_ARTIFACT_REGISTRY_REPOSITORY": "salon-production"}
    require(all(os.environ.get(key) == value for key, value in expected.items()), "Deployment target variables differ")
    return commit


def traffic(service: dict) -> list[tuple[str, int]]:
    return sorted((row["revisionName"], row["percent"])
                  for row in service["status"]["traffic"] if row.get("percent", 0))


def runtime(service: dict) -> dict:
    """Compare all revision settings, including env and mounted references, privately."""
    template = copy.deepcopy(service["spec"]["template"])
    template["metadata"].pop("name", None)
    template["metadata"].pop("creationTimestamp", None)
    annotations = template["metadata"].get("annotations", {})
    for key in ["run.googleapis.com/client-name", "run.googleapis.com/client-version"]:
        annotations.pop(key, None)
    for container in template["spec"]["containers"]:
        container.pop("image", None)
    return template


def verify_unchanged(before: dict, after: dict) -> None:
    require(traffic(before) == traffic(after), "Production traffic changed unexpectedly; stop and inspect")
    require(runtime(before) == runtime(after), "Runtime settings changed unexpectedly; stop and inspect")
    for key in ["run.googleapis.com/ingress", "run.googleapis.com/maxScale", "run.googleapis.com/minScale"]:
        require(before["metadata"].get("annotations", {}).get(key)
                == after["metadata"].get("annotations", {}).get(key), "Service configuration changed")


def verify_contract(baseline: dict, candidate: dict) -> None:
    require(bool(candidate.get("openapi")) and bool(candidate.get("paths")), "Invalid OpenAPI contract")
    expected = {"/health", "/health/db", "/health/redis", "/v1/salons", "/v1/subscription-plans"}
    require(expected <= candidate["paths"].keys(), "Expected API routes missing")
    methods = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
    for path, operations in baseline["paths"].items():
        require(path in candidate["paths"], "Existing OpenAPI path removed; review contract separately")
        require((operations.keys() & methods) <= candidate["paths"][path].keys(), "Existing API operation removed")
    schemas = candidate.get("components", {}).get("schemas", {})
    for name, previous in baseline.get("components", {}).get("schemas", {}).items():
        require(name in schemas, "Existing OpenAPI schema removed")
        current = schemas[name]
        require(previous.get("type") == current.get("type"), "Existing schema type changed")
        require(previous.get("required", []) == current.get("required", []), "Schema required fields changed; review separately")
        for field, shape in previous.get("properties", {}).items():
            require(field in current.get("properties", {}), "Existing schema field removed")
            require(shape == current["properties"][field], "Existing schema field changed; review separately")


def candidate() -> None:
    commit = preflight()
    project, region, service = (os.environ[key] for key in ["GCP_PROJECT_ID", "GCP_REGION", "GCP_CLOUD_RUN_SERVICE"])

    def cloud(*args: str) -> dict:
        return json.loads(command("gcloud", *args, "--project=" + project, "--format=json"))

    def describe() -> dict:
        return cloud("run", "services", "describe", service, "--region=" + region)

    before = describe()
    serving = traffic(before)
    require(len(serving) == 1 and serving[0][1] == 100, "A single previous 100% revision is required")
    previous = serving[0][0]
    revision = cloud("run", "revisions", "describe", previous, "--region=" + region)
    previous_image = revision["status"]["imageDigest"]
    registry = f"{region}-docker.pkg.dev"
    command("gcloud", "auth", "configure-docker", registry, "--quiet")
    command("docker", "pull", previous_image)
    previous_labels = json.loads(command("docker", "image", "inspect", previous_image))[0]["Config"].get("Labels") or {}
    require(previous_labels.get("org.opencontainers.image.revision") == os.environ["BASELINE_COMMIT"],
            "Serving image lacks matching proven source label; review baseline provenance separately")
    with urllib.request.urlopen("https://api.salones.in/openapi.json", timeout=60) as response:
        baseline_contract = json.load(response)
    require(bool(baseline_contract.get("paths")), "Cannot establish serving OpenAPI baseline")
    run_id = os.environ["GITHUB_RUN_ID"]
    attempt = os.environ["GITHUB_RUN_ATTEMPT"]
    require(run_id.isdigit() and attempt.isdigit(), "Invalid run identifier")
    suffix = f"gh-{commit[:8]}-{run_id}-{attempt}"
    tag = f"gh-{run_id}-{attempt}"
    image = f"{registry}/{project}/{os.environ['GCP_ARTIFACT_REGISTRY_REPOSITORY']}/api:{commit}-{run_id}-{attempt}"
    # Archive tracked commit contents: ignored/untracked files cannot enter the image.
    archive = subprocess.run(["git", "archive", "--format=tar", commit, "backend"], capture_output=True, check=False)
    require(archive.returncode == 0, "Cannot archive reviewed source")
    with tempfile.TemporaryDirectory(prefix="salon-reviewed-") as directory:
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as source:
            source.extractall(directory, filter="data")
        command("docker", "build", "--pull", "--platform=linux/amd64", "--label", f"org.opencontainers.image.revision={commit}",
                "--label", f"org.opencontainers.image.source=https://github.com/{REPOSITORY}", "--tag", image,
                str(Path(directory) / "backend"))
    command("bash", "backend/scripts/check-container.sh", image)
    latest_main()
    command("docker", "push", image)
    registry_image = cloud("artifacts", "docker", "images", "describe", image)
    digest = registry_image["image_summary"]["digest"]
    require(DIGEST.fullmatch(digest) is not None, "Invalid image digest")
    immutable = image.rsplit(":", 1)[0] + "@" + digest
    # Inspect the registry digest, not just a local tag, to verify source identity.
    command("docker", "pull", immutable)
    labels = json.loads(command("docker", "image", "inspect", immutable))[0]["Config"].get("Labels") or {}
    require(labels.get("org.opencontainers.image.revision") == commit, "Image source SHA mismatch")
    require(labels.get("org.opencontainers.image.source") == f"https://github.com/{REPOSITORY}", "Image repository mismatch")
    latest_main()
    require(before["metadata"]["resourceVersion"] == describe()["metadata"]["resourceVersion"],
            "Service changed during build; inspect and dispatch again")
    receipt = {"status": "STARTED", "commit": commit, "image": immutable, "digest": digest,
               "previous_revision": previous, "previous_image": previous_image, "candidate_revision": service + "-" + suffix,
               "migration_differences": [], "production_traffic_promoted": False, "smoke": {},
               "worker_coverage": "API image only; no worker deployment or execution; see CI_CD.md",
               "rollback_command": f"gcloud run services update-traffic {service} --project={project} --region={region} --to-revisions={previous}=100"}
    path = Path("candidate-result.json")
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    try:
        # Image-only update: never pass env, secrets, service account, scaling or ingress flags.
        command("gcloud", "run", "deploy", service, "--project=" + project, "--region=" + region,
                "--image=" + immutable, "--revision-suffix=" + suffix, "--no-traffic", "--tag=" + tag, "--quiet")
        after = describe()
        verify_unchanged(before, after)
        ready = cloud("run", "revisions", "describe", service + "-" + suffix, "--region=" + region)
        require(any(row["type"] == "Ready" and row["status"] == "True" for row in ready["status"]["conditions"]), "Candidate not Ready")
        receipt["ready"] = True
        resolved = ready["status"]["imageDigest"]
        require(resolved == immutable, "Cloud Run resolved a different image digest")
        url = next(row["url"] for row in after["status"]["traffic"] if row.get("tag") == tag)
        require(url.startswith("https://") and url.endswith(".run.app"), "Unexpected candidate URL")
        receipt["candidate_url"] = url
        for endpoint in ["/health", "/health/db", "/health/redis", "/docs", "/openapi.json"]:
            try:
                with urllib.request.urlopen(url + endpoint, timeout=60) as response:
                    body = response.read()
                    receipt["smoke"][endpoint] = {"status": response.status, "pass": response.status == 200}
                    if endpoint == "/openapi.json":
                        contract = json.loads(body)
                        try:
                            verify_contract(baseline_contract, contract)
                        except RuntimeError:
                            receipt["smoke"][endpoint]["pass"] = False
                            receipt["openapi_contract_checks"] = "FAIL_REVIEW_REQUIRED"
                            raise
                        receipt["openapi_contract_checks"] = "Expected routes and existing paths/operations/schema fields preserved"
                        receipt["openapi_sha256"] = hashlib.sha256(body).hexdigest()
                        receipt["openapi_path_count"] = len(contract["paths"])
            except urllib.error.HTTPError as error:
                receipt["smoke"][endpoint] = {"status": error.code, "pass": False}
            except (OSError, ValueError) as error:
                receipt["smoke"][endpoint] = {"error_type": type(error).__name__, "pass": False}
        require(all(row["pass"] for row in receipt["smoke"].values()), "Candidate smoke failed; production traffic untouched")
        latest_main()
        verify_unchanged(before, describe())
        receipt["status"] = "PASS_AWAITING_EXPLICIT_TRAFFIC_APPROVAL"
    except (RuntimeError, OSError, ValueError, KeyError, StopIteration):
        receipt["status"] = "STOP_NO_TRAFFIC_PROMOTION"
        raise
    finally:
        path.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            summary = {"commit": commit, "actor": os.environ.get("GITHUB_ACTOR"),
                       "actor_id": os.environ["GITHUB_ACTOR_ID"], "target_project": project,
                       "target_service": service, "image_digest": digest,
                       "current_serving_revision": previous, "rollback_revision": previous,
                       "confirmation": os.environ["DEPLOY_CONFIRMATION"], "status": receipt["status"]}
            with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as output:
                output.write("```json\n" + json.dumps(summary, indent=2) + "\n```\n")


if __name__ == "__main__":
    try:
        require(len(sys.argv) == 2 and sys.argv[1] in {"preflight", "candidate"}, "Expected preflight or candidate")
        preflight() if sys.argv[1] == "preflight" else candidate()
    except (RuntimeError, OSError, ValueError, KeyError, StopIteration) as error:
        # RuntimeError messages are our fixed strings; other exceptions may contain credentials.
        print(str(error) if type(error) is RuntimeError else f"Stopped: {type(error).__name__}; diagnostics suppressed", file=sys.stderr)
        sys.exit(1)
