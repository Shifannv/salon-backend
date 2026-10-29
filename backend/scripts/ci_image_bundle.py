"""Bind the image actually tested by CI to its archive, commit and workflow attempt.

The release path loads/retags this image; it never rebuilds it. Network operations
here run only in a future admitted GitHub release, never during local validation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import cloud_run_candidate as release
from docker_image_ids import image_ids

MAX_ARCHIVE = 3 * 1024**3


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def artifact_name() -> str:
    return "ci-image-" + "-".join(os.environ[key] for key in ["GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"])


def archive_config(path: Path) -> tuple[str, dict]:
    with tarfile.open(path) as archive:
        manifest = json.load(archive.extractfile("manifest.json"))
        release.require(len(manifest) == 1, "Expected one tested image")
        raw = archive.extractfile(manifest[0]["Config"]).read()
    return "sha256:" + hashlib.sha256(raw).hexdigest(), json.loads(raw)


def validate(directory: Path) -> dict:
    metadata = json.loads((directory / "provenance.json").read_text())
    expected = {"commit": os.environ["GITHUB_SHA"], "repository": release.REPOSITORY,
                "run_id": os.environ["GITHUB_RUN_ID"], "attempt": os.environ["GITHUB_RUN_ATTEMPT"]}
    release.require(metadata.get("schema_version") == 1 and all(metadata.get(k) == v for k, v in expected.items()),
                    "CI provenance differs from selected source/run/attempt")
    path = directory / "image.tar"
    release.require(path.stat().st_size <= MAX_ARCHIVE and sha256(path) == metadata["archive_sha256"], "CI image archive changed")
    identities = image_ids(str(path), metadata["image_ref"], metadata["tested_image_id"])
    config_digest, config = archive_config(path)
    release.require(identities == metadata["verified_image_ids"] and config_digest == metadata["config_digest"], "Tested image identity changed")
    labels = config.get("config", {}).get("Labels") or {}
    release.require(labels.get("org.opencontainers.image.revision") == expected["commit"]
                    and labels.get("org.opencontainers.image.source") == "https://github.com/" + release.REPOSITORY,
                    "CI image source labels differ")
    release.require(config.get("rootfs", {}).get("diff_ids") == metadata["layer_diff_ids"], "CI image layers changed")
    return metadata


def create(image: str, directory: Path) -> None:
    release.require(release.SHA.fullmatch(os.environ["GITHUB_SHA"]) is not None, "Expected full source SHA")
    directory.mkdir(parents=True, exist_ok=False)
    tested_id = json.loads(release.command("docker", "image", "inspect", image))[0]["Id"]
    path = directory / "image.tar"
    release.command("docker", "image", "save", "--output", str(path), image)
    config_digest, config = archive_config(path)
    metadata = {"schema_version": 1, "repository": release.REPOSITORY, "commit": os.environ["GITHUB_SHA"],
                "run_id": os.environ["GITHUB_RUN_ID"], "attempt": os.environ["GITHUB_RUN_ATTEMPT"],
                "image_ref": image, "tested_image_id": tested_id, "config_digest": config_digest,
                "layer_diff_ids": config["rootfs"]["diff_ids"], "archive_sha256": sha256(path),
                "verified_image_ids": image_ids(str(path), image, tested_id)}
    (directory / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    validate(directory)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def download(directory: Path) -> dict:
    """Verify artifact ownership/digest; never forward GitHub auth to signed storage."""
    artifact_id = os.environ.get("CI_IMAGE_ARTIFACT_ID", "")
    digest = os.environ.get("CI_IMAGE_ARTIFACT_DIGEST", "").removeprefix("sha256:")
    release.require(artifact_id.isdigit() and re.fullmatch(r"[0-9a-f]{64}", digest), "Missing immutable CI artifact output")
    artifact = release.github("actions/artifacts/" + artifact_id)
    release.require(not artifact.get("expired") and artifact.get("name") == artifact_name()
                    and str(artifact.get("workflow_run", {}).get("id")) == os.environ["GITHUB_RUN_ID"]
                    and artifact.get("workflow_run", {}).get("head_sha") == os.environ["GITHUB_SHA"]
                    and artifact.get("digest") == "sha256:" + digest, "Artifact belongs to a different run/source or digest")
    request = urllib.request.Request("https://api.github.com/repos/" + release.REPOSITORY
                                     + "/actions/artifacts/" + artifact_id + "/zip",
                                     headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"]})
    try:
        urllib.request.build_opener(NoRedirect()).open(request, timeout=30)
        raise RuntimeError("Expected a signed artifact download redirect")
    except urllib.error.HTTPError as error:
        release.require(error.code == 302, "Artifact download refused; response suppressed")
        url = error.headers.get("Location", "")
    parsed = urllib.parse.urlsplit(url)
    release.require(parsed.scheme == "https" and parsed.hostname is not None
                    and parsed.hostname.endswith((".blob.core.windows.net", ".githubusercontent.com")), "Unexpected artifact storage")
    directory.mkdir(parents=True, exist_ok=False)
    archive_path = directory / "artifact.zip"
    with urllib.request.urlopen(url, timeout=60) as response, archive_path.open("wb") as output:
        size = 0
        while chunk := response.read(1024**2):
            size += len(chunk)
            release.require(size <= MAX_ARCHIVE, "Artifact too large")
            output.write(chunk)
    release.require(sha256(archive_path) == digest, "Downloaded artifact digest differs")
    with zipfile.ZipFile(archive_path) as archive:
        release.require(set(archive.namelist()) == {"image.tar", "provenance.json"} and len(archive.infolist()) == 2,
                        "Unexpected files in CI artifact")
        for entry in archive.infolist():
            release.require(entry.file_size <= (MAX_ARCHIVE if entry.filename == "image.tar" else 1024**2), "Artifact member too large")
            with archive.open(entry) as source, (directory / entry.filename).open("wb") as output:
                while chunk := source.read(1024**2):
                    output.write(chunk)
    return validate(directory)


def load(directory: Path) -> dict:
    metadata = validate(directory)
    release.command("docker", "load", "--input", str(directory / "image.tar"))
    state = json.loads(release.command("docker", "image", "inspect", metadata["image_ref"]))[0]
    release.require(state["Id"] in metadata["verified_image_ids"]
                    and state.get("RootFS", {}).get("Layers") == metadata["layer_diff_ids"], "Loaded image differs from CI")
    return metadata


if __name__ == "__main__":
    try:
        release.require(len(sys.argv) == 4 and sys.argv[1] == "create", "Expected create IMAGE OUTPUT_DIRECTORY")
        create(sys.argv[2], Path(sys.argv[3]))
    except Exception as error:
        print(str(error) if type(error) is RuntimeError else "CI image verification failed; details suppressed", file=sys.stderr)
        sys.exit(1)
