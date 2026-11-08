"""Versioned checkout remains isolated from legacy money and provider activation."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.checkout import BookingCheckoutUseCases
from app.core.config import Settings
from app.core.exceptions import PaymentProviderNotConfiguredError
from app.domain.services.booking_finance_policy import POLICY_VERSION
from app.domain.services.checkout import checkout_quote
from tests.unit.test_payment_stage1_flows import CUSTOMER, KEY, build


def test_u08_checkout_has_no_customer_surcharge_and_reports_its_version():
    quote = checkout_quote(Decimal('250'), 'PAY_ONLINE', policy_version=POLICY_VERSION)
    assert quote['total_payable'] == quote['service_amount'] == Decimal('250')
    assert quote['online_processing_charge'] == quote['online_processing_charge_percent'] == 0
    assert quote['charge_label'] is None
    assert quote['checkout_policy_version'] == POLICY_VERSION
    assert checkout_quote(Decimal('250'), 'PAY_ONLINE')['total_payable'] == Decimal('255.90')


def test_policy_selection_is_explicit_and_rejects_unknown_versions():
    assert Settings(_env_file=None).booking_checkout_policy_version == 'customer_processing_v1'
    with pytest.raises(ValueError):
        Settings(_env_file=None, booking_checkout_policy_version='unknown')
    with pytest.raises(ValueError):
        checkout_quote(Decimal('250'), 'PAY_ONLINE', policy_version='unknown')


async def test_u08_quote_does_not_advertise_online_collection_before_held_funds_workflow():
    from datetime import UTC, datetime

    repo = SimpleNamespace(
        checkout_salon=AsyncMock(return_value={'timezone': 'UTC', 'accepting_bookings': True}),
        quote_services=AsyncMock(return_value={'duration': 30, 'amount': Decimal('250')}),
        quoted_slot_available=AsyncMock(return_value=True),
    )
    result = await BookingCheckoutUseCases(
        repo, SimpleNamespace(enabled=True), policy_version=POLICY_VERSION,
    ).quote(CUSTOMER, {'salon_id': 's', 'staff_id': 'b', 'service_ids': ['x'],
                       'start_datetime': datetime.now(UTC), 'payment_mode': 'PAY_ONLINE'})
    assert result['total_payable'] == Decimal('250')
    assert result['payment_options'] == ['PAY_AT_SALON']
    assert result['online_payment_available'] is False


async def test_adding_provider_credentials_cannot_activate_u08_online_money():
    ledger, gateway, uc, *_ = build(booking_checkout_policy_version=POLICY_VERSION)
    ledger.booking['checkout_policy_version'] = POLICY_VERSION
    with pytest.raises(PaymentProviderNotConfiguredError):
        await uc.create_intent(CUSTOMER, 'b1', KEY, None)
    assert not ledger.payments
    assert not gateway.requests
    assert uc.config()['enabled'] is False


async def test_new_booking_policy_selection_does_not_reprice_legacy_payment():
    ledger, gateway, uc, *_ = build(booking_checkout_policy_version=POLICY_VERSION)
    ledger.booking['checkout_policy_version'] = 'customer_processing_v1'
    original = ledger.insert_intent
    async def insert_with_legacy_charge(**values):
        charge = values.pop('online_processing_charge', Decimal('0'))
        payment_id = await original(**values)
        ledger.payments[payment_id]['online_processing_charge'] = charge
        return payment_id
    ledger.insert_intent = insert_with_legacy_charge
    result = await uc.create_intent(CUSTOMER, 'b1', KEY, None)
    assert result['amount'] == '1023.60'
    assert len(gateway.requests) == 1
    payment = ledger.payments[result['payment_id']]
    assert payment['platform_commission_amount'] == Decimal('102.36')
