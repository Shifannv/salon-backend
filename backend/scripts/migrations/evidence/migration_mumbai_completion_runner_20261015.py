"""Run Mumbai-only completion checks and save sanitized evidence."""

import asyncio
import contextlib
import io
import json

from backend.scripts.migrations import migration_mumbai_staging_20261015 as staging
from backend.scripts.migrations.evidence import migration_mumbai_booking_20261015 as booking

original = booking.rollback_checks


async def completion_checks(*args, **kwargs):
    return await original(*args, **kwargs, completion=True)


if __name__ == '__main__':
    booking.rollback_checks = completion_checks
    captured = io.StringIO()
    error = None
    with contextlib.redirect_stdout(captured):
        try:
            asyncio.run(staging.run(api_benchmarks=True))
        except Exception as exc:
            error = type(exc).__name__
    result = {"destination": staging.REF, "api_base_url": "http://mumbai-local-test",
              "transport": "in-process ASGI, real Mumbai Auth/Postgres",
              "status": "failed" if error else "completed", "error_type": error,
              "sanitized_output": captured.getvalue(), "migrations_run": False,
              "stamp_run": False, "temporary_permission_grants": False}
    (staging.ROOT / 'backend/migrations/reviews/migration-mumbai-completion-business-2026-10-15.json').write_text(
        json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if error else 0)
