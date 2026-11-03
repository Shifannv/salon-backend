"""0059 on disposable local PostgreSQL: the bank account number is stored encrypted, shown masked."""

from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.repositories.wallet_repository import WalletRepository
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB
from tests.integration.test_payout_proof_sql import new_request, proof_db  # noqa: F401

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

SQL = Path(__file__).parents[2] / "migrations/sql/0059_payout_account_encryption.sql"
NUMBER = "123456789012"


@pytest.fixture(scope="module")
def enc_db(proof_db):  # noqa: F811
    import asyncio

    async def install():
        env = SafetyEnv(proof_db)
        try:
            async with env.session() as session:
                for statement in SQL.read_text(encoding="utf-8").split("\n-- statement --\n"):
                    if statement.strip():
                        await session.execute(text(statement))
                await session.commit()
        finally:
            await env.engine.dispose()

    asyncio.run(install())
    return proof_db


@pytest.fixture
async def env(enc_db):
    environment = SafetyEnv(enc_db)
    yield environment
    await environment.engine.dispose()


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setattr(settings, "payout_encryption_key", SecretStr(Fernet.generate_key().decode()))


async def owner_of(env, salon_id):
    async with env.session() as session:
        return str((await session.execute(text("select owner_id from salons where id=cast(:s as uuid)"), {"s": salon_id})).scalar_one())


async def save_account(env, owner, **values):
    async with env.session() as session:
        return await PlatformRepository(session).update_payout_account(owner, values, lambda view: None)


async def raw_row(env, salon_id):
    async with env.session() as session:
        return (await session.execute(
            text("select bank_account_number, bank_account_last4, ifsc from salon_payout_accounts where salon_id=cast(:s as uuid)"),
            {"s": salon_id})).mappings().one()


BANK = {"account_holder_name": "Alex Owner", "bank_account_number": NUMBER, "ifsc": "HDFC0001234", "bank_name": "HDFC"}


async def test_number_is_stored_encrypted_and_shown_as_last_four(env, key):
    _, salon = await new_request(env)
    owner = await owner_of(env, salon)
    shown = await save_account(env, owner, **BANK)
    assert shown["bank_account_last4"] == "9012" and shown["ifsc"] == "HDFC0001234"
    row = await raw_row(env, salon)
    assert row["bank_account_number"].startswith("enc:v1:") and NUMBER not in row["bank_account_number"]
    assert row["bank_account_last4"] == "9012"


async def test_history_keeps_only_the_last_four_digits(env, key):
    _, salon = await new_request(env)
    await save_account(env, await owner_of(env, salon), **BANK)
    async with env.session() as session:
        states = (await session.execute(
            text("select after_state::text from salon_payout_account_history where salon_id=cast(:s as uuid)"),
            {"s": salon})).scalars().all()
    assert states and all(NUMBER not in s and "enc:v1" not in s and '"9012"' in s for s in states)


async def test_admin_reveal_returns_the_full_number_and_the_owner_view_never_does(env, key):
    request_id, salon = await new_request(env)
    owner = await owner_of(env, salon)
    await save_account(env, owner, **BANK)
    async with env.session() as session:
        account = await WalletRepository(session).payout_account_for_request(request_id)
    assert account["bank_account_number"] == NUMBER
    assert account["ifsc"] == "HDFC0001234" and "salon_id" not in account


async def test_a_plaintext_row_from_before_the_migration_still_masks_and_reveals(env):
    request_id, salon = await new_request(env)
    async with env.session() as session:
        await session.execute(text(
            "insert into salon_payout_accounts(salon_id, account_holder_name, bank_account_number, ifsc) "
            "values (cast(:s as uuid), 'Old Owner', :n, 'SBIN0001234')"), {"s": salon, "n": NUMBER})
        await session.commit()
        masked = (await session.execute(
            text("select bank_account_last4 from salon_payout_account_masked(cast(:s as uuid))"), {"s": salon})).scalar_one()
        account = await WalletRepository(session).payout_account_for_request(request_id)
    assert masked == "9012" and account["bank_account_number"] == NUMBER


async def test_without_a_key_the_number_is_stored_as_before_with_last_four(env, monkeypatch):
    monkeypatch.setattr(settings, "payout_encryption_key", None)
    _, salon = await new_request(env)
    await save_account(env, await owner_of(env, salon), **BANK)
    row = await raw_row(env, salon)
    assert row["bank_account_number"] == NUMBER and row["bank_account_last4"] == "9012"


async def test_clearing_the_number_clears_the_last_four_and_the_dependent_bank_fields(env, key):
    _, salon = await new_request(env)
    owner = await owner_of(env, salon)
    await save_account(env, owner, **BANK, upi_id="alex@okbank")
    shown = await save_account(env, owner, account_holder_name="Alex Owner", upi_id="alex@okbank", bank_account_number=None)
    row = await raw_row(env, salon)
    assert row["bank_account_number"] is None and row["bank_account_last4"] is None and row["ifsc"] is None
    assert shown["bank_account_last4"] is None


async def test_editing_other_fields_keeps_the_encrypted_number(env, key):
    _, salon = await new_request(env)
    owner = await owner_of(env, salon)
    await save_account(env, owner, **BANK)
    before = await raw_row(env, salon)
    await save_account(env, owner, account_holder_name="Alex Owner", upi_id="alex@okbank")
    assert await raw_row(env, salon) == before


async def test_the_database_refuses_malformed_or_unmasked_values(env):
    _, salon = await new_request(env)
    for number, last4 in (("not-a-number", None), ("enc:v1:" + "A" * 80, None), ("12345", None), (NUMBER, "12ab")):
        async with env.session() as session:
            with pytest.raises(IntegrityError):
                await session.execute(text(
                    "insert into salon_payout_accounts(salon_id, account_holder_name, bank_account_number, "
                    "bank_account_last4, ifsc) values (cast(:s as uuid), 'X Y', :n, :l, 'SBIN0001234')"),
                    {"s": salon, "n": number, "l": last4})
            await session.rollback()


async def test_backfill_encrypts_legacy_rows_without_touching_history_or_updated_at(env, key):
    from app.infrastructure.db.payout_backfill import convert_payout_accounts

    request_id, salon = await new_request(env)
    async with env.session() as session:
        # Earlier tests in this database wrote rows under their own throwaway keys.
        await session.execute(text("delete from salon_payout_accounts"))
        await session.execute(text(
            "insert into salon_payout_accounts(salon_id, account_holder_name, bank_account_number, ifsc) "
            "values (cast(:s as uuid), 'Old Owner', :n, 'SBIN0001234')"), {"s": salon, "n": NUMBER})
        await session.commit()

    async def stamp():
        async with env.session() as session:
            return (await session.execute(text(
                "select updated_at, (select count(*) from salon_payout_account_history "
                "where salon_id = cast(:s as uuid)) from salon_payout_accounts "
                "where salon_id = cast(:s as uuid)"), {"s": salon})).one()

    before = await stamp()

    async with env.session() as session:
        dry = await convert_payout_accounts(session)
        assert dry["eligible"] >= 1 and dry["converted"] == 0
        await session.rollback()
    assert (await raw_row(env, salon))["bank_account_number"] == NUMBER

    async with env.session() as session:
        done = await convert_payout_accounts(session, apply=True)
        await session.commit()
    assert done["converted"] >= 1
    row = await raw_row(env, salon)
    assert row["bank_account_number"].startswith("enc:v1:") and row["bank_account_last4"] == "9012"
    assert await stamp() == before

    async with env.session() as session:
        account = await WalletRepository(session).payout_account_for_request(request_id)
        disabled = (await session.execute(text(
            "select count(*) from pg_trigger where tgrelid = 'public.salon_payout_accounts'::regclass "
            "and tgname like 't_salon_payout_accounts_%' and tgenabled = 'D'"))).scalar_one()
    assert account["bank_account_number"] == NUMBER and disabled == 0

    async with env.session() as session:
        back = await convert_payout_accounts(session, decrypt=True, apply=True)
        await session.commit()
    assert back["converted"] >= 1 and (await raw_row(env, salon))["bank_account_number"] == NUMBER


async def test_backfill_refuses_to_encrypt_without_a_key(env, monkeypatch):
    from app.infrastructure.db.payout_backfill import convert_payout_accounts

    monkeypatch.setattr(settings, "payout_encryption_key", None)
    async with env.session() as session:
        with pytest.raises(RuntimeError, match="PAYOUT_ENCRYPTION_KEY"):
            await convert_payout_accounts(session, apply=True)


async def test_backfill_failure_rolls_back_rows_and_trigger_state(env, key):
    from app.infrastructure.db import payout_backfill

    _, first_salon = await new_request(env)
    _, second_salon = await new_request(env)
    async with env.session() as session:
        await session.execute(text("delete from salon_payout_accounts"))
        for salon in (first_salon, second_salon):
            await session.execute(
                text(
                    "insert into salon_payout_accounts"
                    "(salon_id, account_holder_name, bank_account_number, ifsc) "
                    "values (cast(:s as uuid), 'Old Owner', :n, 'SBIN0001234')"
                ),
                {"s": salon, "n": NUMBER},
            )
        await session.commit()

    original_encrypt = payout_backfill.encrypt_field
    calls = 0

    def fail_second(value, binding):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic conversion failure")
        return original_encrypt(value, binding)

    async with env.session() as session:
        with (
            patch.object(payout_backfill, "encrypt_field", fail_second),
            pytest.raises(RuntimeError, match="synthetic conversion failure"),
        ):
            await payout_backfill.convert_payout_accounts(session, apply=True)
        await session.rollback()

    async with env.session() as session:
        rows = (
            await session.execute(
                text(
                    "select bank_account_number, bank_account_last4 "
                    "from salon_payout_accounts order by salon_id"
                )
            )
        ).all()
        disabled = (
            await session.execute(
                text(
                    "select count(*) from pg_trigger "
                    "where tgrelid = 'public.salon_payout_accounts'::regclass "
                    "and tgname like 't_salon_payout_accounts_%' and tgenabled = 'D'"
                )
            )
        ).scalar_one()
    assert rows == [(NUMBER, None), (NUMBER, None)]
    assert disabled == 0


async def test_masking_function_is_not_executable_by_browser_roles(env):
    async with env.session() as session:
        privileges = (
            await session.execute(
                text(
                    "select has_function_privilege('anon', 'public.salon_payout_account_masked(uuid)', 'execute'), "
                    "has_function_privilege('authenticated', 'public.salon_payout_account_masked(uuid)', 'execute'), "
                    "has_function_privilege('service_role', 'public.salon_payout_account_masked(uuid)', 'execute')"
                )
            )
        ).one()
    assert privileges == (False, False, True)
