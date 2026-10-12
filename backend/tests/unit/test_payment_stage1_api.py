"""Commission arithmetic, API contract for the new/changed routes, KYC scrubbing, migration 0029 shape."""

import importlib.util
import logging
import re
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.routes import payments as payment_routes
from app.core.exceptions import register_exception_handlers
from app.domain.entities.payment import CommissionBase
from app.domain.entities.profile import Role
from app.domain.services.commission import commission_reversal, compute_commission
from app.main import app as real_app
from tests.conftest import make_profile

D = Decimal
VERSIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"


# --------------------------------------------------------------------- commission maths
@pytest.mark.parametrize(
    ("rate", "base", "pay", "total", "allocated", "expected"),
    [
        ("10", "online_amount", "199.99", "500", "0", "20.00"),       # 19.999 -> half-up
        ("2.5", "online_amount", "100.00", "100", "0", "2.50"),
        ("0", "online_amount", "100.00", "100", "0", "0.00"),
        ("100", "online_amount", "100.00", "100", "0", "100.00"),
        ("10", "booking_total", "300.00", "1000", "0", "100.00"),
        ("10", "booking_total", "50.00", "1000", "0", "50.00"),        # clamped to the payment
        ("10", "booking_total", "700.00", "1000", "100.00", "0.00"),   # already fully allocated
        ("10", "booking_total", "700.00", "1000", "30.00", "70.00"),
    ],
)
def test_commission_snapshot_arithmetic(rate, base, pay, total, allocated, expected):
    got = compute_commission(rate_percent=D(rate), base=base, payment_amount=D(pay),
                             booking_total=D(total), already_allocated=D(allocated))
    assert got == D(expected) and isinstance(got, Decimal)


def test_commission_rejects_out_of_range_rate_and_never_exceeds_payment():
    with pytest.raises(ValueError):
        compute_commission(rate_percent=D("101"), base=CommissionBase.online_amount,
                           payment_amount=D("1"), booking_total=D("1"), already_allocated=D(0))
    with pytest.raises(ValueError):
        compute_commission(rate_percent=D("-1"), base="online_amount", payment_amount=D("1"),
                           booking_total=D("1"), already_allocated=D(0))
    with pytest.raises(ValueError):
        compute_commission(rate_percent=D("5"), base="nonsense", payment_amount=D("1"),
                           booking_total=D("1"), already_allocated=D(0))


def test_reversal_is_proportional_and_the_last_refund_absorbs_rounding():
    kw = {"commission": D("10.00"), "payment_amount": D("30.00")}
    first = commission_reversal(refund_amount=D("10.00"), already_reversed=D(0), already_refunded=D(0), **kw)
    second = commission_reversal(refund_amount=D("10.00"), already_reversed=first, already_refunded=D("10.00"), **kw)
    last = commission_reversal(refund_amount=D("10.00"), already_reversed=first + second,
                               already_refunded=D("20.00"), **kw)
    assert (first, second, last) == (D("3.33"), D("3.33"), D("3.34")) and first + second + last == D("10.00")
    assert commission_reversal(commission=D("0"), payment_amount=D("30"), refund_amount=D("5"),
                               already_reversed=D(0), already_refunded=D(0)) == D("0.00")
    assert commission_reversal(commission=D("10"), payment_amount=D("30"), refund_amount=D("5"),
                               already_reversed=D("10"), already_refunded=D("25")) == D("0.00")


# ------------------------------------------------------------------------ API contract
class FakeUseCases:
    def __init__(self):
        self.calls = []

    async def register_settlement_account(self, actor, key, details):
        self.calls.append(("register", key, details))
        return {"provider_enabled": True, "supported": True, "requires_details": True,
                "onboarding_status": "pending", "requirements": ["Your KYC details are being reviewed."],
                "account_reference_masked": "...g1"}

    async def refresh(self, actor, booking_id, order_ref, key):
        self.calls.append(("refresh", booking_id, order_ref, key))
        return BOOKING_BODY

    async def confirm(self, actor, booking_id, order_ref, payment_ref, signature, key):
        self.calls.append(("confirm", order_ref, payment_ref, signature))
        return BOOKING_BODY


BOOKING_BODY = {
    "booking_id": "b1", "currency": "INR", "total_price": "500.00", "deposit_amount": None,
    "paid_amount": "500.00", "refunded_amount": "0.00", "payment_status": "paid",
    "payment_state": "paid", "refunds": [],
    "payments": [{"id": "p1", "booking_id": "b1", "channel": "gateway", "purpose": "full",
                  "settlement_model": "platform_collect", "provider": "cashfree", "amount": "500.00",
                  "currency": "INR", "status": "captured", "overcollected_amount": "0.00",
                  "created_at": "2026-10-12T10:00:00+00:00"}],
}

VALID = {
    "legal_name": "Asha Salon", "contact_email": "owner@example.com", "contact_phone": "9876543210",
    "account_type": "individual", "business_type": "salon", "pan": "ABCDE1234F",
    "bank_account_number": "123456789012", "ifsc": "HDFC0001234",
}


@pytest.fixture
def client():
    fake = FakeUseCases()
    api = FastAPI()
    register_exception_handlers(api)
    api.include_router(payment_routes.router)
    api.dependency_overrides[deps.get_current_actor] = lambda: make_profile("owner-1", Role.owner)
    api.dependency_overrides[deps.get_authenticated_session] = lambda: None
    with patch.object(payment_routes, "_use_cases", lambda session, resolver: fake):
        yield TestClient(api), fake


H = {"Idempotency-Key": "idem-key-0001"}


def test_register_accepts_kyc_and_never_returns_it(client):
    http, fake = client
    response = http.post("/salons/me/settlement-account/register", json=VALID, headers=H)
    assert response.status_code == 200
    body = response.json()
    assert body["onboarding_status"] == "pending" and body["account_reference_masked"] == "...g1"
    for secret in VALID.values():
        assert secret not in response.text
    details = fake.calls[0][2]
    assert details.pan == "ABCDE1234F" and "ABCDE1234F" not in repr(details)  # not in repr either


def test_register_is_still_callable_without_a_body_for_providers_that_need_none(client):
    http, fake = client
    assert http.post("/salons/me/settlement-account/register", headers=H).status_code == 200
    assert fake.calls[0][2] is None


@pytest.mark.parametrize("bad", [
    {"pan": "not-a-pan"}, {"ifsc": "BAD"}, {"bank_account_number": "12ab"}, {"contact_phone": "123"},
    {"contact_email": "nope"}, {"account_type": "company"}, {"unexpected": "field"},
    {"bank_account_number": None, "ifsc": None},                       # neither bank nor upi
    {"upi_id": "asha@okbank"},                                         # both bank and upi
    {"ifsc": None},                                                    # half a bank pair
])
def test_register_422_never_echoes_submitted_values_or_logs_them(client, bad, caplog):
    http, _ = client
    payload = {**VALID, **bad}
    with caplog.at_level(logging.DEBUG):
        response = http.post("/salons/me/settlement-account/register", json=payload, headers=H)
    assert response.status_code == 422
    sensitive = ("pan", "bank_account_number", "ifsc", "contact_email", "contact_phone", "upi_id", "legal_name")
    leaked = [str(payload[k]) for k in sensitive if payload.get(k) and k not in bad or k in bad and bad[k] and len(str(bad[k])) >= 4]
    haystack = response.text + "\n".join(r.getMessage() for r in caplog.records)
    for value in leaked:
        assert value not in haystack, value
    assert all("input" not in err for err in response.json()["error"]["details"])


def test_confirm_body_is_additive_signature_fields_optional(client):
    http, fake = client
    assert http.post("/bookings/b1/payments/confirm", json={"order_ref": "o1"}, headers=H).status_code == 200
    assert http.post("/bookings/b1/payments/confirm", headers=H,
                     json={"order_ref": "o1", "payment_ref": "p", "signature": "s"}).status_code == 200
    assert fake.calls[0] == ("confirm", "o1", None, None) and fake.calls[1] == ("confirm", "o1", "p", "s")
    assert http.post("/bookings/b1/payments/confirm", json={}, headers=H).status_code == 422


def test_refresh_route_contract(client):
    http, fake = client
    response = http.post("/bookings/b1/payments/refresh", json={"order_ref": "o1"}, headers=H)
    assert response.status_code == 200
    assert response.json()["payments"][0]["overcollected_amount"] == "0.00"
    assert fake.calls == [("refresh", "b1", "o1", "idem-key-0001")]
    assert http.post("/bookings/b1/payments/refresh", json={"order_ref": "o1", "x": 1}, headers=H).status_code == 422


def test_new_routes_are_in_openapi_and_dormant_by_default():
    paths = real_app.openapi()["paths"]
    assert "/v1/bookings/{booking_id}/payments/refresh" in paths
    body = TestClient(real_app).get("/v1/payments/config").json()
    assert body["enabled"] is False
    assert "/v1/webhooks/{provider}" not in paths  # no payment or subscription provider configured


# -------------------------------------------------------------------------- migration 0029
def load(name):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(module, fn):
    statements = []
    with patch.object(module.op, "execute", side_effect=lambda s: statements.append(str(s))):
        getattr(module, fn)()
    return "\n".join(statements).lower()


def test_0029_shape_chain_and_idempotent_statements():
    m = load("0029_payment_monetary_policy")
    assert m.revision == "0029_payment_monetary_policy" and m.down_revision == "0028_account_erasure_hardening"
    sql = run(m, "upgrade")
    for fragment in (
        "commission_rate_percent numeric(7,4)", "commission_base text", "platform_commission_amount numeric(10,2)",
        "commission_policy_version text", "provider_fee_amount numeric(10,2)", "provider_tax_amount numeric(10,2)",
        "overcollected_amount numeric(10,2) not null default 0", "applies_to_excess boolean",
        "commission_reversal_amount numeric(10,2)", "create table if not exists public.payment_anomalies",
        "create table if not exists public.payment_provider_account_audit", "registration_generation integer",
        "booking_payment_commission_snapshot_is_immutable", "commission_reversal_exceeds_snapshot",
        "booking_payment_overcollection_is_immutable",
    ):
        assert fragment in sql, fragment
    for table in ("payment_anomalies", "payment_provider_account_audit"):
        assert f"alter table public.{table} enable row level security" in sql
        assert f"revoke all on public.{table} from public, anon, authenticated" in sql
    assert "float" not in sql and "double precision" not in sql  # money is numeric
    for statement in re.findall(r"(?m)^\s*(?:alter table|create table|create index)[^\n]*", sql):
        if "add column" in statement or statement.strip().startswith(("create table", "create index")):
            assert "if not exists" in statement, statement


def test_0029_downgrade_restores_legacy_functions_and_drops_additions():
    sql = run(load("0029_payment_monetary_policy"), "downgrade")
    assert "drop table if exists public.payment_anomalies" in sql
    assert "drop column if exists overcollected_amount" in sql
    assert "p.amount - p.overcollected_amount" not in sql  # the legacy recompute is back
    assert "booking_payment_commission_snapshot_is_immutable" not in sql


def test_a_case_expression_never_sits_inside_a_plpgsql_if_condition():
    # plpgsql ends an IF condition at the first THEN, which a CASE would contain (found in 0029).
    sql = (VERSIONS / "0029_payment_monetary_policy.py").read_text(encoding="utf-8")
    assert not re.search(r"\bif\b[^;]*\bcase\b[^;]*\bthen\b[^;]*\bend\b[^;]*\bthen\b", sql, re.DOTALL | re.IGNORECASE)
