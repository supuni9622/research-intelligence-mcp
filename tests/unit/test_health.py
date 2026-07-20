"""Tests for the health-check tool."""

from datetime import UTC

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.mcp.tools.health import (
    build_health_check_result,
)


def test_build_health_check_result() -> None:
    """Health result should contain current runtime metadata."""

    settings = Settings(
        _env_file=None,
        APP_NAME="Research Intelligence MCP",
        APP_VERSION="0.1.0",
        APP_ENVIRONMENT="test",
        MCP_SERVER_NAME="research-intelligence-mcp",
        MCP_TRANSPORT="stdio",
    )

    result = build_health_check_result(settings)

    assert result.status == "healthy"
    assert result.service == "Research Intelligence MCP"
    assert result.server_name == "research-intelligence-mcp"
    assert result.version == "0.1.0"
    assert result.environment == "test"
    assert result.transport == "stdio"
    assert result.timestamp.tzinfo is UTC
