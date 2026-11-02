"""Publish the CI-tested image once; consume its immutable digest without artifacts."""
from __future__ import annotations

import json
import os
import sys

import cloud_run_candidate as release


def validate(metadata: dict) -> dict:
    expected = {"repository": release.REPOSITORY, "commit": os.environ["GITHUB_SHA"],
                "run_id": os.environ["GITHUB_RUN_ID"], "attempt": os.environ["GITHUB_RUN_ATTEMPT"]}
    release.require(metadata.get("schema_version") == 1
                    and all(metadata.get(key) == value for key, value in expected.items()),
                    "Registry CI provenance differs from selected source/run/attempt")
    image = metadata.get("image", "")
    release.require(image.startswith(release.IMAGE_ROOT)
                    and release.DIGEST.fullmatch(image.removeprefix(release.IMAGE_ROOT)) is not None,
                    "Registry CI image must use the exact immutable production repository")
    layers = metadata.get("layer_diff_ids")
    release.require(isinstance(layers, list) and bool(layers)
                    and all(isinstance(value, str) and release.DIGEST.fullmatch(value) for value in layers)
                    and release.DIGEST.fullmatch(metadata.get("config_digest", "")),
                    "Registry CI image identities are missing or invalid")
    return metadata


def inspect_verified(metadata: dict) -> dict:
    validate(metadata)
    image = metadata["image"]
    release.command("docker", "pull", image)
    state = json.loads(release.command("docker", "image", "inspect", image))[0]
    manifest = json.loads(release.command("docker", "buildx", "imagetools", "inspect", image, "--raw"))
    labels = state["Config"].get("Labels") or {}
    release.require(manifest.get("config", {}).get("digest") == metadata["config_digest"]
                    and state.get("RootFS", {}).get("Layers") == metadata["layer_diff_ids"]
                    and labels.get("org.opencontainers.image.revision") == metadata["commit"]
                    and labels.get("org.opencontainers.image.source") == "https://github.com/" + release.REPOSITORY,
                    "Published registry image differs from the CI-tested image")
    return metadata


def publish(image: str) -> dict:
    commit = release.identity(automatic=True)
    run, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
    release.require(run.isdigit() and attempt.isdigit()
                    and image == f"salon-platform-api:sha-{commit}-{run}-{attempt}",
                    "Unexpected CI-tested image reference")
    tested = json.loads(release.command("docker", "image", "inspect", image))[0]
    labels = tested["Config"].get("Labels") or {}
    release.require(labels.get("org.opencontainers.image.revision") == commit
                    and labels.get("org.opencontainers.image.source") == "https://github.com/" + release.REPOSITORY,
                    "CI-tested image source labels differ")
    target = release.IMAGE_ROOT.removesuffix("@") + f":{commit}-{run}-{attempt}"
    release.command("gcloud", "auth", "configure-docker", "asia-south1-docker.pkg.dev", "--quiet")
    release.command("docker", "tag", image, target)
    release.latest_main()
    release.command("docker", "push", target)
    published = json.loads(release.command("gcloud", "artifacts", "docker", "images", "describe", target,
                                           "--project=saloon-505509", "--format=json"))
    digest = published["image_summary"]["digest"]
    release.require(release.DIGEST.fullmatch(digest), "Invalid published registry digest")
    index_image = release.IMAGE_ROOT + digest
    index = json.loads(release.command("docker", "buildx", "imagetools", "inspect", index_image, "--raw"))
    immutable = release.platform_image(index_image, index)
    metadata = {"schema_version": 1, "repository": release.REPOSITORY, "commit": commit,
                "run_id": run, "attempt": attempt, "image": immutable,
                "config_digest": tested["Id"], "layer_diff_ids": tested["RootFS"]["Layers"]}
    inspect_verified(metadata)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write("registry_image_metadata=" + json.dumps(metadata, separators=(",", ":")) + "\n")
    return metadata


if __name__ == "__main__":
    try:
        release.require(len(sys.argv) == 3 and sys.argv[1] == "publish", "Expected publish IMAGE")
        print(json.dumps(publish(sys.argv[2])))
    except Exception as error:
        print(str(error) if type(error) is RuntimeError else "Registry CI image verification failed; diagnostics suppressed", file=sys.stderr)
        sys.exit(1)
