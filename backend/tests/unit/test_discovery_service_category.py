"""Discovery must agree with the service category shown to customers."""

import pytest

from tests.unit.test_public_salon_visibility import public_api  # noqa: F401


@pytest.mark.parametrize("path", ["/v1/salons", "/v1/salons/nearby"])
def test_category_uses_service_presentation_not_salon_business_label(public_api, path):  # noqa: F811
    client, session, _ = public_api
    salon_id = session.ids[0]
    session.db.execute("update service_categories set name='General'")
    session.db.execute("update services set category_name='Hair Cutting'")
    session.db.execute("update salons set category='Beard Care'")

    response = client.get(path, params={"category": "Hair Cutting"})
    assert response.status_code == 200
    assert [salon["id"] for salon in response.json()] == [salon_id]
    assert client.get(path, params={"category": "Beard Care"}).json() == []
    assert client.get(path, params={"category": "General"}).json() == []


@pytest.mark.parametrize("change", [
    "update staff_services set is_active=0",
    "update staff set is_active=0",
    "delete from staff_services",
])
def test_category_requires_service_assigned_to_active_staff(public_api, change):  # noqa: F811
    client, session, _ = public_api
    session.db.execute(change)
    response = client.get("/v1/salons", params={"category": "Hair"})
    assert response.status_code == 200
    assert response.json() == []
