"""Provider payee accounts."""

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.json_utils import decode_json


class ProviderAccountMixin:
    """Settlement-account persistence."""

    session: AsyncSession

    # ------------------------------------------------------- provider accounts
    async def apply_account_update(
        self, provider: str, account_ref: str, onboarding_status: str | None
    ) -> str:
        if onboarding_status is None:
            return "ignored"
        old = (
            await self.session.execute(
                text(
                    """
                    select salon_id, onboarding_status from payment_provider_accounts
                    where provider = :p and provider_account_ref = :a for update
                    """
                ),
                {"p": provider, "a": account_ref},
            )
        ).mappings().one_or_none()
        if old is None:
            return "unmatched"
        if old["onboarding_status"] == onboarding_status:
            return "ignored"
        await self.session.execute(
            text(
                """
                update payment_provider_accounts set onboarding_status = :s
                where provider = :p and provider_account_ref = :a
                """
            ),
            {"p": provider, "a": account_ref, "s": onboarding_status},
        )
        await self.add_account_audit(
            salon_id=str(old["salon_id"]), provider=provider, action="status_changed",
            previous_status=old["onboarding_status"], new_status=onboarding_status,
            vendor_ref=account_ref, actor_id=None,
        )
        return "applied"

    async def add_account_audit(
        self,
        *,
        salon_id: str,
        provider: str,
        action: str,
        previous_status: str | None,
        new_status: str | None,
        vendor_ref: str | None,
        actor_id: str | None,
        detail: str | None = None,
    ) -> None:
        """Append-only registration trail. References and statuses only, never KYC data."""

        await self.session.execute(
            text(
                """
                insert into payment_provider_account_audit
                  (salon_id, provider, action, previous_status, new_status, vendor_ref,
                   actor_id, detail)
                values (:s, :p, :a, :ps, :ns, :v, :actor, :d)
                """
            ),
            {
                "s": salon_id, "p": provider, "a": action, "ps": previous_status,
                "ns": new_status, "v": vendor_ref, "actor": actor_id,
                "d": (detail or "")[:300] or None,
            },
        )

    async def begin_registration(
        self, salon_id: str, provider: str, actor_id: str, vendor_ref_for: Callable[[int], str]
    ) -> dict[str, Any]:
        """Persist the payee identity with status 'pending' BEFORE the provider call.

        A pending registration is retried under the same vendor id (idempotent at the
        provider). Re-registering from any other status starts a new generation, hence a new
        vendor id: bank details are never stored, so a change can only be a fresh submission.
        ``vendor_ref_for(generation)`` derives the id.
        """

        existing = (
            await self.session.execute(
                text(
                    """
                    select provider_account_ref, onboarding_status, registration_generation
                    from payment_provider_accounts
                    where salon_id = :s and provider = :p for update
                    """
                ),
                {"s": salon_id, "p": provider},
            )
        ).mappings().one_or_none()
        if existing is None:
            generation, action, previous = 1, "registered", None
        elif existing["onboarding_status"] == "pending" and existing["provider_account_ref"]:
            return {
                "vendor_ref": existing["provider_account_ref"],
                "generation": existing["registration_generation"],
                "previous_status": "pending",
            }
        else:
            generation = int(existing["registration_generation"]) + 1
            action, previous = "re_registered", existing["onboarding_status"]
        vendor_ref = vendor_ref_for(generation)
        await self.session.execute(
            text(
                """
                insert into payment_provider_accounts
                  (salon_id, provider, provider_account_ref, onboarding_status, requirements,
                   registration_generation, created_by, updated_by)
                values (:s, :p, :v, 'pending', cast('[]' as jsonb), :g, :actor, :actor)
                on conflict (salon_id, provider) do update set
                  provider_account_ref = excluded.provider_account_ref,
                  onboarding_status = 'pending', requirements = cast('[]' as jsonb),
                  registration_generation = excluded.registration_generation
                """
            ),
            {"s": salon_id, "p": provider, "v": vendor_ref, "g": generation, "actor": actor_id},
        )
        await self.add_account_audit(
            salon_id=salon_id, provider=provider, action=action, previous_status=previous,
            new_status="pending", vendor_ref=vendor_ref, actor_id=actor_id,
        )
        return {"vendor_ref": vendor_ref, "generation": generation, "previous_status": previous}

    async def set_account_result(
        self,
        salon_id: str,
        provider: str,
        status: str,
        requirements: list[str],
        actor_id: str,
        account_ref: str | None = None,
    ) -> None:
        await self.session.execute(
            text(
                """
                update payment_provider_accounts
                set onboarding_status = :st, requirements = cast(:r as jsonb), updated_by = :actor,
                    provider_account_ref = coalesce(cast(:ref as text), provider_account_ref)
                where salon_id = :s and provider = :p
                """
            ),
            {"s": salon_id, "p": provider, "st": status, "r": json.dumps(requirements),
             "actor": actor_id, "ref": account_ref},
        )

    async def find_owner_salon_id(self, actor_id: str) -> str | None:
        """Read-only: never provisions a salon."""

        result = await self.session.execute(
            text(
                """
                select id from salons where owner_id = :a and is_active
                order by created_at limit 1
                """
            ),
            {"a": actor_id},
        )
        row = result.first()
        return str(row[0]) if row else None

    async def get_provider_account(self, salon_id: str, provider: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                select provider_account_ref, onboarding_status, requirements,
                       registration_generation
                from payment_provider_accounts where salon_id = :s and provider = :p
                """
            ),
            {"s": salon_id, "p": provider},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        data = dict(row)
        data["requirements"] = decode_json(data["requirements"]) or []
        return data

    async def upsert_provider_account(
        self,
        salon_id: str,
        provider: str,
        account_ref: str,
        onboarding_status: str,
        requirements: list[str],
        actor_id: str,
    ) -> None:
        await self.session.execute(
            text(
                """
                insert into payment_provider_accounts
                  (salon_id, provider, provider_account_ref, onboarding_status,
                   requirements, created_by, updated_by)
                values (:s, :p, :a, :st, cast(:r as jsonb), :actor, :actor)
                on conflict (salon_id, provider) do update set
                  provider_account_ref = excluded.provider_account_ref,
                  onboarding_status = excluded.onboarding_status,
                  requirements = excluded.requirements
                """
            ),
            {
                "s": salon_id,
                "p": provider,
                "a": account_ref,
                "st": onboarding_status,
                "r": json.dumps(requirements),
                "actor": actor_id,
            },
        )

    async def get_payout_holder_name(self, salon_id: str) -> str | None:
        result = await self.session.execute(
            text("select account_holder_name from salon_payout_accounts where salon_id = :s"),
            {"s": salon_id},
        )
        row = result.first()
        return row[0] if row else None
