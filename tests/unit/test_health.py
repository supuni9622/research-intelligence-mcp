"""Tests for the health-check tool."""

from datetime import UTC

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.mcp.tools.health import (
    HealthCheckResult,
    build_health_check_result,
)


def test_build_health_check_result() -> None:
    """Health output should contain validated runtime metadata."""

    settings = Settings(
        _env_file=None,
        APP_NAME="Research Intelligence MCP",
        APP_VERSION="0.1.0",
        APP_ENVIRONMENT="test",
        MCP_SERVER_NAME="research-intelligence-mcp",
        MCP_TRANSPORT="stdio",
    )

    result = build_health_check_result(settings=settings)

    assert isinstance(result, HealthCheckResult)
    assert result.status == "healthy"
    assert result.service == "Research Intelligence MCP"
    assert result.server_name == "research-intelligence-mcp"
    assert result.version == "0.1.0"
    assert result.environment == "test"
    assert result.transport == "stdio"
    assert result.timestamp.tzinfo is UTC


def test_health_check_result_serializes_to_expected_shape() -> None:
    """Health output should expose a stable JSON-compatible contract."""

    settings = Settings(
        _env_file=None,
        APP_ENVIRONMENT="test",
    )

    result = build_health_check_result(settings=settings)
    payload = result.model_dump(mode="json")

    assert set(payload) == {
        "status",
        "service",
        "server_name",
        "version",
        "environment",
        "transport",
        "timestamp",
    }

    assert payload["status"] == "healthy"
    assert payload["environment"] == "test"
    assert isinstance(payload["timestamp"], str)
