"""Liveness for the account-deletion worker (Docker healthcheck).

The worker touches a heartbeat file after every completed poll cycle and after every request
it finishes. Compose runs ``python -m app.infrastructure.account_deletion.health`` which
exits 0 only while the file is fresh. If the worker is wedged, crash-looping on a bad config
or cannot reach the database, the file goes stale and the container turns ``unhealthy`` -
before this, a dead worker meant locked accounts whose data was never erased, silently.

This module imports nothing heavy on purpose: it must start in milliseconds and must not
need the database or any secret.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_MAX_AGE_SECONDS = 180


def heartbeat_path() -> Path:
    override = os.environ.get("ACCOUNT_DELETION_HEARTBEAT_FILE")
    return Path(override) if override else Path(tempfile.gettempdir()) / "account_deletion_worker.heartbeat"


def touch(path: Path | None = None) -> None:
    target = path or heartbeat_path()
    target.write_text(str(time.time()), encoding="utf-8")


def max_age_seconds() -> int:
    """Generous enough for a poll sleep plus one slow refund call, tight enough to alarm."""

    try:
        poll = int(os.environ.get("ACCOUNT_DELETION_WORKER_POLL_SECONDS", "15"))
    except ValueError:
        poll = 15
    return max(DEFAULT_MAX_AGE_SECONDS, poll * 6 + 60)


def is_healthy(path: Path | None = None, now: float | None = None, max_age: int | None = None) -> bool:
    target = path or heartbeat_path()
    limit = max_age if max_age is not None else max_age_seconds()
    try:
        beat = float(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return ((now if now is not None else time.time()) - beat) <= limit


def main() -> int:
    healthy = is_healthy()
    if not healthy:
        print("account-deletion worker heartbeat is missing or stale", file=sys.stderr)
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
