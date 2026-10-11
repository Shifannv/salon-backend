"""Owner payout account + setup checklist: validation, merge, masking, authorization."""

import importlib.util
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_current_actor, get_session
from app.application.use_cases.platform import OwnerUseCases, build_setup_status
from app.domain.entities.profile import Role
from app.main import app
from tests.conftest import make_owner, make_profile

VERSIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
ACCOUNT = "123456789012"
NOW = datetime(2026, 10, 11, tzinfo=UTC)


class FakeRepo:
    """In-memory stand-in honouring the repository contract (merge callback)."""

    def __init__(self, facts=None):
        self.row = None
        self.history = []
        self.facts = facts or {}

    def _masked(self):
        if not self.row:
            return None
        masked = {k: v for k, v in self.row.items() if k != "bank_account_number"}
        number = self.row.get("bank_account_number")
        masked["bank_account_last4"] = number[-4:] if number else None
        return masked

    async def get_payout_account(self, actor_id):
        # Contract: the repository returns the masked projection, never the full number.
        return self._masked()

    async def update_payout_account(self, actor_id, values, validate):
        # Mirrors the SQL merge: omitted keeps, explicit None clears; Python sees only
        # a presence marker for the stored account number.
        current = self.row or {}
        view = {f: current.get(f) for f in
                ("account_holder_name", "upi_id", "bank_name", "ifsc")}
        view["bank_account_number"] = "stored" if current.get("bank_account_number") else None
        view.update(values)
        if "bank_account_number" in values and values["bank_account_number"] is None:
            for dependent in ("ifsc", "bank_name"):
                if dependent not in values:
                    view[dependent] = None
                    values = {**values, dependent: None}
        validate(view)
        self.row = {**{f: current.get(f) for f in view}, **values,
                    "created_at": NOW, "updated_at": NOW}
        return self._masked()

    async def list_payout_account_history(self, actor_id, limit=50):
        return self.history[:limit]

    async def get_setup_facts(self, actor_id):
        return self.facts


@pytest.fixture
def api():
    repo = FakeRepo()
    overrides = app.dependency_overrides.copy()
    actor = {"value": make_owner()}
    app.dependency_overrides[get_current_actor] = lambda: actor["value"]
    app.dependency_overrides[get_session] = lambda: None
    app.dependency_overrides[get_authenticated_session] = lambda: None
    with patch(
        "app.api.v1.routes.owner._use_cases", side_effect=lambda *a, **k: OwnerUseCases(repo)
    ):
        try:
            yield TestClient(app), repo, actor
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(overrides)


URL = "/v1/salons/me/payout-account"


def test_get_when_nothing_saved_is_unconfigured(api):
    http, _, _ = api
    body = http.get(URL).json()
    assert body == {
        "configured": False, "account_holder_name": None, "upi_id": None, "bank_name": None,
        "bank_account_last4": None, "ifsc": None, "has_upi": False, "has_bank": False,
        "updated_at": None,
    }


def test_put_upi_only_normalises_and_masks(api):
    http, repo, _ = api
    response = http.put(URL, json={"account_holder_name": "  Asha Nair ", "upi_id": "Asha.N@OkBank"})
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] and body["has_upi"] and not body["has_bank"]
    assert body["account_holder_name"] == "Asha Nair"
    assert body["upi_id"] == "asha.n@okbank"
    assert repo.row["upi_id"] == "asha.n@okbank"


def test_put_bank_masks_account_number_everywhere(api):
    http, repo, _ = api
    response = http.put(URL, json={
        "account_holder_name": "Asha Nair", "bank_name": "HDFC", "bank_account_number": ACCOUNT,
        "ifsc": "hdfc0001234",
    })
    assert response.status_code == 200
    assert ACCOUNT not in response.text
    body = response.json()
    assert body["bank_account_last4"] == "9012" and body["ifsc"] == "HDFC0001234"
    assert body["has_bank"] and not body["has_upi"]
    assert "bank_account_number" not in body
    assert repo.row["bank_account_number"] == ACCOUNT
    assert ACCOUNT not in http.get(URL).text


def test_merge_keeps_omitted_and_null_clears(api):
    http, repo, _ = api
    http.put(URL, json={"account_holder_name": "Asha Nair", "upi_id": "asha@okbank",
                        "bank_account_number": ACCOUNT, "ifsc": "HDFC0001234"})
    body = http.put(URL, json={"bank_name": "HDFC"}).json()
    assert body["upi_id"] == "asha@okbank" and body["bank_account_last4"] == "9012"
    body = http.put(URL, json={"upi_id": None}).json()
    assert body["upi_id"] is None and body["has_bank"]
    assert repo.row["bank_account_number"] == ACCOUNT


def test_clearing_last_destination_is_rejected_without_leaking(api):
    http, repo, _ = api
    http.put(URL, json={"account_holder_name": "Asha Nair", "upi_id": "asha@okbank"})
    response = http.put(URL, json={"upi_id": None})
    assert response.status_code == 422
    assert repo.row["upi_id"] == "asha@okbank"


def test_requires_destination_and_holder_name(api):
    http, _, _ = api
    r = http.put(URL, json={"account_holder_name": "Asha Nair"})
    assert r.status_code == 422 and "UPI" in r.json()["error"]["message"]
    r = http.put(URL, json={"upi_id": "asha@okbank"})
    assert r.status_code == 422 and "holder" in r.json()["error"]["message"]
    # account number without IFSC is not a destination
    r = http.put(URL, json={"account_holder_name": "Asha Nair", "bank_account_number": ACCOUNT})
    assert r.status_code == 422


@pytest.mark.parametrize("payload", [
    {"account_holder_name": "A", "upi_id": "ab@okbank"},
    {"account_holder_name": "Asha", "upi_id": "not-a-upi"},
    {"account_holder_name": "Asha", "upi_id": "a@ok1"},
    {"account_holder_name": "Asha", "bank_account_number": "12345678", "ifsc": "HDFC0001234"},
    {"account_holder_name": "Asha", "bank_account_number": "1234567890123456789",
     "ifsc": "HDFC0001234"},
    {"account_holder_name": "Asha", "bank_account_number": "12345678a", "ifsc": "HDFC0001234"},
    {"account_holder_name": "Asha", "bank_account_number": ACCOUNT, "ifsc": "HDFC1001234"},
    {"account_holder_name": "Asha", "upi_id": "ab@okbank", "bank_name": "x" * 101},
    {"account_holder_name": "Asha", "upi_id": "ab@okbank", "salon_id": "other"},
])
def test_field_validation_rejects_bad_input(api, payload):
    http, repo, _ = api
    assert http.put(URL, json=payload).status_code == 422
    assert repo.row is None


def test_validation_error_never_echoes_or_logs_account_number(api, caplog):
    http, _, _ = api
    secret = "98765432109x"
    with caplog.at_level(logging.DEBUG):
        response = http.put(URL, json={"account_holder_name": "Asha", "bank_account_number": secret,
                                       "ifsc": "HDFC0001234"})
    assert response.status_code == 422
    assert secret not in response.text
    assert secret not in caplog.text


@pytest.mark.parametrize("role", [Role.customer, Role.staff, Role.super_admin])
def test_only_owner_can_read_or_write(api, role):
    http, repo, actor = api
    actor["value"] = make_profile(role=role)
    assert http.get(URL).status_code == 403
    assert http.put(URL, json={"account_holder_name": "Asha", "upi_id": "ab@okbank"}).status_code == 403
    assert http.get("/v1/salons/me/setup-status").status_code == 403
    assert repo.row is None


# ---- setup checklist --------------------------------------------------------

FULL = {
    "name": "Luxe", "category": "unisex", "address": "MG Road", "city": "Kochi",
    "working_hours": {"mon": {"open": "09:00", "close": "18:00"}},
    "has_photos": True, "has_services": True, "has_staff": True, "has_payout": True,
}


def test_setup_status_fresh_owner_has_nothing_done():
    status = build_setup_status({
        "name": "", "category": None, "address": None, "city": None, "working_hours": {},
        "has_photos": False, "has_services": False, "has_staff": False, "has_payout": False,
    })
    assert [i["key"] for i in status["items"]] == [
        "profile_basics", "working_hours", "photos", "services", "staff", "payout"]
    assert [i["action"] for i in status["items"]] == [
        "business_profile", "working_hours", "photos", "services", "staff", "payout"]
    assert status["completed_count"] == 0 and status["total_count"] == 6
    assert status["is_complete"] is False
    assert all(i["title"] and i["description"] and i["done"] is False for i in status["items"])


def test_setup_status_complete_and_partial_rules():
    assert build_setup_status(FULL)["is_complete"] is True
    partial = build_setup_status({**FULL, "city": "  ", "working_hours": {"mon": {"open": None}},
                                  "has_staff": False})
    done = {i["key"]: i["done"] for i in partial["items"]}
    assert done == {"profile_basics": False, "working_hours": False, "photos": True,
                    "services": True, "staff": False, "payout": True}
    assert partial["completed_count"] == 3 and partial["is_complete"] is False


def test_setup_status_endpoint_shape(api):
    http, repo, _ = api
    repo.facts = FULL
    body = http.get("/v1/salons/me/setup-status").json()
    assert set(body) == {"completed_count", "total_count", "is_complete", "items"}
    assert set(body["items"][0]) == {"key", "title", "description", "done", "action"}
    assert body["is_complete"] is True


def test_openapi_lists_new_routes():
    paths = app.openapi()["paths"]
    assert {"get", "put"} <= set(paths[URL])
    assert "get" in paths["/v1/salons/me/setup-status"]
    schema = str(app.openapi()["components"]["schemas"]["OwnerPayoutAccountResponse"])
    assert "bank_account_number" not in schema


# ---- migration / erasure ----------------------------------------------------


def _migration():
    spec = importlib.util.spec_from_file_location(
        "payout_revision", VERSIONS / "0025_salon_payout_accounts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sql(fn):
    statements = []
    module = _migration()
    with patch.object(module.op, "execute", side_effect=lambda s: statements.append(str(s))):
        getattr(module, fn)()
    return " ".join(statements).lower()


def test_migration_chain_and_security_shape():
    module = _migration()
    assert module.revision == "0025_salon_payout_accounts"
    assert module.down_revision == "0024_secure_new_user_role"
    sql = _sql("upgrade")
    assert "salon_id            uuid primary key references public.salons(id) on delete cascade" in sql
    assert "enable row level security" in sql
    assert "owns_salon(salon_id)" in sql
    assert "revoke all on public.salon_payout_accounts from public, anon, authenticated" in sql
    assert "upi_id is not null or (bank_account_number is not null and ifsc is not null)" in sql
    assert "drop table" in _sql("downgrade")


def test_erasure_explicitly_deletes_payout_rows():
    source = (Path(__file__).resolve().parents[2] / "app" / "infrastructure" / "db"
              / "repositories" / "account_deletion_repository.py").read_text(encoding="utf-8")
    from app.infrastructure.db.repositories.account_deletion_repository import SALON_CASCADE_TABLES

    assert "salon_payout_accounts" in SALON_CASCADE_TABLES
    assert "salon_payout_account_history" in SALON_CASCADE_TABLES
    assert "delete from {table} where salon_id in" in source


# ---- Part 4 hardening --------------------------------------------------------


def test_history_endpoint_returns_last4_only(api):
    http, repo, _ = api
    repo.history = [{
        "id": "h1", "changed_at": NOW, "action": "updated", "changed_fields": ["upi_id"],
        "changed_by_name": "Asha",
        "before_state": {"upi_id": "a@okbank", "bank_account_last4": "9012"},
        "after_state": {"upi_id": "b@okbank", "bank_account_last4": "9012"},
    }]
    response = http.get(URL + "/history")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["after"]["bank_account_last4"] == "9012" and body[0]["before"]["upi_id"]
    assert "bank_account_number" not in response.text


def test_history_is_owner_only(api):
    http, _, actor = api
    actor["value"] = make_profile(role=Role.staff)
    assert http.get(URL + "/history").status_code == 403


async def test_reads_never_provision_a_salon():
    from unittest.mock import AsyncMock, MagicMock

    from app.infrastructure.db.repositories.platform_repository import PlatformRepository

    repo = PlatformRepository(MagicMock())
    repo._get_owner_salon_row = AsyncMock(return_value=None)
    repo.provision_owner_salon = AsyncMock()
    assert await repo.get_payout_account("owner") is None
    assert await repo.list_payout_account_history("owner") == []
    facts = await repo.get_setup_facts("owner")
    assert facts["has_payout"] is False and facts["name"] is None
    repo.provision_owner_salon.assert_not_awaited()


def test_repository_never_selects_the_full_account_number():
    source = (Path(__file__).resolve().parents[2] / "app/infrastructure/db/repositories"
              / "platform_repository.py").read_text(encoding="utf-8")
    start = source.index("async def get_payout_account")
    end = source.index("async def update_owner_salon")
    block = source[start:end]
    assert "salon_payout_account_masked" in block
    assert not re.search(r"select[^;]*bbank_account_numberb[^;]*from salon_payout_accounts",
                         block, re.DOTALL)
    assert "coalesce" not in block or "case when" in block  # merge is SQL-side


def test_clearing_account_number_also_clears_dependent_bank_fields(api):
    http, _, _ = api
    http.put(URL, json={"account_holder_name": "Asha Nair", "upi_id": "asha@okbank",
                        "bank_name": "HDFC", "bank_account_number": ACCOUNT,
                        "ifsc": "HDFC0001234"})
    body = http.put(URL, json={"bank_account_number": None}).json()
    assert body["has_bank"] is False and body["ifsc"] is None and body["bank_name"] is None


def test_0027_shape():
    module = _migration_named("0027_payout_account_audit")
    assert module.down_revision == "0026_booking_payments"


def _migration_named(name):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
