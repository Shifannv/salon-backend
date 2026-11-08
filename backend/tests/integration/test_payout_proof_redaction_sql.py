# ruff: noqa: F811
"""Payout proof redaction (0064) on disposable local PostgreSQL: only expired owner-deleted proofs go."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.infrastructure.db.repositories.payout_proof_repository import PayoutProofRepository
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_payment_ledger_sql import TEST_DB
from tests.integration.test_payout_proof_sql import (  # noqa: F401
    PNG,
    mark_paid,
    new_request,
    proof_db,
    record_payment,
)

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")


@pytest.fixture
async def renv(proof_db):
    from tests.integration.test_checkout_safety_sql import SafetyEnv

    environment = SafetyEnv(proof_db)
    yield environment
    await environment.engine.dispose()


async def paid_payout(env, reference: str) -> tuple[str, str]:
    request_id, salon_id = await new_request(env)
    await record_payment(env, request_id, reference)
    async with env.session() as session:
        await mark_paid(session, request_id, reference)
        await session.commit()
    return request_id, salon_id


async def owner_deleted(env, salon_id: str, months_ago: int, status: str = "completed") -> None:
    async with env.session() as session:
        await session.execute(
            text(
                """insert into account_deletion_requests (role, salon_id, status, completed_at)
                   values ('owner', cast(:s as uuid), :status, now() - make_interval(months => :m))"""
            ),
            {"s": salon_id, "status": status, "m": months_ago},
        )
        await session.commit()


async def proof_state(env, request_id: str) -> dict:
    async with env.session() as session:
        row = (await session.execute(
            text(
                """select pf.size_bytes, pf.redacted_at, pf.content from salon_payout_payments pp
                   join payout_proofs pf on pf.id = pp.proof_id where pp.payout_id = cast(:id as uuid)"""
            ),
            {"id": request_id},
        )).mappings().one()
    return dict(row)


async def redact(env, months: int = 12) -> int:
    async with env.session() as session:
        removed = (await session.execute(text("select public.redact_expired_payout_proofs(:m)"), {"m": months})).scalar_one()
        await session.commit()
    return removed


async def test_only_proofs_of_owners_deleted_past_the_window_are_removed(renv):
    old_id, old_salon = await paid_payout(renv, f"UTR-OLD-{uuid4().hex[:8]}")
    recent_id, recent_salon = await paid_payout(renv, f"UTR-NEW-{uuid4().hex[:8]}")
    live_id, _ = await paid_payout(renv, f"UTR-LIVE-{uuid4().hex[:8]}")
    pending_id, pending_salon = await paid_payout(renv, f"UTR-PEND-{uuid4().hex[:8]}")
    await owner_deleted(renv, old_salon, 13)
    await owner_deleted(renv, recent_salon, 2)
    await owner_deleted(renv, pending_salon, 20, status="processing")

    assert await redact(renv) >= 1

    old = await proof_state(renv, old_id)
    assert old["redacted_at"] is not None and old["size_bytes"] == 1 and bytes(old["content"]) == b"\x00"
    for untouched in (recent_id, live_id, pending_id):
        state = await proof_state(renv, untouched)
        assert state["redacted_at"] is None and bytes(state["content"]) == PNG


async def test_the_payment_record_survives_redaction_and_a_second_run_removes_nothing_more(renv):
    request_id, salon_id = await paid_payout(renv, f"UTR-KEEP-{uuid4().hex[:8]}")
    await owner_deleted(renv, salon_id, 24)
    await redact(renv)
    async with renv.session() as session:
        row = (await session.execute(
            text("select amount_paid_paise, reference, method from salon_payout_payments where payout_id = cast(:i as uuid)"),
            {"i": request_id},
        )).mappings().one()
    assert row["amount_paid_paise"] == 100_000 and row["reference"].startswith("UTR-KEEP-")
    assert await redact(renv) == 0


async def test_a_shorter_window_removes_sooner_and_a_bad_window_is_refused(renv):
    request_id, salon_id = await paid_payout(renv, f"UTR-SOON-{uuid4().hex[:8]}")
    await owner_deleted(renv, salon_id, 7)
    assert (await proof_state(renv, request_id))["redacted_at"] is None
    await redact(renv, months=6)
    assert (await proof_state(renv, request_id))["redacted_at"] is not None
    async with renv.session() as session:
        with pytest.raises(DBAPIError, match="retention_months_must_be_positive"):
            await session.execute(text("select public.redact_expired_payout_proofs(0)"))


async def test_the_guard_still_blocks_deletes_and_any_other_edit(renv):
    await paid_payout(renv, f"UTR-GUARD-{uuid4().hex[:8]}")
    async with renv.session() as session:
        with pytest.raises(DBAPIError, match="payout_records_are_never_deleted"):
            await session.execute(text("delete from payout_proofs"))
    async with renv.session() as session:
        with pytest.raises(DBAPIError, match="payout_records_are_append_only"):
            await session.execute(text("update payout_proofs set sha256 = repeat('c', 64)"))
    async with renv.session() as session:
        # Blanking the file without the redaction stamp, or with a different placeholder, is refused.
        with pytest.raises(DBAPIError, match="payout_records_are_append_only"):
            await session.execute(text("update payout_proofs set content = '\\x00'::bytea, size_bytes = 1"))


async def test_a_redacted_proof_is_reported_as_removed_not_served(renv):
    from app.application.use_cases.payout_proof import PayoutProofUseCases
    from app.core.exceptions import NotFoundError
    from tests.conftest import make_super_admin

    request_id, salon_id = await paid_payout(renv, f"UTR-GONE-{uuid4().hex[:8]}")
    await owner_deleted(renv, salon_id, 18)
    await redact(renv)
    admin = make_super_admin(str(uuid4()))
    async with renv.session() as session:
        uc = PayoutProofUseCases(PayoutProofRepository(session))
        with pytest.raises(NotFoundError, match="removed under the retention rule"):
            await uc.proof(admin, request_id)
