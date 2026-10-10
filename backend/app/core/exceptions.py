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


class SalonNotAcceptingBookingsError(ConflictError):
    """The salon owner has paused new bookings."""

    code = "salon_not_accepting_bookings"


class DeletionBlockedError(ConflictError):
    """Account deletion is blocked until open bookings or requests are resolved."""

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
                return {k: _sanitise(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitise(i) for i in obj]
            return obj

        safe_errors = _sanitise(exc.errors())
        logger.warning(
            "Request validation error on %s %s: %s",
            request.method,
            request.url.path,
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
        body: dict = {"code": exc.code, "message": exc.message}
        if exc.details is not None:
            body["details"] = exc.details
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": body},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle all SQLAlchemy/asyncpg errors with a safe 500.

        SQLAlchemyError is a named type → routed to ExceptionMiddleware (inside
        CORSMiddleware), so the browser receives Access-Control-Allow-Origin
        automatically.  We log the full error but never expose SQL fragments to
        the client.
        """
        logger.exception(
            "Database error on %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
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
        logger.exception(
            "Unhandled server error on %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "internal_error", "message": "An unexpected server error occurred."}},
            headers=_cors_headers(request, settings.backend_cors_origins),
        )
