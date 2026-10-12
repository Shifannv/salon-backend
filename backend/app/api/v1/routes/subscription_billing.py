"""Owner subscription billing routes (website purchase flow + entitlement reads).

The native apps never expose a purchase entry point (store policy); the website uses these
with the same Supabase JWT. Admin manual/test activation stays under ``/admin`` and is not
callable by owners.
"""

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_authenticated_session,
    get_current_actor,
    get_subscription_provider_resolver,
)
from app.api.v1.schemas.subscription_billing import (
    AccessStateResponse,
    BillingPaymentResponse,
    CheckoutRequest,
    CheckoutResponse,
    PurchasablePlanResponse,
    SubscriptionConfigResponse,
    SubscriptionStateResponse,
    VerifyRequest,
)
from app.application.use_cases.subscription_billing import SubscriptionBillingUseCases
from app.core.config import settings
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)
from app.infrastructure.subscriptions.resolver import SubscriptionProviderResolver

router = APIRouter()


def _uc(
    session: AsyncSession | None, resolver: SubscriptionProviderResolver
) -> SubscriptionBillingUseCases:
    if session is None:  # config: no database access at all
        return SubscriptionBillingUseCases(None, resolver, settings)
    return SubscriptionBillingUseCases(
        SubscriptionBillingRepository(session), resolver, settings, PlatformRepository(session)
    )


@router.get(
    "/subscriptions/config",
    response_model=SubscriptionConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Is subscription billing available?",
    description="Always 200, no auth. `native_purchase_allowed` is always false (store policy).",
)
async def subscription_config(
    resolver: SubscriptionProviderResolver = Depends(get_subscription_provider_resolver),
) -> SubscriptionConfigResponse:
    return SubscriptionConfigResponse(**_uc(None, resolver).config())


@router.get(
    "/subscription-plans",
    response_model=list[PurchasablePlanResponse],
    status_code=status.HTTP_200_OK,
    summary="Purchasable subscription plans (owner)",
)
async def list_purchasable_plans(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: SubscriptionProviderResolver = Depends(get_subscription_provider_resolver),
) -> list[PurchasablePlanResponse]:
    rows = await _uc(session, resolver).list_plans(actor)
    return [PurchasablePlanResponse(**{**r, "id": str(r["id"])}) for r in rows]


@router.get(
    "/salons/me/subscription",
    response_model=SubscriptionStateResponse,
    status_code=status.HTTP_200_OK,
    summary="My salon subscription and entitlement (owner)",
)
async def my_subscription(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: SubscriptionProviderResolver = Depends(get_subscription_provider_resolver),
) -> SubscriptionStateResponse:
    return SubscriptionStateResponse(**await _uc(session, resolver).get_subscription(actor))


@router.get(
    "/salons/me/access-state",
    response_model=AccessStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Access state implied by the subscription alone (owner)",
    description="Thin read of the subscription-derived state; trial and soft-lock states are extended later.",
)
async def my_access_state(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: SubscriptionProviderResolver = Depends(get_subscription_provider_resolver),
) -> AccessStateResponse:
    return AccessStateResponse(**await _uc(session, resolver).access_state(actor))


@router.post(
    "/salons/me/subscription/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Start a subscription payment (owner, website)",
    description=(
        "Requires `Idempotency-Key`. The price is the plan price at this moment, snapshotted "
        "server-side; nothing about money is accepted from the client. 503 when billing is off."
    ),
)
async def checkout(
    payload: CheckoutRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: SubscriptionProviderResolver = Depends(get_subscription_provider_resolver),
) -> CheckoutResponse:
    body = await _uc(session, resolver).checkout(actor, str(payload.plan_id), idempotency_key)
    return CheckoutResponse(**body)


@router.post(
    "/salons/me/subscription/verify",
    response_model=SubscriptionStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify a subscription payment with the provider (owner)",
    description=(
        "The backend asks the provider; a client signature, if sent, only selects which payment "
        "to fetch. Safe to call repeatedly: activation happens at most once."
    ),
)
async def verify(
    payload: VerifyRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: SubscriptionProviderResolver = Depends(get_subscription_provider_resolver),
) -> SubscriptionStateResponse:
    body = await _uc(session, resolver).verify(
        actor, payload.order_ref, payload.payment_ref, payload.signature
    )
    return SubscriptionStateResponse(**body)


@router.post(
    "/salons/me/subscription/cancel",
    response_model=SubscriptionStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel future renewal (owner)",
    description="Idempotent. Paid-through access remains until the period ends.",
)
async def cancel(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: SubscriptionProviderResolver = Depends(get_subscription_provider_resolver),
) -> SubscriptionStateResponse:
    return SubscriptionStateResponse(**await _uc(session, resolver).cancel(actor))


@router.get(
    "/salons/me/subscription/payments",
    response_model=list[BillingPaymentResponse],
    status_code=status.HTTP_200_OK,
    summary="Subscription billing history (owner)",
)
async def payments(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: SubscriptionProviderResolver = Depends(get_subscription_provider_resolver),
) -> list[BillingPaymentResponse]:
    rows = await _uc(session, resolver).history(actor, limit, offset)
    return [BillingPaymentResponse(**r) for r in rows]
