"""Payout proof (0057) on disposable local PostgreSQL: the paid rule, unique reference, append-only, reads."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.use_cases.payout_proof import PayoutProofUseCases
from app.infrastructure.db.repositories.payout_proof_repository import PayoutProofRepository
from tests.conftest import make_super_admin
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

SQL = Path(__file__).parents[2] / "migrations/sql"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture(scope="module")
def proof_db(changes_db):  # noqa: F811
    import asyncio

    async def install():
        env = SafetyEnv(changes_db)
        try:
            async with env.session() as session:
                for file in ("0053_salon_payout_requests.sql", "0057_payout_proof.sql"):
                    for statement in (SQL / file).read_text(encoding="utf-8").split("\n-- statement --\n"):
                        if statement.strip():
                            await session.execute(text(statement))
                await session.commit()
        finally:
            await env.engine.dispose()

    asyncio.run(install())
    return changes_db


@pytest.fixture
async def env(proof_db):
    environment = SafetyEnv(proof_db)
    yield environment
    await environment.engine.dispose()


async def new_request(env, amount: int = 100_000) -> tuple[str, str]:
    """A waiting payout request for a fresh salon: (request id, salon id)."""

    fixture = await env.seed()
    request_id = str(uuid4())
    async with env.session() as session:
        await session.execute(
            text(
                """insert into salon_payout_requests
                     (id, salon_id, amount_paise, scheduled_for, idempotency_key, request_hash, balance_snapshot)
                   values (cast(:id as uuid), cast(:s as uuid), :amount, current_date, :key, :hash,
                           cast('{"collected_paise": 1}' as jsonb))"""
            ),
            {"id": request_id, "s": fixture["salon"], "amount": amount, "key": uuid4().hex, "hash": "a" * 64},
        )
        await session.commit()
    return request_id, fixture["salon"]


async def record_payment(env, request_id: str, reference: str, admin: str | None = None) -> None:
    async with env.session() as session:
        repo = PayoutProofRepository(session)
        proof = await repo.add_proof(mime_type="image/png", content=PNG, sha256="b" * 64, admin_id=admin)
        await repo.add_payment(
            payout_id=request_id, reference=reference, method="upi", paid_at=datetime.now(UTC),
            amount_paid_paise=100_000, adjustment_reason=None, note=None, proof_id=proof, admin_id=admin,
        )
        await session.commit()


async def mark_paid(session, request_id: str, reference: str) -> None:
    await session.execute(
        text(
            """update salon_payout_requests set status = 'paid', reference = :r, processed_at = now()
               where id = cast(:id as uuid)"""
        ),
        {"id": request_id, "r": reference},
    )


async def test_a_request_cannot_become_paid_without_a_recorded_payment(env):
    request_id, _ = await new_request(env)
    async with env.session() as session:
        with pytest.raises(DBAPIError, match="payout_paid_needs_recorded_payment"):
            await mark_paid(session, request_id, "UTR-NONE")


async def test_it_becomes_paid_once_the_payment_and_proof_exist_and_the_reference_matches(env):
    request_id, _ = await new_request(env)
    await record_payment(env, request_id, "UTR-OK-1")
    async with env.session() as session:
        with pytest.raises(DBAPIError, match="payout_paid_needs_recorded_payment"):
            await mark_paid(session, request_id, "UTR-DIFFERENT")
        await session.rollback()
        await mark_paid(session, request_id, "UTR-OK-1")
        await session.commit()
        status = (await session.execute(
            text("select status from salon_payout_requests where id = cast(:id as uuid)"), {"id": request_id}
        )).scalar_one()
    assert status == "paid"


async def test_one_reference_one_payout_whatever_the_case_or_spacing(env):
    first, _ = await new_request(env)
    second, _ = await new_request(env)
    await record_payment(env, first, "UTR-DUP-1")
    with pytest.raises(IntegrityError):
        await record_payment(env, second, "  utr-dup-1 ")


async def test_the_snapshot_and_the_request_stay_frozen_after_the_move(env):
    request_id, _ = await new_request(env)
    async with env.session() as session:
        with pytest.raises(DBAPIError, match="payout_request_fields_are_frozen"):
            await session.execute(
                text("update salon_payout_requests set balance_snapshot = '{}' where id = cast(:id as uuid)"),
                {"id": request_id},
            )


@pytest.mark.parametrize("table", ["payout_proofs", "salon_payout_payments", "payout_audit"])
async def test_proof_payment_and_audit_rows_are_never_updated_or_deleted(env, table):
    request_id, _ = await new_request(env)
    await record_payment(env, request_id, f"UTR-{table}")
    async with env.session() as session:
        await PayoutProofRepository(session).audit(request_id, "reveal", None)
        await session.commit()
    async with env.session() as session:
        with pytest.raises(DBAPIError, match="payout_records_are_append_only"):
            await session.execute(text(f"update {table} set created_at = now() - interval '1 day'"))
        await session.rollback()
        with pytest.raises(DBAPIError, match="payout_records_are_never_deleted"):
            await session.execute(text(f"delete from {table}"))
        await session.rollback()
        with pytest.raises(DBAPIError, match="payout_records_are_never_deleted"):
            await session.execute(text(f"truncate {table} cascade"))


async def test_a_file_that_is_not_an_allowed_type_or_whose_size_is_wrong_is_refused(env):
    async with env.session() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text(
                "insert into payout_proofs(mime_type,size_bytes,sha256,content) "
                "values ('text/html', 3, repeat('c',64), 'abc'::bytea)"))
        await session.rollback()
        with pytest.raises(IntegrityError):
            await session.execute(text(
                "insert into payout_proofs(mime_type,size_bytes,sha256,content) "
                "values ('image/png', 99, repeat('c',64), 'abc'::bytea)"))


async def test_deleting_the_admin_blanks_who_paid_but_keeps_the_record(env):
    request_id, _ = await new_request(env)
    admin = str(uuid4())
    async with env.session() as session:
        await session.execute(text("set local session_replication_role=replica"))
        await session.execute(text("insert into auth.users(id,email) values(:id,:e)"), {"id": admin, "e": admin + "@x.test"})
        await session.execute(
            text("insert into profiles(id,role,email) values(:id,cast('super_admin' as user_role),:e)"),
            {"id": admin, "e": admin + "@x.test"},
        )
        await session.commit()
    await record_payment(env, request_id, "UTR-ADMIN-GONE", admin)
    async with env.session() as session:
        await session.execute(text("delete from profiles where id = cast(:id as uuid)"), {"id": admin})
        await session.commit()
        who = (await session.execute(
            text("select paid_by from salon_payout_payments where payout_id = cast(:id as uuid)"), {"id": request_id}
        )).scalar_one()
    assert who is None


async def test_pay_detail_proof_and_reconciliation_work_end_to_end(env):
    request_id, _ = await new_request(env)
    admin = make_super_admin(str(uuid4()))
    async with env.session() as session:
        await session.execute(text("set local session_replication_role=replica"))
        await session.execute(text("insert into auth.users(id,email) values(:id,:e)"), {"id": admin.id, "e": "a@x.test"})
        await session.execute(
            text("insert into profiles(id,role,email) values(:id,cast('super_admin' as user_role),:e)"),
            {"id": admin.id, "e": "a@x.test"},
        )
        await session.commit()
    async with env.session() as session:
        uc = PayoutProofUseCases(PayoutProofRepository(session))
        paid = await uc.pay(
            admin, request_id, reference="UTR-E2E-1", method="imps", paid_at=datetime.now(UTC),
            amount_paid_paise=95_000, adjustment_reason="Bank fee kept", note="HDFC", proof=PNG,
        )
        assert paid["status"] == "paid" and paid["method"] == "imps"
        again = await uc.pay(
            admin, request_id, reference="utr-e2e-1", method="imps", paid_at=datetime.now(UTC),
            amount_paid_paise=95_000, adjustment_reason="Bank fee kept", note=None, proof=PNG,
        )
        assert again["id"] == paid["id"]
        detail = await uc.detail(admin, request_id)
        assert detail["payment"]["amount_paid_paise"] == 95_000 and detail["balance_at_request"]["collected_paise"] == 1
        assert [item["action"] for item in detail["timeline"]] == ["pay"]
        file = await uc.proof(admin, request_id)
        assert file["content"] == PNG and file["mime_type"] == "image/png"
        today = datetime.now(UTC).date()
        report = await uc.reconciliation(admin, today - timedelta(days=1), today + timedelta(days=1))
        assert report["totals"]["paid_count"] >= 1 and report["totals"]["difference_paise"] <= -5_000
        fixed = await uc.correct(
            admin, request_id, delta_paise=5_000, reason="Sent the rest", reference="UTR-E2E-2", proof=PNG
        )
        assert fixed["corrections"][0]["delta_paise"] == 5_000
        assert fixed["payment"]["amount_paid_paise"] == 95_000
