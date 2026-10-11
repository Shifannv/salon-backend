"""Booking action-request and closure workflow routes."""

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.booking_actions import (
    BookingActionCreateRequest,
    BookingActionRequestResponse,
    BookingActionRespondRequest,
    ClosureApplyRequest,
    ClosureApplyResponse,
    ClosurePreviewRequest,
    ClosurePreviewResponse,
)
from app.application.use_cases.booking_actions import (
    BookingActionRequestUseCases,
    ClosureUseCases,
)
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

router = APIRouter()


def _action_use_cases(session: AsyncSession) -> BookingActionRequestUseCases:
    return BookingActionRequestUseCases(PlatformRepository(session))


def _closure_use_cases(session: AsyncSession) -> ClosureUseCases:
    return ClosureUseCases(PlatformRepository(session))


@router.post(
    "/bookings/{booking_id}/payment-confirmation-requests",
    response_model=BookingActionRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Claim a Pay at Salon payment",
)
async def create_payment_confirmation_request(
    booking_id: str,
    background_tasks: BackgroundTasks,
    payload: BookingActionCreateRequest = BookingActionCreateRequest(),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingActionRequestResponse:
    """Keep the booking unpaid while asking the salon to verify payment."""

    row = await _action_use_cases(session).create_customer_request(
        actor,
        booking_id,
        "payment_confirmation",
        payload.reason,
        background_tasks,
        payment_method=payload.payment_method,
    )
    return BookingActionRequestResponse(**row)


@router.post(
    "/bookings/{booking_id}/cancellation-requests",
    response_model=BookingActionRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request cancellation after the immediate cutoff",
)
async def create_cancellation_request(
    booking_id: str,
    background_tasks: BackgroundTasks,
    payload: BookingActionCreateRequest = BookingActionCreateRequest(),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingActionRequestResponse:
    """Create a pending request without releasing the booking slot."""

    row = await _action_use_cases(session).create_customer_request(
        actor,
        booking_id,
        "cancellation",
        payload.reason,
        background_tasks,
    )
    return BookingActionRequestResponse(**row)


@router.get(
    "/booking-action-requests",
    response_model=list[BookingActionRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List salon booking action requests",
)
async def list_booking_action_requests(
    request_status: Literal["pending", "resolved"] | None = Query(
        default=None, alias="status"
    ),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[BookingActionRequestResponse]:
    """Return only requests belonging to the actor's salon workspace."""

    rows = await _action_use_cases(session).list_requests(actor, request_status)
    return [BookingActionRequestResponse(**row) for row in rows]


@router.post(
    "/booking-action-requests/{request_id}/respond",
    response_model=BookingActionRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve a booking action request",
)
async def respond_booking_action_request(
    request_id: str,
    payload: BookingActionRespondRequest,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingActionRequestResponse:
    """Apply an owner/staff decision with row-lock and duplicate protection."""

    row = await _action_use_cases(session).respond(
        actor,
        request_id,
        payload.decision,
        payload.reason,
        background_tasks,
    )
    return BookingActionRequestResponse(**row)


@router.post(
    "/salons/me/closures/preview",
    response_model=ClosurePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview bookings affected by a salon closure",
)
async def preview_closure(
    payload: ClosurePreviewRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ClosurePreviewResponse:
    """Return the exact active bookings overlapped by a holiday or leave."""

    row = await _closure_use_cases(session).preview(actor, payload.model_dump())
    return ClosurePreviewResponse(**row)


@router.post(
    "/salons/me/closures",
    response_model=ClosureApplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply a confirmed salon closure",
)
async def apply_closure(
    payload: ClosureApplyRequest,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ClosureApplyResponse:
    """Block the interval and cancel/notify exactly the confirmed impact set."""

    row = await _closure_use_cases(session).apply(
        actor, payload.model_dump(), background_tasks
    )
    return ClosureApplyResponse(**row)
