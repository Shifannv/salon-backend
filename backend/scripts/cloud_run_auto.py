"""Main-push release: verified candidate, traffic-only promotion and health rollback.

No migration execution, bootstrap bypass, application secret access or worker changes.
Cloud Run metadata and short-lived authentication remain in process memory only.
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import cloud_run_candidate as release

RESOURCE = "projects/saloon-505509/locations/asia-south1/services/salon-api-production"
API = "https://run.googleapis.com/v2/"
REVISION = "TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION"
SMOKES = {"/health/ready", "/version", "/health", "/health/db", "/health/redis", "/docs", "/openapi.json"}
PUBLIC_CHECKS = [(host, path) for host in ("https://api.salones.in",)
                 for path in ("/health/ready", "/version", "/health", "/health/db", "/health/redis")]


def cloud(*args: str) -> dict:
    return json.loads(release.command("gcloud", *args, "--project=saloon-505509", "--format=json"))


def describe() -> dict:
    return cloud("run", "services", "describe", "salon-api-production", "--region=asia-south1")


def api(method: str, resource: str, body: dict | None = None) -> dict:
    release.require(resource == RESOURCE, "Unexpected API target")
    token = release.command("gcloud", "auth", "print-access-token")
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(API + resource + ("?updateMask=traffic" if method == "PATCH" else ""),
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                                     data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Cloud Run API refused operation (HTTP {error.code}); response suppressed") from None


def resolved(service: dict) -> list[tuple[str, int]]:
    return sorted((row["revision"], row["percent"]) for row in service.get("trafficStatuses", []) if row.get("percent"))


def desired(service: dict) -> list[tuple[str, int]]:
    rows = [row for row in service.get("traffic", []) if row.get("percent")]
    release.require(all(row.get("type") == REVISION and row.get("revision") for row in rows), "Explicit revision traffic required")
    return sorted((row["revision"], row["percent"]) for row in rows)


def targets(service: dict, revision: str) -> list[dict]:
    release.require(re.fullmatch(r"salon-api-production-[a-z0-9-]+", revision), "Invalid revision")
    tagged = []
    for row in service.get("traffic", []):
        if row.get("tag"):
            release.require(row.get("type") == REVISION and row.get("revision"), "Unresolved tag target")
            tagged.append({"type": REVISION, "revision": row["revision"], "tag": row["tag"], "percent": 0})
    return [*tagged, {"type": REVISION, "revision": revision, "percent": 100}]


def target_identity(rows: list[dict]) -> list[tuple]:
    return sorted((row.get("type"), row.get("revision"), row.get("tag", ""), row.get("percent", 0)) for row in rows)


def patch_traffic(service: dict, traffic: list[dict]) -> None:
    release.require(service.get("name") == RESOURCE and bool(service.get("etag")), "Missing service identity/etag")
    operation = api("PATCH", RESOURCE, {"name": RESOURCE, "etag": service["etag"], "traffic": traffic})
    release.require(not operation.get("error"), "Traffic update failed; response suppressed")
    deadline = time.monotonic() + 300
    expected = sorted((row["revision"], row["percent"]) for row in traffic if row.get("percent"))
    while True:
        # Only run.services.get is needed; do not require location-wide operations.get.
        current = api("GET", RESOURCE)
        release.require(configuration(current) == configuration(service), "Configuration changed during traffic update")
        if (not current.get("reconciling") and target_identity(current.get("traffic", [])) == target_identity(traffic)
                and desired(current) == resolved(current) == expected):
            return
        release.require(current.get("terminalCondition", {}).get("state") != "CONDITION_FAILED", "Traffic reconciliation failed")
        release.require(time.monotonic() < deadline, "Traffic update did not finish; inspect retained receipt")
        time.sleep(3)


def configuration(service: dict) -> dict:
    # Ignore server-reconciled output fields; retain every configuration-bearing field.
    output = {"etag", "generation", "observedGeneration", "updateTime", "reconciling", "terminalCondition",
              "conditions", "traffic", "trafficStatuses", "latestReadyRevision", "latestCreatedRevision", "urls", "lastModifier"}
    return {key: value for key, value in service.items() if key not in output}


def public_health(*, expected_commit: str | None = None) -> dict:
    checks = {}
    for host, path in PUBLIC_CHECKS:
        try:
            with urllib.request.urlopen(host + path, timeout=20) as response:
                passed = response.status == 200
                if path == "/version":
                    body = json.load(response)
                    passed = passed and expected_commit is not None and body.get("commit_sha") == expected_commit and body.get("version") == "0.1.0"
                elif path == "/health/ready":
                    passed = passed and json.load(response).get("status") == "ok"
                checks[host + path] = {"status": response.status, "pass": passed}
        except urllib.error.HTTPError as error:
            checks[host + path] = {"status": error.code, "pass": False}
        except (OSError, ValueError) as error:
            checks[host + path] = {"error_type": type(error).__name__, "pass": False}
        if not checks[host + path]["pass"]:
            break  # Roll back immediately; do not wait for five more potentially slow probes.
    return checks


def all_healthy(checks: dict) -> bool:
    return set(checks) == {host + path for host, path in PUBLIC_CHECKS} and all(row["pass"] for row in checks.values())


def baseline() -> str:
    service = describe()
    serving = release.traffic(service)
    release.require(len(serving) == 1 and serving[0][1] == 100, "One previous 100% revision required")
    revision = cloud("run", "revisions", "describe", serving[0][0], "--region=asia-south1")
    image = revision["status"]["imageDigest"]
    release.require(image.startswith(release.IMAGE_ROOT) and release.DIGEST.fullmatch(image.split("@", 1)[1]),
                    "Serving image must use the existing immutable registry")
    release.command("gcloud", "auth", "configure-docker", "asia-south1-docker.pkg.dev", "--quiet")
    release.command("docker", "pull", image)
    labels = json.loads(release.command("docker", "image", "inspect", image))[0]["Config"].get("Labels") or {}
    commit = labels.get("org.opencontainers.image.revision", "")
    release.require(release.SHA.fullmatch(commit) is not None and labels.get("org.opencontainers.image.source")
                    == "https://github.com/" + release.REPOSITORY,
                    "Serving image lacks proven Git source; complete separately reviewed bootstrap first")
    release.command("git", "merge-base", "--is-ancestor", commit, os.environ["GITHUB_SHA"])
    return commit


def verified_receipt(receipt: dict) -> None:
    release.require(receipt.get("status") == "PASS_CANDIDATE_VERIFIED" and receipt.get("ready") is True,
                    "Only a verified automatic candidate may promote")
    release.require(receipt.get("commit") == release.deployment_commit(), "Candidate source differs from latest main")
    release.require(receipt.get("migration_differences") == [], "Migration differences forbid promotion")
    smoke = receipt.get("smoke", {})
    release.require(set(smoke) == SMOKES and all(row.get("pass") is True for row in smoke.values()), "Incomplete candidate smoke")
    release.require(receipt.get("api_identity", {}).get("commit_sha") == receipt["commit"], "API identity not verified")
    release.require(bool(receipt.get("openapi_sha256")) and receipt.get("openapi_contract_checks")
                    == "Expected routes and existing paths/operations/schema fields preserved", "Contract not verified")
    image = receipt.get("image", "")
    release.require(image.startswith(release.IMAGE_ROOT) and image == release.IMAGE_ROOT + receipt.get("digest", "")
                    and release.DIGEST.fullmatch(receipt.get("digest", "")), "Invalid candidate digest")
    state = describe()
    release.require(state["metadata"]["resourceVersion"] == receipt.get("verified_resource_version"),
                    "Service changed after candidate checks")
    release.require(release.traffic(state) == [(receipt["previous_revision"], 100)], "Serving revision changed")
    revision = cloud("run", "revisions", "describe", receipt["candidate_revision"], "--region=asia-south1")
    release.require(revision["status"]["imageDigest"] == image and any(row.get("type") == "Ready"
                    and row.get("status") == "True" for row in revision["status"]["conditions"]), "Candidate readiness/digest changed")


def promote(receipt: dict) -> None:
    release.require(not receipt.get("requires_supervised_promotion"),
                    "Reviewed schema candidate requires separate explicit traffic approval")
    release.identity(automatic=True)
    verified_receipt(receipt)
    before = api("GET", RESOURCE)
    previous, candidate = receipt["previous_revision"], receipt["candidate_revision"]
    release.require(desired(before) == resolved(before) == [(previous, 100)] and not before.get("reconciling"),
                    "Production traffic is not settled on previous revision")
    # Bridge the v1 candidate receipt to the v2 etag without accepting an intervening edit.
    release.require(describe()["metadata"]["resourceVersion"] == receipt["verified_resource_version"], "Service changed")
    release.deployment_commit()
    promoted_targets = targets(before, candidate)
    receipt["status"] = "PROMOTION_REQUESTED"
    receipt["promotion_attempted"] = True
    try:
        patch_traffic(before, promoted_targets)
        current = api("GET", RESOURCE)
        release.require(desired(current) == resolved(current) == [(candidate, 100)], "Candidate traffic did not settle")
        receipt["production_traffic_promoted"] = True
        release.require(configuration(before) == configuration(current), "Runtime configuration changed during promotion")
        checks = public_health(expected_commit=receipt["commit"])
        receipt["production_smoke"] = checks
        release.require(all_healthy(checks), "Production health failed; rollback required")
        receipt["status"] = "PASS_PRODUCTION_PROMOTED"
    except Exception:
        # A timeout may occur after the patch was accepted. Inspect desired state, not just response success.
        receipt["status"] = "ROLLBACK_REQUIRED"
        try:
            current = api("GET", RESOURCE)
            if desired(current) == [(previous, 100)]:
                release.require(resolved(current) == [(previous, 100)], "Previous traffic has not settled")
                receipt["production_traffic_promoted"] = False
                receipt["status"] = "STOP_PREVIOUS_REVISION_RETAINED"
            else:
                release.require(target_identity(current.get("traffic", [])) == target_identity(promoted_targets)
                                and configuration(current) == configuration(before),
                                "Concurrent external edit; refusing to overwrite it during rollback")
                patch_traffic(current, copy.deepcopy(before["traffic"]))
                restored = api("GET", RESOURCE)
                release.require(desired(restored) == resolved(restored) == [(previous, 100)], "Rollback traffic did not settle")
                receipt["production_traffic_promoted"] = False
                receipt["rollback_smoke"] = public_health(expected_commit=receipt.get("previous_commit"))
                receipt["status"] = "ROLLED_BACK" if all_healthy(receipt["rollback_smoke"]) else "ROLLBACK_HEALTH_FAILED"
        except Exception:
            receipt["production_traffic_promoted"] = None
            receipt["status"] = "ROLLBACK_FAILED_OPERATOR_ACTION_REQUIRED"
            raise
        raise


def output(name: str, value: str) -> None:
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
            stream.write(name + "=" + value + "\n")


def gate() -> bool:
    checks = {
        "auto_deploy_enabled": os.environ.get("AUTO_DEPLOY_ENABLED") == "true",
        "repository": os.environ.get("GITHUB_REPOSITORY") == release.REPOSITORY,
        "event_push": os.environ.get("GITHUB_EVENT_NAME") == "push",
        "ref_main": os.environ.get("GITHUB_REF") == "refs/heads/main",
        "actor_id": os.environ.get("GITHUB_ACTOR_ID") == "172572480",
    }
    enabled = all(checks.values())
    failed = [k for k, v in checks.items() if not v]
    print(f"Deployment gate: enabled={str(enabled).lower()}; blocked_by={','.join(failed) or 'none'}")
    output("enabled", str(enabled).lower())
    if not enabled:
        print("Automatic deployment disabled or context ineligible; no cloud authentication or deployment.")
    return enabled


def guard() -> bool:
    if not gate():
        output("eligible", "false")
        return False
    try:
        commit = release.identity(automatic=True)
    except RuntimeError as error:
        if str(error) != "main advanced; run again for latest main":
            raise
        output("eligible", "false")
        print("SKIPPED_SUPERSEDED: newer main exists; production untouched.")
        return False
    release.require(os.environ.get("GITHUB_TRIGGERING_ACTOR", os.environ.get("GITHUB_ACTOR"))
                    == os.environ.get("GITHUB_ACTOR"), "Only original approved actor may retry")
    pulls = release.github("commits/" + commit + "/pulls?per_page=100")
    release.require(isinstance(pulls, list) and any(pr.get("merged_at")
                    and pr.get("merge_commit_sha") == commit and pr.get("base", {}).get("ref") == "main"
                    and pr.get("base", {}).get("repo", {}).get("full_name") == release.REPOSITORY for pr in pulls),
                    "Selected main commit must be the exact result of a merged PR")
    output("eligible", "true")
    return True


def deploy() -> None:
    if not guard():
        return
    registry = os.environ.get("REGISTRY_IMAGE_METADATA", "")
    if registry:
        import ci_registry_image
        image_source = {"tested_registry": ci_registry_image.validate(json.loads(registry))}
    else:
        import ci_image_bundle
        bundle = Path(".release-image")
        ci_image_bundle.download(bundle)
        image_source = {"tested_bundle": bundle}
    os.environ["BASELINE_COMMIT"] = baseline()
    previous_health = public_health(expected_commit=os.environ["BASELINE_COMMIT"])
    release.require(all_healthy(previous_health), "Previous revision health/identity is not established")
    receipt = release.candidate(automatic=True, **image_source)
    receipt["previous_commit"] = os.environ["BASELINE_COMMIT"]
    receipt["previous_health"] = previous_health
    try:
        if receipt.get("requires_supervised_promotion") is True:
            receipt["status"] = "PASS_AWAITING_EXPLICIT_TRAFFIC_APPROVAL"
            print("Reviewed schema candidate verified; production traffic unchanged. Explicit promotion approval required.")
        else:
            promote(receipt)
    finally:
        receipt["deployment_finished_at_utc"] = datetime.now(UTC).isoformat()
        Path("candidate-result.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as output:
                output.write("\nAutomatic release result:\n```json\n" + json.dumps(receipt, indent=2) + "\n```\n")


if __name__ == "__main__":
    try:
        release.require(len(sys.argv) == 2 and sys.argv[1] in {"gate", "guard", "deploy"}, "Expected guard or deploy")
        gate() if sys.argv[1] == "gate" else guard() if sys.argv[1] == "guard" else deploy()
    except Exception as error:
        print(str(error) if type(error) is RuntimeError else f"Stopped: {type(error).__name__}; details suppressed", file=sys.stderr)
        sys.exit(1)
