"""Consent routes: what must be accepted, and recording the answer."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.consent import ConsentRequest, ConsentStatusResponse, MarketingChoiceRequest
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.consent_repository import ConsentRepository

router = APIRouter()


def _status(latest: dict[str, dict]) -> ConsentStatusResponse:
    def accepted(kind: str, current: str) -> str | None:
        row = latest.get(kind)
        return row["version"] if row and row["granted"] and row["version"] == current else None

    terms = accepted("terms", settings.terms_version)
    privacy = accepted("privacy", settings.privacy_version)
    age = bool(latest.get("age_13_plus", {}).get("granted"))
    return ConsentStatusResponse(
        terms_version=settings.terms_version,
        privacy_version=settings.privacy_version,
        accepted_terms_version=terms,
        accepted_privacy_version=privacy,
        age_13_plus=age,
        marketing=bool(latest.get("marketing", {}).get("granted")),
        needs_consent=not (terms and privacy and age),
    )


@router.get(
    "/consents",
    response_model=ConsentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Consent status",
)
async def consent_status(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ConsentStatusResponse:
    """Which Terms and Privacy Policy versions apply, and whether this person has accepted them."""

    return _status(await ConsentRepository(session).latest(str(actor.id)))


@router.post(
    "/consents",
    response_model=ConsentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Record consent",
)
async def record_consent(
    payload: ConsentRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ConsentStatusResponse:
    """Record acceptance of the current Terms and Privacy Policy, the age statement and the marketing choice."""

    if not (payload.accept_terms and payload.accept_privacy and payload.age_13_plus):
        raise ValidationError("Accept the Terms, the Privacy Policy and confirm you are 13 or older to continue")
    repository = ConsentRepository(session)
    await repository.record(
        str(actor.id),
        payload.source,
        [
            ("terms", settings.terms_version, True),
            ("privacy", settings.privacy_version, True),
            ("age_13_plus", "1", True),
            ("marketing", "1", payload.marketing),
        ],
    )
    return _status(await repository.latest(str(actor.id)))


@router.put(
    "/consents/marketing",
    response_model=ConsentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Turn offers and news on or off",
)
async def set_marketing_choice(
    payload: MarketingChoiceRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ConsentStatusResponse:
    """Record a new marketing answer. Withdrawing is as easy as giving it and never affects the service."""

    repository = ConsentRepository(session)
    await repository.record(str(actor.id), payload.source, [("marketing", "1", payload.marketing)])
    return _status(await repository.latest(str(actor.id)))
