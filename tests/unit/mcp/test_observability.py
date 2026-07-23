"""Tests for MCP request-correlation and caller-context propagation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

import structlog

from research_intelligence_mcp.mcp.observability import (
    correlation_scope,
    resolve_correlation,
)


@dataclass
class _StubHeaders:
    """Minimal case-sensitive header stand-in matching our lookup keys."""

    values: dict[str, str]

    def get(self, name: str) -> str | None:
        return self.values.get(name)


def _stub_ctx(headers: dict[str, str] | None) -> SimpleNamespace:
    request = (
        SimpleNamespace(headers=_StubHeaders(headers)) if headers is not None else None
    )
    request_context = SimpleNamespace(request=request)
    return SimpleNamespace(request_context=request_context)


def test_resolve_correlation_without_context_generates_request_id() -> None:
    """stdio (no ctx, no HTTP request) must still get a traceable request ID."""

    request_id, correlation_id, caller_context = resolve_correlation(None)

    assert request_id
    assert correlation_id == request_id
    assert caller_context is None


def test_resolve_correlation_without_headers_generates_request_id() -> None:
    """A Context whose transport has no HTTP request behaves like stdio."""

    ctx = _stub_ctx(headers=None)

    request_id, correlation_id, caller_context = resolve_correlation(ctx)

    assert request_id
    assert correlation_id == request_id
    assert caller_context is None


def test_resolve_correlation_reads_request_and_correlation_id_headers() -> None:
    """Explicit X-Request-ID / X-Correlation-ID headers must be honored."""

    ctx = _stub_ctx(
        headers={
            "x-request-id": "req-123",
            "x-correlation-id": "session-abc",
        }
    )

    request_id, correlation_id, _ = resolve_correlation(ctx)

    assert request_id == "req-123"
    assert correlation_id == "session-abc"


def test_resolve_correlation_falls_back_correlation_id_to_request_id() -> None:
    """Without an explicit correlation ID, it should default to the request ID."""

    ctx = _stub_ctx(headers={"x-request-id": "req-123"})

    request_id, correlation_id, _ = resolve_correlation(ctx)

    assert request_id == "req-123"
    assert correlation_id == "req-123"


def test_resolve_correlation_parses_valid_caller_context() -> None:
    """A well-formed X-Request-Context header should populate caller context."""

    ctx = _stub_ctx(
        headers={
            "x-request-context": json.dumps(
                {
                    "user_id": "usr_123",
                    "tenant_id": "tenant_1",
                    "research_session_id": "res_456",
                }
            )
        }
    )

    _, _, caller_context = resolve_correlation(ctx)

    assert caller_context is not None
    assert caller_context.user_id == "usr_123"
    assert caller_context.tenant_id == "tenant_1"
    assert caller_context.research_session_id == "res_456"


def test_resolve_correlation_ignores_invalid_json_caller_context() -> None:
    """Malformed JSON must be dropped, not raised."""

    ctx = _stub_ctx(headers={"x-request-context": "{not-json"})

    _, _, caller_context = resolve_correlation(ctx)

    assert caller_context is None


def test_resolve_correlation_ignores_schema_invalid_caller_context() -> None:
    """A JSON payload with the wrong field types must be dropped, not raised."""

    ctx = _stub_ctx(headers={"x-request-context": json.dumps({"user_id": 12345})})

    _, _, caller_context = resolve_correlation(ctx)

    assert caller_context is None


def test_resolve_correlation_ignores_oversized_caller_context() -> None:
    """An oversized X-Request-Context header must be rejected, not parsed."""

    huge_payload = json.dumps({"user_id": "x" * 10_000})
    ctx = _stub_ctx(headers={"x-request-context": huge_payload})

    _, _, caller_context = resolve_correlation(ctx)

    assert caller_context is None


def test_resolve_correlation_ignores_unknown_caller_context_fields() -> None:
    """Extra fields in the caller-context payload must be ignored, not raise."""

    ctx = _stub_ctx(
        headers={
            "x-request-context": json.dumps(
                {
                    "user_id": "usr_123",
                    "unexpected_field": "should-be-ignored",
                }
            )
        }
    )

    _, _, caller_context = resolve_correlation(ctx)

    assert caller_context is not None
    assert caller_context.user_id == "usr_123"


def test_correlation_scope_binds_and_clears_log_context() -> None:
    """Correlation fields must be bound only for the scope's duration."""

    ctx = _stub_ctx(
        headers={
            "x-request-id": "req-123",
            "x-correlation-id": "session-abc",
            "x-request-context": json.dumps({"tenant_id": "tenant_1"}),
        }
    )

    assert structlog.contextvars.get_contextvars() == {}

    with correlation_scope(ctx) as (request_id, correlation_id):
        assert request_id == "req-123"
        assert correlation_id == "session-abc"

        bound = structlog.contextvars.get_contextvars()
        assert bound["request_id"] == "req-123"
        assert bound["correlation_id"] == "session-abc"
        assert bound["caller_tenant_id"] == "tenant_1"
        assert "caller_user_id" not in bound

    assert structlog.contextvars.get_contextvars() == {}
