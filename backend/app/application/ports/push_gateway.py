"""Push notification gateway port."""

from abc import ABC, abstractmethod


class PushGateway(ABC):
    """Abstract interface for sending push notifications.

    The infrastructure layer (FCMGateway) implements this.
    The application layer depends on this interface only.
    """

    @abstractmethod
    async def fan_out(self, notification_id: str, user_id: str) -> None:
        """Send a notification to all active devices belonging to user_id.

        Reads recipients from get_active_tokens(user_id) only.
        Writes one notification_deliveries row per device.
        Deactivates tokens that FCM reports as unregistered.
        """
