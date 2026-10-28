"""WhatsApp/SMS messaging logic: templates, quota, gating, idempotency. No provider, no network."""

from datetime import UTC, datetime

import pytest

from app.application.ports.messaging_gateway import OutboundMessage, SendOutcome
from app.application.use_cases.completion_message import CompletionMessageService
from app.domain.services.message_templates import UnsafeMessageError, render
from app.domain.services.messaging_quota import (
    DEFAULT_MONTHLY_CAP,
    has_quota,
    month_window,
    remaining,
)
from app.infrastructure.messaging.fake_gateway import FakeMessagingGateway
from app.infrastructure.messaging.none_gateway import NoneMessagingGateway
from tests.support_messaging import InMemoryUsageStore

NOW = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)


class TestTemplates:
    def test_completion_message_has_only_what_the_customer_needs(self):
        text = render("service_completed", first_name="Arun", service="Buzz cut", salon="Elite Cuts")
        assert text == "Hi Arun, your Buzz cut at Elite Cuts is complete. Thank you for visiting!"

    def test_owner_alerts_carry_the_reply_code_and_nothing_private(self):
        waiting = render("booking_waiting", salon="Elite Cuts", service="Buzz cut", time="10:30 AM", code="K7M2QX")
        assert "Reply A K7M2QX to accept or D K7M2QX to decline." in waiting
        done = render("completion_request", service="Buzz cut", time="10:30 AM", code="K7M2QX")
        assert "Reply C K7M2QX after service is complete." in done

    @pytest.mark.parametrize(
        "bad",
        [
            "Call 9876543210", "mail me a@b.com", "see https://x.example", "pay ₹500",
            "ref 123456789", "pay Rs. 500", "pay Rs500", "via UPI", "INR total",
        ],
    )
    def test_a_phone_number_link_email_amount_or_reference_never_gets_through(self, bad):
        with pytest.raises(UnsafeMessageError):
            render("service_completed", first_name="Arun", service=bad, salon="Elite Cuts")

    def test_unknown_template_or_missing_parameter_is_refused(self):
        with pytest.raises(UnsafeMessageError):
            render("secret_template", first_name="Arun")
        with pytest.raises(UnsafeMessageError):
            render("service_completed", first_name="Arun", service="Buzz cut")

    def test_reply_code_must_be_a_short_unambiguous_code(self):
        with pytest.raises(UnsafeMessageError):
            render("completion_request", service="Buzz cut", time="10:30 AM", code="1234567890")


class TestQuota:
    def test_default_cap_is_three_hundred(self):
        assert DEFAULT_MONTHLY_CAP == 300

    def test_remaining_and_exhaustion(self):
        assert remaining(120, 300) == 180
        assert remaining(300, 300) == 0
        assert remaining(305, 300) == 0
        assert has_quota(299, 300) is True
        assert has_quota(300, 300) is False

    def test_window_is_the_salons_local_calendar_month(self):
        # 31 Oct 20:00 UTC is already 1 Nov 01:30 in India, so it belongs to November.
        window = month_window(datetime(2026, 10, 31, 20, 0, tzinfo=UTC), "Asia/Kolkata")
        assert window.reset_date.isoformat() == "2026-12-01"
        assert window.start == datetime(2026, 10, 31, 18, 30, tzinfo=UTC)
        assert window.end == datetime(2026, 11, 30, 18, 30, tzinfo=UTC)

    def test_december_rolls_into_the_next_year(self):
        window = month_window(datetime(2026, 12, 15, 5, 0, tzinfo=UTC), "Asia/Kolkata")
        assert window.reset_date.isoformat() == "2027-01-01"


def service(*, enabled=True, gateway=None, usage=None, cap=300):
    gateway = gateway or FakeMessagingGateway()
    usage = usage or InMemoryUsageStore()
    return CompletionMessageService(gateway, usage, enabled=enabled, monthly_cap=cap), gateway, usage


def call(svc, **overrides):
    values = {
        "salon_id": "salon-1", "salon_name": "Elite Cuts", "timezone": "Asia/Kolkata",
        "booking_id": "booking-1", "customer_name": "Arun Kumar", "customer_phone": "+919876543210",
        "service_name": "Buzz cut", "entitled": True, "now": NOW,
    }
    values.update(overrides)
    return svc.notify_completed(**values)


class TestCompletionMessage:
    async def test_sends_once_and_uses_one_quota_unit(self):
        svc, gateway, usage = service()
        decision = await call(svc)
        assert decision.sent is True
        assert gateway.sent[0].channel == "whatsapp"
        assert gateway.sent[0].recipient == "+919876543210"
        assert gateway.sent[0].text.startswith("Hi Arun, your Buzz cut")
        assert usage.used("salon-1") == 1

    async def test_everything_is_off_by_default(self):
        svc, gateway, _ = service(enabled=False)
        decision = await call(svc)
        assert (decision.sent, decision.reason) == (False, "disabled")
        assert gateway.sent == []

    async def test_a_second_complete_for_the_same_booking_sends_nothing(self):
        svc, gateway, usage = service()
        await call(svc)
        again = await call(svc)
        assert (again.sent, again.reason) == (False, "duplicate")
        assert len(gateway.sent) == 1
        assert usage.used("salon-1") == 1

    @pytest.mark.parametrize(
        ("overrides", "reason"),
        [
            ({"entitled": False}, "not_entitled"),
            ({"customer_phone": None}, "no_phone"),
            ({"customer_phone": "12345"}, "invalid_phone"),
            ({"service_name": "Call 9876543210"}, "unsafe_content"),
        ],
    )
    async def test_skips_without_sending_or_counting(self, overrides, reason):
        svc, gateway, usage = service()
        decision = await call(svc, **overrides)
        assert (decision.sent, decision.reason) == (False, reason)
        assert gateway.sent == []
        assert usage.used("salon-1") == 0

    async def test_a_ten_digit_indian_number_is_sent_in_international_form(self):
        svc, gateway, _ = service()
        await call(svc, customer_phone="98765 43210")
        assert gateway.sent[0].recipient == "+919876543210"

    async def test_stops_at_the_monthly_cap_and_does_not_call_the_provider(self):
        usage = InMemoryUsageStore(preset={"salon-1": 300})
        svc, gateway, _ = service(usage=usage)
        decision = await call(svc)
        assert (decision.sent, decision.reason) == (False, "quota_exhausted")
        assert gateway.sent == []

    async def test_a_new_month_starts_with_a_fresh_quota(self):
        usage = InMemoryUsageStore(preset={"salon-1": 300})
        svc, _gateway, _ = service(usage=usage)
        october = await call(svc)
        assert (october.sent, october.reason) == (False, "quota_exhausted")
        november = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
        decision = await call(svc, now=november, booking_id="booking-2")
        assert decision.sent is True

    async def test_a_salon_name_that_merely_contains_a_blocked_word_is_fine(self):
        svc, gateway, _ = service()
        decision = await call(svc, salon_name="Jupiter Salon", service_name="Beard trim")
        assert decision.sent is True
        assert "Jupiter Salon" in gateway.sent[0].text

    async def test_a_provider_refusal_is_not_counted_and_is_not_retried(self):
        gateway = FakeMessagingGateway(outcome=SendOutcome(accepted=False, reason="provider_rejected"))
        svc, gateway, usage = service(gateway=gateway)
        first = await call(svc)
        second = await call(svc)
        assert (first.sent, first.reason) == (False, "provider_rejected")
        assert (second.sent, second.reason) == (False, "duplicate")
        assert usage.used("salon-1") == 0
        assert len(gateway.attempts) == 1

    async def test_a_provider_crash_never_breaks_completing_a_booking(self):
        gateway = FakeMessagingGateway(raises=RuntimeError("network down"))
        svc, _, usage = service(gateway=gateway)
        decision = await call(svc)
        assert (decision.sent, decision.reason) == (False, "provider_error")
        assert usage.used("salon-1") == 0

    async def test_the_default_gateway_sends_nothing(self):
        svc, _, usage = service(gateway=NoneMessagingGateway())
        decision = await call(svc)
        assert (decision.sent, decision.reason) == (False, "provider_disabled")
        assert usage.used("salon-1") == 0


class TestFakeGateway:
    async def test_is_idempotent_on_the_key(self):
        gateway = FakeMessagingGateway()
        message = OutboundMessage(channel="sms", recipient="+919876543210", text="hello", idempotency_key="k1")
        first = await gateway.send(message)
        second = await gateway.send(message)
        assert first.accepted and second.accepted
        assert first.provider_message_id == second.provider_message_id
        assert len(gateway.sent) == 1
