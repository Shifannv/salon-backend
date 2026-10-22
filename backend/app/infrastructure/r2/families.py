"""Immutable WebP families, with signed manifests and compatibility images.

An alias is an image, never a JSON file or redirect: old clients can continue to
display the URL issued before the source bytes (and their hash) are known.
"""

import base64
import hashlib
import hmac
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.application.ports.image_processor import (
    IMAGE_POLICY_VERSION,
    IMAGE_VARIANT_POLICIES,
    ProcessedImageFamily,
)
from app.core.exceptions import ValidationError

POLICY_VERSION = IMAGE_POLICY_VERSION
POLICIES = {category: {name: (policy.max_dimension, policy.max_bytes) for name, policy in policies}
            for category, policies in IMAGE_VARIANT_POLICIES.items()}
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def namespace_for(path: str) -> tuple[str, str]:
    parts = path.split("/")
    count, category = {"avatars": (2, "avatar"), "salon-images": (2, "gallery"),
                       "staff-photos": (3, "staff")}.get(parts[0], (0, ""))
    if (not count or len(parts) <= count or
            any(not re.fullmatch(r"[A-Za-z0-9_-]+", p) for p in parts[1:count])):
        raise ValidationError("Invalid media namespace")
    return "/".join(parts[:count]) + "/", category


def family_id(namespace: str, manifest: list[dict]) -> str:
    return hashlib.sha256(json.dumps([namespace, POLICY_VERSION, manifest],
                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def member_path(proof: dict, member: dict) -> str:
    return (f"{proof['namespace']}{POLICY_VERSION}/{proof['family_id']}/"
            f"{member['variant']}-{member['sha256']}.webp")


class ImageFamilies:
    """R2 gateway mixin; all boto calls go through the gateway's bounded executor."""

    def _family_proofs(self, family: ProcessedImageFamily, namespace: str, alias: str | None) -> list[tuple[str, bytes, dict]]:
        if not isinstance(family, ProcessedImageFamily) or family.policy_version != POLICY_VERSION:
            raise ValidationError("A processed image family is required")
        manifest = [{"variant": v.name, "width": v.width, "height": v.height,
                     "size": len(v.data), "sha256": v.sha256} for v in family.variants]
        base = {"bucket": self.settings.r2_bucket, "namespace": namespace,
                "policy_version": POLICY_VERSION, "family_id": family_id(namespace, manifest),
                "manifest": manifest, "mime": "image/webp"}
        result = []
        for variant, item in zip(family.variants, manifest, strict=True):
            path = member_path(base, item)
            result.append((path, variant.data, {**base, **item, "path": path, "alias": False}))
        if alias:
            item = manifest[-1]
            result.append((alias, family.variants[-1].data, {**base, **item, "path": alias, "alias": True}))
        if not result:
            raise ValidationError("Empty image family")
        return result

    def _family_metadata(self, proof: dict) -> dict[str, str]:
        payload = json.dumps(proof, sort_keys=True, separators=(",", ":"))
        return {"processed-image-v2": payload, "processed-signature": self._sign(payload)}

    def _verify_family_head(self, path: str, head: dict) -> dict:
        try:
            metadata = head["Metadata"]
            payload = metadata["processed-image-v2"]
            if not hmac.compare_digest(self._sign(payload), metadata["processed-signature"]):
                raise ValueError()
            proof = json.loads(payload)
            namespace, category = namespace_for(path)
            manifest = proof["manifest"]
            policies = POLICIES[category]
            if (proof["namespace"] != namespace or proof["bucket"] != self.settings.r2_bucket or
                    proof["path"] != path or proof["policy_version"] != POLICY_VERSION or
                    head.get("ResponseMetadata", {}).get("HTTPStatusCode") != 200 or
                    proof["mime"] != "image/webp" or head["ContentType"] != "image/webp" or
                    proof["size"] != head["ContentLength"] or
                    not isinstance(manifest, list) or len(manifest) != len(policies) or
                    [m["variant"] for m in manifest] != list(policies) or
                    proof["family_id"] != family_id(namespace, manifest)):
                raise ValueError()
            for item in manifest:
                edge, cap = policies[item["variant"]]
                if (not _HEX.fullmatch(item["sha256"]) or
                        any(type(item[k]) is not int for k in ("width", "height", "size")) or
                        not 0 < item["width"] <= edge or not 0 < item["height"] <= edge or
                        item["width"] * item["height"] > self.settings.image_max_pixels or
                        not 0 < item["size"] <= cap):
                    raise ValueError()
            item = next(m for m in manifest if m["variant"] == proof["variant"])
            if any(proof[k] != item[k] for k in ("width", "height", "size", "sha256")):
                raise ValueError()
            if type(proof["alias"]) is not bool:
                raise ValueError()
            if proof["alias"]:
                if "/" in path[len(namespace):] or item != manifest[-1]:
                    raise ValueError()
            elif path != member_path(proof, item):
                raise ValueError()
            return {**proof, "dimension": max(proof["width"], proof["height"]),
                    "pixels": proof["width"] * proof["height"]}
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise ValidationError("Image family metadata is invalid") from exc

    async def _complete_family(self, proof: dict) -> None:
        for item in proof["manifest"]:
            other = await self.inspect_processed_object(member_path(proof, item))
            if (other.get("family_id") != proof["family_id"] or other.get("alias") is not False or
                    other.get("manifest") != proof["manifest"]):
                raise ValidationError("Image family is incomplete")

    def _put_family_member_sync(self, path: str, data: bytes, proof: dict) -> Any:
        return self._get_client().put_object(
            Bucket=self.settings.r2_bucket, Key=path, Body=data, ContentType="image/webp",
            IfNoneMatch="*", Metadata=self._family_metadata(proof),
            CacheControl="public, max-age=31536000, immutable",
            ContentMD5=base64.b64encode(hashlib.md5(data, usedforsecurity=False).digest()).decode(),
        )

    async def upload_processed_family(self, bucket: str, namespace: str, family: ProcessedImageFamily,
                                      *, alias: str | None = None) -> dict:
        self._assert_configured()
        if bucket != self.settings.r2_bucket:
            raise ValidationError("Invalid upload bucket")
        objects = self._family_proofs(family, namespace, alias)
        for path, data, proof in objects:
            # Validate the typed encoder output and proof even for internal callers.
            self._verify_family_head(path, {"Metadata": self._family_metadata(proof),
                                           "ContentType": "image/webp", "ContentLength": len(data),
                                           "ResponseMetadata": {"HTTPStatusCode": 200}})
            if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
                raise ValidationError("A processed WebP image is required")
        try:
            for path, data, proof in objects:
                try:
                    response = await self._r2_call(self._put_family_member_sync, path, data, proof)
                    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                    if not isinstance(status, int) or not 200 <= status < 300:
                        raise ValidationError("Image storage did not acknowledge the upload")
                except Exception:
                    # Conditional conflicts and lost responses are safe only when
                    # HEAD proves exactly the intended immutable object exists.
                    existing = await self.inspect_processed_object(path)
                    if any(existing.get(k) != proof[k] for k in proof):
                        raise ValidationError("Image upload conflicts with an existing object") from None
                existing = await self.inspect_processed_object(path)
                if any(existing.get(k) != proof[k] for k in proof):
                    raise ValidationError("Image upload verification failed")
            proof = await self.inspect_processed_object(objects[-1][0])
            await self._complete_family(proof)
        except Exception as exc:
            # Never blindly roll back storage: another request may have published
            # an identical family. Aged partial families are retried or swept.
            logging.getLogger(__name__).warning("image_family_upload_failed", extra={
                "family_id": objects[0][2]["family_id"], "error_type": type(exc).__name__})
            raise ValidationError("Image family upload failed; retry the same upload") from exc
        return self._family_result(proof)

    def _family_result(self, proof: dict) -> dict:
        return {"public_url": self.get_public_url(self.settings.r2_bucket, proof["path"]),
                "family_id": proof["family_id"], "policy_version": POLICY_VERSION,
                "variants": {item["variant"]: {
                    **item, "mime": "image/webp",
                    "url": self.get_public_url(self.settings.r2_bucket, member_path(proof, item)),
                } for item in proof["manifest"]}}

    async def upload_result(self, token: str) -> dict:
        # Read-only token with its own signature domain; expiry also applies to lookup.
        claims = self._result_claims(token)
        proof = await self.inspect_processed_object(claims["path"])
        if "family_id" not in proof:
            raise ValidationError("Image family is unavailable")
        await self._complete_family(proof)
        return self._family_result(proof)

    async def publication_urls(self, url: str) -> list[str]:
        base = str(self.settings.r2_public_url).rstrip("/") + "/"
        if not url.startswith(base):
            return []
        proof = await self.inspect_processed_object(url[len(base):])
        if "family_id" not in proof:
            return []
        return [self.get_public_url(self.settings.r2_bucket, member_path(proof, m)) for m in proof["manifest"]]

    async def retirement_paths(self, path: str) -> list[str]:
        proof = await self._retirement_proof(path)
        if "family_id" not in proof:
            return [path]
        # Aliases predate knowledge of the content hash. Inventory their namespace
        # to protect every alias reference without adding database columns.
        aliases = []
        count = 0
        async for item in self._objects(proof["namespace"]):
            count += 1
            if count > 10000:
                raise ValidationError("Media namespace requires an operator inventory")
            key = item["Key"]
            if "/" in key[len(proof["namespace"]):]:
                continue
            # An unknown object is preserved. A transient HEAD failure MUST stop
            # retirement, rather than hiding a possibly referenced alias.
            head = await self._r2_call(self._head_sync, key)
            if "processed-image-v2" not in head.get("Metadata", {}):
                continue
            other = self._verify_family_head(key, head)
            if other["family_id"] == proof["family_id"]:
                aliases.append(key)
        members = [member_path(proof, item) for item in proof["manifest"]]
        # Check all declared members for references, including currently missing
        # members of a partial upload. Missing deletes are idempotent.
        return sorted(set(aliases)) + members

    async def retirement_lock_paths(self, path: str) -> list[str]:
        proof = await self._retirement_proof(path)
        if "family_id" not in proof:
            return [path]
        return sorted(member_path(proof, item) for item in proof["manifest"])

    async def _retirement_proof(self, path: str) -> dict:
        # A missing/unmarked object is a skip; a transient provider failure must
        # reach the worker's failure counter/heartbeat, not look like legacy media.
        head = await self._erasure_head(path)
        if head is None:
            raise ValidationError("Image is missing")
        return self._verify_processed_head(path, head)

    async def retirement_ready(self, paths: list[str]) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.settings.media_cleanup_grace_seconds)
        for path in paths:
            head = await self._erasure_head(path)
            if head is None:
                continue
            if "processed-image-v2" in head.get("Metadata", {}):
                # A fresh alias is a new in-flight upload, even if deduplicated
                # canonical members were created long ago. Give it its full grace.
                modified = head.get("LastModified")
                if not isinstance(modified, datetime) or modified >= cutoff:
                    return False
        return True

    async def erasure_lock_paths(self, path: str) -> list[str]:
        head = await self._erasure_head(path)
        if head is None:
            return []
        if "processed-image-v2" not in head.get("Metadata", {}):
            return [path]
        return await self.retirement_lock_paths(path)

    async def erasure_paths(self, path: str) -> list[str]:
        head = await self._erasure_head(path)
        if head is None:
            return []
        if "processed-image-v2" not in head.get("Metadata", {}):
            return [path]
        return await self.retirement_paths(path)

    async def _erasure_head(self, path: str) -> dict | None:
        from botocore.exceptions import ClientError
        try:
            return await self._r2_call(self._head_sync, path)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "NotFound", "404"}:
                return None
            raise
