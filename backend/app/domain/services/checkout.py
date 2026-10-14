"""Customer checkout policy. Money stays Decimal throughout."""

from decimal import ROUND_HALF_UP, Decimal

PROCESSING_PERCENT = Decimal("5")
PAY_AT_SALON_INSTRUCTIONS = [
    "No payment now. Please visit salon at booked slot time.",
    "After service is completed, pay total amount directly to barber by cash or UPI.",
    "To avoid fake bookings, you can keep only 1 active Pay at Salon booking per day.",
]


def checkout_quote(service_amount: Decimal, mode: str) -> dict:
    if not isinstance(service_amount, Decimal) or not service_amount.is_finite() or service_amount < 0:
        raise ValueError("Service amount must be a non-negative Decimal")
    if mode not in {"PAY_ONLINE", "PAY_AT_SALON"}:
        raise ValueError("Unsupported payment mode")
    service = service_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    charge = ((service * PROCESSING_PERCENT / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) if mode == "PAY_ONLINE" else Decimal("0.00"))
    return {
        "payment_mode": mode,
        "service_amount": service,
        "online_processing_charge_percent": PROCESSING_PERCENT if mode == "PAY_ONLINE" else Decimal(0),
        "online_processing_charge": charge,
        "total_payable": service + charge,
        "charge_label": "Online payment processing charge" if mode == "PAY_ONLINE" else None,
        "instructions": PAY_AT_SALON_INSTRUCTIONS if mode == "PAY_AT_SALON" else [],
    }
