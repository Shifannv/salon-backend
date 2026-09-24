"""Notification and device API routes."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.platform import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    MarkAllNotificationsReadResponse,
    NotificationResponse,
)
from app.application.use_cases.platform import NotificationUseCases
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

router = APIRouter()


def _use_cases(session: AsyncSession) -> NotificationUseCases:
    return NotificationUseCases(PlatformRepository(session))


@router.get(
    "/notifications",
    response_model=list[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List notifications",
)
async def list_notifications(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[NotificationResponse]:
    """List notifications owned by the actor."""

    rows = await _use_cases(session).list_notifications(actor)
    return [NotificationResponse(**row) for row in rows]


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark notification read",
)
async def mark_notification_read(
    notification_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> NotificationResponse:
    """Mark one notification as read."""

    row = await _use_cases(session).mark_read(actor, notification_id)
    return NotificationResponse(**row)


@router.post(
    "/notifications/read-all",
    response_model=MarkAllNotificationsReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications read",
)
async def mark_all_notifications_read(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> MarkAllNotificationsReadResponse:
    """Mark every unread notification owned by the actor."""

    updated_count = await _use_cases(session).mark_all_read(actor)
    return MarkAllNotificationsReadResponse(updated_count=updated_count)


@router.post(
    "/devices",
    response_model=DeviceRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Register device token",
)
async def register_device(
    payload: DeviceRegisterRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> DeviceRegisterResponse:
    """Register or reactivate one device token for the authenticated user."""

    row = await _use_cases(session).register_device(
        actor, payload.token, payload.platform, payload.device_name
    )
    return DeviceRegisterResponse(**row)


@router.delete(
    "/devices/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate device token",
)
async def deactivate_device(
    token: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> Response:
    """Deactivate this actor's device token."""

    await _use_cases(session).deactivate_device(actor, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
