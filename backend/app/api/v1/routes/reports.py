"""Salon report submission contract used by the customer app."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.application.use_cases.reports import SubmitReport
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

router = APIRouter()


class ReportRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    salon_id: UUID
    reason: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=5000)
    # Accepted for compatibility; identity and timestamps remain server-owned.
    salon_name: str | None = Field(default=None, max_length=300)
    created_at: datetime | None = None


class ReportResponse(BaseModel):
    id: UUID
    status: Literal["received"]


@router.post("/reports", response_model=ReportResponse, status_code=201)
async def submit_report(
    payload: ReportRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ReportResponse:
    result = await SubmitReport(PlatformRepository(session)).execute(
        actor, str(payload.salon_id), payload.reason, payload.details,
    )
    return ReportResponse(**result)
