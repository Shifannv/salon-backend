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
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.push_gateway import PushGateway
from app.core.config import Settings

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="fcm")

# Expo push API endpoint (no auth required for standard project tokens).
_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_EXPO_TOKEN_PREFIX = "ExponentPushToken["


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

        tokens = await self._get_active_tokens(user_id)
        if not tokens:
            return

        for token, platform in tokens:
            await self._send_one(notification_id, token, platform)

    async def _get_active_tokens(self, user_id: str) -> list[tuple[str, str | None]]:
        """Return active (token, platform) pairs via the DB function."""

        result = await self.session.execute(
            text("select token, platform from get_active_tokens(:user_id)"),
            {"user_id": user_id},
        )
        return [(row.token, row.platform) for row in result]

    async def _send_one(
        self,
        notification_id: str,
        token: str,
        platform: str | None,
    ) -> None:
        """Dispatch to the appropriate push channel and record delivery."""

        if token.startswith(_EXPO_TOKEN_PREFIX):
            await self._send_expo(notification_id, token)
        else:
            await self._send_fcm(notification_id, token, platform)

    # ── Expo push path ─────────────────────────────────────────────────────

    async def _send_expo(self, notification_id: str, token: str) -> None:
        """Send via Expo's push API and record the delivery attempt."""

        delivered = False
        error_msg: str | None = None

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    _EXPO_PUSH_URL,
                    json={"to": token},
                    headers={"Accept": "application/json", "Accept-Encoding": "gzip, deflate"},
                )
                resp.raise_for_status()
                data = resp.json()
                # Expo returns a `data` list; each item has a `status` field.
                item = (data.get("data") or [{}])[0]
                if item.get("status") == "ok":
                    delivered = True
                else:
                    error_msg = item.get("message", "Expo push rejected")
                    details = item.get("details", {})
                    # "DeviceNotRegistered" means the token is permanently invalid.
                    if details.get("error") == "DeviceNotRegistered":
                        await self._deactivate_token(token)
        except Exception as exc:
            error_msg = str(exc)
            logger.warning("Expo push failed for token %s: %s", token[:40], error_msg)

        await self._write_delivery(notification_id, token, delivered, error_msg)

    # ── FCM push path ──────────────────────────────────────────────────────

    async def _send_fcm(
        self,
        notification_id: str,
        token: str,
        platform: str | None,  # reserved for future platform-specific config
    ) -> None:
        """Send via the firebase-admin SDK and record the delivery attempt."""

        if not self.settings.firebase_credentials_json:
            logger.warning("FCM not configured; skipping push for notification %s", notification_id)
            return

        loop = asyncio.get_event_loop()
        try:
            app = await loop.run_in_executor(_executor, self._get_or_init_app)
            await loop.run_in_executor(_executor, partial(self._send_sync, app, token))
            delivered = True
            error_msg = None
        except Exception as exc:
            delivered = False
            error_msg = str(exc)
            if "registration-token-not-registered" in error_msg or "invalid-argument" in error_msg:
                await self._deactivate_token(token)

        await self._write_delivery(notification_id, token, delivered, error_msg)

    def _send_sync(self, app: Any, token: str) -> None:
        """Synchronous FCM send — runs in the thread pool."""

        # Import here to avoid import-time failure when firebase-admin is absent.
        from firebase_admin import messaging  # type: ignore[import]

        message = messaging.Message(token=token)
        messaging.send(message, app=app)

    def _get_or_init_app(self) -> Any:
        """Lazily initialise the Firebase app (thread-safe via GIL)."""

        if self._app is not None:
            return self._app

        import json

        import firebase_admin  # type: ignore[import]
        from firebase_admin import credentials  # type: ignore[import]

        cred = credentials.Certificate(
            json.loads(self.settings.firebase_credentials_json)  # type: ignore[arg-type]
        )
        self._app = firebase_admin.initialize_app(cred)
        return self._app

    # ── Shared helpers ─────────────────────────────────────────────────────

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
