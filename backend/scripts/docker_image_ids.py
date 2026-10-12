"""Record equivalent classic/containerd IDs from a tested single-image Docker archive."""

import hashlib
import json
import sys
import tarfile


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def image_ids(archive_path: str, image_ref: str, tested_id: str) -> list[str]:
    with tarfile.open(archive_path) as archive:
        def read(name: str) -> bytes:
            entry = archive.extractfile(name)
            if entry is None:
                raise ValueError(f"Missing image metadata: {name}")
            return entry.read()

        saved_images = json.loads(read("manifest.json"))
        if len(saved_images) != 1 or saved_images[0].get("RepoTags") != [image_ref]:
            raise ValueError("Archive must contain only the tested image tag")
        config_id = digest(read(saved_images[0]["Config"]))
        identities = {config_id}
        try:
            index = json.loads(read("index.json"))
        except KeyError:
            index = {"manifests": []}  # Legacy Docker save archives have no OCI index.
        for descriptor in index["manifests"]:
            manifest_id = descriptor["digest"]
            payload = read("blobs/" + manifest_id.replace(":", "/", 1))
            if digest(payload) != manifest_id:
                raise ValueError("Archive manifest digest mismatch")
            manifest = json.loads(payload)
            if manifest.get("config", {}).get("digest") != config_id:
                raise ValueError("Archive manifest does not reference the tested configuration")
            identities.add(manifest_id)
        if tested_id not in identities:
            raise ValueError("Archive does not match the image tested in CI")
        return sorted(identities)


if __name__ == "__main__":
    print("\n".join(image_ids(*sys.argv[1:])))
