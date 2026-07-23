"""Tests for the HTTP-layer metrics ASGI middleware."""

from __future__ import annotations

from typing import Any

import pytest

from research_intelligence_mcp.infrastructure.observability.http_middleware import (
    HttpMetricsMiddleware,
)
from research_intelligence_mcp.infrastructure.observability.metrics import (
    METRICS_REGISTRY,
)


def _sample(name: str, labels: dict[str, str]) -> float | None:
    return METRICS_REGISTRY.get_sample_value(name, labels)


async def _ok_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"{}"})


@pytest.mark.asyncio
async def test_http_metrics_middleware_records_status_and_duration() -> None:
    """A completed HTTP request should record a status-labeled count."""

    middleware = HttpMetricsMiddleware(_ok_app)

    before = (
        _sample(
            "mcp_http_requests_total",
            {"method": "GET", "route": "/unit-test-ok", "status_code": "200"},
        )
        or 0.0
    )

    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await middleware(
        {"type": "http", "method": "GET", "path": "/unit-test-ok"},
        receive,
        send,
    )

    after = _sample(
        "mcp_http_requests_total",
        {"method": "GET", "route": "/unit-test-ok", "status_code": "200"},
    )

    assert after == before + 1.0
    assert sent[0]["type"] == "http.response.start"

    in_flight = _sample(
        "mcp_http_in_flight_requests",
        {"method": "GET", "route": "/unit-test-ok"},
    )

    assert in_flight == 0.0


@pytest.mark.asyncio
async def test_http_metrics_middleware_defaults_to_500_when_app_raises() -> None:
    """An app that raises before responding should be recorded as status 500."""

    async def failing_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        raise RuntimeError("boom")

    middleware = HttpMetricsMiddleware(failing_app)

    async def receive() -> dict[str, Any]:
        return {"type": "http.request"}

    async def send(message: dict[str, Any]) -> None:
        return None

    with pytest.raises(RuntimeError):
        await middleware(
            {"type": "http", "method": "GET", "path": "/unit-test-fail"},
            receive,
            send,
        )

    status_count = _sample(
        "mcp_http_requests_total",
        {"method": "GET", "route": "/unit-test-fail", "status_code": "500"},
    )

    assert status_count == 1.0


@pytest.mark.asyncio
async def test_http_metrics_middleware_ignores_non_http_scopes() -> None:
    """Lifespan (and other non-http) scopes must pass through untouched."""

    calls: list[dict[str, Any]] = []

    async def lifespan_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        calls.append(scope)

    middleware = HttpMetricsMiddleware(lifespan_app)

    async def receive() -> dict[str, Any]:
        raise AssertionError("receive should not be called")

    async def send(message: dict[str, Any]) -> None:
        raise AssertionError("send should not be called")

    await middleware({"type": "lifespan"}, receive, send)

    assert calls == [{"type": "lifespan"}]
