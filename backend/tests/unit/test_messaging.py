"""SMS alert logic: templates, quota math, gateways. No provider, no network."""

from datetime import UTC, datetime

import pytest

from app.application.ports.messaging_gateway import OutboundMessage
from app.domain.services.message_templates import UnsafeMessageError, render
from app.domain.services.messaging_quota import (
    DEFAULT_MONTHLY_CAP,
    has_quota,
    month_window,
    remaining,
)
from app.infrastructure.messaging.fake_gateway import FakeMessagingGateway

NOW = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)


class TestTemplates:
    def test_a_cancellation_alert_has_only_what_the_owner_needs(self):
        text = render("booking_cancelled", salon="Elite Cuts", service="Buzz cut", time="10:30 AM")
        assert text == "A booking at Elite Cuts for Buzz cut at 10:30 AM was cancelled."

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
            render("booking_cancelled", salon="Elite Cuts", service=bad, time="10:30 AM")

    def test_unknown_template_or_missing_parameter_is_refused(self):
        with pytest.raises(UnsafeMessageError):
            render("secret_template", first_name="Arun")
        with pytest.raises(UnsafeMessageError):
            render("booking_cancelled", salon="Elite Cuts", service="Buzz cut")

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


class TestFakeGateway:
    async def test_is_idempotent_on_the_key(self):
        gateway = FakeMessagingGateway()
        message = OutboundMessage(channel="sms", recipient="+919876543210", text="hello", idempotency_key="k1")
        first = await gateway.send(message)
        second = await gateway.send(message)
        assert first.accepted and second.accepted
        assert first.provider_message_id == second.provider_message_id
        assert len(gateway.sent) == 1
