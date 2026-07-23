"""Prometheus ``/metrics`` HTTP endpoint.

Implements the "Structured Metrics" milestone of
``docs/remote_mcp_deployment_prd.md``. Registered via FastMCP's
``custom_route``, so it is unauthenticated like ``/health`` and ``/ready`` —
the PRD requires this endpoint to remain private at the network layer
(ECS security groups), not behind application authentication, since
scraping tools typically do not carry a service JWT.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import Response

from research_intelligence_mcp.infrastructure.observability.metrics import (
    METRICS_CONTENT_TYPE,
    refresh_cache_gauges,
    render_metrics,
)
from research_intelligence_mcp.mcp.dependencies import AppDependencies


def register_metrics_route(
    *,
    server: FastMCP,
    dependencies: AppDependencies,
) -> None:
    """Register the ``/metrics`` HTTP route.

    Only meaningful for the ``streamable-http`` transport; ``stdio`` never
    builds the Starlette app this route is attached to.
    """

    @server.custom_route("/metrics", methods=["GET"])  # type: ignore[untyped-decorator]
    async def metrics(request: Request) -> Response:
        """Return current metrics in Prometheus text-exposition format."""

        search_cache_stats = await dependencies.search_cache.stats()
        paper_cache_stats = await dependencies.paper_cache.stats()

        refresh_cache_gauges(cache="search", stats=search_cache_stats)
        refresh_cache_gauges(cache="paper", stats=paper_cache_stats)

        return Response(
            content=render_metrics(),
            media_type=METRICS_CONTENT_TYPE,
        )
