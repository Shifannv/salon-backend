"""Authenticated support endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor, require_role
from app.api.v1.schemas.support import (
    EmailEventResponse,
    SupportCreateRequest,
    SupportReplyRequest,
    SupportTicketResponse,
)
from app.application.use_cases.support import SupportUseCases
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.support_repository import SupportRepository

router = APIRouter()


@router.post("/support/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: SupportCreateRequest, actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    key: str | None = Header(default=None, alias="Idempotency-Key")):
    values = payload.model_dump()
    values["salon_id"] = str(values["salon_id"]) if values["salon_id"] else None
    return await SupportUseCases(SupportRepository(session), settings).create(actor, values, key)


@router.get("/support/tickets/{ticket_id}", response_model=SupportTicketResponse, status_code=status.HTTP_200_OK)
async def read_ticket(ticket_id: UUID,
    actor: Profile = Depends(require_role(Role.customer, Role.owner, Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session)):
    return await SupportUseCases(SupportRepository(session), settings).read(actor, str(ticket_id))


@router.post("/support/tickets/{ticket_id}/reply", response_model=SupportTicketResponse, status_code=status.HTTP_200_OK)
async def reply_ticket(ticket_id: UUID, payload: SupportReplyRequest,
    actor: Profile = Depends(require_role(Role.owner, Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    key: str | None = Header(default=None, alias="Idempotency-Key")):
    return await SupportUseCases(SupportRepository(session), settings).reply(actor, str(ticket_id), payload.body, key)


@router.get("/email/events/{event_id}", response_model=EmailEventResponse, status_code=status.HTTP_200_OK)
async def email_event(event_id: UUID, actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session)):
    event = await SupportRepository(session).email_status(str(event_id), actor.id)
    if event is None:
        raise NotFoundError("Email event not found")
    return event
