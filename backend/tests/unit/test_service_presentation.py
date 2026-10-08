"""Service contract validation and media ownership checks."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.platform import ServiceCreateRequest, ServiceUpdateRequest
from app.application.use_cases.platform import OwnerUseCases
from app.core.exceptions import ValidationError as BusinessValidationError
from app.main import app
from tests.conftest import make_mock_repo, make_owner


@pytest.mark.parametrize("model", [ServiceCreateRequest, ServiceUpdateRequest])
@pytest.mark.parametrize("fields", [
    {"category_name": " "}, {"subcategory_name": "x" * 81},
    {"photo_url": "file:///photo.jpg"}, {"photo_url": "content://photo"},
    {"photo_url": "blob:https://example.com/photo"},
    {"photo_url": "data:image/jpeg;base64,abc"},
    {"photo_url": "http://example.com/photo"}, {"photo_url": "https://"},
    {"photo_url": "https://user:password@example.com/photo"},
    {"photo_url": "https://example.com/" + "x" * 2048},
    {"photo_url": "https://example.com/ bad"}, {"unknown": True},
    {"photo_url": "https://example.com/owner/%2e%2e/other/photo.jpg"},
    {"photo_url": "https://example.com:invalid/photo.jpg"},
])
def test_invalid_service_fields(model, fields):
    with pytest.raises(ValidationError):
        model.model_validate({"name": "Nails", "duration_minutes": 30, "price": 250, **fields})


def test_patch_omission_null_and_openapi():
    assert ServiceUpdateRequest(price=300).model_dump(exclude_unset=True) == {"price": 300}
    assert ServiceUpdateRequest(photo_url=None).model_dump(exclude_unset=True) == {"photo_url": None}
    assert ServiceUpdateRequest(category_name=" Nail care ").category_name == "Nail care"
    for field in ("name", "duration_minutes", "price", "is_active", "subcategory_id"):
        with pytest.raises(ValidationError):
            ServiceUpdateRequest.model_validate({field: None})
    schemas = app.openapi()["components"]["schemas"]
    for name in ("ServiceCreateRequest", "ServiceUpdateRequest"):
        assert {"category_name", "subcategory_name", "photo_url"} <= schemas[name]["properties"].keys()
        assert schemas[name]["additionalProperties"] is False
    for name in ("ServiceResponse", "WalkInServiceSummary"):
        assert "photo_url" in schemas[name]["properties"]


@pytest.mark.asyncio
async def test_service_photo_uses_owned_media_namespace():
    repo = make_mock_repo()
    repo.get_owner_salon.return_value = {"id": "salon-001"}
    uc = OwnerUseCases(repo, service_media_base="https://media.example.com")
    for url in ("https://evil.example.com/photo.jpg",
                "https://media.example.com/salon-images/other/photo.jpg"):
        with pytest.raises(BusinessValidationError):
            await uc.update_service(make_owner(), "service", {"photo_url": url})
    repo.update_owner_service.assert_not_awaited()
    await uc.update_service(make_owner(), "service", {
        "photo_url": "https://media.example.com/salon-images/salon-001/photo.jpg",
    })
    repo.update_owner_service.assert_awaited_once()
