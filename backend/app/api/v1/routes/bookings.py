"""Booking and availability API routes."""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_authenticated_session,
    get_cache,
    get_current_actor,
    get_mfa_checked_actor,
)
from app.api.v1.schemas.booking import VisitAvailabilityRequest, VisitAvailabilityResponse
from app.api.v1.schemas.booking_changes import (
    BookingChangeCommitRequest,
    BookingChangeQuote,
    BookingChangeRequest,
)
from app.api.v1.schemas.platform import (
    AvailabilityResponse,
    BarberCancelBookingRequest,
    BookingCreateRequest,
    BookingResponse,
    CancelBookingRequest,
    DelayBookingRequest,
    NoShowBookingRequest,
    PaymentRequest,
    RejectBookingRequest,
)
from app.application.ports.cache_gateway import CacheGateway
from app.application.use_cases.booking_changes import BookingChangeUseCases
from app.application.use_cases.platform import BookingUseCases
from app.core.config import settings
from app.domain.entities.profile import Profile
from app.domain.services.checkout import online_checkout_available
from app.infrastructure.db.repositories.booking_changes import BookingChangeRepository
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import get_session
from app.infrastructure.payments.resolver import get_payment_resolver

router = APIRouter()


@router.post("/availability/visit", response_model=list[VisitAvailabilityResponse], status_code=200)
async def visit_availability(payload: VisitAvailabilityRequest, session: AsyncSession = Depends(get_session)) -> list[VisitAvailabilityResponse]:
    rows = await _use_cases(session).visit_availability(
        payload.salon_id, payload.date, [segment.model_dump() for segment in payload.segments])
    return [VisitAvailabilityResponse(**row) for row in rows]



@router.get("/bookings/{booking_id}/change-availability", response_model=list[AvailabilityResponse], status_code=200)
async def booking_change_availability(
    booking_id: UUID, staff_id: UUID, booking_date: date = Query(alias="date"),
    service_ids: list[UUID] = Query(min_length=1, max_length=30),
    actor: Profile = Depends(get_current_actor), session: AsyncSession = Depends(get_authenticated_session),
) -> list[AvailabilityResponse]:
    rows = await BookingChangeUseCases(BookingChangeRepository(session)).availability(
        actor, str(booking_id), str(staff_id), [str(s) for s in service_ids], booking_date,
    )
    return [AvailabilityResponse(**row) for row in rows]


@router.post("/bookings/{booking_id}/change-quote", response_model=BookingChangeQuote, status_code=200)
async def quote_booking_change(
    booking_id: UUID, payload: BookingChangeRequest, actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingChangeQuote:
    row = await BookingChangeUseCases(BookingChangeRepository(session)).quote(actor, str(booking_id), payload.model_dump())
    return BookingChangeQuote(**row)


@router.post("/bookings/{booking_id}/change", response_model=BookingResponse, status_code=200)
async def change_booking(
    booking_id: UUID, payload: BookingChangeCommitRequest, actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> BookingResponse:
    row = await BookingChangeUseCases(BookingChangeRepository(session)).commit(actor, str(booking_id), payload.model_dump(), key)
    return BookingResponse(**row)


@router.post("/bookings/{booking_id}/check-in", response_model=BookingResponse, status_code=status.HTTP_200_OK)
async def check_in(booking_id: UUID, actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    key: str | None = Header(default=None, alias="Idempotency-Key")) -> BookingResponse:
    return BookingResponse(**await _use_cases(session).mark_attendance(actor, str(booking_id), no_show=False, idempotency_key=key))


@router.post("/bookings/{booking_id}/no-show", response_model=BookingResponse, status_code=status.HTTP_200_OK)
async def no_show(booking_id: UUID, payload: NoShowBookingRequest, background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    key: str | None = Header(default=None, alias="Idempotency-Key")) -> BookingResponse:
    return BookingResponse(**await _use_cases(session).mark_attendance(
        actor, str(booking_id), no_show=True, idempotency_key=key,
        reason=payload.reason, background_tasks=background_tasks,
    ))


def _use_cases(session: AsyncSession) -> BookingUseCases:
    return BookingUseCases(PlatformRepository(session), online_payments_enabled=online_checkout_available(
        get_payment_resolver().enabled, settings.booking_checkout_policy_version,
    ))


@router.get(
    "/availability",
    response_model=list[AvailabilityResponse],
    status_code=status.HTTP_200_OK,
    summary="Get available booking slots",
    description=(
        "Delegates to the `get_available_slots` Postgres function. Returns slots only "
        "from the salon's local today through 30 days ahead. Never cached. Public — no auth required."
    ),
)
async def availability(
    staff_id: UUID,
    booking_date: date = Query(alias="date"),
    service_ids: list[UUID] = Query(min_length=1),
    session: AsyncSession = Depends(get_session),
) -> list[AvailabilityResponse]:
    """Return availability from the database slot function — public, no auth required."""

    rows = await _use_cases(session).availability(
        str(staff_id), booking_date, [str(s) for s in service_ids]
    )
    return [AvailabilityResponse(**row) for row in rows]


@router.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create booking",
    description=(
        "Delegates to the `create_booking` Postgres function. Customer bookings are "
        "limited to the salon's local today through 30 days ahead. Slot conflicts return 409."
    ),
)
async def create_booking(
    payload: BookingCreateRequest,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> BookingResponse:
    """Create a booking through the database booking function."""

    row = await _use_cases(session).create_booking(
        actor, {**payload.model_dump(), "_idempotency_key": idempotency_key}, background_tasks
    )

    return BookingResponse(**row)


@router.get(
    "/bookings",
    response_model=list[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="List role-scoped bookings",
    description=(
        "Owners see all bookings in their salon. "
        "Customers see only their own bookings."
    ),
)
async def list_bookings(
    booking_status: Literal["pending", "confirmed", "checked_in", "no_show", "rejected", "completed", "cancelled"]
    | None = Query(default=None, alias="status"),
    source: Literal["app", "manual_walkin", "qr_walkin"] | None = None,
    date_from: date | None = Query(default=None, description="Inclusive calendar date in each booking salon's timezone"),
    date_to: date | None = Query(default=None, description="Inclusive calendar date in each booking salon's timezone"),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: Profile = Depends(get_mfa_checked_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[BookingResponse]:
    """List bookings visible to the actor."""

    rows = await _use_cases(session).list_bookings(
        actor,
        booking_status=booking_status,
        source=source,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [BookingResponse(**row) for row in rows]


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get booking details",
)
async def get_booking(
    booking_id: UUID,
    actor: Profile = Depends(get_mfa_checked_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingResponse:
    """Return a booking visible to the actor."""

    row = await _use_cases(session).get_booking(actor, str(booking_id))
    return BookingResponse(**row)


@router.post(
    "/bookings/{booking_id}/approve",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve booking",
)
async def approve_booking(
    booking_id: UUID,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingResponse:
    """Approve a pending booking. Notifies the customer via push."""

    row = await _use_cases(session).approve(actor, str(booking_id), background_tasks)
    return BookingResponse(**row)


@router.post(
    "/bookings/{booking_id}/reject",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject booking",
)
async def reject_booking(
    booking_id: UUID,
    payload: RejectBookingRequest,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingResponse:
    """Reject a booking with a reason. Notifies the customer via push."""

    row = await _use_cases(session).reject(
        actor, str(booking_id), payload.rejection_reason, background_tasks
    )
    return BookingResponse(**row)


@router.post(
    "/bookings/{booking_id}/complete",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete booking",
)
async def complete_booking(
    booking_id: UUID,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> BookingResponse:
    """Complete a booking. Notifies the customer via push."""

    row = await _use_cases(session).complete(actor, str(booking_id), background_tasks, idempotency_key=idempotency_key)
    return BookingResponse(**row)


@router.post(
    "/bookings/{booking_id}/delay",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Record a booking delay",
)
async def delay_booking(
    booking_id: UUID,
    payload: DelayBookingRequest,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingResponse:
    """Update the completion estimate and optionally notify affected customers."""

    row = await _use_cases(session).delay(
        actor,
        str(booking_id),
        payload.estimated_end_datetime,
        payload.notify_affected_customers,
        background_tasks,
    )
    return BookingResponse(**row)


@router.post(
    "/bookings/{booking_id}/cancel",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel booking (customer)",
    description=(
        "Cancels a booking on behalf of the **customer**. "
        "Both `reason_code` and `reason_text` are optional — "
        "customers can cancel with a single tap and provide context later. "
        "To cancel as the **salon/barber**, use `POST /bookings/{id}/cancel/barber`."
    ),
)
async def cancel_booking(
    booking_id: UUID,
    background_tasks: BackgroundTasks,
    payload: CancelBookingRequest = CancelBookingRequest(),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingResponse:
    """Cancel a booking as the customer. No reason required."""

    row = await _use_cases(session).cancel(
        actor,
        str(booking_id),
        background_tasks,
        reason_code=payload.reason_code,
        reason_text=payload.reason_text,
    )
    return BookingResponse(**row)


@router.post(
    "/bookings/{booking_id}/cancel/barber",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel booking (barber/owner)",
    description=(
        "Cancels a booking on behalf of the **salon**. "
        "`reason_code` is **required** so the customer always receives "
        "a clear explanation. The combined reason is stored in "
        "`cancellation_reason` and included in the push notification "
        "sent to the customer."
    ),
)
async def barber_cancel_booking(
    booking_id: UUID,
    payload: BarberCancelBookingRequest,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingResponse:
    """Cancel a booking as the barber/owner — requires a reason."""

    row = await _use_cases(session).barber_cancel(
        actor,
        str(booking_id),
        background_tasks,
        reason_code=payload.reason_code,
        reason_text=payload.reason_text,
    )
    return BookingResponse(**row)


@router.post(
    "/bookings/{booking_id}/payment",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Record booking payment",
)
async def record_payment(
    booking_id: UUID,
    payload: PaymentRequest,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> BookingResponse:
    """Record booking payment."""

    row = await _use_cases(session).record_payment(
        actor, str(booking_id), payload.payment_method, background_tasks, idempotency_key=idempotency_key
    )
    return BookingResponse(**row)
