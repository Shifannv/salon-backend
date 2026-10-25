"""Removed owner metadata must not leak into the client contract or writes."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.platform import (
    OwnerSalonUpdateRequest,
    ServiceCreateRequest,
    ServiceUpdateRequest,
)
from app.main import app


def test_removed_fields_are_absent_from_openapi():
    schemas = app.openapi()["components"]["schemas"]
    for name in ("SalonSummaryResponse", "SalonDetailResponse", "OwnerSalonResponse",
                 "AdminSalonResponse", "AdminSalonOnboardingResponse", "OwnerSalonUpdateRequest",
                 "OwnerSalonCompleteProfileRequest", "WalkInSalonResponse"):
        assert "description" not in schemas[name]["properties"], name
        assert "category" not in schemas[name]["properties"], name
    for name in ("ServiceCreateRequest", "ServiceUpdateRequest"):
        assert "description" not in schemas[name]["properties"]
        assert {"category_name", "subcategory_name"} <= schemas[name]["properties"].keys()
    for name in ("ServiceResponse", "WalkInServiceSummary"):
        assert "description" not in schemas[name]["properties"]
        # Catalog identifiers and category display labels remain available.
        assert {"subcategory_id", "category_name", "subcategory_name"} <= schemas[name]["properties"].keys()


@pytest.mark.parametrize("field", ["description", "category"])
def test_salon_rejects_removed_fields(field):
    with pytest.raises(ValidationError):
        OwnerSalonUpdateRequest.model_validate({field: "obsolete"})


@pytest.mark.parametrize("model", [ServiceCreateRequest, ServiceUpdateRequest])
@pytest.mark.parametrize("field", ["description"])
def test_services_reject_optional_overrides(model, field):
    with pytest.raises(ValidationError):
        model.model_validate({"name": "Cut", "duration_minutes": 30, "price": 100, field: "obsolete"})


@pytest.mark.parametrize("field", ["name", "address", "city"])
@pytest.mark.parametrize("value", [None, "", " \t\n "])
def test_salon_cannot_clear_required_profile_details(field, value):
    with pytest.raises(ValidationError):
        OwnerSalonUpdateRequest.model_validate({field: value})


def test_partial_salon_updates_preserve_omitted_fields_and_trim_details():
    assert OwnerSalonUpdateRequest().model_dump(exclude_unset=True) == {}
    assert OwnerSalonUpdateRequest(name="  Studio  ").name == "Studio"
