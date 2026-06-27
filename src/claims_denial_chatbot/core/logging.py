"""
Structured logging configuration for the Claims Denial FAQ Chatbot.

Uses structlog for JSON-structured logs suitable for production log aggregation
(Datadog, CloudWatch, ELK). Configures log level from application settings.
"""

import logging
import sys

import structlog

from claims_denial_chatbot.config import get_application_settings


def configure_structured_logging() -> None:
    """
    Configure structlog and standard logging for the application.

    Sets up JSON-formatted structured logging with timestamps, log levels,
    and exception info. Log level is derived from LOG_LEVEL env variable.

    This function should be called once at application startup (FastAPI lifespan
    or Slack bot initialization).
    """
    settings = get_application_settings()

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Retrieve a named structured logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        BoundLogger: Configured structlog logger bound to the given name.
    """
    return structlog.get_logger(name)
