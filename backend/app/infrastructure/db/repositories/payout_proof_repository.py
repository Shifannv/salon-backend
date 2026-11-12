"""Payout payments, proofs, corrections and the audit trail (migration 0057).

Everything here is append-only: the database refuses updates and deletes on these tables. The proof
file lives in ``payout_proofs`` and is read only by ``proof_file``, for a super admin. Callers hold the
request row lock and commit once, so a payment, its proof and the move to 'paid' land together or not
at all.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.exceptions import PayoutAlreadyProcessedError, PayoutTransferInProgressError
from app.infrastructure.db.repositories.wallet_repository import WalletRepository

_DETAIL_SQL = text(
    """select q.id::text as id, q.salon_id::text as salon_id, q.amount_paise, q.scheduled_for, q.status,
              q.reference, q.reject_reason, q.created_at, q.processed_at, q.cancelled_at,
              q.balance_snapshot, s.name as salon_name, o.full_name as owner_name,
              a.account_holder_name, a.upi_id, a.bank_name, a.bank_account_last4, a.ifsc
       from salon_payout_requests q
       join salons s on s.id = q.salon_id
       left join profiles o on o.id = s.owner_id
       left join lateral salon_payout_account_masked(q.salon_id) a on true
       where q.id = cast(:id as uuid)"""
)

_TRANSFER_COLUMNS = (
    "t.id::text as id, t.request_id::text as request_id, t.transfer_id, t.beneficiary_id, t.mode, "
    "t.amount_paise, t.status, t.provider_status, t.cf_transfer_id, t.utr, t.failure_reason, "
    "t.created_at, t.updated_at"
)

_RECONCILIATION_SQL = text(
    """select day, kind, count, amount_paise, asked_paise from (
         select (created_at at time zone cast(:tz as text))::date as day, 'requested' as kind,
                count(*) as count, coalesce(sum(amount_paise), 0)::bigint as amount_paise,
                coalesce(sum(amount_paise), 0)::bigint as asked_paise
         from salon_payout_requests where created_at >= :start and created_at < :end group by 1
         union all
         select (pp.paid_at at time zone cast(:tz as text))::date, 'paid', count(*),
                coalesce(sum(pp.amount_paid_paise), 0)::bigint, coalesce(sum(q.amount_paise), 0)::bigint
         from salon_payout_payments pp join salon_payout_requests q on q.id = pp.payout_id
         where pp.paid_at >= :start and pp.paid_at < :end group by 1
         union all
         select (processed_at at time zone cast(:tz as text))::date, 'declined', count(*),
                coalesce(sum(amount_paise), 0)::bigint, coalesce(sum(amount_paise), 0)::bigint
         from salon_payout_requests
         where status = 'rejected' and processed_at >= :start and processed_at < :end group by 1
       ) t order by day"""
)


class PayoutProofRepository(WalletRepository):
    # ---------------------------------------------------------------- detail
    async def request_detail(self, request_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(_DETAIL_SQL, {"id": request_id})
        row = result.mappings().first()
        return dict(row) if row else None

    async def owner_id_of_salon(self, salon_id: str) -> str | None:
        result = await self.session.execute(
            text("select owner_id::text from salons where id = cast(:s as uuid)"), {"s": salon_id}
        )
        return result.scalar_one_or_none()

    # ---------------------------------------------------------------- payments and proofs
    async def reference_taken(self, reference: str) -> bool:
        result = await self.session.execute(
            text("select 1 from salon_payout_payments where lower(btrim(reference)) = lower(btrim(:r))"),
            {"r": reference},
        )
        return result.first() is not None

    async def add_proof(self, *, mime_type: str, content: bytes, sha256: str, admin_id: str) -> str:
        result = await self.session.execute(
            text(
                """insert into payout_proofs (mime_type, size_bytes, sha256, content, uploaded_by)
                   values (:mime, :size, :sha, :content, cast(:admin as uuid)) returning id::text"""
            ),
            {"mime": mime_type, "size": len(content), "sha": sha256, "content": content, "admin": admin_id},
        )
        return result.scalar_one()

    async def add_payment(
        self,
        *,
        payout_id: str,
        reference: str,
        method: str,
        paid_at: datetime,
        amount_paid_paise: int,
        adjustment_reason: str | None,
        note: str | None,
        proof_id: str,
        admin_id: str,
    ) -> None:
        await self.session.execute(
            text(
                """insert into salon_payout_payments
                     (payout_id, reference, method, paid_at, amount_paid_paise, adjustment_reason, note,
                      proof_id, paid_by)
                   values (cast(:payout as uuid), :reference, :method, :paid_at, :amount, :reason, :note,
                           cast(:proof as uuid), cast(:admin as uuid))"""
            ),
            {
                "payout": payout_id, "reference": reference, "method": method, "paid_at": paid_at,
                "amount": amount_paid_paise, "reason": adjustment_reason, "note": note,
                "proof": proof_id, "admin": admin_id,
            },
        )

    async def payment(self, payout_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """select pp.reference, pp.method, pp.paid_at, pp.amount_paid_paise, pp.adjustment_reason,
                          pp.note, pp.proof_id::text as proof_id, pf.mime_type as proof_mime,
                          pf.size_bytes as proof_size, pp.source, pp.transfer_id
                   from salon_payout_payments pp left join payout_proofs pf on pf.id = pp.proof_id
                   where pp.payout_id = cast(:id as uuid)"""
            ),
            {"id": payout_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def proof_file(self, payout_id: str) -> dict[str, Any] | None:
        """The payment proof bytes of one payout. The only read of ``payout_proofs.content``."""

        result = await self.session.execute(
            text(
                """select pf.mime_type, pf.content, pf.redacted_at from salon_payout_payments pp
                   join payout_proofs pf on pf.id = pp.proof_id where pp.payout_id = cast(:id as uuid)"""
            ),
            {"id": payout_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def correction_proof_file(self, payout_id: str, correction_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """select pf.mime_type, pf.content, pf.redacted_at from salon_payout_corrections c
                   join payout_proofs pf on pf.id = c.proof_id
                   where c.payout_id = cast(:p as uuid) and c.id = cast(:c as uuid)"""
            ),
            {"p": payout_id, "c": correction_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    # ---------------------------------------------------------------- transfers (0068)
    async def owner_contact(self, salon_id: str) -> dict[str, Any] | None:
        """The salon owner's name and phone, which the provider needs to register the account."""

        result = await self.session.execute(
            text(
                """select p.full_name, p.phone from salons s join profiles p on p.id = s.owner_id
                   where s.id = cast(:s as uuid)"""
            ),
            {"s": salon_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def transfers(self, request_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                f"""select {_TRANSFER_COLUMNS} from salon_payout_transfers t
                    where t.request_id = cast(:id as uuid) order by t.created_at, t.id"""
            ),
            {"id": request_id},
        )
        return [dict(row) for row in result.mappings()]

    async def transfer_by_provider_id(self, transfer_id: str, *, lock: bool = False) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                f"""select {_TRANSFER_COLUMNS} from salon_payout_transfers t where t.transfer_id = :t
                    {'for no key update' if lock else ''}"""
            ),
            {"t": transfer_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def add_transfer(
        self, *, request_id: str, transfer_id: str, beneficiary_id: str, mode: str, amount_paise: int, admin_id: str
    ) -> dict[str, Any]:
        try:
            await self.session.execute(
                text(
                    """insert into salon_payout_transfers
                         (request_id, transfer_id, beneficiary_id, mode, amount_paise, created_by)
                       values (cast(:r as uuid), :t, :b, :m, :a, cast(:admin as uuid))"""
                ),
                {"r": request_id, "t": transfer_id, "b": beneficiary_id, "m": mode, "a": amount_paise, "admin": admin_id},
            )
        except IntegrityError as error:  # a second live transfer for this request (the unique index)
            raise PayoutTransferInProgressError("A payout transfer is already on its way for this payout") from error
        except DBAPIError as error:  # the request was handled by someone else while this was starting
            if "payout_transfer_needs_waiting_request" in str(error.orig or error):
                raise PayoutAlreadyProcessedError("This payout request has already been handled") from error
            raise
        row = await self.transfer_by_provider_id(transfer_id)
        assert row is not None  # just inserted in this transaction
        return row

    async def update_transfer(
        self, transfer_id: str, *, status: str, provider_status: str | None, cf_transfer_id: str | None,
        utr: str | None, failure_reason: str | None,
    ) -> dict[str, Any]:
        """Record what the provider said. Keeps a value already stored when the provider sends none."""

        await self.session.execute(
            text(
                """update salon_payout_transfers
                   set status = :status, provider_status = coalesce(:ps, provider_status),
                       cf_transfer_id = coalesce(:cf, cf_transfer_id), utr = coalesce(:utr, utr),
                       failure_reason = coalesce(:reason, failure_reason), updated_at = now()
                   where transfer_id = :t"""
            ),
            {
                "t": transfer_id, "status": status, "ps": provider_status, "cf": cf_transfer_id,
                "utr": utr, "reason": failure_reason,
            },
        )
        row = await self.transfer_by_provider_id(transfer_id)
        assert row is not None
        return row

    async def add_provider_payment(
        self, *, payout_id: str, reference: str, method: str, amount_paise: int, transfer_id: str
    ) -> None:
        """The payment record of a payout the provider sent: no proof file, the transfer is the evidence."""

        await self.session.execute(
            text(
                """insert into salon_payout_payments
                     (payout_id, reference, method, paid_at, amount_paid_paise, source, transfer_id)
                   values (cast(:p as uuid), :ref, :m, now(), :a, 'transfer', :t)"""
            ),
            {"p": payout_id, "ref": reference, "m": method, "a": amount_paise, "t": transfer_id},
        )

    # ---------------------------------------------------------------- corrections
    async def add_correction(
        self, *, payout_id: str, delta_paise: int, reason: str, reference: str, proof_id: str, admin_id: str
    ) -> None:
        await self.session.execute(
            text(
                """insert into salon_payout_corrections
                     (payout_id, delta_paise, reason, reference, proof_id, created_by)
                   values (cast(:payout as uuid), :delta, :reason, :reference, cast(:proof as uuid),
                           cast(:admin as uuid))"""
            ),
            {
                "payout": payout_id, "delta": delta_paise, "reason": reason, "reference": reference,
                "proof": proof_id, "admin": admin_id,
            },
        )

    async def corrections(self, payout_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """select id::text as id, delta_paise, reason, reference, created_at
                   from salon_payout_corrections where payout_id = cast(:id as uuid)
                   order by created_at, id"""
            ),
            {"id": payout_id},
        )
        return [dict(row) for row in result.mappings()]

    # ---------------------------------------------------------------- audit
    async def audit(self, payout_id: str, action: str, admin_id: str) -> None:
        """Who did what to which payout. Never the account or the proof itself."""

        await self.session.execute(
            text(
                """insert into payout_audit (payout_id, action, actor_id)
                   values (cast(:payout as uuid), :action, cast(:admin as uuid))"""
            ),
            {"payout": payout_id, "action": action, "admin": admin_id},
        )

    async def audit_trail(self, payout_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """select a.action, a.created_at, p.full_name as actor_name
                   from payout_audit a left join profiles p on p.id = a.actor_id
                   where a.payout_id = cast(:id as uuid) order by a.created_at, a.id"""
            ),
            {"id": payout_id},
        )
        return [dict(row) for row in result.mappings()]

    # ---------------------------------------------------------------- reconciliation
    async def reconciliation(self, start: datetime, end: datetime, timezone: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            _RECONCILIATION_SQL, {"start": start, "end": end, "tz": timezone}
        )
        return [dict(row) for row in result.mappings()]
