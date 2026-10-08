"""Structured logging configuration using structlog.

Configures structlog with JSON output in production and pretty-print in local/test.
A request-ID processor is included so every log line in a request shares the same
correlation ID.
"""

import logging
import sys
from contextvars import ContextVar

import structlog

# Per-request correlation ID stored in a context variable.
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current request-scoped correlation ID (empty string if none)."""

    return _request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Bind a new request ID to the current async context."""

    _request_id_var.set(request_id)


def _add_request_id(
    logger: logging.Logger,
    method: str,
    event_dict: dict,
) -> dict:
    """structlog processor: inject the current request_id."""

    rid = get_request_id()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging(json_logs: bool | None = None) -> None:
    """Configure structlog for the current environment.

    Args:
        json_logs: Force JSON output. If None (default), uses JSON in
                   production and pretty-print in local/test.
    """

    from app.core.config import settings

    is_production = settings.environment not in {"local", "test"}
    use_json = json_logs if json_logs is not None else is_production

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if use_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO if is_production else logging.DEBUG)

    # Silence noisy loggers
    for name in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
