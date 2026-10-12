"""Account deletion: contact-bound verification, explicit confirmation, status."""

import re
from datetime import timedelta
from typing import Any

from app.application.ports.account_deletion_repository import AccountDeletionRepository
from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.auth_gateway import AuthGateway
from app.core.config import Settings
from app.core.exceptions import (
    ContactMismatchError,
    DeletionBlockedError,
    ForbiddenError,
    InvalidVerificationCodeError,
    NotFoundError,
    ServiceUnavailableError,
    TooManyRequestsError,
)
from app.core.tokens import digest, digests_match, new_token
from app.domain.entities.profile import Profile, Role
from app.domain.services.authorization import is_super_admin

_LOCAL_ENVIRONMENTS = {"local", "test"}
_LOCAL_SECRET = "local-development-account-deletion-secret"
_ELIGIBLE_ROLES = {Role.customer, Role.owner}


def normalize_contact(channel: str, value: str) -> str:
    """Canonical form used for comparison and hashing."""

    value = value.strip()
    if channel == "email":
        return value.lower()
    return "+" + re.sub(r"\D", "", value)


def mask_contact(channel: str, value: str) -> str:
    """Return a display-safe masked destination."""

    if channel == "email":
        local, _, domain = value.partition("@")
        return f"{local[:1]}***@{domain}"
    return "*" * max(len(value) - 4, 0) + value[-4:]


def deletion_stage(status: str, step_state: dict[str, Any]) -> str:
    """Coarse, PII-free progress label derived from the recorded steps."""

    if status == "completed":
        return "completed"
    if step_state.get("auth_banned") or step_state.get("db_erased"):
        return "erasing"
    if step_state.get("refunds_settled"):
        return "erasing"
    if step_state.get("refunds_issued"):
        return "waiting_for_refunds"
    if step_state.get("bookings_cancelled"):
        return "refunding"
    return "queued"


class AccountDeletionUseCases:
    """Authorizes and coordinates the user-facing deletion workflow."""

    def __init__(
        self,
        repository: AccountDeletionRepository,
        auth_gateway: AuthGateway,
        auth_admin: AuthAdminGateway,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.auth_gateway = auth_gateway
        self.auth_admin = auth_admin
        self.settings = settings

    def _secret(self) -> str:
        if self.settings.account_deletion_secret:
            return self.settings.account_deletion_secret
        if self.settings.environment in _LOCAL_ENVIRONMENTS:
            return _LOCAL_SECRET
        raise ServiceUnavailableError("Account deletion is not configured")

    def _assert_eligible(self, actor: Profile) -> None:
        if actor.role not in _ELIGIBLE_ROLES:
            raise ForbiddenError("Account deletion is not available for this account type")

    async def _assert_not_blocked(self, actor: Profile) -> None:
        blockers = await self.repository.count_blockers(actor.id, actor.role.value)
        details: dict[str, int] = {}
        if blockers["open_bookings"]:
            details["open_bookings"] = blockers["open_bookings"]
        if blockers["pending_requests"]:
            details["pending_requests"] = blockers["pending_requests"]
        if details:
            # Only customers reach this: an owner's open bookings and requests are cancelled,
            # refunded and resolved by the erasure worker instead of blocking.
            raise DeletionBlockedError(
                "Cancel your upcoming bookings and resolve pending requests before "
                "deleting your account",
                details=details,
            )
        self._raise_if_subscription_blocks(blockers)

    def _raise_if_subscription_blocks(self, blockers: dict[str, int]) -> None:
        if blockers["active_subscriptions"] and self.settings.subscription_provider != "none":
            raise DeletionBlockedError(
                "Cancel your active subscription before deleting your account",
                details={"active_subscriptions": blockers["active_subscriptions"]},
            )

    async def _verified_destination(self, actor: Profile, channel: str) -> str:
        contacts = await self.auth_admin.get_user(actor.id)
        value, verified = (
            (contacts.email, contacts.email_verified) if contacts and channel == "email"
            else (contacts.phone, contacts.phone_verified) if contacts
            else (None, False)
        )
        if not value or not verified:
            raise ContactMismatchError(f"This account has no verified {channel}")
        return normalize_contact(channel, value)

    async def start_challenge(
        self, actor: Profile, channel: str, contact: str | None
    ) -> dict[str, Any]:
        """Send a code to the account's own verified contact, never to client input."""

        self._assert_eligible(actor)
        secret = self._secret()
        await self._assert_not_blocked(actor)
        destination = await self._verified_destination(actor, channel)
        if contact is not None and normalize_contact(channel, contact) != destination:
            raise ContactMismatchError("The contact does not match a verified contact on this account")

        cfg = self.settings
        contact_hash = digest(secret, f"contact:{channel}", destination)
        live = await self.repository.get_live_challenge(actor.id)
        if live and live["status"] == "sent":
            wait = cfg.account_deletion_resend_cooldown_seconds - int(live["seconds_since_sent"])
            if wait > 0:
                raise TooManyRequestsError(f"Wait {wait} seconds before requesting another code")
            if live["resend_count"] >= cfg.account_deletion_max_resends:
                raise TooManyRequestsError("Too many codes requested; start again later")
            challenge = await self.repository.resend_challenge(
                str(live["id"]), channel, contact_hash, cfg.account_deletion_challenge_ttl_seconds
            )
        else:
            if live:
                await self.repository.expire_live_challenge(actor.id)
            recent = await self.repository.count_recent_challenges(actor.id, 3600)
            if recent >= cfg.account_deletion_max_challenges_per_hour:
                raise TooManyRequestsError("Too many deletion attempts; try again later")
            challenge = await self.repository.create_challenge(
                actor.id, channel, contact_hash,
                cfg.account_deletion_challenge_ttl_seconds, cfg.account_deletion_max_attempts,
            )
        await self.auth_gateway.send_verification_code(channel, destination)
        impact = (
            await self.repository.count_closure_impact(actor.id)
            if actor.role == Role.owner else {"bookings_to_cancel": 0}
        )
        return {
            "bookings_to_cancel": impact["bookings_to_cancel"],
            "challenge_id": str(challenge["id"]),
            "channel": channel,
            "masked_destination": mask_contact(channel, destination),
            "expires_at": challenge["expires_at"],
            "resend_available_at": challenge["last_sent_at"]
            + timedelta(seconds=cfg.account_deletion_resend_cooldown_seconds),
        }

    async def verify_challenge(self, actor: Profile, challenge_id: str, code: str) -> dict[str, Any]:
        """Check the code for THIS account and mint a one-time confirmation token."""

        self._assert_eligible(actor)
        secret = self._secret()
        if await self.repository.get_challenge(challenge_id, actor.id) is None:
            raise NotFoundError("Verification challenge not found")
        attempt = await self.repository.begin_verify_attempt(challenge_id, actor.id)
        if attempt is None:
            raise InvalidVerificationCodeError("The verification code is invalid or expired")
        channel = str(attempt["channel"])
        try:
            destination = await self._verified_destination(actor, channel)
            if not digests_match(attempt["contact_hash"],
                                 digest(secret, f"contact:{channel}", destination)):
                raise InvalidVerificationCodeError("The verification code is invalid or expired")
            verified_user = await self.auth_gateway.verify_code_user_id(channel, destination, code)
            if verified_user != actor.id:
                await self.repository.expire_challenge(challenge_id)
                raise InvalidVerificationCodeError("The verification code is invalid or expired")
        except InvalidVerificationCodeError:
            if attempt["attempts"] >= attempt["max_attempts"]:
                await self.repository.expire_challenge(challenge_id)
            raise
        token = new_token()
        marked = await self.repository.mark_verified(
            challenge_id, actor.id, digest(secret, "confirm", token),
            self.settings.account_deletion_confirmation_ttl_seconds,
        )
        if marked is None:
            raise InvalidVerificationCodeError("The verification code is invalid or expired")
        return {"confirmation_token": token, "expires_at": marked["confirmation_expires_at"]}

    async def confirm(
        self, actor: Profile, challenge_id: str, confirmation_token: str
    ) -> dict[str, Any]:
        """Irreversibly lock the account and queue erasure."""

        self._assert_eligible(actor)
        secret = self._secret()
        if actor.role.value == "owner":
            # A subscription bought AFTER the challenge started must not slip past the blocker.
            self._raise_if_subscription_blocks(
                await self.repository.count_blockers(actor.id, actor.role.value)
            )
        request = await self.repository.confirm_deletion(
            actor.id, challenge_id, digest(secret, "confirm", confirmation_token)
        )
        request_id = str(request["id"])
        return {
            "request_id": request_id,
            "status": str(request["status"]),
            "status_token": digest(secret, "status", request_id),
        }

    async def get_status(self, request_id: str, status_token: str) -> dict[str, Any]:
        """Report progress using the status token, since the JWT is dead after confirm."""

        secret = self._secret()
        row = await self.repository.get_request(request_id)
        if row is None or not digests_match(digest(secret, "status", request_id), status_token):
            raise NotFoundError("Deletion request not found")
        return {
            "request_id": request_id,
            "status": str(row["status"]),
            "stage": deletion_stage(str(row["status"]), row.get("step_state") or {}),
            "requested_at": row["requested_at"],
            "completed_at": row["completed_at"],
        }

    async def list_requests(self, actor: Profile, limit: int, offset: int) -> list[dict[str, Any]]:
        if not is_super_admin(actor):
            raise ForbiddenError("Super admin access required")
        return await self.repository.list_requests(limit, offset)
