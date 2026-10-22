"""QR contract (token format, expiry, authorization) and the direct booking-by-salon-id contract."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_cache, get_current_actor, get_session
from app.api.v1.schemas.platform import BookingCreateRequest
from app.application.use_cases.platform import BookingUseCases
from app.core.config import Settings
from app.core.exceptions import BookingSourceNotAllowedError, ForbiddenError, QrCodeNotFoundError
from app.core.qr import QR_TOKEN_PATTERN, _build_walkin_url, is_valid_qr_token_format
from app.domain.entities.profile import Role
from app.main import app
from tests.conftest import make_booking, make_mock_repo, make_owner, make_profile
from tests.unit.test_cache_integration import InMemoryCache

TOKEN = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"  # 32 lowercase hex, as the database issues them
SALON_ID = "00000000-0000-0000-0000-000000000001"
OTHER_SALON_ID = "00000000-0000-0000-0000-000000000002"
MALFORMED = ["ab", "x" * 129, "bad token", "tok$en", "to.ken", "tok!en", "é" * 10, "x" * 500]
BOOKING = {
    "salon_id": SALON_ID, "staff_id": "00000000-0000-0000-0000-0000000000a1",
    "service_ids": ["00000000-0000-0000-0000-0000000000b1"], "start_datetime": "2030-06-01T10:00:00+00:00",
    "customer_name": "Test",
}


@pytest.fixture
def client(monkeypatch):
    """TestClient whose walk-in repository fails the test if a malformed token reaches it."""
    repo = AsyncMock()
    monkeypatch.setattr("app.api.v1.routes.walkin.PlatformRepository", lambda _: repo)
    overrides = app.dependency_overrides.copy()
    cache = InMemoryCache()

    async def session():
        yield MagicMock()

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_cache] = lambda: cache
    try:
        yield TestClient(app), repo, cache
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)


# ── token format ─────────────────────────────────────────────────────────────


def test_issued_tokens_and_the_documented_format_are_accepted():
    assert is_valid_qr_token_format(TOKEN)
    assert QR_TOKEN_PATTERN.fullmatch("A1_b-2")
    for bad in ("", "a", "ab", "a b", "a/b", "a.b", "a" * 129, "tok\n", "%2F%2F", "é" * 4):
        assert not is_valid_qr_token_format(bad), repr(bad)


def test_printed_payload_is_the_web_route_plus_the_token():
    assert _build_walkin_url(TOKEN, "https://site.example/s") == f"https://site.example/s/{TOKEN}"
    assert _build_walkin_url(TOKEN, "https://site.example/s/") == f"https://site.example/s/{TOKEN}"
    default = Settings(_env_file=None).walkin_base_url
    assert default.rstrip("/").endswith("/s")


@pytest.mark.parametrize("token", MALFORMED)
@pytest.mark.parametrize(("method", "suffix"), [
    ("get", ""), ("get", "/qr"), ("post", "/verify-phone"), ("post", "/bookings"),
])
def test_malformed_tokens_are_not_found_before_any_lookup(client, token, method, suffix):
    http, repo, cache = client
    response = getattr(http, method)(f"/v1/walkin/{token}{suffix}", **({"json": {}} if method == "post" else {}))
    assert response.status_code == 404, (token, response.text)
    body = response.json()["error"]
    assert body["code"] == "qr_not_found"
    assert body["message"] == "Salon not found or not accepting walk-ins"
    assert repo.method_calls == []
    assert cache._store == {}


# ── unknown, expired and revoked tokens look identical ───────────────────────


def test_unknown_expired_or_unpublished_token_is_one_machine_readable_404(client):
    http, repo, cache = client
    repo.get_salon_by_qr.side_effect = QrCodeNotFoundError("Salon not found or not accepting walk-ins")
    response = http.get(f"/v1/walkin/{TOKEN}")
    assert response.status_code == 404
    assert response.json()["error"] == {"code": "qr_not_found", "message": "Salon not found or not accepting walk-ins"}
    assert cache._store == {}


def test_a_cached_salon_is_revalidated_so_an_expired_token_stops_working(client):
    http, repo, cache = client
    repo.validate_qr_token.return_value = SALON_ID
    repo.get_salon_by_qr.return_value = {
        "id": SALON_ID, "name": "S", "timezone": "UTC", "approval_mode": "auto", "qr_token": TOKEN,
        "accepting_bookings": True,
    }
    first = http.get(f"/v1/walkin/{TOKEN}")
    assert first.status_code == 200 and first.json()["qr_token"] == TOKEN
    assert f"walkin:qr:{TOKEN}" in cache._store
    repo.validate_qr_token.side_effect = QrCodeNotFoundError("Salon not found or not accepting walk-ins")
    second = http.get(f"/v1/walkin/{TOKEN}")
    assert second.status_code == 404
    assert second.json()["error"]["code"] == "qr_not_found"


def test_the_resolver_is_the_only_public_response_with_a_token_and_reports_payment_capability(client):
    http, repo, _ = client
    repo.get_salon_by_qr.return_value = {
        "id": SALON_ID, "name": "S", "timezone": "UTC", "approval_mode": "auto", "qr_token": TOKEN,
        "accepting_bookings": True, "services": [], "staff": [],
    }
    body = http.get(f"/v1/walkin/{TOKEN}").json()
    assert body["qr_token"] == TOKEN
    assert body["payment_options"] == ["PAY_AT_SALON"]
    assert body["accepts_bookings"] is True
    assert body["online_payment_available"] is False
    repo.get_salon_by_qr.return_value = {**repo.get_salon_by_qr.return_value, "accepting_bookings": False}
    http2 = http.get(f"/v1/walkin/{TOKEN}?fresh=true").json()
    assert http2["payment_options"] == [] and http2["accepts_bookings"] is False


# ── authorization on the QR booking route ────────────────────────────────────


def test_qr_booking_requires_authentication(client):
    http, repo, _ = client
    response = http.post(f"/v1/walkin/{TOKEN}/bookings", json=BOOKING)
    assert response.status_code in (401, 403)
    assert repo.method_calls == []


def _as(actor):
    async def current():
        return actor

    async def session():
        yield MagicMock()

    app.dependency_overrides[get_current_actor] = current
    app.dependency_overrides[get_authenticated_session] = session


def test_qr_booking_is_customer_only(client):
    http, repo, _ = client
    _as(make_owner())
    response = http.post(f"/v1/walkin/{TOKEN}/bookings", json=BOOKING)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    repo.validate_qr_token.assert_not_awaited()


def test_qr_booking_rejects_a_salon_that_does_not_match_the_token(client):
    http, repo, _ = client
    _as(make_profile(role=Role.customer))
    repo.validate_qr_token.return_value = OTHER_SALON_ID
    response = http.post(f"/v1/walkin/{TOKEN}/bookings", json=BOOKING)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "qr_salon_mismatch"
    repo.create_booking.assert_not_awaited()


def test_qr_booking_unknown_token_is_the_same_404(client):
    http, repo, _ = client
    _as(make_profile(role=Role.customer))
    repo.validate_qr_token.side_effect = QrCodeNotFoundError("Salon not found or not accepting walk-ins")
    response = http.post(f"/v1/walkin/{TOKEN}/bookings", json=BOOKING)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "qr_not_found"


# ── direct booking by salon id (POST /v1/bookings) ───────────────────────────


def test_direct_booking_needs_a_bearer_token_and_documents_it():
    operation = app.openapi()["paths"]["/v1/bookings"]["post"]
    assert operation["security"]
    assert operation["responses"]["201"]
    assert TestClient(app).post("/v1/bookings", json=BOOKING).status_code in (401, 403)


def test_the_request_carries_no_price_duration_or_end_time():
    props = set(app.openapi()["components"]["schemas"]["BookingCreateRequest"]["properties"])
    assert props == {"salon_id", "staff_id", "service_ids", "start_datetime", "customer_name",
                     "customer_phone", "source", "notes", "payment_preference"}
    parsed = BookingCreateRequest.model_validate({**BOOKING, "total_price": 1, "price": 1, "end_datetime": "x"})
    assert not {"total_price", "price", "end_datetime"} & set(parsed.model_dump())


@pytest.mark.asyncio
async def test_a_direct_booking_cannot_claim_the_qr_source():
    repo = make_mock_repo()
    with pytest.raises(BookingSourceNotAllowedError) as raised:
        await BookingUseCases(repo).create_booking(
            make_profile(role=Role.customer), {**BOOKING, "source": "qr_walkin"})
    assert raised.value.code == "booking_source_not_allowed"
    repo.create_booking.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_direct_booking_is_limited_to_customers_and_owners_and_checks_the_salon_is_public():
    repo = make_mock_repo()
    repo.create_booking.return_value = make_booking()
    use_cases = BookingUseCases(repo)
    with pytest.raises(ForbiddenError):
        await use_cases.create_booking(make_profile(role=Role.staff), {**BOOKING, "source": "app"})
    repo.create_booking.assert_not_awaited()

    await use_cases.create_booking(make_profile(role=Role.customer), {**BOOKING, "source": "app"})
    repo.get_public_salon.assert_awaited_once_with(SALON_ID)
    sent = repo.create_booking.await_args.args[0]
    assert sent["actor_id"] == "user-001"
    assert not {"price", "total_price", "end_datetime"} & set(sent)


@pytest.mark.asyncio
async def test_online_payment_preferences_stay_refused_while_the_gateway_is_off():
    repo = make_mock_repo()
    for preference in ("pay_advance", "pay_full"):
        with pytest.raises(Exception) as raised:
            await BookingUseCases(repo).create_booking(
                make_profile(role=Role.customer), {**BOOKING, "source": "app", "payment_preference": preference})
        assert raised.value.status_code == 422
        assert raised.value.code == "online_payment_unavailable"
    repo.create_booking.assert_not_awaited()
    repo.get_public_salon.assert_not_awaited()


# ── machine-readable errors for framework-raised failures ────────────────────


def test_missing_credentials_use_the_shared_error_envelope_and_keep_detail():
    response = TestClient(app).post("/v1/bookings", json=BOOKING)
    assert response.status_code == 401
    assert response.json()["error"] == {"code": "unauthorized", "message": "Not authenticated"}
    assert response.json()["detail"] == "Not authenticated"
    assert response.headers["www-authenticate"] == "Bearer"


def test_unknown_routes_use_the_shared_error_envelope():
    response = TestClient(app).get("/v1/this-route-does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# ── QR booking end to end (HTTP -> use case -> repository) ───────────────────


def _qr_booking_client(client, *, replay=False):
    http, repo, _ = client
    _as(make_profile(role=Role.customer))
    repo.validate_qr_token.return_value = SALON_ID
    row = make_booking(salon_id=SALON_ID)
    row["source"] = "qr_walkin"
    if replay:
        row["_idempotency_replay"] = True
    repo.create_booking.return_value = row
    return http, repo


@pytest.mark.parametrize("claimed", [None, "app", "manual_walkin", "qr_walkin"])
def test_qr_booking_is_recorded_as_qr_walkin_whatever_the_client_claims(client, monkeypatch, claimed):
    monkeypatch.setattr("app.api.v1.routes.walkin.BookingUseCases.notify_new_booking_owner", AsyncMock())
    http, repo = _qr_booking_client(client)
    body = {**BOOKING, **({"source": claimed} if claimed else {})}
    response = http.post(f"/v1/walkin/{TOKEN}/bookings", json=body, headers={"Idempotency-Key": "k-1"})
    assert response.status_code == 201
    assert response.json()["source"] == "qr_walkin"
    sent = repo.create_booking.await_args.args[0]
    assert sent["source"] == "qr_walkin"
    assert sent["salon_id"] == SALON_ID
    assert sent["actor_id"] == "user-001"
    assert sent["_idempotency_key"] == "k-1"
    assert sent["_idempotency_scope"].startswith("booking:qr:")
    repo.validate_qr_token.assert_awaited_with(TOKEN)


def test_qr_booking_ignores_client_supplied_price_and_duration(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.walkin.BookingUseCases.notify_new_booking_owner", AsyncMock())
    http, repo = _qr_booking_client(client)
    response = http.post(
        f"/v1/walkin/{TOKEN}/bookings",
        json={**BOOKING, "total_price": 1, "price": 1, "end_datetime": "2030-06-01T10:01:00+00:00",
              "total_duration_minutes": 1},
    )
    assert response.status_code == 201
    sent = repo.create_booking.await_args.args[0]
    assert not {"total_price", "price", "end_datetime", "total_duration_minutes"} & set(sent)
    assert sent["service_ids"] == BOOKING["service_ids"]  # only ids are forwarded; Postgres prices them


def test_qr_booking_replay_does_not_notify_again(client, monkeypatch):
    notify = AsyncMock()
    monkeypatch.setattr("app.api.v1.routes.walkin.BookingUseCases.notify_new_booking_owner", notify)
    http, _ = _qr_booking_client(client, replay=True)
    assert http.post(f"/v1/walkin/{TOKEN}/bookings", json=BOOKING).status_code == 201
    notify.assert_not_awaited()


@pytest.mark.parametrize("token", MALFORMED[:5])
def test_qr_booking_with_a_malformed_token_never_reaches_the_database(client, token):
    http, repo, _ = client
    _as(make_profile(role=Role.customer))
    response = http.post(f"/v1/walkin/{token}/bookings", json=BOOKING)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "qr_not_found"
    repo.validate_qr_token.assert_not_awaited()
    repo.create_booking.assert_not_awaited()


def test_qr_booking_slot_conflict_is_the_database_decision(client):
    from app.core.exceptions import SlotUnavailableError

    http, repo = _qr_booking_client(client)
    repo.create_booking.side_effect = SlotUnavailableError("Selected slot is no longer available")
    response = http.post(f"/v1/walkin/{TOKEN}/bookings", json=BOOKING)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "slot_unavailable"


def test_direct_booking_over_http_rejects_the_qr_source_with_a_machine_code(client):
    http, repo, _ = client
    _as(make_profile(role=Role.customer))
    response = http.post("/v1/bookings", json={**BOOKING, "source": "qr_walkin"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "booking_source_not_allowed"
    repo.create_booking.assert_not_awaited()


def test_direct_booking_over_http_is_recorded_as_app(client, monkeypatch):
    http, repo, _ = client
    _as(make_profile(role=Role.customer))
    repo.get_public_salon.return_value = {"id": SALON_ID}
    repo.create_booking.return_value = make_booking(salon_id=SALON_ID)
    monkeypatch.setattr("app.api.v1.routes.bookings.PlatformRepository", lambda _: repo)
    response = http.post("/v1/bookings", json=BOOKING)
    assert response.status_code == 201, response.text
    assert repo.create_booking.await_args.args[0]["source"] == "app"
    repo.get_public_salon.assert_awaited_once_with(SALON_ID)


@pytest.mark.parametrize("preference", ["pay_advance", "pay_full"])
def test_qr_booking_refuses_online_payment_while_the_gateway_is_off(client, monkeypatch, preference):
    notify = AsyncMock()
    monkeypatch.setattr("app.api.v1.routes.walkin.BookingUseCases.notify_new_booking_owner", notify)
    http, repo = _qr_booking_client(client)
    response = http.post(f"/v1/walkin/{TOKEN}/bookings", json={**BOOKING, "payment_preference": preference})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "online_payment_unavailable"
    repo.create_booking.assert_not_awaited()
    notify.assert_not_awaited()


@pytest.mark.parametrize("preference", ["pay_advance", "pay_full"])
def test_direct_booking_refuses_online_payment_with_the_same_422(client, preference):
    http, repo, _ = client
    _as(make_profile(role=Role.customer))
    response = http.post("/v1/bookings", json={**BOOKING, "payment_preference": preference})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "online_payment_unavailable"
    repo.create_booking.assert_not_awaited()


def test_pay_at_salon_and_default_preferences_are_still_accepted(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.walkin.BookingUseCases.notify_new_booking_owner", AsyncMock())
    http, _ = _qr_booking_client(client)
    for body in (BOOKING, {**BOOKING, "payment_preference": "pay_at_salon"}):
        assert http.post(f"/v1/walkin/{TOKEN}/bookings", json=body).status_code == 201


def test_a_real_slot_conflict_is_the_only_409_slot_unavailable(client):
    from app.core.exceptions import SlotUnavailableError

    http, repo = _qr_booking_client(client)
    repo.create_booking.side_effect = SlotUnavailableError("Selected slot is no longer available")
    qr = http.post(f"/v1/walkin/{TOKEN}/bookings", json=BOOKING)
    assert (qr.status_code, qr.json()["error"]["code"]) == (409, "slot_unavailable")


# ── idempotency scope ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_qr_idempotency_scope_binds_the_validated_salon_and_the_token():
    from app.application.use_cases.walkin import WalkInUseCases

    repo = AsyncMock()
    repo.validate_qr_token.return_value = SALON_ID
    repo.create_booking.return_value = make_booking()
    await WalkInUseCases(repo).create_walkin_booking(make_profile(role=Role.customer), TOKEN, dict(BOOKING))
    scope = repo.create_booking.await_args.args[0]["_idempotency_scope"]
    assert scope.startswith(f"booking:qr:{SALON_ID}:")
    assert TOKEN not in scope  # only a hash of the public token is stored

    repo.validate_qr_token.return_value = OTHER_SALON_ID
    await WalkInUseCases(repo).create_walkin_booking(
        make_profile(role=Role.customer), TOKEN, {**BOOKING, "salon_id": OTHER_SALON_ID})
    assert repo.create_booking.await_args.args[0]["_idempotency_scope"] != scope


@pytest.mark.asyncio
async def test_idempotency_is_keyed_by_the_authenticated_customer():
    from app.application.use_cases.walkin import WalkInUseCases

    repo = AsyncMock()
    repo.validate_qr_token.return_value = SALON_ID
    repo.create_booking.return_value = make_booking()
    for actor_id in ("customer-a", "customer-b"):
        await WalkInUseCases(repo).create_walkin_booking(
            make_profile(id=actor_id, role=Role.customer), TOKEN, {**BOOKING, "_idempotency_key": "same-key-123"})
    first, second = (call.args[0] for call in repo.create_booking.await_args_list)
    assert (first["actor_id"], second["actor_id"]) == ("customer-a", "customer-b")
    assert first["_idempotency_scope"] == second["_idempotency_scope"]  # the actor id is what separates them


@pytest.mark.asyncio
async def test_key_reuse_with_a_different_booking_is_a_422_with_its_own_code():
    from app.core.exceptions import IdempotencyKeyReuseError
    from app.infrastructure.db.repositories import platform_repository as module

    class FakePayments:
        def __init__(self, _session):
            pass

        async def begin_idempotent(self, *_args):
            raise IdempotencyKeyReuseError("reused")

    session = AsyncMock()
    original = module.PlatformRepository
    import app.infrastructure.db.repositories.payment_repository as payments

    saved = payments.PaymentRepository
    payments.PaymentRepository = FakePayments
    try:
        with pytest.raises(Exception) as raised:
            await original(session).create_booking({**BOOKING, "actor_id": "u", "source": "app",
                                                    "_idempotency_key": "reuse-key-123"})
    finally:
        payments.PaymentRepository = saved
    assert raised.value.status_code == 422
    assert raised.value.code == "idempotency_key_reused"


# ── idempotency fingerprint: one instant, one fingerprint ────────────────────


def _fingerprint(start):
    from app.infrastructure.db.repositories.platform_repository import _request_fingerprint

    request = BookingCreateRequest.model_validate({**BOOKING, "start_datetime": start})
    return _request_fingerprint(request.model_dump())


def test_same_instant_in_different_offsets_has_one_fingerprint():
    assert _fingerprint("2026-10-21T10:00:00Z") == _fingerprint("2026-10-21T15:30:00+05:30")
    assert _fingerprint("2026-10-21T10:00:00+00:00") == _fingerprint("2026-10-21T15:30:00+05:30")


def test_different_instant_has_a_different_fingerprint():
    assert _fingerprint("2026-10-21T10:00:00Z") != _fingerprint("2026-10-21T10:30:00Z")
    assert _fingerprint("2026-10-21T10:00:00Z") != _fingerprint("2026-10-21T10:00:00+05:30")


def test_naive_start_datetime_is_rejected_not_reinterpreted():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        BookingCreateRequest.model_validate({**BOOKING, "start_datetime": "2026-10-21T10:00:00"})
