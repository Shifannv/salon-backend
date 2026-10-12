"""Verify image identity across Docker classic and containerd image stores."""

import io
import json
import tarfile

import pytest

from scripts.docker_image_ids import digest, image_ids


def archive_fixture(tmp_path, *, legacy=False, wrong_config=False, corrupt_manifest=False):
    config = b'{"architecture":"amd64","os":"linux","rootfs":{"diff_ids":[]}}'
    config_id = digest(config)
    manifest = json.dumps({"config": {"digest": "sha256:wrong" if wrong_config else config_id}}).encode()
    manifest_id = digest(manifest)
    config_path = "blobs/" + config_id.replace(":", "/")
    entries = {
        "manifest.json": json.dumps([{"Config": config_path, "RepoTags": ["test:release"]}]).encode(),
        config_path: config,
    }
    if not legacy:
        entries["index.json"] = json.dumps({"manifests": [{"digest": manifest_id}]}).encode()
        entries["blobs/" + manifest_id.replace(":", "/")] = b"corrupt" if corrupt_manifest else manifest
    path = tmp_path / "image.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        for name, content in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return str(path), config_id, manifest_id


@pytest.mark.parametrize("store", ["classic", "containerd"])
def test_accepts_equivalent_ids_from_verified_archive(tmp_path, store):
    path, config_id, manifest_id = archive_fixture(tmp_path)
    tested_id = config_id if store == "classic" else manifest_id
    assert set(image_ids(path, "test:release", tested_id)) == {config_id, manifest_id}


def test_legacy_archive_keeps_config_id(tmp_path):
    path, config_id, _ = archive_fixture(tmp_path, legacy=True)
    assert image_ids(path, "test:release", config_id) == [config_id]


@pytest.mark.parametrize("issue", ["wrong_config", "corrupt_manifest", "wrong_tag", "wrong_image"])
def test_rejects_unrelated_or_corrupt_metadata(tmp_path, issue):
    path, config_id, _ = archive_fixture(
        tmp_path, wrong_config=issue == "wrong_config", corrupt_manifest=issue == "corrupt_manifest"
    )
    with pytest.raises(ValueError):
        image_ids(
            path,
            "other:tag" if issue == "wrong_tag" else "test:release",
            "sha256:other" if issue == "wrong_image" else config_id,
        )
