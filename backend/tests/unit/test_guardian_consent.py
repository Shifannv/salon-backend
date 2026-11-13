"""Age policy and the guardian approval flow, against an in-memory repository."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.application.ports.messaging_gateway import SendOutcome
from app.application.use_cases.guardian_consent import GuardianConsentUseCases
from app.core.exceptions import (
    BirthDateRequiredError,
    ConflictError,
    ForbiddenError,
    GuardianConsentRequiredError,
    ServiceUnavailableError,
    TooManyRequestsError,
    UnderMinimumAgeError,
    ValidationError,
)
from app.domain.entities.profile import Role
from app.domain.services.age_policy import age_band, age_on, booking_access, is_plausible_birth_date
from app.infrastructure.messaging.fake_gateway import FakeMessagingGateway
from tests.conftest import make_profile

TODAY = date(2026, 11, 8)
NOW = datetime(2026, 11, 8, 6, 0, tzinfo=UTC)
GUARDIAN = "+919812345678"


class MemoryAges:
    """Just enough of AgeRepository for the use case."""

    def __init__(self, birth: date | None = None) -> None:
        self.birth = birth
        self.row: dict | None = None
        self.history_sends = 0
        self.history_last: datetime | None = None

    async def birth_date(self, user_id):
        return self.birth

    async def set_birth_date(self, user_id, birth_date):
        self.birth = self.birth or birth_date
        return self.birth

    async def open_guardian_request(self, user_id):
        return dict(self.row) if self.row and self.row["status"] in {"pending", "approved"} else None

    async def recent_sends(self, user_id, since):
        total = self.history_sends + (self.row["sends"] if self.row else 0)
        last = self.row["last_sent_at"] if self.row else self.history_last
        return total, last

    async def lock_profile(self, user_id):
        return None

    async def start_request(self, user_id, phone_hash, last4, code_hash, expires_at):
        self.row = {"id": "g1", "status": "pending", "guardian_phone_hash": phone_hash, "guardian_phone_last4": last4,
                    "code_hash": code_hash, "code_expires_at": expires_at, "attempts": 0, "sends": 1,
                    "last_sent_at": NOW}

    async def resend(self, request_id, phone_hash, last4, code_hash, expires_at):
        self.row.update(guardian_phone_hash=phone_hash, guardian_phone_last4=last4, code_hash=code_hash,
                        code_expires_at=expires_at, attempts=0, sends=self.row["sends"] + 1, last_sent_at=NOW)

    async def count_attempt(self, request_id):
        self.row["attempts"] += 1

    async def clear_code(self, request_id):
        self.row["code_hash"] = None

    async def approve(self, request_id):
        self.row.update(status="approved", code_hash=None)

    async def revoke(self, request_id):
        self.history_sends += self.row["sends"]
        self.history_last = self.row["last_sent_at"]
        self.row = None

    async def commit(self):
        return None

    async def rollback(self):
        return None


def settings(**over):
    base = {"account_deletion_secret": "s" * 32, "environment": "test", "guardian_test_otps": "",
            "guardian_test_otps_until": None}
    return SimpleNamespace(**{**base, **over})


def make(birth=None, *, connected=True, gateway=None, now=NOW, **cfg):
    repo = MemoryAges(birth)
    gw = gateway or FakeMessagingGateway()
    uc = GuardianConsentUseCases(repo, gw, settings(**cfg), provider_connected=connected, clock=lambda: now)
    return uc, repo, gw


CUSTOMER = make_profile(role=Role.customer)
TEEN = date(2012, 3, 1)  # 14
ADULT = date(2000, 1, 1)
KID = date(2018, 1, 1)  # 8


def last_code(gw: FakeMessagingGateway) -> str:
    return gw.sent[-1].text.split()[1]


# ------------------------------------------------------------------ pure policy
def test_age_counts_whole_years_and_respects_the_birthday():
    assert age_on(date(2013, 11, 8), TODAY) == 13
    assert age_on(date(2013, 11, 9), TODAY) == 12
    assert age_on(date(2008, 11, 8), TODAY) == 18


@pytest.mark.parametrize(("birth", "band"), [
    (None, "unknown"), (date(2013, 11, 9), "child"), (date(2013, 11, 8), "teen"),
    (date(2008, 11, 9), "teen"), (date(2008, 11, 8), "adult"),
])
def test_age_bands_switch_exactly_on_13_and_18(birth, band):
    assert age_band(birth, TODAY) == band


def test_booking_access_rules():
    assert booking_access(ADULT, False, TODAY).allowed
    assert booking_access(TEEN, True, TODAY).allowed
    assert booking_access(TEEN, False, TODAY).reason == "guardian_consent_required"
    assert booking_access(KID, True, TODAY).reason == "under_minimum_age"
    assert booking_access(None, True, TODAY).reason == "birth_date_required"


def test_implausible_birth_dates_are_refused():
    assert not is_plausible_birth_date(date(2027, 1, 1), TODAY)
    assert not is_plausible_birth_date(date(1890, 1, 1), TODAY)
    assert is_plausible_birth_date(date(1990, 5, 5), TODAY)


# ------------------------------------------------------------------ birth date
async def test_a_teen_can_save_a_birth_date_and_is_then_locked_out_of_booking():
    uc, _, _ = make()
    status = await uc.set_birth_date(CUSTOMER, TEEN)
    assert status["age_band"] == "teen" and status["booking_allowed"] is False
    assert status["block_reason"] == "guardian_consent_required"
    with pytest.raises(GuardianConsentRequiredError):
        await uc.assert_can_book(CUSTOMER)


async def test_an_adult_can_book_and_an_unknown_age_cannot():
    uc, _, _ = make(ADULT)
    await uc.assert_can_book(CUSTOMER)
    uc, _, _ = make(None)
    with pytest.raises(BirthDateRequiredError):
        await uc.assert_can_book(CUSTOMER)


async def test_under_13_is_refused_and_nothing_is_stored():
    uc, repo, _ = make()
    with pytest.raises(UnderMinimumAgeError):
        await uc.set_birth_date(CUSTOMER, KID)
    assert repo.birth is None


async def test_the_birth_date_cannot_be_changed_to_become_an_adult():
    uc, repo, _ = make(TEEN)
    with pytest.raises(ForbiddenError, match="Contact support"):
        await uc.set_birth_date(CUSTOMER, ADULT)
    assert repo.birth == TEEN
    assert (await uc.set_birth_date(CUSTOMER, TEEN))["age_band"] == "teen"  # same value is fine


async def test_future_dates_are_refused():
    uc, _, _ = make()
    with pytest.raises(ValidationError):
        await uc.set_birth_date(CUSTOMER, date(2027, 1, 1))


async def test_staff_have_no_age_check():
    staff = make_profile(role=Role.staff)
    uc, _, _ = make(None)
    await uc.assert_can_book(staff)
    with pytest.raises(ForbiddenError):
        await uc.set_birth_date(staff, ADULT)


async def test_an_owner_booking_as_a_customer_gets_the_same_age_gate_as_a_new_customer():
    owner = make_profile(role=Role.owner)
    uc, _, _ = make(None)
    with pytest.raises(BirthDateRequiredError):
        await uc.assert_can_book(owner)
    status = await uc.set_birth_date(owner, ADULT)
    assert status["booking_allowed"] is True
    await uc.assert_can_book(owner)


# ------------------------------------------------------------------ guardian flow
async def test_the_guardian_code_unlocks_booking_and_is_never_stored_in_clear():
    uc, repo, gw = make(TEEN)
    status = await uc.request_guardian(CUSTOMER, GUARDIAN)
    assert status["guardian_state"] == "pending" and status["guardian_phone_last4"] == "5678"
    assert GUARDIAN not in repr(repo.row) and last_code(gw) not in repr(repo.row)
    status = await uc.verify_guardian(CUSTOMER, last_code(gw))
    assert status["guardian_state"] == "approved" and status["booking_allowed"] is True
    await uc.assert_can_book(CUSTOMER)


async def test_a_wrong_code_is_refused_and_five_wrong_codes_burn_the_code():
    uc, repo, gw = make(TEEN)
    await uc.request_guardian(CUSTOMER, GUARDIAN)
    good = last_code(gw)
    bad = "000000" if good != "000000" else "111111"
    for _ in range(5):
        with pytest.raises(ValidationError, match="not right"):
            await uc.verify_guardian(CUSTOMER, bad)
    with pytest.raises(TooManyRequestsError):
        await uc.verify_guardian(CUSTOMER, good)
    assert repo.row["status"] == "pending" and repo.row["code_hash"] is None


async def test_an_expired_code_is_refused():
    uc, _, gw = make(TEEN)
    await uc.request_guardian(CUSTOMER, GUARDIAN)
    code = last_code(gw)
    uc.clock = lambda: NOW + timedelta(minutes=11)
    with pytest.raises(ValidationError, match="expired"):
        await uc.verify_guardian(CUSTOMER, code)


async def test_resending_is_rate_limited_and_capped():
    uc, _, _ = make(TEEN)
    await uc.request_guardian(CUSTOMER, GUARDIAN)
    with pytest.raises(TooManyRequestsError, match="Wait a minute"):
        await uc.request_guardian(CUSTOMER, GUARDIAN)
    for _ in range(4):
        uc.clock = lambda t=uc.clock(): t + timedelta(minutes=2)
        await uc.request_guardian(CUSTOMER, GUARDIAN)
        uc.repository.row["last_sent_at"] = NOW - timedelta(hours=1)
    with pytest.raises(TooManyRequestsError, match="Too many codes"):
        await uc.request_guardian(CUSTOMER, GUARDIAN)


async def test_guardian_cannot_be_the_teens_own_number_or_requested_by_an_adult():
    uc, _, _ = make(TEEN)
    with pytest.raises(ValidationError, match="own phone number"):
        await uc.request_guardian(CUSTOMER, CUSTOMER.phone)
    uc, _, _ = make(ADULT)
    with pytest.raises(ValidationError, match="13 to 17"):
        await uc.request_guardian(CUSTOMER, GUARDIAN)


async def test_without_an_sms_provider_nothing_is_sent_and_booking_stays_locked():
    uc, repo, gw = make(TEEN, connected=False)
    with pytest.raises(ServiceUnavailableError, match="not available yet"):
        await uc.request_guardian(CUSTOMER, GUARDIAN)
    assert repo.row is None and gw.attempts == []
    assert (await uc.status(CUSTOMER))["guardian_code_available"] is False


async def test_a_refused_send_leaves_no_request_behind():
    gw = FakeMessagingGateway(outcome=SendOutcome(accepted=False, reason="blocked"))
    uc, _, _ = make(TEEN, gateway=gw)
    with pytest.raises(ServiceUnavailableError):
        await uc.request_guardian(CUSTOMER, GUARDIAN)


async def test_test_numbers_work_without_a_provider_until_they_expire_and_send_nothing():
    cfg = {"guardian_test_otps": f"{GUARDIAN}=123456", "guardian_test_otps_until": NOW + timedelta(days=1)}
    uc, _, gw = make(TEEN, connected=False, **cfg)
    await uc.request_guardian(CUSTOMER, GUARDIAN)
    assert gw.attempts == []
    assert (await uc.verify_guardian(CUSTOMER, "123456"))["booking_allowed"] is True

    uc, _, _ = make(TEEN, connected=False, now=NOW + timedelta(days=2), **cfg)
    with pytest.raises(ServiceUnavailableError):
        await uc.request_guardian(CUSTOMER, GUARDIAN)


async def test_a_second_request_after_approval_conflicts_and_revoking_locks_again():
    uc, _, gw = make(TEEN)
    await uc.request_guardian(CUSTOMER, GUARDIAN)
    await uc.verify_guardian(CUSTOMER, last_code(gw))
    with pytest.raises(ConflictError):
        await uc.request_guardian(CUSTOMER, GUARDIAN)
    status = await uc.revoke_guardian(CUSTOMER)
    assert status["booking_allowed"] is False and status["guardian_state"] == "none"


async def test_withdrawing_and_starting_again_does_not_reset_the_send_limit():
    uc, _, _ = make(TEEN)
    for _ in range(5):
        await uc.request_guardian(CUSTOMER, GUARDIAN)
        await uc.revoke_guardian(CUSTOMER)
        uc.repository.history_last = NOW - timedelta(hours=1)
    with pytest.raises(TooManyRequestsError, match="Too many codes"):
        await uc.request_guardian(CUSTOMER, GUARDIAN)
