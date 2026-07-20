"""Health-check MCP tool."""

from datetime import UTC, datetime
from typing import Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.logging import get_logger
from research_intelligence_mcp.mcp.dependencies import AppDependencies

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
    async def health_check() -> HealthCheckResult:
        """Return server health and runtime metadata."""

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
