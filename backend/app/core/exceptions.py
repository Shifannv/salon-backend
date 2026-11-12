"""Application exception hierarchy and HTTP mappings."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected application failures."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "internal_error"

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist or is hidden from the actor."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class QrCodeNotFoundError(NotFoundError):
    """A walk-in QR token is malformed, unknown, revoked or its salon is not publicly bookable.

    One code for every cause on purpose: the response must not reveal which.
    """

    code = "qr_not_found"


class ForbiddenError(AppError):
    """Raised when the actor is authenticated but not allowed to perform an action."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class SalonApprovalRequiredError(ForbiddenError):
    """Raised when onboarding has not received super admin approval."""

    code = "awaiting_admin_approval"


class AdminMFARequiredError(ForbiddenError):
    """An admin operation needs a verified second authentication factor."""

    code = "mfa_required"


class BirthDateRequiredError(ForbiddenError):
    """A booking needs a date of birth on file."""

    code = "birth_date_required"


class UnderMinimumAgeError(ForbiddenError):
    """The person is younger than the minimum age for an account."""

    code = "under_minimum_age"


class GuardianConsentRequiredError(ForbiddenError):
    """A 13 to 17 year old needs a guardian's approval before booking."""

    code = "guardian_consent_required"


class UnauthorizedError(AppError):
    """Raised when authentication is missing or invalid."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ConflictError(AppError):
    """Raised when a request conflicts with current server state."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class SalonNotReadyForDeletionError(ConflictError):
    """Raised when a salon still has refunds or payouts outstanding, so it cannot be erased yet."""

    code = "salon_not_ready_for_deletion"


class SlotUnavailableError(ConflictError):
    """Raised when a booking slot is no longer available."""

    code = "slot_unavailable"


class SalonClosedError(ConflictError):
    """Raised when the salon has an active holiday on the requested date."""

    code = "salon_closed"


class BreakConflictError(ConflictError):
    """Raised when a requested booking time falls inside a scheduled salon or staff break."""

    code = "break_conflict"

    def __init__(
        self,
        message: str = "The selected time collides with a scheduled break",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details)


class BookingChangeError(ConflictError):
    """A sanitized, explicitly classified booking-change conflict."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class PayAtSalonDailyLimitError(ConflictError):
    code = "pay_at_salon_daily_limit"


class PayAtSalonBlockedError(ConflictError):
    code = "pay_at_salon_temporarily_blocked"


class PaymentCollectionRequiredError(ConflictError):
    code = "payment_collection_required"


class SalonNotAcceptingBookingsError(ConflictError):
    """The salon owner has paused new bookings."""

    code = "salon_not_accepting_bookings"


class DeletionBlockedError(ConflictError):
    """Account deletion is blocked: a customer's own open work or an owner's paid subscription."""

    code = "deletion_blocked"


class ValidationError(AppError):
    """Raised when business validation fails."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


class RuleOccurrenceError(ValidationError):
    """An expense claiming to be a repeating expense's day that the rule does not allow."""

    code = "rule_occurrence_invalid"


class QrSalonMismatchError(ValidationError):
    """The request names a salon other than the one the scanned QR token belongs to."""

    code = "qr_salon_mismatch"


class BookingSourceNotAllowedError(ValidationError):
    """The booking source cannot be claimed on this route."""

    code = "booking_source_not_allowed"


class BookingWindowExceededError(ValidationError):
    """A customer booking is later than the rolling advance-booking window."""

    code = "booking_window_exceeded"


class OnlinePaymentUnavailableError(ValidationError):
    """An online payment preference was requested while online payment is not offered.

    422, never 409: clients treat 409 ``slot_unavailable`` as a retryable slot conflict.
    """

    code = "online_payment_unavailable"


class BookingIdempotencyKeyReusedError(ValidationError):
    """A booking Idempotency-Key was already used by the same customer with a different request."""

    code = "idempotency_key_reused"


class ContactMismatchError(ValidationError):
    """The supplied contact is not a verified contact of the authenticated account."""

    code = "contact_mismatch"


class InvalidVerificationCodeError(AppError):
    """A verification code or confirmation token is wrong, expired or already used."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "invalid_verification_code"


class ServiceUnavailableError(AppError):
    """Raised when a required infrastructure dependency cannot be reached."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "service_unavailable"


class TooManyRequestsError(AppError):
    """Raised when rate limits are exceeded."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "too_many_requests"


class PayloadTooLargeError(AppError):
    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    code = "payload_too_large"


class UnsupportedMediaTypeError(AppError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = "unsupported_media_type"


class RequestTimeoutError(AppError):
    status_code = status.HTTP_408_REQUEST_TIMEOUT
    code = "request_timeout"


class PaymentProviderNotConfiguredError(AppError):
    """No payment provider is configured, so online payment is unavailable."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "payment_provider_not_configured"


class PaymentCapabilityError(AppError):
    """The configured gateway/settlement model does not support this operation."""

    status_code = status.HTTP_501_NOT_IMPLEMENTED
    code = "payment_capability_unsupported"


class PaymentProviderError(AppError):
    """The payment provider rejected a request or was unreachable."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "payment_provider_error"


class InvalidWebhookSignatureError(AppError):
    """A webhook body failed signature verification; nothing is recorded."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "invalid_webhook_signature"


class PaymentOutcomeUnknownError(PaymentProviderError):
    """The provider call timed out or failed in transit: it may or may not have taken effect.

    Callers must reconcile by the persisted operation identity before retrying.
    """

    code = "payment_outcome_unknown"


class WebhookPayloadTooLargeError(AppError):
    """A webhook body exceeded the configured size cap."""

    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    code = "webhook_payload_too_large"


class PaymentAmountMismatchError(ConflictError):
    """The provider reports an amount different from the ledger row."""

    code = "payment_amount_mismatch"


class PaymentOvercollectionError(ConflictError):
    """Accepting this payment would collect more than the booking total."""

    code = "payment_overcollection"


class PaymentInProgressError(ConflictError):
    """A gateway payment is open on the booking, so it cannot be settled manually."""

    code = "payment_in_progress"


class IdempotencyKeyRequiredError(AppError):
    """A money-mutating request arrived without an Idempotency-Key header."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "idempotency_key_required"


class IdempotencyKeyReuseError(ConflictError):
    """The Idempotency-Key was already used with a different request."""

    code = "idempotency_key_reuse"


class IdempotencyInProgressError(ConflictError):
    """The first request carrying this Idempotency-Key is still running."""

    code = "idempotency_in_progress"


def _cors_headers(request: Request, allowed_origins: list[str]) -> dict[str, str]:
    """Build CORS headers for the response, based on the request Origin.

    The ``Exception`` catch-all handler is routed by Starlette to
    ``ServerErrorMiddleware``, which sits *outside* ``CORSMiddleware`` in the
    middleware stack.  Responses returned from that handler therefore bypass
    ``CORSMiddleware`` entirely, so we must inject the headers manually here.
    """
    origin = request.headers.get("origin", "")
    if origin in allowed_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


def app_error_response(exc: AppError) -> JSONResponse:
    """Shared application-error serialization for routes and early middleware."""
    from app.core.telemetry import metrics

    body: dict = {"code": exc.code, "message": exc.message}
    if metrics.get() is not None:
        metrics.get().error_code = exc.code
    if exc.details is not None:
        body["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content={"error": body})


_HTTP_STATUS_CODES = {
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
}


def register_exception_handlers(app: FastAPI) -> None:
    """Register one HTTP translation point for application exceptions."""

    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import SQLAlchemyError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from app.core.config import settings

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Override FastAPI's default 422 handler to avoid UnicodeDecodeError.

        FastAPI's built-in handler calls ``jsonable_encoder(exc.errors())``,
        which tries to UTF-8–decode any ``bytes`` values embedded in the error
        detail.  When a client sends a binary file (e.g. a JPEG) to a JSON
        endpoint the raw bytes end up in the validation-error context and the
        decode crashes with ``UnicodeDecodeError``.

        This handler sanitises the error list before serialising it: any
        ``bytes`` value is replaced with a human-readable placeholder so the
        server always returns a clean 422 JSON response.
        """

        def _sanitise(obj: object) -> object:
            """Recursively replace bytes with a safe placeholder."""
            if isinstance(obj, ValueError):
                return str(obj)
            if isinstance(obj, bytes):
                return f"<{len(obj)} binary bytes — not shown>"
            if isinstance(obj, dict):
                return {k: _sanitise(v) for k, v in obj.items() if k not in {"input", "ctx"}}
            if isinstance(obj, list):
                return [_sanitise(i) for i in obj]
            return obj

        safe_errors = _sanitise(exc.errors())
        logger.warning(
            "Request validation error on %s %s: %s",
            request.method,
            getattr(request.scope.get("route"), "path", "unmatched"),
            safe_errors,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": safe_errors,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Framework-raised errors (missing bearer token, unknown route) use the shared envelope too.

        ``detail`` is kept at the top level so a client that still reads the framework shape keeps working.
        """

        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        code = _HTTP_STATUS_CODES.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message}, "detail": message},
            headers=exc.headers,
        )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        # AppError is a named type → routed to ExceptionMiddleware (inside CORSMiddleware).
        # CORSMiddleware adds Access-Control-Allow-Origin automatically.
        return app_error_response(exc)

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle all SQLAlchemy/asyncpg errors with a safe 500.

        SQLAlchemyError is a named type → routed to ExceptionMiddleware (inside
        CORSMiddleware), so the browser receives Access-Control-Allow-Origin
        automatically.  We log the full error but never expose SQL fragments to
        the client.
        """
        logger.error("Database request failed (%s)", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "internal_error", "message": "A database error occurred. Please try again."}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for any remaining unexpected errors.

        ``Exception`` is special-cased by Starlette — it is routed to
        ``ServerErrorMiddleware`` (the *outermost* layer), which runs before
        ``CORSMiddleware``.  Responses from this handler therefore bypass
        ``CORSMiddleware``, so we must inject the CORS headers manually.
        """
        logger.error("Unhandled request failed (%s)", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "internal_error", "message": "An unexpected server error occurred."}},
            headers=_cors_headers(request, settings.backend_cors_origins),
        )


class EntitlementRequiredError(ForbiddenError):
    """The salon's plan (or free trial) does not include this feature."""

    code = "entitlement_required"


class DayInFutureError(ValidationError):
    """A day cannot be closed before it has started in the salon's own time zone."""

    code = "day_in_future"


class DifferenceReasonRequiredError(ValidationError):
    """Counted cash differs from the expected cash and no reason was given."""

    code = "difference_reason_required"


class OpeningCashRequiredError(ValidationError):
    """The owner must confirm the cash in the drawer at the start of the day being closed."""

    code = "opening_cash_required"


class ExpenseAlreadyReversedError(ConflictError):
    """An expense can be reversed once; a reversal itself cannot be reversed."""

    code = "expense_already_reversed"


class InsufficientBalanceError(ConflictError):
    """The owner asked for more than the wallet has available."""

    code = "insufficient_balance"


class PayoutBelowMinimumError(ValidationError):
    """The amount asked for is below the smallest payout."""

    code = "below_minimum"


class PayoutAccountMissingError(ConflictError):
    """No bank or UPI details are saved to pay the money into."""

    code = "payout_account_missing"


class PayoutDayInvalidError(ValidationError):
    """The payout day is in the past or too far ahead."""

    code = "invalid_date"


class PayoutNotCancellableError(ConflictError):
    """A payout request that has already been paid, rejected or cancelled cannot be cancelled."""

    code = "not_cancellable"


class PayoutAlreadyProcessedError(ConflictError):
    """A payout request that has already been paid, rejected or cancelled cannot be processed again."""

    code = "already_processed"


class PayoutReferenceUsedError(ConflictError):
    """The bank or UPI reference was already recorded against another payout."""

    code = "reference_already_used"


class PayoutProofInvalidError(ValidationError):
    """The proof file is missing, too large, or not a screenshot or PDF."""

    code = "proof_invalid"


class PayoutPaymentInvalidError(ValidationError):
    """The payment details (date, method or amount) are not acceptable."""

    code = "payment_details_invalid"


class PayoutProviderUnavailableError(ServiceUnavailableError):
    """Automatic payout is not configured, so the admin pays this payout by hand."""

    code = "payout_provider_unavailable"


class PayoutProviderError(AppError):
    """The payout provider refused the request or returned something unusable."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "payout_provider_error"


class PayoutOutcomeUnknownError(PayoutProviderError):
    """The provider call timed out or failed in transit: the money may or may not be on its way.

    Callers must look the transfer up by its id before deciding anything, and never send it again.
    """

    code = "payout_outcome_unknown"


class PayoutTransferInProgressError(ConflictError):
    """A transfer for this payout is already on its way or done."""

    code = "transfer_in_progress"


class PayoutTransferInvalidError(ValidationError):
    """The payout cannot be sent through the provider (account, amount or owner details)."""

    code = "payout_transfer_invalid"
