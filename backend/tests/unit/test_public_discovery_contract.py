"""Public discovery contract: service search, public-response privacy and payment capability.

Runs the real repository SQL against the in-memory harness from test_public_salon_visibility.
"""

import json

import pytest

from app.api.v1.schemas.platform import SalonDetailResponse, SalonSummaryResponse
from app.main import app
from tests.unit.test_public_salon_visibility import public_api  # noqa: F401

TOKEN = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"
SERVICE_COLUMNS = "(id,salon_id,price,is_active,subcategory_id,name,duration_minutes)"

# Fields that must never appear in a public salon, service or staff payload.
PRIVATE_KEYS = {
    "qr_token", "owner_id", "approval_status", "approved_by", "approved_at", "rejection_reason",
    "slot_interval_minutes", "display_priority", "discovery_visibility", "home_placement",
    "email", "phone", "payout", "upi_id",
}


def add_salon(session, key, name, *, city=None, address=None, services=(), accepting=True,
              staff_active=True, service_active=True):
    """Insert a public salon. ``services`` is a list of service names (all under subcategory 'Cut')."""
    salon_id = f"00000000-0000-0000-0000-{key:012d}"
    session.db.execute(
        "insert into salons (id,name,city,address,timezone,working_hours,approval_mode,"
        "slot_interval_minutes,approval_status,is_active,profile_completed,accepting_bookings,qr_token) "
        "values (?,?,?,?, 'UTC','{}','automatic',30,'approved',1,1,?,?)",
        (salon_id, name, city, address, accepting, TOKEN),
    )
    for number, service in enumerate(services):
        service_id = f"{salon_id[:-3]}s{key % 10}{number}"
        session.db.execute(
            f"insert into services {SERVICE_COLUMNS} values (?,?,100,?,'subcategory',?,30)",
            (service_id, salon_id, service_active, service),
        )
        staff_id = f"{service_id}-staff"
        session.db.execute("insert into staff (id,salon_id,is_active,name) values (?,?,?, 'Barber')",
                           (staff_id, salon_id, staff_active))
        session.db.execute("insert into staff_services(staff_id,service_id,is_active) values (?,?,1)", (staff_id, service_id))
    return salon_id


@pytest.fixture
def catalog(public_api):  # noqa: F811
    client, session, cache = public_api
    session.db.execute("delete from salons")
    session.db.execute("update service_subcategories set name='Styling'")
    ids = {
        "alpha": add_salon(session, 101, "Alpha Cuts", city="Kochi", address="1 Marine Drive",
                           services=["Haircut", "Beard trim"]),
        "bravo": add_salon(session, 102, "Bravo Studio", city="Kochi Fort", address="9 Beach Road",
                           services=["Facial"]),
        "charlie": add_salon(session, 103, "Charlie Salon", city="Kozhikode", address="Alpha Tower, MG Road",
                             services=["Haircut"]),
    }
    return client, session, cache, ids


def found(client, path, **params):
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    return sorted(row["name"] for row in response.json())


# ── search by salon name, city/area and service ──────────────────────────────


def test_search_matches_name_city_or_address_ignoring_case(catalog):
    client, *_ = catalog
    assert found(client, "/v1/salons", search="alpha") == ["Alpha Cuts", "Charlie Salon"]  # name and address
    assert found(client, "/v1/salons", search="KOZHI") == ["Charlie Salon"]  # city
    assert found(client, "/v1/salons", search="marine") == ["Alpha Cuts"]  # address
    assert found(client, "/v1/salons", search="nothing like this") == []


def test_percent_and_underscore_in_search_are_literal(catalog):
    client, *_ = catalog
    assert found(client, "/v1/salons", search="%") == []
    assert found(client, "/v1/salons", search="_") == []
    assert found(client, "/v1/salons", service="%") == []


def test_city_filter_is_exact_but_ignores_case_and_spaces(catalog):
    client, *_ = catalog
    assert found(client, "/v1/salons", city="kochi") == ["Alpha Cuts"]
    assert found(client, "/v1/salons", city="  KOCHI ") == ["Alpha Cuts"]
    assert found(client, "/v1/salons", city="Kochi Fort") == ["Bravo Studio"]


def test_service_filter_matches_service_name_and_subcategory(catalog):
    client, *_ = catalog
    assert found(client, "/v1/salons", service="haircut") == ["Alpha Cuts", "Charlie Salon"]
    assert found(client, "/v1/salons", service="FACIAL") == ["Bravo Studio"]
    assert found(client, "/v1/salons", service="styling") == ["Alpha Cuts", "Bravo Studio", "Charlie Salon"]
    assert found(client, "/v1/salons", service="massage") == []


def test_filters_combine_with_and(catalog):
    client, *_ = catalog
    assert found(client, "/v1/salons", service="haircut", city="Kochi") == ["Alpha Cuts"]
    assert found(client, "/v1/salons", service="haircut", search="charlie") == ["Charlie Salon"]
    assert found(client, "/v1/salons", service="facial", city="Kozhikode") == []


def test_nearby_supports_the_same_filters(catalog):
    client, *_ = catalog
    assert found(client, "/v1/salons/nearby", service="facial") == ["Bravo Studio"]
    assert found(client, "/v1/salons/nearby", search="alpha", service="haircut", latitude=9.9, longitude=76.2) == [
        "Alpha Cuts", "Charlie Salon"]


def test_service_search_only_counts_bookable_services_at_public_salons(catalog):
    client, session, *_ = catalog
    add_salon(session, 104, "Delta Hidden Service", services=["Massage"], service_active=False)
    add_salon(session, 105, "Echo No Staff", services=["Massage"], staff_active=False)
    private = add_salon(session, 106, "Foxtrot Unapproved", services=["Massage"])
    session.db.execute("update salons set approval_status='pending' where id=?", (private,))
    assert found(client, "/v1/salons", service="massage") == []
    assert found(client, "/v1/salons/nearby", service="massage") == []


def test_search_inputs_are_length_limited(catalog):
    client, *_ = catalog
    for path in ("/v1/salons", "/v1/salons/nearby"):
        for param in ("search", "city", "service"):
            response = client.get(path, params={param: "x" * 81})
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "validation_error"
            assert client.get(path, params={param: "x" * 80}).status_code == 200


# ── public responses never expose tokens or private salon/owner data ─────────


def walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def test_public_responses_never_contain_a_qr_token_or_private_fields(catalog):
    client, _, cache, ids = catalog
    salon_id = ids["alpha"]
    # A poisoned cache entry from before the fix must not leak either: the response model is the filter.
    cache._store[f"salon:{salon_id}:detail"] = {
        "id": salon_id, "name": "Alpha Cuts", "timezone": "UTC", "working_hours": {}, "approval_mode": "automatic",
        "profile_completed": True, "is_active": True, "qr_token": TOKEN, "owner_id": "owner-1",
    }
    paths = [
        "/v1/salons", "/v1/salons?search=alpha", "/v1/salons?service=haircut", "/v1/salons/nearby",
        "/v1/salons/nearby?latitude=9.9&longitude=76.2", f"/v1/salons/{salon_id}",
        f"/v1/salons/{salon_id}/services", f"/v1/salons/{salon_id}/staff",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path
        assert TOKEN not in response.text, path
        assert not PRIVATE_KEYS & set(walk(response.json())), path


def test_openapi_keeps_tokens_in_the_walkin_resolver_only():
    schemas = app.openapi()["components"]["schemas"]
    for name in ("SalonSummaryResponse", "SalonDetailResponse", "ServiceResponse", "PublicStaffResponse"):
        assert "qr_token" not in schemas[name]["properties"], name
    assert "qr_token" in schemas["WalkInSalonResponse"]["properties"]
    # Services and staff inside the walk-in payload carry no token either.
    for name in ("WalkInServiceSummary", "WalkInStaffSummary"):
        assert "qr_token" not in schemas[name]["properties"], name


def test_openapi_documents_the_service_filter_on_both_list_routes():
    paths = app.openapi()["paths"]
    for path in ("/v1/salons", "/v1/salons/nearby"):
        params = {p["name"]: p for p in paths[path]["get"]["parameters"]}
        assert params["service"]["schema"]["anyOf"][0]["maxLength"] == 80
        assert "service" in params["service"]["description"].lower()
        assert params["search"]["schema"]["anyOf"][0]["maxLength"] == 80
        assert params["city"]["schema"]["anyOf"][0]["maxLength"] == 80


# ── payment capability is backend-owned and accurate ─────────────────────────


def test_payment_options_default_to_pay_at_salon_only(catalog):
    client, _, _, ids = catalog
    for path in ("/v1/salons", "/v1/salons/nearby"):
        for row in client.get(path).json():
            assert row["accepts_bookings"] is True
            assert row["payment_options"] == ["PAY_AT_SALON"]
            assert row["online_payment_available"] is False
            assert row["online_payment_unavailable_reason"]
    detail = client.get(f"/v1/salons/{ids['alpha']}").json()
    assert detail["payment_options"] == ["PAY_AT_SALON"]
    assert detail["online_payment_available"] is False


def test_a_paused_salon_offers_no_payment_method(catalog):
    client, session, *_ = catalog
    paused = add_salon(session, 107, "Golf Paused", services=["Haircut"], accepting=False)
    row = next(r for r in client.get("/v1/salons").json() if r["id"] == paused)
    assert row["accepting_bookings"] is False
    assert row["accepts_bookings"] is False
    assert row["payment_options"] == []
    assert row["online_payment_available"] is False
    assert client.get(f"/v1/salons/{paused}").json()["payment_options"] == []


def test_online_payment_is_listed_only_when_the_gateway_is_enabled(catalog, monkeypatch):
    client, *_ = catalog

    class Enabled:
        enabled = True

    monkeypatch.setattr("app.infrastructure.payments.resolver.get_payment_resolver", lambda: Enabled())
    row = client.get("/v1/salons").json()[0]
    assert row["payment_options"] == ["PAY_AT_SALON", "PAY_ONLINE"]
    assert row["online_payment_available"] is True
    assert row["online_payment_unavailable_reason"] is None


def test_capability_is_recomputed_for_cached_payloads(catalog, monkeypatch):
    client, _, cache, ids = catalog
    assert client.get(f"/v1/salons/{ids['alpha']}").json()["payment_options"] == ["PAY_AT_SALON"]
    assert f"salon:{ids['alpha']}:detail" in cache._store  # second request is served from cache

    class Enabled:
        enabled = True

    monkeypatch.setattr("app.infrastructure.payments.resolver.get_payment_resolver", lambda: Enabled())
    assert "PAY_ONLINE" in client.get(f"/v1/salons/{ids['alpha']}").json()["payment_options"]


def test_payment_schema_values_are_enumerated():
    schemas = app.openapi()["components"]["schemas"]
    for name in ("SalonSummaryResponse", "SalonDetailResponse", "WalkInSalonResponse"):
        items = schemas[name]["properties"]["payment_options"]["items"]
        assert set(items["enum"]) == {"PAY_AT_SALON", "PAY_ONLINE"}, name


def test_response_models_still_validate_directly():
    base = {"id": "1", "name": "S", "timezone": "UTC", "approval_mode": "auto", "profile_completed": True,
            "is_active": True, "accepting_bookings": True}
    assert SalonSummaryResponse(**base).payment_options == ["PAY_AT_SALON"]
    assert json.loads(SalonDetailResponse(**base, working_hours={}).model_dump_json())["payment_options"] == [
        "PAY_AT_SALON"]


# ── service search stays consistent with the public services list ────────────


def _listed(client, salon_id):
    return [row["name"] for row in client.get(f"/v1/salons/{salon_id}/services").json()]


def test_service_search_matches_what_the_services_list_shows(catalog):
    client, _, _, ids = catalog
    assert found(client, "/v1/salons", service="facial") == ["Bravo Studio"]
    assert found(client, "/v1/salons/nearby", service="facial") == ["Bravo Studio"]
    assert _listed(client, ids["bravo"]) == ["Facial"]


@pytest.mark.parametrize("table", ["service_categories", "service_subcategories"])
def test_service_search_requires_active_category_and_subcategory(catalog, table):
    client, session, _, ids = catalog
    session.db.execute(f"update {table} set is_active=0")
    assert found(client, "/v1/salons", service="facial") == []
    assert found(client, "/v1/salons/nearby", service="facial") == []
    assert _listed(client, ids["bravo"]) == []


def test_inactive_category_service_search_keeps_literal_wildcards(catalog):
    client, session, *_ = catalog
    session.db.execute("update service_categories set is_active=0")
    assert found(client, "/v1/salons", service="%") == []
    assert found(client, "/v1/salons", service="_") == []
