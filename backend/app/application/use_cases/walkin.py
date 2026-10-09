"""Walk-in QR use cases."""

from typing import Any

from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.core.exceptions import ForbiddenError, ValidationError
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.platform_repository import PlatformRepository


class WalkInUseCases:
    """Walk-in QR booking use cases."""

    def __init__(
        self,
        repository: PlatformRepository,
        auth_admin: AuthAdminGateway | None = None,
    ) -> None:
        self.repository = repository
        self.auth_admin = auth_admin

    async def assert_public_qr_token(self, qr_token: str) -> str:
        """Revalidate publication through Postgres before serving cached QR data."""
        return await self.repository.validate_qr_token(qr_token)

    async def resolve_qr_token(self, qr_token: str) -> dict[str, Any]:
        """Return salon + services + staff for an unauthenticated scan.

        Delegates to get_salon_by_qr() — never leaks internal IDs beyond
        what the database function returns.
        """
        return await self.repository.get_salon_by_qr(qr_token)

    async def validate_booking_context(
        self, actor: Profile, qr_token: str, values: dict[str, Any]
    ) -> str:
        """Authorize the scanned salon before creating or replaying a booking."""
        if actor.role != Role.customer:
            raise ForbiddenError("Walk-in bookings require a customer account")
        salon_id = await self.repository.validate_qr_token(qr_token)
        if values.get("salon_id") and str(values["salon_id"]) != salon_id:
            raise ValidationError("salon_id does not match the QR token")
        return salon_id

    async def create_walkin_booking(
        self, actor: Profile, qr_token: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a qr_walkin booking, verifying the QR token first."""

        salon_id = await self.validate_booking_context(actor, qr_token, values)

        return await self.repository.create_booking(
            {
                **values,
                "salon_id": salon_id,
                "source": "qr_walkin",
                "actor_id": actor.id,
            }
        )
