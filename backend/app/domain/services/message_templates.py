"""Approved message templates for WhatsApp/SMS, and the guard that keeps private data out of them.

A message carries no customer phone number, address, bank detail, internal split, payment
reference, link or secret. Every rendered text is checked, so a careless caller (or an odd
service name typed by an owner) cannot leak one.
"""

import re

_TEMPLATES: dict[str, tuple[str, tuple[str, ...]]] = {
    "service_completed": (
        "Hi {first_name}, your {service} at {salon} is complete. Thank you for visiting!",
        ("first_name", "service", "salon"),
    ),
    "booking_waiting": (
        "New booking at {salon}: {service} at {time}. Reply A {code} to accept or D {code} to decline.",
        ("salon", "service", "time", "code"),
    ),
    "booking_cancelled": (
        "A booking at {salon} for {service} at {time} was cancelled.",
        ("salon", "service", "time"),
    ),
    "completion_request": (
        "Is the {service} at {time} done? Reply C {code} after service is complete.",
        ("service", "time", "code"),
    ),
}

_CODE = re.compile(r"[A-HJ-NP-Z2-9]{4,8}")  # no 0/O/1/I so a typed reply is unambiguous
_TIME = re.compile(r"[0-9]{1,2}:[0-9]{2} ?[AaPp][Mm]")
_DIGIT_RUN = re.compile(r"\d(?:[\s-]?\d){6,}")  # 7+ digits: a phone number or a reference
# Links, e-mail, and anything that reads as an amount or a payment instrument.
_FORBIDDEN = re.compile(r"@|https?:|://|\bwww\.|₹|\brs\.?\s*\d|\binr\b|\bupi\b", re.IGNORECASE)
_MAX_PARAM = 60


class UnsafeMessageError(ValueError):
    """The template, a parameter, or the final text is not allowed to be sent."""


def _check_text(text: str) -> None:
    if _DIGIT_RUN.search(text) or _FORBIDDEN.search(text):
        raise UnsafeMessageError("message would expose private or payment data")


def render(template: str, **params: str) -> str:
    entry = _TEMPLATES.get(template)
    if entry is None:
        raise UnsafeMessageError(f"unknown template {template!r}")
    body, required = entry
    if set(params) != set(required):
        raise UnsafeMessageError(f"template {template!r} needs exactly {', '.join(required)}")
    for name, value in params.items():
        if not isinstance(value, str) or not value.strip() or len(value) > _MAX_PARAM:
            raise UnsafeMessageError(f"parameter {name!r} is empty or too long")
        _check_text(value)
    if "code" in params and not _CODE.fullmatch(params["code"]):
        raise UnsafeMessageError("reply code must be 4-8 unambiguous characters")
    if "time" in params and not _TIME.fullmatch(params["time"]):
        raise UnsafeMessageError("time must look like 10:30 AM")
    text = body.format(**{name: value.strip() for name, value in params.items()})
    _check_text(text)
    return text
