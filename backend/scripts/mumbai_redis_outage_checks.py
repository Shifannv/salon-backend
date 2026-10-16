"""Run Redis recovery regression checks against disposable loopback services only.

Set MIGRATION_TEST_DB to the disposable PostgreSQL admin URL on port 16432 and
RECOVERY_TEST_REDIS to redis://127.0.0.1:16479/0. The suite creates a unique test
database through 0037 only, then drops it. No Mumbai credentials are consumed.
Set RECOVERY_PLAYWRIGHT_MODULE when Playwright is installed outside this checkout.
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


def main():
    database = os.environ.get("MIGRATION_TEST_DB", "")
    redis_url = os.environ.get("RECOVERY_TEST_REDIS", "")
    db = urlsplit(database)
    if db.hostname != "127.0.0.1" or db.port != 16432 or db.path != "/postgres":
        raise SystemExit("Requires explicit disposable loopback PostgreSQL on port 16432")
    if redis_url != "redis://127.0.0.1:16479/0":
        raise SystemExit("Requires dedicated loopback recovery Redis on port 16479")
    environment = dict(os.environ, SALON_ENV_FILE="__no_environment_file__",
        ENVIRONMENT="test", DATABASE_URL=database.replace("postgresql://", "postgresql+asyncpg://", 1))
    return subprocess.call([sys.executable, "-m", "pytest", "-q",
        "tests/integration/test_redis_recovery_sql.py", *sys.argv[1:]],
        cwd=Path(__file__).resolve().parents[1], env=environment)


if __name__ == "__main__":
    sys.exit(main())
