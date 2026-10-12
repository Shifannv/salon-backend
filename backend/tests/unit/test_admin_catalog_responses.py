"""Admin catalog endpoints must serialize UUID values returned by asyncpg."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_cache, get_current_actor
from app.core.config import settings
from app.main import app
from tests.conftest import make_super_admin

CATEGORY_ID = UUID("00000000-0000-4000-8000-000000000001")
SUBCATEGORY_ID = UUID("00000000-0000-4000-8000-000000000002")


@pytest.fixture
def catalog_client(monkeypatch):
    previous = app.dependency_overrides.copy()
    monkeypatch.setattr(settings, "admin_require_mfa", False)
    app.dependency_overrides[get_current_actor] = make_super_admin
    app.dependency_overrides[get_authenticated_session] = lambda: None
    app.dependency_overrides[get_cache] = lambda: AsyncMock()
    use_cases = AsyncMock()
    try:
        with patch("app.api.v1.routes.admin._catalog_use_cases", return_value=use_cases):
            yield TestClient(app, raise_server_exceptions=False), use_cases
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.parametrize("subcategory", [False, True])
@pytest.mark.parametrize("action", ["list", "create", "update", "deactivate"])
def test_catalog_responses_accept_database_uuids(catalog_client, subcategory, action):
    client, use_cases = catalog_client
    object_id = SUBCATEGORY_ID if subcategory else CATEGORY_ID
    singular = "subcategory" if subcategory else "category"
    plural = "subcategories" if subcategory else "categories"
    now = datetime.now(UTC)
    row = {
        "id": object_id,
        "name": "Hair",
        "slug": "hair",
        "sort_order": 0,
        "is_active": action != "deactivate",
        "created_at": now,
        "updated_at": now,
    }
    if subcategory:
        row["category_id"] = CATEGORY_ID
    operation = getattr(use_cases, f"{action}_{plural if action == 'list' else singular}")
    operation.return_value = [row] if action == "list" else row
    path = f"/v1/admin/catalog/{plural}"
    if action == "list":
        if subcategory:
            path = f"/v1/admin/catalog/categories/{CATEGORY_ID}/subcategories"
        response = client.get(path)
    elif action == "create":
        payload = {"name": "Hair", "slug": "hair"}
        if subcategory:
            payload["category_id"] = str(CATEGORY_ID)
        response = client.post(path, json=payload)
    elif action == "update":
        response = client.patch(f"{path}/{object_id}", json={"name": "Hair"})
    else:
        response = client.post(f"{path}/{object_id}/deactivate")
    assert response.status_code == (201 if action == "create" else 200), response.text
    result = response.json()[0] if action == "list" else response.json()
    assert result["id"] == str(object_id)
    if subcategory:
        assert result["category_id"] == str(CATEGORY_ID)
    operation.assert_awaited_once()
