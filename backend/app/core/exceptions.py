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


class UnauthorizedError(AppError):
    """Raised when authentication is missing or invalid."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ConflictError(AppError):
    """Raised when a request conflicts with current server state."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class SlotUnavailableError(ConflictError):
    """Raised when a booking slot is no longer available."""

    code = "slot_unavailable"


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


def register_exception_handlers(app: FastAPI) -> None:
    """Register one HTTP translation point for application exceptions."""

    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import SQLAlchemyError

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
