"""One-off conversion of stored payout account numbers between plain text and encrypted.

Run through ``scripts/encrypt_payout_accounts.py``. It changes only the account number column,
so the three triggers that would otherwise stamp ``updated_at``, the audit actor and a history
row are switched off for the duration of the transaction: re-encrypting a number is not an
owner edit, and a bumped ``updated_at`` would falsely tell an admin the account "changed since
the request". Nothing here ever returns or logs a number.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.field_crypto import decrypt_field, encrypt_field, encryption_enabled, is_encrypted

_TRIGGERS = (
    "t_salon_payout_accounts_updated",
    "t_salon_payout_accounts_audit",
    "t_salon_payout_accounts_history",
)
_SELECT_PLAIN = text(
    "select salon_id::text as salon_id, bank_account_number as number from salon_payout_accounts "
    "where bank_account_number ~ '^[0-9]{9,18}$' order by salon_id for update"
)
_SELECT_ENCRYPTED = text(
    "select salon_id::text as salon_id, bank_account_number as number from salon_payout_accounts "
    "where bank_account_number like 'enc:%' order by salon_id for update"
)


async def convert_payout_accounts(session: AsyncSession, *, decrypt: bool = False, apply: bool = False) -> dict[str, Any]:
    """Convert every eligible row; with ``apply`` false, only count them (the default)."""

    if not decrypt and not encryption_enabled():
        raise RuntimeError("Set PAYOUT_ENCRYPTION_KEY before encrypting payout accounts")
    rows = (await session.execute(_SELECT_ENCRYPTED if decrypt else _SELECT_PLAIN)).mappings().all()
    summary: dict[str, Any] = {
        "mode": "decrypt" if decrypt else "encrypt",
        "eligible": len(rows),
        "converted": 0,
        "applied": apply,
    }
    if not apply or not rows:
        return summary

    for trigger in _TRIGGERS:
        await session.execute(text(f"alter table public.salon_payout_accounts disable trigger {trigger}"))
    try:
        for row in rows:
            salon_id, current = row["salon_id"], row["number"]
            plain = decrypt_field(current, salon_id)
            target = plain if decrypt else encrypt_field(plain, salon_id)
            # Prove the round trip before the old value is overwritten.
            if decrypt_field(target, salon_id) != plain or (not decrypt and not is_encrypted(target)):
                raise RuntimeError("Round-trip check failed; nothing was changed")
            await session.execute(
                text(
                    "update salon_payout_accounts set bank_account_number = :n, bank_account_last4 = :l "
                    "where salon_id = cast(:s as uuid)"
                ),
                {"n": target, "l": plain[-4:], "s": salon_id},
            )
            summary["converted"] += 1
    finally:
        for trigger in _TRIGGERS:
            await session.execute(text(f"alter table public.salon_payout_accounts enable trigger {trigger}"))
    return summary
