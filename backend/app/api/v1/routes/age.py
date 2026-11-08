"""Age routes: date of birth, and a guardian's approval for 13 to 17 year olds."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.age import (
    AgeStatusResponse,
    BirthDateRequest,
    GuardianRequest,
    GuardianVerifyRequest,
)
from app.application.use_cases.guardian_consent import GuardianConsentUseCases
from app.core.config import settings
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.age_repository import AgeRepository
from app.infrastructure.messaging.resolver import get_messaging_gateway, provider_connected

router = APIRouter()


def guardian_use_cases(session: AsyncSession) -> GuardianConsentUseCases:
    return GuardianConsentUseCases(
        AgeRepository(session),
        get_messaging_gateway(settings),
        settings,
        provider_connected=provider_connected(settings),
    )


@router.get("/age/status", response_model=AgeStatusResponse, status_code=status.HTTP_200_OK, summary="Age and booking status")
async def age_status(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> AgeStatusResponse:
    """Whether this person may book and what unlocks it. The date of birth itself is never returned."""

    return AgeStatusResponse(**await guardian_use_cases(session).status(actor))


@router.put("/age/birth-date", response_model=AgeStatusResponse, status_code=status.HTTP_200_OK, summary="Save date of birth")
async def set_birth_date(
    payload: BirthDateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> AgeStatusResponse:
    """Save the date of birth once. Under 13 is refused; a different date later needs support."""

    return AgeStatusResponse(**await guardian_use_cases(session).set_birth_date(actor, payload.birth_date))


@router.post("/age/guardian", response_model=AgeStatusResponse, status_code=status.HTTP_200_OK, summary="Send a guardian code")
async def request_guardian_code(
    payload: GuardianRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> AgeStatusResponse:
    """Text a one-time code to a parent or guardian's phone (13 to 17 year olds only)."""

    return AgeStatusResponse(**await guardian_use_cases(session).request_guardian(actor, payload.guardian_phone))


@router.post("/age/guardian/verify", response_model=AgeStatusResponse, status_code=status.HTTP_200_OK, summary="Confirm the guardian code")
async def verify_guardian_code(
    payload: GuardianVerifyRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> AgeStatusResponse:
    """The guardian reads out the code; a correct one unlocks booking."""

    return AgeStatusResponse(**await guardian_use_cases(session).verify_guardian(actor, payload.code))


@router.delete("/age/guardian", response_model=AgeStatusResponse, status_code=status.HTTP_200_OK, summary="Withdraw guardian approval")
async def revoke_guardian_approval(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> AgeStatusResponse:
    """Withdraw the approval. Bookings lock again until a guardian approves."""

    return AgeStatusResponse(**await guardian_use_cases(session).revoke_guardian(actor))
