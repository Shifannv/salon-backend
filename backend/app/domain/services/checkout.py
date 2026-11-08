"""Customer checkout policy. Money stays Decimal throughout."""

from decimal import ROUND_HALF_UP, Decimal

from app.domain.services.booking_finance_policy import POLICY_VERSION

CHARGE_LABEL = "Payment gateway charge (incl. GST)"
PAY_AT_SALON_INSTRUCTIONS = [
    "No payment now. Please visit salon at booked slot time.",
    "After service is completed, pay total amount directly to barber by cash or UPI.",
    "To avoid fake bookings, you can keep only 1 active Pay at Salon booking per day.",
]


def online_checkout_available(provider_enabled: bool, policy_version: str) -> bool:
    """U08 needs its own held-funds implementation before advertising collection."""
    return bool(provider_enabled and policy_version == "customer_processing_v1")


def checkout_quote(
    service_amount: Decimal,
    mode: str,
    *,
    policy_version: str = "customer_processing_v1",
    charge_percent: Decimal | None = None,
) -> dict:
    if policy_version not in {"customer_processing_v1", POLICY_VERSION}:
        raise ValueError("Unsupported checkout policy")
    if not isinstance(service_amount, Decimal) or not service_amount.is_finite() or service_amount < 0:
        raise ValueError("Service amount must be a non-negative Decimal")
    if mode not in {"PAY_ONLINE", "PAY_AT_SALON"}:
        raise ValueError("Unsupported payment mode")
    service = service_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if charge_percent is None:
        from app.core.config import settings

        charge_percent = settings.online_charge_percent
    percentage = charge_percent if policy_version == "customer_processing_v1" and mode == "PAY_ONLINE" else Decimal(0)
    charge = ((service * percentage / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) if mode == "PAY_ONLINE" else Decimal("0.00"))
    return {
        "payment_mode": mode,
        "service_amount": service,
        "checkout_policy_version": policy_version,
        "online_processing_charge_percent": percentage,
        "online_processing_charge": charge,
        "total_payable": service + charge,
        "charge_label": CHARGE_LABEL if percentage else None,
        "instructions": PAY_AT_SALON_INSTRUCTIONS if mode == "PAY_AT_SALON" else [],
    }
