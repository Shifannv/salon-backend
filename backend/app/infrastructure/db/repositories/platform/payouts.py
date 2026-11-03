"""Owner payout account and setup facts."""

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
)
from app.core.field_crypto import encrypt_field
from app.infrastructure.db.rows import one_dict_or_none


class PayoutsMixin:
    """Owner payout account and setup facts."""

    session: AsyncSession

    async def get_payout_account(self, actor_id: str) -> dict[str, Any] | None:
        """Return the owner's payout row with the account number already masked.

        The projection to ``bank_account_last4`` happens inside Postgres
        (``salon_payout_account_masked``), so the full number is never read into Python.
        Does not provision a salon: an owner with no salon simply has no payout row.
        """

        salon_id = await self._find_owner_salon_id(actor_id)
        if salon_id is None:
            return None
        result = await self.session.execute(
            text("select * from salon_payout_account_masked(:salon_id)"),
            {"salon_id": salon_id},
        )
        return one_dict_or_none(result)

    async def update_payout_account(
        self,
        actor_id: str,
        values: dict[str, Any],
        validate: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        """Merge ``values`` into the owner's payout row entirely inside SQL.

        Omitted fields keep their stored value; an explicit ``None`` clears the field.
        ``validate`` receives the merged *view* in which the stored account number is
        represented only by a presence marker, so Python never holds the full value and
        ``validate`` may raise ``ValidationError``. A per-salon advisory lock serialises
        writers.
        """

        salon_id = await self._owner_salon_id(actor_id)
        await self.session.execute(
            text("select pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"payout:{salon_id}"},
        )
        current = await self.get_payout_account(actor_id) or {}
        view: dict[str, Any] = {
            "account_holder_name": current.get("account_holder_name"),
            "upi_id": current.get("upi_id"),
            "bank_name": current.get("bank_name"),
            "ifsc": current.get("ifsc"),
            # Presence marker only; never the stored number.
            "bank_account_number": "stored" if current.get("bank_account_last4") else None,
        }
        view.update({k: v for k, v in values.items() if k in view})

        fields = ("account_holder_name", "upi_id", "bank_name", "bank_account_number", "ifsc")
        written = {k: v for k, v in values.items() if k in fields}
        if "bank_account_number" in values and values["bank_account_number"] is None:
            # Clearing the account number takes the dependent bank fields with it unless the
            # caller says otherwise (ck_payout_bank_triple: they cannot stand alone).
            for dependent in ("ifsc", "bank_name"):
                if dependent not in values:
                    view[dependent] = None
                    written[dependent] = None
        validate(view)
        if "bank_account_number" in written:
            # The number is stored encrypted when a key is configured; its last four digits go
            # in their own column so masking never has to decrypt.
            number = written["bank_account_number"]
            written["bank_account_last4"] = number[-4:] if number else None
            written["bank_account_number"] = encrypt_field(number, str(salon_id))
        params: dict[str, Any] = {"salon_id": salon_id}
        for field in (*fields, "bank_account_last4"):
            params[field] = written.get(field)
            params[f"set_{field}"] = field in written
        await self.session.execute(
            text(
                """
                insert into salon_payout_accounts
                  (salon_id, account_holder_name, upi_id, bank_name, bank_account_number,
                   bank_account_last4, ifsc)
                values
                  (:salon_id, :account_holder_name, :upi_id, :bank_name,
                   :bank_account_number, :bank_account_last4, :ifsc)
                on conflict (salon_id) do update set
                  account_holder_name = case when cast(:set_account_holder_name as boolean)
                    then excluded.account_holder_name
                    else salon_payout_accounts.account_holder_name end,
                  upi_id = case when cast(:set_upi_id as boolean)
                    then excluded.upi_id else salon_payout_accounts.upi_id end,
                  bank_name = case when cast(:set_bank_name as boolean)
                    then excluded.bank_name else salon_payout_accounts.bank_name end,
                  bank_account_number = case when cast(:set_bank_account_number as boolean)
                    then excluded.bank_account_number
                    else salon_payout_accounts.bank_account_number end,
                  bank_account_last4 = case when cast(:set_bank_account_last4 as boolean)
                    then excluded.bank_account_last4
                    else salon_payout_accounts.bank_account_last4 end,
                  ifsc = case when cast(:set_ifsc as boolean)
                    then excluded.ifsc else salon_payout_accounts.ifsc end
                """
            ),
            params,
        )
        row = await self.get_payout_account(actor_id)
        await self.session.commit()
        if row is None:  # pragma: no cover - the upsert above guarantees a row
            raise NotFoundError("Payout account not found")
        return row

    async def list_payout_account_history(
        self, actor_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return the owner's payout change history (last four digits only)."""

        salon_id = await self._find_owner_salon_id(actor_id)
        if salon_id is None:
            return []
        result = await self.session.execute(
            text(
                """
                select h.id, h.changed_at, h.action, h.changed_fields,
                       h.before_state as before_state, h.after_state as after_state,
                       p.full_name as changed_by_name
                from salon_payout_account_history h
                left join profiles p on p.id = h.changed_by
                where h.salon_id = :salon_id
                order by h.changed_at desc, h.id desc
                limit :limit
                """
            ),
            {"salon_id": salon_id, "limit": limit},
        )
        rows = [dict(row) for row in result.mappings().all()]
        for row in rows:
            for key in ("before_state", "after_state"):
                if isinstance(row.get(key), str):
                    row[key] = json.loads(row[key])
        return rows

    async def get_setup_facts(self, actor_id: str) -> dict[str, Any]:
        """Return the raw facts behind the owner setup checklist in one query.

        Read-only: an owner who has no salon yet gets all-empty facts rather than a
        freshly provisioned row.
        """

        salon_id = await self._find_owner_salon_id(actor_id)
        if salon_id is None:
            return {
                "name": None, "address": None, "city": None,
                "working_hours": None, "has_photos": False, "has_services": False,
                "has_staff": False, "has_payout": False,
            }
        result = await self.session.execute(
            text(
                """
                select s.name, s.address, s.city, s.working_hours,
                       exists (select 1 from salon_images i
                               where i.salon_id = s.id and i.is_active) as has_photos,
                       exists (select 1 from services sv
                               where sv.salon_id = s.id and sv.is_active) as has_services,
                       exists (select 1 from staff st
                               where st.salon_id = s.id and st.is_active) as has_staff,
                       exists (select 1 from salon_payout_accounts p
                               where p.salon_id = s.id) as has_payout
                from salons s
                where s.id = :salon_id
                """
            ),
            {"salon_id": salon_id},
        )
        return dict(result.mappings().one())
