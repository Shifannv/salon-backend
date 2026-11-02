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
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

DEPLOYMENT_STARTED = False
SCHEMA_COMPATIBILITY = None
SCHEMA_RECEIPT_PATH = "backend/deployments/schema-0053-0055-20261101.json"
REPOSITORY = "Shifannv/salon-backend"
SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
BOOTSTRAP_REVISION = "salon-api-production-subpct-20261028"
IMAGE_ROOT = "asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@"
BOOTSTRAP_INDEX = IMAGE_ROOT + "sha256:ee92c2f588acbab37e905162cc8346d5eeea387046521db4c2c52eb717858f69"
BOOTSTRAP_PLATFORM = IMAGE_ROOT + "sha256:76ce6bec396732f0ac82957248547eead50f662bbc35fce3a42cbdfdb728a9d7"
BOOTSTRAP_MANIFEST = Path(__file__).resolve().parents[1] / "deployments/bootstrap-subpct-20261028.json"


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


def deployment_commit() -> str:
    # Once remote mutation begins, a newer push must not interrupt verification/rollback.
    return os.environ["GITHUB_SHA"] if DEPLOYMENT_STARTED else latest_main()


def latest_main() -> str:
    branch = github("branches/main")
    commit = os.environ["GITHUB_SHA"]
    require(branch["commit"]["sha"] == commit, "main advanced; run again for latest main")
    return commit


def bootstrap_enabled() -> bool:
    value = os.environ.get("BOOTSTRAP_BASELINE", "false")
    require(value in {"true", "false"}, "Invalid bootstrap selection")
    return value == "true"


def bootstrap_manifest() -> dict:
    data = json.loads(BOOTSTRAP_MANIFEST.read_text(encoding="utf-8"))
    require(data.get("schema_version") == 1 and data.get("source_kind") == "hybrid-overlay", "Invalid bootstrap attestation")
    require(data.get("revision") == BOOTSTRAP_REVISION and data.get("index_image") == BOOTSTRAP_INDEX
            and data.get("platform_image") == BOOTSTRAP_PLATFORM, "Bootstrap attestation target differs")
    require(data.get("project") == "saloon-505509" and data.get("region") == "asia-south1"
            and data.get("service") == "salon-api-production", "Bootstrap target differs")
    files = data.get("files", {})
    require(bool(files) and {"requirements.txt", "alembic.ini"} <= files.keys(), "Incomplete bootstrap inventory")
    for name, digest in files.items():
        parts = PurePosixPath(name).parts
        require(not PurePosixPath(name).is_absolute() and ".." not in parts
                and not any(part.startswith(".env") for part in parts), "Unsafe inventory path")
        require(name in {"requirements.txt", "alembic.ini"} or name.startswith(("app/", "migrations/")), "Unexpected inventory root")
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, "Invalid inventory hash")
    return data


def git_blob(commit: str, name: str) -> bytes:
    result = subprocess.run(["git", "show", commit + ":" + name], capture_output=True, check=False)
    require(result.returncode == 0, "Cannot read reviewed source blob")
    return result.stdout


def bootstrap_migration_changes(data: dict, commit: str) -> list[str]:
    # No migration allow-list or bypass: compare real packaged bytes to selected Git.
    current = command("git", "ls-tree", "-r", "--name-only", commit, "--", "backend/migrations").splitlines()
    expected = {"backend/" + name: digest for name, digest in data["files"].items()
                if name.startswith("migrations/") and "__pycache__" not in PurePosixPath(name).parts}
    runtime_files = [name for name in current if not name.startswith("backend/migrations/reviews/")]
    actual = {}
    for name in runtime_files:
        content = git_blob(commit, name)
        lf = content.replace(b"\r\n", b"\n")
        # Equivalent checkout line endings do not represent a schema change.
        actual[name] = {hashlib.sha256(blob).hexdigest() for blob in [content, lf, lf.replace(b"\n", b"\r\n")]}
    changes = {name for name in expected.keys() | actual.keys() if expected.get(name) not in actual.get(name, set())}
    # Historical review material is not packaged in the image. Pin its separate
    # Git reference; this is not a claim that the hybrid image equals that commit.
    review_reference = data["overlay_reference_commit"]
    require(SHA.fullmatch(review_reference) is not None, "Full review metadata reference required")
    changes.update(command("git", "diff", "--name-only", review_reference, commit,
                           "--", "backend/migrations/reviews").splitlines())
    return sorted(changes)


def platform_image(image: str, manifest: dict) -> str:
    require(image.count("@") == 1 and DIGEST.fullmatch(image.split("@", 1)[1]) is not None,
            "An immutable registry image is required")
    if "manifests" not in manifest:
        require(manifest.get("config") is not None and manifest.get("layers") is not None, "Invalid image manifest")
        return image
    matches = [row for row in manifest["manifests"] if row.get("platform", {}).get("os") == "linux"
               and row.get("platform", {}).get("architecture") == "amd64"]
    require(len(matches) == 1 and DIGEST.fullmatch(matches[0].get("digest", "")) is not None,
            "Registry must contain exactly one linux/amd64 image")
    return image.split("@", 1)[0] + "@" + matches[0]["digest"]


def image_inventory(image: str) -> dict[str, str]:
    container = command("docker", "create", "--network=none", image)
    require(re.fullmatch(r"[0-9a-f]{64}", container) is not None, "Invalid inspection container")
    files = {}
    try:
        for root in ["app", "migrations", "requirements.txt", "alembic.ini"]:
            result = subprocess.run(["docker", "cp", container + ":/app/" + root, "-"], capture_output=True, check=False)
            require(result.returncode == 0, "Cannot inspect selected image files")
            with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
                for entry in archive:
                    require(entry.isdir() or entry.isfile(), "Image inventory contains a link or special file")
                    if entry.isdir():
                        continue
                    parts = PurePosixPath(entry.name).parts
                    require(parts and parts[0] == root and ".." not in parts
                            and not any(part.startswith(".env") for part in parts), "Unsafe image inventory path")
                    require(entry.size <= 10_000_000 and entry.name not in files, "Invalid inventory member")
                    files[entry.name] = hashlib.sha256(archive.extractfile(entry).read()).hexdigest()
    finally:
        # Only our newly created stopped container; never delete images/revisions.
        subprocess.run(["docker", "rm", container], capture_output=True, check=False)
    return dict(sorted(files.items()))


def verify_bootstrap(data: dict, revision: str, image: str, files: dict[str, str]) -> None:
    require(revision == BOOTSTRAP_REVISION and image == BOOTSTRAP_PLATFORM, "Bootstrap allowed only for the pinned legacy release")
    require(data["files"] == files, "Serving image inventory differs from reviewed attestation")


def identity(*, automatic: bool = False) -> str:
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "Wrong repository")
    require(os.environ.get("GITHUB_REF") == "refs/heads/main", "Only main can deploy")
    require(os.environ.get("GITHUB_ACTOR_ID") == "172572480", "Only the approved actor can deploy")
    if automatic:
        require(os.environ.get("GITHUB_EVENT_NAME") == "push", "Automatic deployment requires main push")
        require(os.environ.get("AUTO_DEPLOY_ENABLED") == "true", "Automatic deployment is disabled")
        require(not bootstrap_enabled(), "Automatic bootstrap is forbidden")
    else:
        require(os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "Manual dispatch required")
        require(os.environ.get("APPROVE_DEPLOYMENT") == "true", "Explicit candidate approval required")
        require(os.environ.get("DEPLOY_CONFIRMATION") == "DEPLOY api.salones.in", "Exact typed confirmation required")
    commit = deployment_commit() if automatic else latest_main()
    require(os.environ.get("REQUESTED_COMMIT") == commit, "Supplied commit must equal workflow SHA")
    require(SHA.fullmatch(commit) is not None, "Full source SHA required")
    require(command("git", "rev-parse", "HEAD") == commit, "Checkout differs from selected commit")
    require(not command("git", "status", "--porcelain"), "Working tree must be clean")
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


def approved_schema_release(baseline: str, commit: str, changes: list[str]) -> dict:
    """Admit only the independently executed 0053-0055 delta, candidate-only."""
    message = "Migration differences require separate reviewed backup, target and approval; candidate refused"
    require(baseline == "6fefff404b148af4798105228418d96f03ad8e4c", message)
    raw = git_blob(commit, SCHEMA_RECEIPT_PATH)
    data = json.loads(raw)
    source = "4208c76d5dad71a923b8de2991ff5677e391b8e8"
    names = ["0053_salon_payout_requests", "0054_staff_earnings", "0055_feature_access"]
    expected_paths = {f"backend/migrations/{folder}/{name}.{extension}"
                      for name in names for folder, extension in [("sql", "sql"), ("versions", "py")]}
    require(data.get("schema_version") == 1 and data.get("status") == "PRODUCTION_SQL_VERIFIED"
            and data.get("repository") == REPOSITORY and data.get("baseline_commit") == baseline
            and data.get("sql_source_commit") == source and data.get("gcp_project") == "saloon-505509"
            and data.get("region") == "asia-south1" and data.get("service") == "salon-api-production"
            and data.get("database_project") == "wqjlgpnbiapcrlkxumcp"
            and data.get("release_mode") == "zero-traffic-candidate-only"
            and data.get("migration_target") == "0055_feature_access"
            and set(changes) == set(data.get("files", {})) == expected_paths, message)
    command("git", "merge-base", "--is-ancestor", source, commit)
    for path, digest in data["files"].items():
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None
                and hashlib.sha256(git_blob(source, path)).hexdigest() == digest
                and hashlib.sha256(git_blob(commit, path)).hexdigest() == digest, message)
    evidence = {
        "backend/docs/verification/PRODUCTION_0053_0055_EXECUTION_RESULT_2026-11-01.md",
        "backend/docs/verification/GATE_A_0053_0055_2026-11-01.md",
    }
    require(set(data.get("evidence", {})) == evidence, message)
    for path, digest in data["evidence"].items():
        require(hashlib.sha256(git_blob(commit, path)).hexdigest() == digest, message)
    return {"receipt_sha256": hashlib.sha256(raw).hexdigest(), "migration_target": data["migration_target"],
            "previous_revision": data["previous_revision"], "previous_image": data["previous_image"],
            "reviewed_migration_differences": sorted(changes), "requires_supervised_promotion": True}


def preflight(*, automatic: bool = False) -> str:
    global SCHEMA_COMPATIBILITY
    SCHEMA_COMPATIBILITY = None
    commit = identity(automatic=automatic)
    baseline = os.environ.get("BASELINE_COMMIT", "")
    if bootstrap_enabled():
        require(not baseline, "Bootstrap must not invent a Git baseline commit")
        require(os.environ.get("BOOTSTRAP_CONFIRMATION") == "BOOTSTRAP " + BOOTSTRAP_REVISION,
                "Exact bootstrap confirmation required")
        changes = bootstrap_migration_changes(bootstrap_manifest(), commit)
        if changes:
            print(json.dumps({"migration_differences": changes}))
        require(not changes, "Migration differences require separate reviewed backup, target and approval; bootstrap refused")
    else:
        require(not os.environ.get("BOOTSTRAP_CONFIRMATION"), "Unexpected bootstrap confirmation")
        require(SHA.fullmatch(baseline) is not None, "Full proven deployed source SHA required")
        require(command("git", "cat-file", "-t", baseline) == "commit", "Baseline commit missing")
        changes = command("git", "diff", "--name-only", baseline, commit, "--", "backend/migrations").splitlines()
        if changes:
            SCHEMA_COMPATIBILITY = approved_schema_release(baseline, commit, changes)
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


def candidate(*, automatic: bool = False, tested_bundle: Path | None = None,
              tested_registry: dict | None = None) -> dict:
    global DEPLOYMENT_STARTED
    if automatic:
        require((tested_bundle is not None) != (tested_registry is not None),
                "Automatic release requires exactly one exact CI-tested image source")
    commit = preflight(automatic=automatic)
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
    if SCHEMA_COMPATIBILITY is not None:
        require(previous == SCHEMA_COMPATIBILITY["previous_revision"]
                and previous_image == SCHEMA_COMPATIBILITY["previous_image"],
                "Approved schema compatibility baseline revision/image changed")
    registry = f"{region}-docker.pkg.dev"
    command("gcloud", "auth", "configure-docker", registry, "--quiet")
    command("docker", "pull", previous_image)
    previous_labels = json.loads(command("docker", "image", "inspect", previous_image))[0]["Config"].get("Labels") or {}
    if bootstrap_enabled():
        attestation = bootstrap_manifest()
        index = json.loads(command("docker", "buildx", "imagetools", "inspect", BOOTSTRAP_INDEX, "--raw"))
        require(platform_image(BOOTSTRAP_INDEX, index) == previous_image, "Serving platform is not in the pinned release index")
        verify_bootstrap(attestation, previous, previous_image, image_inventory(previous_image))
    else:
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
    ci_metadata = None
    if automatic and tested_registry is not None:
        import ci_registry_image
        ci_metadata = ci_registry_image.inspect_verified(tested_registry)
        immutable = ci_metadata["image"]
        index_image = immutable
        digest = immutable.split("@", 1)[1]
    elif automatic:
        require(tested_bundle is not None, "Automatic release requires the exact CI-tested image")
        import ci_image_bundle
        ci_metadata = ci_image_bundle.load(tested_bundle)
        command("docker", "tag", ci_metadata["image_ref"], image)
    else:
        # Archive tracked commit contents: ignored/untracked files cannot enter the image.
        archive = subprocess.run(["git", "archive", "--format=tar", commit, "backend"], capture_output=True, check=False)
        require(archive.returncode == 0, "Cannot archive reviewed source")
        with tempfile.TemporaryDirectory(prefix="salon-reviewed-") as directory:
            with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as source:
                source.extractall(directory, filter="data")
            command("docker", "build", "--pull", "--platform=linux/amd64", "--build-arg", f"SOURCE_COMMIT={commit}", "--label", f"org.opencontainers.image.revision={commit}",
                    "--label", f"org.opencontainers.image.source=https://github.com/{REPOSITORY}", "--tag", image,
                    str(Path(directory) / "backend"))
        command("bash", "backend/scripts/check-container.sh", image, commit)
    latest_main()
    if tested_registry is None:
        if automatic:
            DEPLOYMENT_STARTED = True
        command("docker", "push", image)
        registry_image = cloud("artifacts", "docker", "images", "describe", image)
        digest = registry_image["image_summary"]["digest"]
        require(DIGEST.fullmatch(digest) is not None, "Invalid image digest")
        immutable = image.rsplit(":", 1)[0] + "@" + digest
        index_image = immutable
        index = json.loads(command("docker", "buildx", "imagetools", "inspect", index_image, "--raw"))
        immutable = platform_image(index_image, index)
    if ci_metadata is not None:
        platform_manifest = json.loads(command("docker", "buildx", "imagetools", "inspect", immutable, "--raw"))
        require(platform_manifest.get("config", {}).get("digest") == ci_metadata["config_digest"], "Registry image differs from tested CI config")
    # Inspect the registry digest, not just a local tag, to verify source identity.
    command("docker", "pull", immutable)
    registry_state = json.loads(command("docker", "image", "inspect", immutable))[0]
    if ci_metadata is not None:
        require(registry_state.get("RootFS", {}).get("Layers") == ci_metadata["layer_diff_ids"], "Registry layers differ from CI")
    labels = registry_state["Config"].get("Labels") or {}
    require(labels.get("org.opencontainers.image.revision") == commit, "Image source SHA mismatch")
    require(labels.get("org.opencontainers.image.source") == f"https://github.com/{REPOSITORY}", "Image repository mismatch")
    deployment_commit() if automatic else latest_main()
    require(before["metadata"]["resourceVersion"] == describe()["metadata"]["resourceVersion"],
            "Service changed during build; inspect and dispatch again")
    receipt = {"status": "STARTED", "commit": commit, "image": immutable, "digest": immutable.split("@", 1)[1],
               "index_image": index_image, "index_digest": digest, "baseline_kind": "bootstrap-attestation" if bootstrap_enabled() else "git-commit",
               "previous_revision": previous, "previous_image": previous_image, "candidate_revision": service + "-" + suffix,
               "migration_differences": [], "production_traffic_promoted": False, "smoke": {},
               "deployment_started_at_utc": datetime.now(UTC).isoformat(),
               "migration_target": "unchanged-from-proven-baseline:" + os.environ.get("BASELINE_COMMIT", "bootstrap"),
               "ci_artifact_id": os.environ.get("CI_IMAGE_ARTIFACT_ID"),
               "ci_artifact_digest": os.environ.get("CI_IMAGE_ARTIFACT_DIGEST"),
               "worker_coverage": "API image only; no worker deployment or execution; see CI_CD.md",
               "rollback_command": f"gcloud run services update-traffic {service} --project={project} --region={region} --to-revisions={previous}=100"}
    if SCHEMA_COMPATIBILITY is not None:
        receipt["schema_compatibility"] = copy.deepcopy(SCHEMA_COMPATIBILITY)
        receipt["requires_supervised_promotion"] = True
        receipt["migration_target"] = SCHEMA_COMPATIBILITY["migration_target"]
    if tested_registry is not None:
        receipt["ci_registry_provenance"] = ci_metadata
    path = Path("candidate-result.json")
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    try:
        if automatic and tested_registry is not None:
            latest_main()
            DEPLOYMENT_STARTED = True
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
        for endpoint in ["/health/ready", "/version", "/health", "/health/db", "/health/redis", "/docs", "/openapi.json"]:
            try:
                with urllib.request.urlopen(url + endpoint, timeout=60) as response:
                    body = response.read()
                    receipt["smoke"][endpoint] = {"status": response.status, "pass": response.status == 200}
                    if endpoint == "/version":
                        identity = json.loads(body)
                        require(identity.get("commit_sha") == commit and identity.get("version") == "0.1.0", "Candidate API commit identity differs")
                        receipt["api_identity"] = identity
                    if endpoint == "/health/ready":
                        require(json.loads(body).get("status") == "ok", "Candidate readiness body differs")
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
        deployment_commit() if automatic else latest_main()
        final = describe()
        verify_unchanged(before, final)
        receipt["verified_resource_version"] = final["metadata"]["resourceVersion"]
        receipt["status"] = "PASS_CANDIDATE_VERIFIED" if automatic else "PASS_AWAITING_EXPLICIT_TRAFFIC_APPROVAL"
    except (RuntimeError, OSError, ValueError, KeyError, StopIteration):
        receipt["status"] = "STOP_NO_TRAFFIC_PROMOTION"
        raise
    finally:
        path.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            summary = {"commit": commit, "actor": os.environ.get("GITHUB_ACTOR"),
                       "actor_id": os.environ["GITHUB_ACTOR_ID"], "target_project": project,
                       "target_service": service, "image_digest": receipt["digest"],
                       "current_serving_revision": previous, "rollback_revision": previous,
                       "confirmation": os.environ.get("DEPLOY_CONFIRMATION", "AUTOMATIC MAIN PUSH"), "status": receipt["status"]}
            with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as output:
                output.write("```json\n" + json.dumps(summary, indent=2) + "\n```\n")

    return receipt


if __name__ == "__main__":
    try:
        require(len(sys.argv) == 2 and sys.argv[1] in {"preflight", "candidate"}, "Expected preflight or candidate")
        preflight() if sys.argv[1] == "preflight" else candidate()
    except (RuntimeError, OSError, ValueError, KeyError, StopIteration) as error:
        # RuntimeError messages are our fixed strings; other exceptions may contain credentials.
        print(str(error) if type(error) is RuntimeError else f"Stopped: {type(error).__name__}; diagnostics suppressed", file=sys.stderr)
        sys.exit(1)
