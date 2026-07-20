"""Health-check MCP tool."""

from datetime import UTC, datetime
from typing import Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.logging import get_logger

logger = get_logger(__name__)


class HealthCheckResult(BaseModel):
    """Structured response returned by the health-check tool."""

    model_config = ConfigDict(frozen=True)

    status: Literal["healthy"] = "healthy"

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
    """Build the health-check result independently of MCP transport."""

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
    settings: Settings,
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

        result = build_health_check_result(settings)

        logger.info(
            "health_check_completed",
            status=result.status,
            environment=result.environment,
            transport=result.transport,
        )

        return result
