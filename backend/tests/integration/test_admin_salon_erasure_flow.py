"""Admin salon deletion end to end on the prepared schema: readiness -> prepare -> erase.

Real database and real SQL; the payment provider, object storage, Auth admin and cache are fakes.
"""

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.use_cases.admin_salon_erasure import AdminSalonErasureUseCases
from app.core.exceptions import ForbiddenError, NotFoundError, SalonNotReadyForDeletionError
from app.domain.entities.payment import GatewayCapability, RefundStatus
from app.domain.entities.profile import Role
from app.domain.value_objects.money import Money
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.repositories.wallet_repository import WalletRepository
from tests.conftest import make_profile
from tests.integration import salon_erasure_support as support
from tests.integration.salon_erasure_support import count, seed_money
from tests.integration.test_payment_ledger_sql import TEST_DB

env = support.env
prepared_db = support.prepared_db

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

BUCKET = "media"


class FakeGateway:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.refunds: list = []

    def supports(self, capability):
        return capability == GatewayCapability.refunds

    async def refund(self, request):
        if self.fail:
            raise RuntimeError("provider down")
        self.refunds.append(request)
        return SimpleNamespace(refund_ref="rf_1", status=RefundStatus.processed, failure_code=None)


class FakeStorage:
    def __init__(self):
        self.deleted: list[str] = []

    def get_public_url(self, bucket, path):
        return f"https://cdn.test/{bucket}/{path}"

    async def erasure_lock_paths(self, path):
        return [path]

    async def erasure_paths(self, path):
        return [path]

    async def delete_object(self, bucket, path):
        self.deleted.append(path)


class FakeMediaReferences:
    async def lock_media_url(self, url):
        return None

    async def media_url_is_referenced(self, url):
        return False


class FakeAuth:
    def __init__(self, users):
        self.users = set(users)
        self.deleted: list[str] = []

    async def get_user(self, user_id):
        return SimpleNamespace(id=user_id) if user_id in self.users else None

    async def delete_user(self, user_id):
        self.users.discard(user_id)
        self.deleted.append(user_id)


class FakeCache:
    def __init__(self):
        self.cleared: list[str] = []

    async def delete_prefix(self, prefix, *, strict=False):
        self.cleared.append(prefix)


async def build(env, f, *, gateway=None, auth_users=()):
    async def release():
        return None

    session = env.session()
    storage, auth, cache = FakeStorage(), FakeAuth(auth_users or [f["owner"]]), FakeCache()
    use_cases = AdminSalonErasureUseCases(
        PlatformRepository(session), WalletRepository(session), auth, storage, cache,
        FakeMediaReferences(), release, BUCKET, lambda provider: gateway, storage_required=False,
    )
    return use_cases, session, storage, auth, cache


async def add_online_payment(env, f, booking, status="captured", amount="250.00"):
    await env.sql(
        """insert into booking_payments(booking_id, salon_id, channel, purpose, amount, intent_reference, provider,
                payment_ref, status, settlement_model, method)
           values(:b, :s, 'gateway', 'full', :a, :ref, 'razorpay', :pref, :st, 'platform_collect', 'online')""",
        b=booking["id"], s=f["salon"], a=Decimal(amount), ref="int-" + uuid4().hex, pref="pay_" + uuid4().hex, st=status)


@pytest.fixture
async def admin(env):
    """A real super-admin profile, because the refund ledger records who acted."""

    admin_id = str(uuid4())
    await env.sql("insert into auth.users(id, email) values(:i, :e)", i=admin_id, e=admin_id + "@example.test")
    # The new-user trigger creates the profile; promote it.
    await env.sql("update profiles set role = cast('super_admin' as user_role) where id = :i", i=admin_id)
    return make_profile(id=admin_id, role=Role.super_admin)


async def test_a_non_admin_cannot_read_or_erase(env):
    f = await env.seed()
    use_cases, session, *_ = await build(env, f)
    async with session:
        for call in (use_cases.readiness, use_cases.erase):
            with pytest.raises(ForbiddenError):
                await call(make_profile(role=Role.owner), f["salon"])


async def test_an_open_booking_with_an_online_payment_blocks_until_refunded_then_it_can_be_erased(env, admin):
    f = await env.seed()
    booking = await env.book(f)
    await add_online_payment(env, f, booking)
    gateway = FakeGateway()
    use_cases, session, _, _, _ = await build(env, f, gateway=gateway)
    async with session:
        before = await use_cases.readiness(admin, f["salon"])
        assert before["can_delete"] is False
        assert before["open_bookings"] == 1
        assert {"open_bookings", "refunds_due"} <= set(before["blockers"])
        assert before["refunds_due_paise"] == 25000

        with pytest.raises(SalonNotReadyForDeletionError):
            await use_cases.erase(admin, f["salon"])
        assert await count(env, "salons", "id = :s", s=f["salon"]) == 1

        after = await use_cases.prepare(admin, f["salon"], "auto")
        assert after["can_delete"] is True, after
        assert [r.amount for r in gateway.refunds] == [Money(Decimal("250.00"))]
        assert (await env.sql("select is_active from salons where id = :s", s=f["salon"]))[0]["is_active"] is False
        assert (await env.sql("select status from bookings where id = :b", b=booking["id"]))[0]["status"] == "cancelled"

        # Repeating prepare never refunds twice.
        await use_cases.prepare(admin, f["salon"], "auto")
        assert len(gateway.refunds) == 1

    # A fresh transaction, as a separate request would be.
    use_cases, session, _, auth, cache = await build(env, f, gateway=gateway)
    async with session:
        await use_cases.erase(admin, f["salon"])
    assert await count(env, "salons", "id = :s", s=f["salon"]) == 0
    assert await count(env, "bookings", "salon_id = :s", s=f["salon"]) == 0
    assert await count(env, "booking_payments", "salon_id = :s", s=f["salon"]) == 0
    assert f["salon"] in "".join(cache.cleared)
    assert auth.deleted == [f["owner"]]  # the owner had no other salon
    assert (await env.sql("select status from salon_erasure_jobs where salon_id = :s", s=f["salon"]))[0]["status"] == "complete"
    assert await count(env, "profiles", "id = :o", o=f["owner"]) == 0


async def test_manual_refund_is_recorded_so_the_salon_can_be_deleted(env, admin):
    f = await env.seed()
    booking = await env.book(f)
    await add_online_payment(env, f, booking)
    use_cases, session, *_ = await build(env, f, gateway=None)
    async with session:
        state = await use_cases.prepare(admin, f["salon"], "manual")
        assert state["can_delete"] is True, state
        refund = (await env.sql("select status, refund_ref, kind from payment_refunds where booking_id = :b", b=booking["id"]))[0]
        assert (refund["status"], refund["refund_ref"], refund["kind"]) == ("processed", "manual", "closure")


async def test_a_refund_the_provider_cannot_take_keeps_the_salon_blocked(env, admin):
    f = await env.seed()
    booking = await env.book(f)
    await add_online_payment(env, f, booking)
    use_cases, session, *_ = await build(env, f, gateway=FakeGateway(fail=True))
    async with session:
        state = await use_cases.prepare(admin, f["salon"], "auto")
        assert state["can_delete"] is False
        assert "refunds_due" in state["blockers"]
        with pytest.raises(SalonNotReadyForDeletionError):
            await use_cases.erase(admin, f["salon"])


async def test_a_pending_payout_request_blocks_deletion(env, admin):
    f = await env.seed()
    await env.sql(
        """insert into salon_payout_requests(salon_id, amount_paise, scheduled_for, idempotency_key, request_hash)
           values(:s, 10000, current_date, :k, repeat('a', 64))""", s=f["salon"], k="payout-" + uuid4().hex)
    use_cases, session, *_ = await build(env, f)
    async with session:
        state = await use_cases.readiness(admin, f["salon"])
        assert state["blockers"] == ["payout_requests_pending"]
        with pytest.raises(SalonNotReadyForDeletionError):
            await use_cases.erase(admin, f["salon"])


async def test_an_owner_with_another_salon_keeps_their_login(env, admin):
    f = await env.seed()
    await seed_money(env, f)
    # Pay the payout and clear it so nothing blocks, then give the owner a second salon.
    second = await env.seed()
    await env.sql("update salons set owner_id = :o where id = :s", o=f["owner"], s=second["salon"])
    use_cases, session, _, auth, _ = await build(env, f)
    async with session:
        state = await use_cases.readiness(admin, f["salon"])
        assert state["can_delete"] is False  # the seeded booking is still open
        await use_cases.prepare(admin, f["salon"], "manual")
        await use_cases.erase(admin, f["salon"])
    assert await count(env, "salons", "id = :s", s=second["salon"]) == 1
    assert await count(env, "profiles", "id = :o", o=f["owner"]) == 1
    assert auth.deleted == []


async def test_an_unknown_salon_is_not_found(env, admin):
    f = await env.seed()
    use_cases, session, *_ = await build(env, f)
    async with session:
        with pytest.raises(NotFoundError):
            await use_cases.readiness(admin, str(uuid4()))
