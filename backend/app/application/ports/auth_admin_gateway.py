"""Auth admin gateway port."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreatedAuthUser:
    """Result of creating a Supabase Auth user via the admin API."""

    user_id: str
    email: str


@dataclass(frozen=True, slots=True)
class AuthUserContacts:
    """Provider-side contact methods and whether the provider has verified them."""

    user_id: str
    email: str | None
    email_verified: bool
    phone: str | None
    phone_verified: bool


class AuthAdminGateway(ABC):
    """Abstract interface for privileged Supabase Auth management.

    Uses the service-role key. The application layer depends on this
    interface only; the infrastructure layer provides the implementation.
    """

    @abstractmethod
    async def create_user(
        self,
        email: str,
        password: str,
        role: str,
        full_name: str,
    ) -> CreatedAuthUser:
        """Create a Supabase Auth user with the given metadata.

        The database trigger ``handle_new_user`` will insert the ``profiles``
        row automatically; the caller must NOT also insert into profiles.

        Args:
            email: The user's email address.
            password: Initial password. Owner must change it on first login.
            role: The platform role to embed in raw_user_meta_data.
            full_name: Display name embedded in raw_user_meta_data.

        Returns:
            The created user's id and email.

        Raises:
            ConflictError: If the email is already registered.
        """

    @abstractmethod
    async def ban_user(self, user_id: str) -> None:
        """Ban a Supabase Auth user so they cannot sign in.

        Used when deactivating a salon owner. Does not delete the user —
        the profile is soft-deleted via ``is_active`` separately.

        Args:
            user_id: The Supabase Auth user UUID.
        """

    @abstractmethod
    async def unban_user(self, user_id: str) -> None:
        """Lift a Supabase Auth ban so the user can sign in again."""

    @abstractmethod
    async def get_user(self, user_id: str) -> AuthUserContacts | None:
        """Return the provider's verified contacts for a user, or None if absent."""

    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """Permanently delete a Supabase Auth user. A missing user counts as success."""
