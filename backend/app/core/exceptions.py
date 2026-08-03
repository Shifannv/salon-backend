"""Application exception hierarchy and HTTP mappings."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for expected application failures."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "internal_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist or is hidden from the actor."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ForbiddenError(AppError):
    """Raised when the actor is authenticated but not allowed to perform an action."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


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


class ValidationError(AppError):
    """Raised when business validation fails."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


def register_exception_handlers(app: FastAPI) -> None:
    """Register one HTTP translation point for application exceptions."""

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
