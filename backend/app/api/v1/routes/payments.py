"""Customer and owner payment routes. Always registered; dormant without a provider."""

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor, get_payment_gateway_resolver
from app.api.v1.schemas.payment import (
    BookingPaymentsResponse,
    EarningsResponse,
    PaymentConfigResponse,
    PaymentConfirmRequest,
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentRefundRequest,
    SettlementAccountResponse,
)
from app.application.use_cases.payments import BookingPaymentUseCases
from app.core.config import settings
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.payment_repository import PaymentRepository
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.payments.resolver import PaymentGatewayResolver

router = APIRouter()


def _use_cases(session: AsyncSession | None, resolver: PaymentGatewayResolver) -> BookingPaymentUseCases:
    if session is None:  # config endpoint: no database access at all
        return BookingPaymentUseCases(None, resolver, settings)  # type: ignore[arg-type]
    return BookingPaymentUseCases(
        PaymentRepository(session), resolver, settings, PlatformRepository(session)
    )


@router.get(
    "/payments/config",
    response_model=PaymentConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Is online payment available?",
    description="Always 200. `enabled: false` until a payment provider is configured.",
)
async def payment_config(
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> PaymentConfigResponse:
    return PaymentConfigResponse(**_use_cases(None, resolver).config())


@router.post(
    "/bookings/{booking_id}/payments/intent",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Start an online payment (customer)",
    description="Requires `Idempotency-Key`. The amount is derived server-side. 503 without a provider.",
)
async def create_payment_intent(
    booking_id: str,
    payload: PaymentIntentRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> PaymentIntentResponse:
    body = await _use_cases(session, resolver).create_intent(
        actor, booking_id, idempotency_key, payload.purpose if payload else None
    )
    return PaymentIntentResponse(**body)


@router.post(
    "/bookings/{booking_id}/payments/confirm",
    response_model=BookingPaymentsResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm a client-side payment callback (customer)",
    description="Requires `Idempotency-Key`. The callback signature and amount are verified server-side.",
)
async def confirm_payment(
    booking_id: str,
    payload: PaymentConfirmRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> BookingPaymentsResponse:
    body = await _use_cases(session, resolver).confirm(
        actor,
        booking_id,
        payload.order_ref,
        payload.payment_ref,
        payload.signature,
        idempotency_key,
    )
    return BookingPaymentsResponse(**body)


@router.post(
    "/bookings/{booking_id}/payments/cancel",
    response_model=BookingPaymentsResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel the open online payment (customer)",
)
async def cancel_payment(
    booking_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> BookingPaymentsResponse:
    body = await _use_cases(session, resolver).cancel(actor, booking_id, idempotency_key)
    return BookingPaymentsResponse(**body)


@router.get(
    "/bookings/{booking_id}/payments",
    response_model=BookingPaymentsResponse,
    status_code=status.HTTP_200_OK,
    summary="Payment ledger for a booking (customer or salon)",
)
async def list_booking_payments(
    booking_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> BookingPaymentsResponse:
    return BookingPaymentsResponse(
        **await _use_cases(session, resolver).list_payments(actor, booking_id)
    )


@router.post(
    "/bookings/{booking_id}/payments/{payment_id}/refund",
    response_model=BookingPaymentsResponse,
    status_code=status.HTTP_200_OK,
    summary="Refund an online payment (owner)",
    description="Requires `Idempotency-Key`. Cash receipts cannot be refunded by the platform.",
)
async def refund_payment(
    booking_id: str,
    payment_id: str,
    payload: PaymentRefundRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> BookingPaymentsResponse:
    body = await _use_cases(session, resolver).refund(
        actor, booking_id, payment_id, payload.amount, payload.reason, idempotency_key
    )
    return BookingPaymentsResponse(**body)


@router.get(
    "/salons/me/earnings",
    response_model=EarningsResponse,
    status_code=status.HTTP_200_OK,
    summary="Owner earnings from the payment ledger",
)
async def my_earnings(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> EarningsResponse:
    return EarningsResponse(**await _use_cases(session, resolver).earnings(actor))


@router.get(
    "/salons/me/settlement-account",
    response_model=SettlementAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Provider settlement (payee) account state",
)
async def get_settlement_account(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> SettlementAccountResponse:
    return SettlementAccountResponse(
        **await _use_cases(session, resolver).get_settlement_account(actor)
    )


@router.post(
    "/salons/me/settlement-account/register",
    response_model=SettlementAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Register the salon as a payee at the provider",
    description="Requires `Idempotency-Key`. Only meaningful for split-settlement providers.",
)
async def register_settlement_account(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> SettlementAccountResponse:
    return SettlementAccountResponse(
        **await _use_cases(session, resolver).register_settlement_account(
            actor, idempotency_key
        )
    )
