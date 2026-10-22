"""Stateful, thread-safe boto fake. Never opens a network connection."""

import base64
import hashlib
import threading
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import MagicMock

from botocore.exceptions import ClientError


def storage_error(code: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "Synthetic storage error"}}, operation)


class FakeR2Client:
    def __init__(self):
        self.objects: dict[str, dict] = {}
        self.fail_put_at: set[int] = set()
        self.lose_response_at: set[int] = set()
        self.bad_response_at: set[int] = set()
        self.fail_delete_keys: set[str] = set()
        self.put_attempts = 0
        self._lock = threading.RLock()
        self.put_object = MagicMock(side_effect=self._put)
        self.head_object = MagicMock(side_effect=self._head)
        self.list_objects_v2 = MagicMock(side_effect=self._list)
        self.delete_object = MagicMock(side_effect=self._delete)

    def _put(self, **kwargs):
        with self._lock:
            self.put_attempts += 1
            attempt = self.put_attempts
            if attempt in self.fail_put_at:
                raise storage_error("ServiceUnavailable", "PutObject")
            key, body = kwargs["Key"], bytes(kwargs["Body"])
            if kwargs.get("IfNoneMatch") == "*" and key in self.objects:
                raise storage_error("PreconditionFailed", "PutObject")
            digest = hashlib.md5(body, usedforsecurity=False).digest()
            if kwargs.get("ContentMD5") and kwargs["ContentMD5"] != base64.b64encode(digest).decode():
                raise storage_error("BadDigest", "PutObject")
            etag = '"' + digest.hex() + '"'
            self.objects[key] = {
                "Body": body, "Metadata": deepcopy(kwargs.get("Metadata", {})),
                "ContentType": kwargs.get("ContentType", "application/octet-stream"),
                "ContentLength": len(body), "LastModified": datetime.now(timezone.utc),
                "ETag": etag, "CacheControl": kwargs.get("CacheControl", ""),
            }
            if attempt in self.lose_response_at:
                raise TimeoutError("Synthetic lost response")
            status = 500 if attempt in self.bad_response_at else 200
            return {"ResponseMetadata": {"HTTPStatusCode": status}, "ETag": etag}

    def _head(self, **kwargs):
        with self._lock:
            key = kwargs["Key"]
            if key not in self.objects:
                raise storage_error("404", "HeadObject")
            return {**deepcopy({k: v for k, v in self.objects[key].items() if k != "Body"}),
                    "ResponseMetadata": {"HTTPStatusCode": 200}}

    def _list(self, **kwargs):
        with self._lock:
            keys = sorted(key for key in self.objects if key.startswith(kwargs.get("Prefix", "")))
            start = int(kwargs.get("ContinuationToken", 0))
            stop = start + kwargs.get("MaxKeys", 1000)
            result = {"Contents": [
                {"Key": key, "LastModified": self.objects[key]["LastModified"]}
                for key in keys[start:stop]
            ], "IsTruncated": stop < len(keys), "ResponseMetadata": {"HTTPStatusCode": 200}}
            if result["IsTruncated"]:
                result["NextContinuationToken"] = str(stop)
            return result

    def _delete(self, **kwargs):
        with self._lock:
            key = kwargs["Key"]
            if key in self.fail_delete_keys:
                raise storage_error("ServiceUnavailable", "DeleteObject")
            self.objects.pop(key, None)
            return {"ResponseMetadata": {"HTTPStatusCode": 204}}
