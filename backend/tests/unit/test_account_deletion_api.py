"""HTTP contract for account deletion: shapes, status codes, auth, strict inputs."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_current_actor, get_session
from app.core.exceptions import (
    DeletionBlockedError,
    InvalidVerificationCodeError,
    NotFoundError,
    TooManyRequestsError,
)
from app.main import app
from tests.conftest import make_owner, make_profile, make_super_admin

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
TOKEN = "t" * 43


@pytest.fixture
def client():
    overrides = app.dependency_overrides.copy()
    actor = {"value": make_profile()}
    app.dependency_overrides[get_current_actor] = lambda: actor["value"]
    app.dependency_overrides[get_session] = lambda: None
    app.dependency_overrides[get_authenticated_session] = lambda: None
    use_cases = AsyncMock(unsafe=True)
    with patch("app.api.v1.routes.account_deletion._use_cases", return_value=use_cases):
        try:
            yield TestClient(app), use_cases, actor
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(overrides)


def test_start_returns_202_with_masked_destination_only(client):
    http, uc, _ = client
    cid = uuid4()
    uc.start_challenge.return_value = {
        "challenge_id": str(cid), "channel": "email", "masked_destination": "t***@example.com",
        "expires_at": NOW, "resend_available_at": NOW,
    }
    response = http.post("/v1/account/deletion/challenges", json={"channel": "email"})
    assert response.status_code == 202
    body = response.json()
    assert body["masked_destination"] == "t***@example.com"
    assert set(body) == {"challenge_id", "channel", "masked_destination", "expires_at",
                         "resend_available_at"}
    uc.start_challenge.assert_awaited_once()
    assert uc.start_challenge.await_args.args[2] is None


def test_client_cannot_name_the_account_or_role_to_delete(client):
    http, uc, _ = client
    for extra in ({"user_id": str(uuid4())}, {"role": "owner"}, {"profile_id": "x"}):
        response = http.post("/v1/account/deletion/challenges", json={"channel": "email", **extra})
        assert response.status_code == 422
    response = http.post(
        "/v1/account/deletion",
        json={"challenge_id": str(uuid4()), "confirmation_token": TOKEN, "confirm": "DELETE",
              "user_id": str(uuid4())},
    )
    assert response.status_code == 422
    uc.start_challenge.assert_not_awaited()
    uc.confirm.assert_not_awaited()


def test_unknown_channel_and_bad_code_shapes_are_rejected(client):
    http, uc, _ = client
    assert http.post("/v1/account/deletion/challenges", json={"channel": "sms"}).status_code == 422
    url = f"/v1/account/deletion/challenges/{uuid4()}/verify"
    assert http.post(url, json={"code": "12"}).status_code == 422
    assert http.post(url, json={"code": "12 34 56"}).status_code == 422
    uc.verify_challenge.assert_not_awaited()


def test_verify_returns_confirmation_token_and_never_deletes(client):
    http, uc, _ = client
    uc.verify_challenge.return_value = {"confirmation_token": TOKEN, "expires_at": NOW}
    response = http.post(
        f"/v1/account/deletion/challenges/{uuid4()}/verify", json={"code": "123456"}
    )
    assert response.status_code == 200
    assert response.json()["confirmation_token"] == TOKEN
    uc.confirm.assert_not_awaited()


def test_confirmation_must_be_the_literal_delete(client):
    http, uc, _ = client
    payload = {"challenge_id": str(uuid4()), "confirmation_token": TOKEN}
    for confirm in (None, "delete", "YES", True):
        body = {**payload, **({} if confirm is None else {"confirm": confirm})}
        assert http.post("/v1/account/deletion", json=body).status_code == 422
    uc.confirm.assert_not_awaited()


def test_confirm_returns_202_with_status_token(client):
    http, uc, _ = client
    rid = uuid4()
    uc.confirm.return_value = {"request_id": str(rid), "status": "pending", "status_token": TOKEN}
    response = http.post(
        "/v1/account/deletion",
        json={"challenge_id": str(uuid4()), "confirmation_token": TOKEN, "confirm": "DELETE"},
    )
    assert response.status_code == 202
    assert response.json() == {"request_id": str(rid), "status": "pending", "status_token": TOKEN}


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (DeletionBlockedError("2 open bookings"), 409, "deletion_blocked"),
        (TooManyRequestsError("slow down"), 429, "too_many_requests"),
        (InvalidVerificationCodeError("bad"), 400, "invalid_verification_code"),
        (NotFoundError("nope"), 404, "not_found"),
    ],
)
def test_domain_errors_map_to_documented_statuses(client, error, status, code):
    http, uc, _ = client
    uc.start_challenge.side_effect = error
    response = http.post("/v1/account/deletion/challenges", json={"channel": "email"})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_status_is_authenticated_by_header_token_not_jwt(client):
    http, uc, _ = client
    rid = uuid4()
    uc.get_status.return_value = {
        "request_id": str(rid), "status": "processing", "requested_at": NOW, "completed_at": None,
    }
    app.dependency_overrides.pop(get_current_actor, None)  # no bearer token at all
    assert http.get(f"/v1/account/deletion/{rid}").status_code == 422
    response = http.get(f"/v1/account/deletion/{rid}", headers={"X-Status-Token": TOKEN})
    assert response.status_code == 200 and response.json()["status"] == "processing"
    uc.get_status.assert_awaited_once_with(str(rid), TOKEN)
    uc.get_status.side_effect = NotFoundError("Deletion request not found")
    assert http.get(f"/v1/account/deletion/{rid}",
                    headers={"X-Status-Token": TOKEN}).status_code == 404


def test_user_routes_require_a_bearer_token():
    overrides = app.dependency_overrides.copy()
    app.dependency_overrides.clear()
    try:
        http = TestClient(app)
        assert http.post("/v1/account/deletion/challenges", json={"channel": "email"}).status_code in {401, 403}
        assert http.post("/v1/account/deletion", json={}).status_code in {401, 403}
    finally:
        app.dependency_overrides.update(overrides)


def test_admin_ledger_is_super_admin_only_and_has_no_personal_fields(client):
    http, uc, actor = client
    uc.list_requests.return_value = [{
        "id": str(uuid4()), "role": "owner", "salon_id": str(uuid4()), "salon_name": "Cuts",
        "salon_city": "Kochi", "status": "completed", "requested_at": NOW, "completed_at": NOW,
        "user_id": "must-not-leak", "email": "leak@example.com",
    }]
    actor["value"] = make_owner()
    assert http.get("/v1/admin/account-deletions").status_code == 403
    actor["value"] = make_super_admin()
    response = http.get("/v1/admin/account-deletions")
    assert response.status_code == 200
    row = response.json()[0]
    assert set(row) == {"id", "role", "salon_id", "salon_name", "salon_city", "status",
                        "requested_at", "completed_at"}


def test_openapi_documents_every_deletion_operation():
    spec = app.openapi()
    paths = spec["paths"]
    expected = {
        ("/v1/account/deletion/challenges", "post", "202", "DeletionChallengeResponse"),
        ("/v1/account/deletion/challenges/{challenge_id}/verify", "post", "200",
         "VerifiedDeletionChallengeResponse"),
        ("/v1/account/deletion", "post", "202", "AccountDeletionAcceptedResponse"),
        ("/v1/account/deletion/{request_id}", "get", "200", "AccountDeletionStatusResponse"),
        ("/v1/admin/account-deletions", "get", "200", "AdminAccountDeletionResponse"),
    }
    for path, method, status, model in expected:
        operation = paths[path][method]
        assert status in operation["responses"], (path, method)
        schema = operation["responses"][status]["content"]["application/json"]["schema"]
        assert model in str(schema), (path, method)
    status_params = {p["name"] for p in paths["/v1/account/deletion/{request_id}"]["get"]["parameters"]}
    assert "x-status-token" in status_params
    confirm = spec["components"]["schemas"]["ConfirmAccountDeletionRequest"]
    assert confirm["properties"]["confirm"] == {
        "const": "DELETE", "description": 'Must be exactly "DELETE".', "title": "Confirm",
        "type": "string",
    }
    assert confirm["additionalProperties"] is False
