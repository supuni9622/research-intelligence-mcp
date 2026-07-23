"""Request correlation and caller-context propagation for MCP tool calls.

Implements the "Correlation IDs" and "User Context Propagation" sections of
``docs/research_intelligence_mcp_authentication.md``: a trusted backend (for
example ResearchMind) may supply ``X-Request-ID`` / ``X-Correlation-ID``
headers and a bounded ``X-Request-Context`` JSON header on ``streamable-http``
requests. These are surfaced only as structured-log correlation fields — the
raw end-user token is never forwarded or logged, matching the documented
"do not forward the user token directly" design.

Only the ``stdio`` transport's ``Context.request_context.request`` is
``None`` here in practice (no HTTP request exists), so every tool call still
gets a generated request ID for local traceability.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from research_intelligence_mcp.infrastructure.logging import (
    bind_log_context,
    get_logger,
)

logger = get_logger(__name__)

_REQUEST_ID_HEADER = "x-request-id"
_CORRELATION_ID_HEADER = "x-correlation-id"
_REQUEST_CONTEXT_HEADER = "x-request-context"

# Bounds are deliberately small: this header carries a handful of short
# identifiers, not an arbitrary payload.
_MAX_REQUEST_CONTEXT_HEADER_BYTES = 4096
_MAX_FIELD_LENGTH = 200


class CallerRequestContext(BaseModel):
    """Non-identity observability metadata forwarded by a trusted backend.

    Deliberately excludes user tokens or credentials; see "User Context
    Propagation" in the authentication doc.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    user_id: str | None = Field(default=None, max_length=_MAX_FIELD_LENGTH)
    tenant_id: str | None = Field(default=None, max_length=_MAX_FIELD_LENGTH)
    research_session_id: str | None = Field(
        default=None,
        max_length=_MAX_FIELD_LENGTH,
    )


def _extract_header(headers: Any, name: str) -> str | None:
    if headers is None:
        return None

    value = headers.get(name)

    return value.strip() or None if isinstance(value, str) else None


def _parse_caller_context(raw: str | None) -> CallerRequestContext | None:
    if raw is None:
        return None

    if len(raw.encode("utf-8")) > _MAX_REQUEST_CONTEXT_HEADER_BYTES:
        logger.warning("request_context_header_too_large")
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("request_context_header_invalid_json")
        return None

    try:
        return CallerRequestContext.model_validate(payload)
    except ValidationError:
        logger.warning("request_context_header_invalid_schema")
        return None


def _resolve_headers(ctx: object | None) -> object | None:
    """Best-effort extraction of HTTP headers from an MCP tool Context.

    Returns ``None`` under stdio (and any transport without an underlying
    HTTP request), where there are no headers to read.
    """

    if ctx is None:
        return None

    request_context = getattr(ctx, "request_context", None)
    request = getattr(request_context, "request", None) if request_context else None

    return getattr(request, "headers", None) if request is not None else None


def resolve_correlation(
    ctx: object | None,
) -> tuple[str, str, CallerRequestContext | None]:
    """Resolve the request ID, correlation ID, and caller context for a call."""

    headers = _resolve_headers(ctx)

    request_id = _extract_header(headers, _REQUEST_ID_HEADER) or str(uuid.uuid4())
    correlation_id = _extract_header(headers, _CORRELATION_ID_HEADER) or request_id
    caller_context = _parse_caller_context(
        _extract_header(headers, _REQUEST_CONTEXT_HEADER)
    )

    return request_id, correlation_id, caller_context


@contextmanager
def correlation_scope(ctx: object | None) -> Generator[tuple[str, str]]:
    """Bind request-correlation and caller-context fields for a tool call.

    Every log statement emitted for the duration of the scope — including
    ones made by downstream provider clients — carries these fields.
    """

    request_id, correlation_id, caller_context = resolve_correlation(ctx)

    with bind_log_context(
        request_id=request_id,
        correlation_id=correlation_id,
        caller_user_id=(caller_context.user_id if caller_context else None),
        caller_tenant_id=(caller_context.tenant_id if caller_context else None),
        caller_research_session_id=(
            caller_context.research_session_id if caller_context else None
        ),
    ):
        yield request_id, correlation_id
