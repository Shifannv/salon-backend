"""Dependency-free heartbeat healthcheck for completed media cleanup sweeps."""

import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path


def heartbeat_path() -> Path:
    override = os.environ.get("MEDIA_CLEANUP_HEARTBEAT_FILE")
    return Path(override) if override else Path(tempfile.gettempdir()) / "media_cleanup_worker.heartbeat"


def touch(candidates: int, deleted: int, failures: int, path: Path | None = None) -> None:
    target = path or heartbeat_path()
    now = time.time()
    last_success = now if failures == 0 else 0.0
    if failures:
        try:
            last_success = json.loads(target.read_text(encoding="utf-8"))["last_success_time"]
        except (OSError, ValueError, TypeError, KeyError):
            last_success = 0.0
    payload = {
        "last_completed_time": now,
        "last_success_time": last_success,
        "candidates": candidates,
        "deleted": deleted,
        "failures": failures,
    }
    # Readers must see a complete snapshot even during a healthcheck.
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(target)


def max_age_seconds() -> int:
    try:
        interval = int(os.environ.get("MEDIA_CLEANUP_INTERVAL_SECONDS", "3600"))
    except ValueError:
        interval = 3600
    return max(1, interval) + 600


def is_healthy(path: Path | None = None, now: float | None = None, max_age: int | None = None) -> bool:
    try:
        payload = json.loads((path or heartbeat_path()).read_text(encoding="utf-8"))
        completed = float(payload["last_completed_time"])
        succeeded = float(payload["last_success_time"])
        age = (time.time() if now is None else now) - completed
        return (
            math.isfinite(completed) and math.isfinite(succeeded)
            and 0 <= age <= (max_age if max_age is not None else max_age_seconds())
            and succeeded > 0 and payload["failures"] == 0
        )
    except (OSError, ValueError, TypeError, KeyError):
        return False


def main() -> int:
    if is_healthy():
        return 0
    print("media cleanup heartbeat missing, stale or reporting failures", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
