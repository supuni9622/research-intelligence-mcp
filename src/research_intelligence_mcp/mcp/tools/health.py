"""Health-check MCP tool and HTTP liveness/readiness endpoints.

The MCP tool (``health_check``) is reachable over any transport, including
``stdio``, and returns rich runtime metadata to MCP clients. The HTTP routes
below (``/health``, ``/ready``) implement the "Health Endpoints" milestone of
``docs/remote_mcp_deployment_prd.md`` for the ``streamable-http`` transport:
they are unauthenticated, ECS-target-group-friendly, and intentionally
minimal. They are registered via FastMCP's ``custom_route``, which never
requires authorization, and have no effect on the ``stdio`` transport since
no HTTP server exists there.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, ConfigDict, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.lifecycle import LifecycleState
from research_intelligence_mcp.infrastructure.logging import get_logger
from research_intelligence_mcp.infrastructure.observability.metrics import (
    record_tool_call,
)
from research_intelligence_mcp.mcp.dependencies import AppDependencies
from research_intelligence_mcp.mcp.observability import correlation_scope

logger = get_logger(__name__)


class HealthCheckResult(BaseModel):
    """Structured response returned by the health-check tool."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    status: Literal["healthy"] = Field(
        default="healthy",
        description="Current health state of the MCP server.",
    )

    service: str = Field(
        description="Human-readable application name.",
    )

    server_name: str = Field(
        description="MCP server identifier.",
    )

    version: str = Field(
        description="Current server version.",
    )

    environment: str = Field(
        description="Current application environment.",
    )

    transport: str = Field(
        description="Configured MCP transport.",
    )

    timestamp: datetime = Field(
        description="UTC time at which the health check was executed.",
    )


def build_health_check_result(settings: Settings) -> HealthCheckResult:
    """Build a health-check result independently of MCP transport.

    Keeping this logic outside the decorated MCP function makes it easy to
    unit test without starting an MCP session.
    """

    return HealthCheckResult(
        service=settings.app_name,
        server_name=settings.mcp_server_name,
        version=settings.app_version,
        environment=settings.app_environment,
        transport=settings.mcp_transport,
        timestamp=datetime.now(UTC),
    )


def register_health_tools(
    server: FastMCP,
    dependencies: AppDependencies,
) -> None:
    """Register health-related tools with the MCP server."""

    @server.tool(
        name="health_check",
        description=(
            "Check whether the Research Intelligence MCP server is running "
            "and return its current runtime metadata."
        ),
    )
    async def health_check(ctx: Context[Any, Any, Any]) -> HealthCheckResult:
        """Return server health and runtime metadata."""

        with correlation_scope(ctx), record_tool_call("health_check"):
            result = build_health_check_result(
                settings=dependencies.settings,
            )

            logger.info(
                "health_check_completed",
                status=result.status,
                server_name=result.server_name,
                version=result.version,
                environment=result.environment,
                transport=result.transport,
            )

            return result


def register_health_routes(
    *,
    server: FastMCP,
    dependencies: AppDependencies,
    lifecycle: LifecycleState,
) -> None:
    """Register unauthenticated HTTP liveness and readiness routes.

    Only meaningful for the ``streamable-http`` transport: FastMCP's
    ``custom_route`` records the route for later inclusion in
    ``streamable_http_app()``, but ``stdio`` never builds that Starlette app,
    so registration here is a no-op for local clients.
    """

    settings = dependencies.settings

    @server.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
    async def health(request: Request) -> JSONResponse:
        """Liveness probe. Verifies only that the process responds.

        Must never call Semantic Scholar, arXiv, or any other upstream
        dependency — an upstream outage must not fail container liveness
        and trigger unnecessary restarts.
        """

        return JSONResponse(
            {
                "status": "healthy",
                "service": settings.mcp_server_name,
                "version": settings.app_version,
            }
        )

    @server.custom_route("/ready", methods=["GET"])  # type: ignore[untyped-decorator]
    async def ready(request: Request) -> JSONResponse:
        """Readiness probe. Reports whether the server can accept traffic.

        Dependencies are already fully constructed by the time the server
        starts serving (see ``build_dependencies`` in ``main.py``), so the
        only condition that can flip readiness afterward is a graceful
        shutdown in progress.
        """

        if not lifecycle.is_ready:
            return JSONResponse(
                {
                    "status": "not_ready",
                    "service": settings.mcp_server_name,
                    "checks": {"dependencies": "not_ready"},
                },
                status_code=503,
            )

        return JSONResponse(
            {
                "status": "ready",
                "service": settings.mcp_server_name,
                "checks": {
                    "settings": "ready",
                    "dependencies": "ready",
                    "providers": "ready",
                },
            }
        )
