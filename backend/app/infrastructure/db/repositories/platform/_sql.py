"""Shared SQL helpers."""

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppError,
    BookingChangeError,
    BookingWindowExceededError,
    BreakConflictError,
    NotFoundError,
    PayAtSalonBlockedError,
    PayAtSalonDailyLimitError,
    PaymentOvercollectionError,
    SalonClosedError,
    SalonNotAcceptingBookingsError,
    SlotUnavailableError,
    ValidationError,
)

# SQLSTATEs the booking SQL deliberately raises to reject a request: P0001 from
# `raise exception '...'` in create_booking, 23514 from the guard_booking_checkout trigger
# (migrations/sql/0035_booking_checkout_safety.sql).
# Safety ceiling for list endpoints whose clients send no ``limit`` and expect every row.
LIST_SAFETY_CEILING = 1000


def page_bounds(limit: int | None, offset: int) -> dict[str, int]:
    """Bind values for ``limit :limit offset :offset``: default and clamp ``limit`` to the ceiling."""

    capped = LIST_SAFETY_CEILING if limit is None else min(limit, LIST_SAFETY_CEILING)
    return {"limit": capped, "offset": max(offset, 0)}


_BUSINESS_ERROR_SQLSTATES = frozenset({"P0001", "23514"})


def _is_business_error(exc: BaseException) -> bool:
    """True when the database rejected the request on purpose, not because it failed."""

    return isinstance(exc, DBAPIError) and getattr(exc.orig, "sqlstate", None) in _BUSINESS_ERROR_SQLSTATES


# (markers, match case-insensitively, error factory). The first rule whose marker appears in
# the Postgres message wins, so order matters.
_MessageRule = tuple[tuple[str, ...], bool, Callable[[], AppError]]

_CREATE_BOOKING_ERROR_RULES: tuple[_MessageRule, ...] = (
    (("invalid_service_selection", "invalid_visit_services", "invalid_visit_staff"), False,
     lambda: ValidationError("Choose compatible services and professionals")),
    (("booking_window_exceeded",), False,
     lambda: BookingWindowExceededError("Bookings are available only through the next 30 days.")),
    (("pay_at_salon_daily_limit",), False,
     lambda: PayAtSalonDailyLimitError("You have reached the Pay at Salon limit for this date.")),
    (("pay_at_salon_upcoming_limit",), False,
     lambda: BookingChangeError("pay_at_salon_upcoming_limit", "You have reached your upcoming Pay at Salon booking limit.")),
    (("pay_at_salon_weekly_limit",), False,
     lambda: BookingChangeError("pay_at_salon_weekly_limit", "You have reached your rolling 7-day Pay at Salon reservation limit. Customer cancellations still count.")),
    (("customer_booking_overlap",), False,
     lambda: BookingChangeError("customer_booking_overlap", "You already have an appointment at this time. Choose a non-overlapping time.")),
    (("pay_at_salon_temporarily_blocked",), False,
     lambda: PayAtSalonBlockedError("Pay at Salon is blocked for 7 days after two no-shows. Online payment remains available where enabled.")),
    (("salon_not_accepting_bookings",), False,
     lambda: SalonNotAcceptingBookingsError("This salon is not accepting bookings right now")),
    (("not offered by this staff",), True,
     lambda: ValidationError("Selected staff member does not offer this service")),
    (("break_conflict",), False,
     lambda: BreakConflictError()),
    (("Salon is closed on this date",), False,
     lambda: SalonClosedError("This salon is closed on the selected date")),
    (("No valid services selected",), False,
     lambda: ValidationError("Selected services are no longer available")),
    (("Salon not found or inactive",), False,
     lambda: NotFoundError("Salon not found")),
    (("slot", "available"), True,
     lambda: SlotUnavailableError("Selected slot is no longer available")),
)

_RECORD_PAYMENT_ERROR_RULES: tuple[_MessageRule, ...] = (
    (("payment_overcollection",), False,
     lambda: PaymentOvercollectionError("This payment would collect more than the booking total")),
)


def _error_for_message(message: str, rules: tuple[_MessageRule, ...]) -> AppError | None:
    """Return the domain error whose marker appears in a Postgres message, else ``None``."""

    lowered = message.lower()
    for markers, ignore_case, build in rules:
        haystack = lowered if ignore_case else message
        if any(marker in haystack for marker in markers):
            return build()
    return None


def _booking_actor_sql(booking_alias: str) -> str:
    """SQL predicate: ``:actor_id`` owns the booking's salon or is its assigned active staff.

    ``booking_alias`` is the alias (or table name) of the ``bookings`` row in the outer query.
    """

    return f"""(
        exists (select 1 from salons s where s.id = {booking_alias}.salon_id and s.owner_id = :actor_id)
        or exists (select 1 from staff st where (st.id = {booking_alias}.staff_id or exists(select 1 from jsonb_array_elements(coalesce(to_jsonb({booking_alias})->'itinerary','[]'::jsonb)) segment where (segment->>'staff_id')::uuid=st.id)) and st.profile_id = :actor_id and st.is_active)
      )"""


def _salon_actor_sql(booking_alias: str, salon_alias: str = "s") -> str:
    """SQL predicate: ``:actor_id`` owns the salon or is any active staff member of it.

    ``salon_alias`` must be the alias of the joined ``salons`` row; ``booking_alias`` the
    ``bookings`` row whose ``salon_id`` is checked for staff access.
    """

    return f"""(
        {salon_alias}.owner_id = :actor_id
        or exists (
          select 1 from staff access_staff
          where access_staff.salon_id = {booking_alias}.salon_id
            and access_staff.profile_id = :actor_id
            and access_staff.is_active
        )
      )"""


def _contains_pattern(value: str | None) -> str | None:
    """Build a literal "contains" ILIKE pattern (escape char ``!``); blank input means no filter."""

    text_value = (value or "").strip()
    if not text_value:
        return None
    escaped = text_value.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escaped}%"


def _canonical_json_value(value: Any) -> str:
    """Serialize non-JSON values; aware datetimes become UTC so one instant has one spelling."""

    if isinstance(value, datetime) and value.utcoffset() is not None:
        return value.astimezone(UTC).isoformat()
    return str(value)


def _request_fingerprint(values: dict[str, Any]) -> str:
    """SHA-256 of a booking request, equal for the same instant sent with different UTC offsets."""

    payload = json.dumps(values, sort_keys=True, default=_canonical_json_value)
    return hashlib.sha256(payload.encode()).hexdigest()


class SqlHelpersMixin:
    """Shared SQL helpers."""

    session: AsyncSession

    def _prepare_jsonb_values(self, values: dict[str, Any]) -> dict[str, Any]:
        """Serialize JSONB fields for raw SQL text statements."""

        prepared = dict(values)
        if "working_hours" in prepared and prepared["working_hours"] is not None:
            prepared["working_hours"] = json.dumps(prepared["working_hours"])
        return prepared

    def _sql_value_placeholder(self, key: str) -> str:
        """Return the SQL placeholder for a writable column."""

        if key == "working_hours":
            return f"cast(:{key} as jsonb)"
        return f":{key}"

    def _sql_assignment(self, key: str) -> str:
        """Return a safe assignment fragment for a writable column."""

        return f"{key} = {self._sql_value_placeholder(key)}"

    def _profile_response(self, row: Any) -> dict[str, Any]:
        """Normalize profile rows for Pydantic response schemas."""

        profile = dict(row)
        profile["id"] = str(profile["id"])
        return profile
