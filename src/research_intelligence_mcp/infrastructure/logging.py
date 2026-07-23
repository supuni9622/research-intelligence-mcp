"""Structured logging configuration."""

import logging
import sys
from collections.abc import Generator, Sequence
from contextlib import contextmanager

import structlog
from structlog.typing import Processor


def configure_logging(
    *,
    log_level: str,
    log_format: str,
) -> None:
    """Configure standard-library logging and structlog.

    Logs are intentionally written to stderr. MCP's stdio transport uses
    stdout for protocol messages, so application logs must not be written
    there.
    """

    numeric_log_level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: Sequence[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(
            fmt="iso",
            utc=True,
        ),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: Processor

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(
            colors=sys.stderr.isatty(),
        )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(numeric_log_level)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_log_level)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a typed structured logger."""

    return structlog.stdlib.get_logger(name)


@contextmanager
def bind_log_context(**fields: str | None) -> Generator[None]:
    """Bind structured-log fields for the duration of a scope.

    ``None``-valued fields are dropped rather than bound, so callers can pass
    optional correlation data (for example, an absent request header)
    without polluting log output with empty fields. Bound values are
    automatically included in every log call made on this task, including
    ones made by downstream infrastructure (HTTP clients, providers), via
    ``structlog.contextvars``.
    """

    bound_fields = {key: value for key, value in fields.items() if value is not None}

    tokens = structlog.contextvars.bind_contextvars(**bound_fields)

    try:
        yield
    finally:
        structlog.contextvars.reset_contextvars(**tokens)
