"""FCM/Expo push gateway behavior."""

from types import SimpleNamespace
from typing import Any, ClassVar, Self

import pytest

from app.core.config import Settings
from app.infrastructure.push.fcm_gateway import FCMGateway

NOTIFICATION = {
    "id": "11111111-1111-1111-1111-111111111111",
    "booking_id": "22222222-2222-2222-2222-222222222222",
    "type": "booking_status",
    "title": "Booking Confirmed",
    "body": "Your appointment has been confirmed.",
}


class FakeMappings:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row

    def one_or_none(self) -> dict[str, Any] | None:
        return self.row


class FakeResult:
    def __init__(
        self,
        *,
        row: dict[str, Any] | None = None,
        rows: list[SimpleNamespace] | None = None,
    ) -> None:
        self.row = row
        self.rows = rows or []

    def mappings(self) -> FakeMappings:
        return FakeMappings(self.row)

    def __iter__(self):
        return iter(self.rows)


class FakeSession:
    def __init__(self, token: str, platform: str | None = "ios") -> None:
        self.token = token
        self.platform = platform
        self.executions: list[dict[str, Any]] = []
        self.commits = 0

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
        sql = str(statement)
        self.executions.append({"sql": sql, "params": params or {}})

        if "from notifications" in sql:
            return FakeResult(row=NOTIFICATION)
        if "get_active_tokens" in sql:
            return FakeResult(rows=[SimpleNamespace(token=self.token, platform=self.platform)])
        return FakeResult()

    async def commit(self) -> None:
        self.commits += 1

    @property
    def delivery_params(self) -> dict[str, Any]:
        deliveries = [
            execution
            for execution in self.executions
            if "insert into notification_deliveries" in execution["sql"]
        ]
        assert deliveries
        return deliveries[-1]["params"]


class FakeExpoResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {"data": {"status": "ok"}}


class FakeExpoClient:
    payloads: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, **_: Any) -> None:
        return None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(
        self,
        _url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> FakeExpoResponse:
        self.payloads.append({"json": json, "headers": headers})
        return FakeExpoResponse()


@pytest.mark.asyncio
async def test_expo_push_includes_notification_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expo pushes include visible title/body plus app metadata."""

    FakeExpoClient.payloads = []
    # The gateway imports httpx when it sends, so patch the client on httpx itself.
    monkeypatch.setattr("httpx.AsyncClient", FakeExpoClient)
    session = FakeSession("ExponentPushToken[abc123]")
    gateway = FCMGateway(Settings(environment="test"), session)  # type: ignore[arg-type]

    await gateway.fan_out(NOTIFICATION["id"], "user-001")

    payload = FakeExpoClient.payloads[0]["json"]
    assert payload["to"] == "ExponentPushToken[abc123]"
    assert payload["sound"] == "default"
    assert payload["title"] == "Booking Confirmed"
    assert payload["body"] == "Your appointment has been confirmed."
    assert payload["data"] == {
        "notification_id": NOTIFICATION["id"],
        "booking_id": NOTIFICATION["booking_id"],
        "type": "booking_status",
    }
    assert session.delivery_params["delivered"] is True
    assert session.delivery_params["error"] is None


@pytest.mark.asyncio
async def test_raw_fcm_without_credentials_records_failed_delivery() -> None:
    """Raw FCM tokens are not silently dropped when Firebase credentials are absent."""

    session = FakeSession("raw-fcm-token", platform="android")
    # Explicitly set firebase_credentials_json=None so the test always hits the
    # "credentials missing" branch, even when a real .env with Firebase creds
    # is present on the developer's machine or CI environment.
    gateway = FCMGateway(
        Settings(environment="test", firebase_credentials_json=None),  # type: ignore[arg-type]
        session,
    )

    await gateway.fan_out(NOTIFICATION["id"], "user-001")

    assert session.delivery_params["delivered"] is False
    assert session.delivery_params["error"] == (
        "FCM not configured; FIREBASE_CREDENTIALS_JSON is missing"
    )


@pytest.mark.asyncio
async def test_raw_fcm_receives_notification_payload_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Firebase send path receives the notification content and marks delivery."""

    sent: dict[str, Any] = {}
    session = FakeSession("raw-fcm-token", platform="android")
    gateway = FCMGateway(
        Settings(environment="test", firebase_credentials_json="{}"),  # type: ignore[arg-type]
        session,
    )

    monkeypatch.setattr(gateway, "_get_or_init_app", lambda: "firebase-app")
    monkeypatch.setattr(
        gateway,
        "_send_sync",
        lambda app, token, notification: sent.update(
            {"app": app, "token": token, "notification": notification}
        ),
    )

    await gateway.fan_out(NOTIFICATION["id"], "user-001")

    assert sent == {
        "app": "firebase-app",
        "token": "raw-fcm-token",
        "notification": NOTIFICATION,
    }
    assert session.delivery_params["delivered"] is True
    assert session.delivery_params["error"] is None
