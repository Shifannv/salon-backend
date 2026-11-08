"""Date of birth and guardian approval: who may book.

The date of birth can be set once, so a teenager cannot turn themselves into an adult later.
A 13 to 17 year old books only after a parent or guardian confirms a one-time code sent to the
guardian's own phone. The code and the guardian's number are stored only as keyed hashes.
"""

import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.application.ports.messaging_gateway import MessagingGateway, OutboundMessage
from app.core.config import Settings
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
from app.domain.entities.profile import Profile, Role
from app.domain.services.age_policy import (
    BookingAccess,
    age_band,
    booking_access,
    is_plausible_birth_date,
)
from app.infrastructure.db.repositories.age_repository import AgeRepository

CODE_TTL = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_SENDS = 5
SEND_WINDOW = timedelta(hours=24)
MAX_ATTEMPTS = 5
_LOCAL_SECRET = "local-guardian-secret-not-for-production"
_INDIA = ZoneInfo("Asia/Kolkata")


class GuardianConsentUseCases:
    def __init__(
        self,
        repository: AgeRepository,
        gateway: MessagingGateway,
        settings: Settings,
        *,
        provider_connected: bool,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repository = repository
        self.gateway = gateway
        self.settings = settings
        self.provider_connected = provider_connected
        self.clock = clock

    # ---------------------------------------------------------------- helpers
    def _today(self) -> date:
        return self.clock().astimezone(_INDIA).date()

    def _secret(self) -> str:
        if self.settings.account_deletion_secret:
            return self.settings.account_deletion_secret
        if self.settings.environment in {"local", "test"}:
            return _LOCAL_SECRET
        raise ServiceUnavailableError("Guardian approval is not configured")

    def _hash(self, purpose: str, value: str) -> str:
        return hmac.new(self._secret().encode(), f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()

    def _test_code(self, phone: str) -> str | None:
        """A fixed code for a registered test number, until the configured expiry."""

        raw = (self.settings.guardian_test_otps or "").strip()
        until = self.settings.guardian_test_otps_until
        if not raw or (until is not None and self.clock() >= until):
            return None
        if until is None and self.settings.environment not in {"local", "test"}:
            return None
        for pair in raw.split(","):
            number, _, code = pair.strip().partition("=")
            if number == phone:
                return code
        return None

    def _code_can_be_sent(self) -> bool:
        return self.provider_connected or bool((self.settings.guardian_test_otps or "").strip())

    @staticmethod
    def _require_customer(actor: Profile) -> None:
        if actor.role != Role.customer:
            raise ForbiddenError("Age checks apply to customer accounts")

    # ---------------------------------------------------------------- status
    async def access(self, actor: Profile) -> BookingAccess:
        if actor.role != Role.customer:
            return BookingAccess(True, "adult")
        birth = await self.repository.birth_date(actor.id)
        row = await self.repository.open_guardian_request(actor.id)
        await self.repository.rollback()
        return booking_access(birth, bool(row and row["status"] == "approved"), self._today())

    async def status(self, actor: Profile) -> dict:
        if actor.role != Role.customer:
            return {"age_band": "adult", "booking_allowed": True, "block_reason": None,
                    "guardian_state": "none", "guardian_phone_last4": None, "guardian_code_available": True}
        birth = await self.repository.birth_date(actor.id)
        row = await self.repository.open_guardian_request(actor.id)
        await self.repository.rollback()
        access = booking_access(birth, bool(row and row["status"] == "approved"), self._today())
        return {
            "age_band": access.band,
            "booking_allowed": access.allowed,
            "block_reason": access.reason,
            "guardian_state": row["status"] if row else "none",
            "guardian_phone_last4": row["guardian_phone_last4"] if row else None,
            "guardian_code_available": self._code_can_be_sent(),
        }

    async def assert_can_book(self, actor: Profile) -> None:
        access = await self.access(actor)
        if access.allowed:
            return
        if access.reason == "birth_date_required":
            raise BirthDateRequiredError("Add your date of birth to book")
        if access.reason == "under_minimum_age":
            raise UnderMinimumAgeError("You must be 13 or older to book")
        raise GuardianConsentRequiredError("A parent or guardian must approve your bookings first")

    # ---------------------------------------------------------------- birth date
    async def set_birth_date(self, actor: Profile, birth_date: date) -> dict:
        self._require_customer(actor)
        today = self._today()
        if not is_plausible_birth_date(birth_date, today):
            raise ValidationError("Enter a valid date of birth")
        if age_band(birth_date, today) == "child":
            raise UnderMinimumAgeError("Salones is for people aged 13 and over")
        stored = await self.repository.set_birth_date(actor.id, birth_date)
        if stored != birth_date:
            raise ForbiddenError("Your date of birth is already saved. Contact support to correct it")
        return await self.status(actor)

    # ---------------------------------------------------------------- guardian
    async def request_guardian(self, actor: Profile, guardian_phone: str) -> dict:
        self._require_customer(actor)
        birth = await self.repository.birth_date(actor.id)
        if age_band(birth, self._today()) != "teen":
            await self.repository.rollback()
            raise ValidationError("A guardian's approval is only needed for ages 13 to 17")
        if actor.phone and guardian_phone == actor.phone:
            await self.repository.rollback()
            raise ValidationError("Use your parent or guardian's own phone number")
        test_code = self._test_code(guardian_phone)
        if test_code is None and not self.provider_connected:
            await self.repository.rollback()
            raise ServiceUnavailableError(
                "Guardian approval by SMS is not available yet. Bookings stay locked until it is"
            )
        try:
            await self.repository.lock_profile(actor.id)
            row = await self.repository.open_guardian_request(actor.id)
            if row and row["status"] == "approved":
                raise ConflictError("A parent or guardian has already approved your bookings")
            now = self.clock()
            sent, last = await self.repository.recent_sends(actor.id, now - SEND_WINDOW)
            if sent >= MAX_SENDS:
                raise TooManyRequestsError("Too many codes were requested. Try again tomorrow")
            if last is not None and now - last < RESEND_COOLDOWN:
                raise TooManyRequestsError("Wait a minute before asking for another code")
            code = test_code or f"{secrets.randbelow(1_000_000):06d}"
            phone_hash = self._hash("phone", guardian_phone)
            code_hash = self._hash("code", f"{actor.id}:{code}")
            last4 = guardian_phone[-4:]
            if row:
                await self.repository.resend(row["id"], phone_hash, last4, code_hash, now + CODE_TTL)
            else:
                await self.repository.start_request(actor.id, phone_hash, last4, code_hash, now + CODE_TTL)
            if test_code is None:
                outcome = await self.gateway.send(OutboundMessage(
                    channel="sms",
                    recipient=guardian_phone,
                    text=(
                        f"Salones: {code} is your code to let a young person you look after book salon "
                        "visits. Do not share it unless you agree."
                    ),
                    idempotency_key=f"guardian:{actor.id}:{int(now.timestamp())}",
                ))
                if not outcome.accepted:
                    raise ServiceUnavailableError("The code could not be sent. Try again shortly")
            await self.repository.commit()
        except BaseException:
            await self.repository.rollback()
            raise
        return await self.status(actor)

    async def verify_guardian(self, actor: Profile, code: str) -> dict:
        self._require_customer(actor)
        try:
            await self.repository.lock_profile(actor.id)
            row = await self.repository.open_guardian_request(actor.id)
            if row is None or row["status"] != "pending" or not row["code_hash"]:
                raise ValidationError("Ask for a new code")
            expires = row["code_expires_at"]
            if expires is None or self.clock() >= expires:
                await self.repository.clear_code(row["id"])
                await self.repository.commit()
                raise ValidationError("That code has expired. Ask for a new one")
            if row["attempts"] >= MAX_ATTEMPTS:
                await self.repository.clear_code(row["id"])
                await self.repository.commit()
                raise TooManyRequestsError("Too many wrong codes. Ask for a new one")
            await self.repository.count_attempt(row["id"])
            expected = self._hash("code", f"{actor.id}:{code}")
            if not hmac.compare_digest(expected, row["code_hash"]):
                await self.repository.commit()
                raise ValidationError("That code is not right")
            await self.repository.approve(row["id"])
            await self.repository.commit()
        except BaseException:
            await self.repository.rollback()
            raise
        return await self.status(actor)

    async def revoke_guardian(self, actor: Profile) -> dict:
        self._require_customer(actor)
        try:
            await self.repository.lock_profile(actor.id)
            row = await self.repository.open_guardian_request(actor.id)
            if row is not None:
                await self.repository.revoke(row["id"])
            await self.repository.commit()
        except BaseException:
            await self.repository.rollback()
            raise
        return await self.status(actor)
