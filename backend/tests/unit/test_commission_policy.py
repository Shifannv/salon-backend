"""Which commission applies, and the super admin's payment settings (in-memory repository)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal as D
from typing import Any

import pytest

from app.application.use_cases.payment_settings import PaymentSettingsUseCases
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.domain.entities.profile import Role
from app.domain.services.commission_policy import check_rate, resolve_commission_policy
from tests.conftest import make_profile, make_super_admin

NOW = datetime(2026, 11, 2, tzinfo=UTC)


def resolve(**kw):
    values: dict[str, Any] = {
        "salon_rate": None, "platform_rate": None, "platform_base": None, "platform_version": 3,
        "env_rate": None, "env_base": None, "env_version": "v1",
    }
    values.update(kw)
    return resolve_commission_policy(**values)


class TestResolve:
    def test_nothing_set_is_no_policy_never_a_default(self):
        assert resolve() is None

    def test_a_rate_without_a_base_is_no_policy(self):
        assert resolve(platform_rate=D("10")) is None
        assert resolve(salon_rate=D("10")) is None

    def test_platform_rate_and_base(self):
        policy = resolve(platform_rate=D("10"), platform_base="online_amount")
        assert (policy.rate_percent, policy.base, policy.version, policy.source) == (
            D("10"), "online_amount", "db-3", "platform")

    def test_salon_rate_wins_and_uses_the_platform_base(self):
        policy = resolve(salon_rate=D("4"), platform_rate=D("10"), platform_base="booking_total")
        assert (policy.rate_percent, policy.base, policy.version, policy.source) == (
            D("4"), "booking_total", "db-3-salon", "salon")

    def test_zero_percent_is_a_rate(self):
        assert resolve(salon_rate=D("0"), platform_base="online_amount").rate_percent == D("0")

    def test_environment_is_only_a_fallback(self):
        policy = resolve(env_rate=D("8"), env_base="online_amount")
        assert (policy.rate_percent, policy.version, policy.source) == (D("8"), "v1", "environment")
        admin = resolve(platform_rate=D("9"), platform_base="online_amount", env_rate=D("8"), env_base="booking_total")
        assert admin.rate_percent == D("9") and admin.base == "online_amount"

    @pytest.mark.parametrize("rate", [D("-0.01"), D("100.01"), D("1.234")])
    def test_a_bad_rate_is_refused(self, rate):
        with pytest.raises(ValueError):
            check_rate(rate)

    @pytest.mark.parametrize("rate", [D("0"), D("7.5"), D("100")])
    def test_a_good_rate_is_accepted(self, rate):
        assert check_rate(rate) == rate


class FakeSettings:
    def __init__(self) -> None:
        self.row = {"commission_rate_percent": None, "commission_base": None, "min_payout_paise": 10_000,
                    "policy_version": 1, "updated_at": NOW}
        self.overrides: dict[str, dict[str, Any]] = {}
        self.salons = {"salon-1"}

    async def get_settings(self):
        return dict(self.row)

    async def update_settings(self, rate, base, minimum, actor_id):
        changed = (rate, base) != (self.row["commission_rate_percent"], self.row["commission_base"])
        self.row.update(commission_rate_percent=rate, commission_base=base, min_payout_paise=minimum,
                        policy_version=self.row["policy_version"] + (1 if changed else 0))
        return dict(self.row)

    async def salon_exists(self, salon_id):
        return salon_id in self.salons

    async def get_override(self, salon_id):
        return self.overrides.get(salon_id)

    async def set_override(self, salon_id, rate, note, actor_id):
        self.overrides[salon_id] = {"commission_rate_percent": rate, "note": note, "updated_at": NOW}

    async def clear_override(self, salon_id):
        self.overrides.pop(salon_id, None)


def uc(repo: FakeSettings, env_rate=None, env_base=None) -> PaymentSettingsUseCases:
    return PaymentSettingsUseCases(repo, env_rate=env_rate, env_base=env_base, env_version="v1")


class TestSettings:
    async def test_only_a_super_admin(self):
        for role in (Role.owner, Role.staff, Role.customer):
            actor = make_profile(role=role)
            with pytest.raises(ForbiddenError):
                await uc(FakeSettings()).get(actor)
            with pytest.raises(ForbiddenError):
                await uc(FakeSettings()).update(actor, rate=D("10"), base="online_amount", min_payout_paise=10_000)
            with pytest.raises(ForbiddenError):
                await uc(FakeSettings()).set_salon_rate(actor, "salon-1", rate=D("5"), note=None)
            with pytest.raises(ForbiddenError):
                await uc(FakeSettings()).clear_salon_rate(actor, "salon-1")

    async def test_fresh_install_has_no_rate_and_the_default_minimum(self):
        view = await uc(FakeSettings()).get(make_super_admin())
        assert view["commission_rate_percent"] is None and view["effective_rate_percent"] is None
        assert view["min_payout_paise"] == 10_000

    async def test_update_sets_rate_base_and_minimum_and_bumps_the_version(self):
        repo = FakeSettings()
        view = await uc(repo).update(make_super_admin(), rate=D("12.5"), base="booking_total", min_payout_paise=50_000)
        assert (view["commission_rate_percent"], view["commission_base"], view["min_payout_paise"]) == (
            D("12.5"), "booking_total", 50_000)
        assert view["policy_version"] == 2 and view["effective_source"] == "platform"

    async def test_changing_only_the_minimum_keeps_the_policy_version(self):
        repo = FakeSettings()
        await uc(repo).update(make_super_admin(), rate=D("10"), base="online_amount", min_payout_paise=10_000)
        view = await uc(repo).update(make_super_admin(), rate=D("10"), base="online_amount", min_payout_paise=20_000)
        assert view["policy_version"] == 2

    @pytest.mark.parametrize(("rate", "base"), [(D("10"), None), (None, "online_amount")])
    async def test_rate_and_base_go_together(self, rate, base):
        with pytest.raises(ValidationError):
            await uc(FakeSettings()).update(make_super_admin(), rate=rate, base=base, min_payout_paise=10_000)

    @pytest.mark.parametrize("rate", [D("-1"), D("101"), D("1.234")])
    async def test_a_bad_rate_is_refused(self, rate):
        with pytest.raises(ValidationError):
            await uc(FakeSettings()).update(make_super_admin(), rate=rate, base="online_amount", min_payout_paise=10_000)

    async def test_an_unknown_base_is_refused(self):
        with pytest.raises(ValidationError):
            await uc(FakeSettings()).update(make_super_admin(), rate=D("10"), base="everything", min_payout_paise=10_000)

    @pytest.mark.parametrize("minimum", [0, 99, 100_000_001])
    async def test_a_silly_minimum_is_refused(self, minimum):
        with pytest.raises(ValidationError):
            await uc(FakeSettings()).update(make_super_admin(), rate=None, base=None, min_payout_paise=minimum)

    async def test_both_can_be_cleared(self):
        repo = FakeSettings()
        await uc(repo).update(make_super_admin(), rate=D("10"), base="online_amount", min_payout_paise=10_000)
        view = await uc(repo).update(make_super_admin(), rate=None, base=None, min_payout_paise=10_000)
        assert view["commission_rate_percent"] is None

    async def test_the_environment_rate_shows_as_the_effective_one_until_the_admin_sets_one(self):
        view = await uc(FakeSettings(), env_rate=D("8"), env_base="online_amount").get(make_super_admin())
        assert view["commission_rate_percent"] is None
        assert (view["effective_rate_percent"], view["effective_source"]) == (D("8"), "environment")

    async def test_a_change_is_logged_without_anything_sensitive(self, caplog):
        with caplog.at_level("INFO"):
            await uc(FakeSettings()).update(make_super_admin(), rate=D("10"), base="online_amount", min_payout_paise=10_000)
        assert "payment settings changed" in caplog.text


class TestSalonRate:
    async def test_set_shows_the_effective_rate_and_clear_returns_to_the_platform_rate(self):
        repo = FakeSettings()
        admin = make_super_admin()
        await uc(repo).update(admin, rate=D("10"), base="online_amount", min_payout_paise=10_000)
        view = await uc(repo).set_salon_rate(admin, "salon-1", rate=D("4"), note="  launch deal  ")
        assert (view["commission_rate_percent"], view["note"], view["effective_rate_percent"],
                view["effective_source"]) == (D("4"), "launch deal", D("4"), "salon")
        cleared = await uc(repo).clear_salon_rate(admin, "salon-1")
        assert cleared["commission_rate_percent"] is None and cleared["effective_rate_percent"] == D("10")
        assert cleared["effective_source"] == "platform"

    async def test_an_unknown_salon_is_not_found(self):
        for call in (
            uc(FakeSettings()).get_salon_rate(make_super_admin(), "nope"),
            uc(FakeSettings()).set_salon_rate(make_super_admin(), "nope", rate=D("5"), note=None),
            uc(FakeSettings()).clear_salon_rate(make_super_admin(), "nope"),
        ):
            with pytest.raises(NotFoundError):
                await call

    async def test_a_bad_salon_rate_or_note_is_refused(self):
        with pytest.raises(ValidationError):
            await uc(FakeSettings()).set_salon_rate(make_super_admin(), "salon-1", rate=D("101"), note=None)
        with pytest.raises(ValidationError):
            await uc(FakeSettings()).set_salon_rate(make_super_admin(), "salon-1", rate=D("5"), note="x" * 201)
