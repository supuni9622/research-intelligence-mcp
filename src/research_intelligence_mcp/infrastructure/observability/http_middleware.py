"""ASGI middleware recording HTTP-layer metrics for the streamable-http transport.

Implemented as a raw ASGI callable (not Starlette's buffering
``BaseHTTPMiddleware``) so that streaming MCP session responses are passed
through untouched. Route labels use the raw request path: every path
currently served (``/mcp``, ``/health``, ``/ready``, ``/metrics``) is fixed
and unparameterized, so cardinality stays bounded.
"""

from __future__ import annotations

from time import perf_counter

from research_intelligence_mcp.infrastructure.lifecycle import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)
from research_intelligence_mcp.infrastructure.observability.metrics import (
    MCP_HTTP_IN_FLIGHT_REQUESTS,
    MCP_HTTP_REQUEST_DURATION_SECONDS,
    MCP_HTTP_REQUESTS_TOTAL,
)


class HttpMetricsMiddleware:
    """Records request counts, durations, and in-flight gauges for HTTP scopes."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        method = str(scope.get("method", "UNKNOWN"))
        route = str(scope.get("path", "unknown"))

        MCP_HTTP_IN_FLIGHT_REQUESTS.labels(method=method, route=route).inc()
        start = perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code

            if message.get("type") == "http.response.start":
                raw_status = message.get("status", 500)
                status_code = raw_status if isinstance(raw_status, int) else 500

            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        finally:
            duration = perf_counter() - start
            status_label = str(status_code)

            MCP_HTTP_REQUESTS_TOTAL.labels(
                method=method,
                route=route,
                status_code=status_label,
            ).inc()
            MCP_HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                route=route,
                status_code=status_label,
            ).observe(duration)
            MCP_HTTP_IN_FLIGHT_REQUESTS.labels(method=method, route=route).dec()
