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

    async def assert_public_qr_token(self, qr_token: str) -> None:
        """Revalidate publication through Postgres before serving cached QR data."""
        await self.repository.validate_qr_token(qr_token)

    async def resolve_qr_token(self, qr_token: str) -> dict[str, Any]:
        """Return salon + services + staff for an unauthenticated scan.

        Delegates to get_salon_by_qr() — never leaks internal IDs beyond
        what the database function returns.
        """
        return await self.repository.get_salon_by_qr(qr_token)

    async def create_walkin_booking(
        self, actor: Profile, qr_token: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a qr_walkin booking, verifying the QR token first."""

        if actor.role != Role.customer:
            raise ForbiddenError("Walk-in bookings require a customer account")

        # Use the lightweight validator — only fetches salon_id, no joins.
        salon_id = await self.repository.validate_qr_token(qr_token)

        # Enforce that the payload salon_id matches the QR, if provided.
        if values.get("salon_id") and str(values["salon_id"]) != salon_id:
            raise ValidationError("salon_id does not match the QR token")

        return await self.repository.create_booking(
            {
                **values,
                "salon_id": salon_id,
                "source": "qr_walkin",
                "actor_id": actor.id,
            }
        )
