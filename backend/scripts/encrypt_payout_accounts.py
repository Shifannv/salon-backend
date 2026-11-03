"""Encrypt (or, for a rollback, decrypt) the stored payout account numbers.

Dry run by default: it only reports how many rows are eligible. Pass --apply to change them.
Needs DATABASE_URL and, to encrypt, PAYOUT_ENCRYPTION_KEY. Run it as the database owner, once,
after migration 0059 is applied and the key is set on the API. Rows are converted in one
transaction, so a failure leaves every row as it was. It prints counts only, never a number.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.db.payout_backfill import convert_payout_accounts  # noqa: E402
from app.infrastructure.db.session import AsyncSessionLocal  # noqa: E402


async def main(decrypt: bool, apply: bool) -> None:
    async with AsyncSessionLocal() as session:
        summary = await convert_payout_accounts(session, decrypt=decrypt, apply=apply)
        if apply:
            await session.commit()
        else:
            await session.rollback()
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="change rows (default is a dry run)")
    parser.add_argument("--decrypt", action="store_true", help="convert encrypted rows back to plain digits")
    args = parser.parse_args()
    asyncio.run(main(args.decrypt, args.apply))
