"""FCM + Expo push notification gateway.

Routes outbound push notifications through the correct delivery channel:

* Tokens starting with ``ExponentPushToken[`` are Expo-managed tokens and are
  delivered via the Expo push HTTP API (https://exp.host/--/api/v2/push/send).
  This is the token format returned by ``Notifications.getExpoPushTokenAsync()``
  in the React-Native / Expo SDK used by the customer app.

* All other tokens are assumed to be raw FCM registration tokens and are
  delivered via the ``firebase-admin`` SDK (unchanged behaviour).

Both paths write a ``notification_deliveries`` row and deactivate tokens that
the upstream service reports as permanently invalid.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.push_gateway import PushGateway
from app.core.config import Settings

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="fcm")

# Expo push API endpoint (no auth required for standard project tokens).
_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_EXPO_TOKEN_PREFIX = "ExponentPushToken["

# Android channel created by the owner app (high importance, audible). Apps that do not
# define it (e.g. the customer app) fall back to their default channel, so this is safe.
_ANDROID_CHANNEL_ID = "salon-alerts-v3"

# Legacy error-code fragments that mean the FCM token can never receive pushes again.
_PERMANENT_FCM_ERROR_FRAGMENTS = ("registration-token-not-registered", "invalid-argument")


def _token_ref(token: str) -> str:
    """Short non-reversible reference to a push token, safe to log."""

    return hashlib.sha256(token.encode()).hexdigest()[:8]


def _is_permanent_fcm_error(exc: Exception) -> bool:
    """True when Firebase reports the registration token as unregistered or invalid."""

    try:
        from firebase_admin import exceptions as fb_exceptions  # type: ignore[import]
        from firebase_admin import messaging  # type: ignore[import]

        if isinstance(
            exc, (messaging.UnregisteredError, fb_exceptions.InvalidArgumentError)
        ):
            return True
    except ImportError:
        pass  # firebase-admin absent: fall back to the message fragments below
    message = str(exc)
    return any(fragment in message for fragment in _PERMANENT_FCM_ERROR_FRAGMENTS)


class FCMGateway(PushGateway):
    """Firebase Cloud Messaging + Expo push delivery.

    FCM path requires ``FIREBASE_CREDENTIALS_JSON`` env var (service account
    JSON string).  If credentials are absent, FCM sends are skipped.

    Expo path requires no credentials — it uses the public Expo push API which
    routes to FCM / APNs on behalf of the Expo project.  This is the correct
    path for tokens obtained via ``Notifications.getExpoPushTokenAsync()``.
    """

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self.settings = settings
        self.session = session
        self._app: Any | None = None  # firebase_admin.App, lazy-initialized

    async def fan_out(self, notification_id: str, user_id: str) -> None:
        """Deliver a notification to all active devices of a user."""

        notification = await self._get_notification(notification_id)
        if notification is None:
            logger.warning("Notification %s not found; skipping push fan-out", notification_id)
            return

        tokens = await self._get_active_tokens(user_id, notification_id)
        if not tokens:
            return

        for token, platform in tokens:
            await self._send_one(notification, token, platform)

    async def _get_notification(self, notification_id: str) -> dict[str, Any] | None:
        """Return the notification payload to send to push providers."""

        result = await self.session.execute(
            text(
                """
                select id, user_id, booking_id, type, title, body, data
                from notifications
                where id = :notification_id
                """
            ),
            {"notification_id": notification_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def _get_active_tokens(
        self, user_id: str, notification_id: str
    ) -> list[tuple[str, str | None]]:
        """Return active tokens without resending already delivered events."""

        result = await self.session.execute(
            text(
                """
                select active.token, active.platform
                from get_active_tokens(:user_id) active
                where not exists (
                  select 1 from notification_deliveries delivery
                  join device_tokens device on device.id = delivery.device_token_id
                  where delivery.notification_id = :notification_id
                    and device.token = active.token
                    and delivery.delivered
                )
                """
            ),
            {"user_id": user_id, "notification_id": notification_id},
        )
        return [(row.token, row.platform) for row in result]

    async def _send_one(
        self,
        notification: dict[str, Any],
        token: str,
        platform: str | None,
    ) -> None:
        """Dispatch to the appropriate push channel and record delivery."""

        if token.startswith(_EXPO_TOKEN_PREFIX):
            await self._send_expo(notification, token)
        else:
            await self._send_fcm(notification, token, platform)

    # ── Expo push path ─────────────────────────────────────────────────────

    async def _send_expo(self, notification: dict[str, Any], token: str) -> None:
        """Send via Expo's push API and record the delivery attempt."""

        delivered = False
        error_msg: str | None = None
        import httpx  # on first use, to keep it out of cold start

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    _EXPO_PUSH_URL,
                    json={
                        "to": token,
                        "sound": "default",
                        "priority": "high",
                        "channelId": _ANDROID_CHANNEL_ID,
                        "title": str(notification["title"]),
                        "body": notification.get("body") or "",
                        "data": self._provider_data(notification),
                    },
                    headers={"Accept": "application/json", "Accept-Encoding": "gzip, deflate"},
                )
                resp.raise_for_status()
                data = resp.json()
                # Expo returns either one data object or a list, depending on request shape.
                response_data = data.get("data")
                item = response_data[0] if isinstance(response_data, list) else response_data
                item = item if isinstance(item, dict) else {}
                if item.get("status") == "ok":
                    delivered = True
                else:
                    error_msg = item.get("message", "Expo push rejected")
                    details = item.get("details", {})
                    # "DeviceNotRegistered" means the token is permanently invalid.
                    if details.get("error") == "DeviceNotRegistered":
                        await self._deactivate_token(token)
        except Exception as exc:
            error_msg = type(exc).__name__
            logger.warning("Expo push failed for token %s: %s", _token_ref(token), error_msg)

        await self._write_delivery(str(notification["id"]), token, delivered, error_msg)

    # ── FCM push path ──────────────────────────────────────────────────────

    async def _send_fcm(
        self,
        notification: dict[str, Any],
        token: str,
        platform: str | None,  # reserved for future platform-specific config
    ) -> None:
        """Send via the firebase-admin SDK and record the delivery attempt."""

        if not self.settings.firebase_credentials_json:
            error_msg = "FCM not configured; FIREBASE_CREDENTIALS_JSON is missing"
            logger.warning("%s for notification %s", error_msg, notification["id"])
            await self._write_delivery(str(notification["id"]), token, False, error_msg)
            return

        loop = asyncio.get_running_loop()
        try:
            app = await loop.run_in_executor(_executor, self._get_or_init_app)
            await loop.run_in_executor(
                _executor, partial(self._send_sync, app, token, notification)
            )
            delivered = True
            error_msg = None
        except Exception as exc:
            delivered = False
            error_msg = type(exc).__name__
            logger.warning("FCM push failed for token %s: %s", _token_ref(token), error_msg)
            if _is_permanent_fcm_error(exc):
                await self._deactivate_token(token)

        await self._write_delivery(str(notification["id"]), token, delivered, error_msg)

    def _send_sync(self, app: Any, token: str, notification: dict[str, Any]) -> None:
        """Synchronous FCM send — runs in the thread pool."""

        # Import here to avoid import-time failure when firebase-admin is absent.
        from firebase_admin import messaging  # type: ignore[import]

        message = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=str(notification["title"]),
                body=notification.get("body") or "",
            ),
            data=self._provider_data(notification),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id=_ANDROID_CHANNEL_ID, sound="default"
                ),
            ),
            apns=messaging.APNSConfig(
                headers={"apns-priority": "10"},
                payload=messaging.APNSPayload(aps=messaging.Aps(sound="default")),
            ),
        )
        messaging.send(message, app=app)

    def _get_or_init_app(self) -> Any:
        """Lazily initialise the Firebase app (thread-safe via GIL)."""

        if self._app is not None:
            return self._app

        import firebase_admin  # type: ignore[import]
        from firebase_admin import credentials  # type: ignore[import]

        try:
            self._app = firebase_admin.get_app()
            return self._app
        except ValueError:
            pass  # no default app yet: expected on first use, initialise it below

        cred = credentials.Certificate(
            json.loads(self.settings.firebase_credentials_json)  # type: ignore[arg-type]  # guarded non-empty by _send_fcm
        )
        self._app = firebase_admin.initialize_app(cred)
        return self._app

    # ── Shared helpers ─────────────────────────────────────────────────────

    def _provider_data(self, notification: dict[str, Any]) -> dict[str, str]:
        """Return string-only metadata accepted by Expo and FCM."""

        extra = notification.get("data") or {}
        if isinstance(extra, str):
            extra = json.loads(extra)
        if not isinstance(extra, dict):
            extra = {}
        data = {
            **extra,
            "notification_id": notification.get("id"),
            # The recipient, so a shared phone can ignore an alert meant for another signed-in account.
            "user_id": notification.get("user_id"),
            "booking_id": notification.get("booking_id"),
            "type": notification.get("type"),
        }
        return {key: str(value) for key, value in data.items() if value is not None}

    async def _deactivate_token(self, token: str) -> None:
        """Deactivate a token reported as permanently invalid."""

        await self.session.execute(
            text("update device_tokens set is_active = false where token = :token"),
            {"token": token},
        )
        await self.session.commit()

    async def _write_delivery(
        self,
        notification_id: str,
        token: str,
        delivered: bool,
        error: str | None,
    ) -> None:
        """Write one notification_deliveries row."""

        await self.session.execute(
            text(
                """
                insert into notification_deliveries
                  (notification_id, device_token_id, delivered, error, attempted_at)
                select :notification_id, dt.id, :delivered, :error, now()
                from device_tokens dt
                where dt.token = :token
                on conflict (notification_id, device_token_id) do update
                  set delivered = excluded.delivered,
                      error = excluded.error,
                      attempted_at = excluded.attempted_at
                """
            ),
            {
                "notification_id": notification_id,
                "token": token,
                "delivered": delivered,
                "error": error,
            },
        )
        await self.session.commit()
