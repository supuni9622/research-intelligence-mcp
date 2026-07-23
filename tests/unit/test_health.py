"""Tests for the health-check tool and HTTP health/ready routes."""

from datetime import UTC

from starlette.testclient import TestClient

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.lifecycle import LifecycleState
from research_intelligence_mcp.mcp.dependencies import build_dependencies
from research_intelligence_mcp.mcp.server import create_mcp_server
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


def _build_streamable_http_app(
    lifecycle: LifecycleState | None = None,
) -> tuple[TestClient, LifecycleState]:
    """Build a Starlette app exposing /health and /ready for HTTP tests."""

    settings = Settings(_env_file=None, APP_ENVIRONMENT="test")
    dependencies = build_dependencies(settings=settings)
    lifecycle = lifecycle or LifecycleState()

    server = create_mcp_server(dependencies=dependencies, lifecycle=lifecycle)

    return TestClient(server.streamable_http_app()), lifecycle


def test_http_health_route_never_requires_authentication_and_is_minimal() -> None:
    """The /health route should return a minimal, unauthenticated payload."""

    client, _ = _build_streamable_http_app()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "research-intelligence-mcp",
        "version": "0.1.0",
    }


def test_http_ready_route_reports_ready_by_default() -> None:
    """The /ready route should report ready when no shutdown has occurred."""

    client, _ = _build_streamable_http_app()

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "research-intelligence-mcp",
        "checks": {
            "settings": "ready",
            "dependencies": "ready",
            "providers": "ready",
        },
    }


def test_http_ready_route_reports_not_ready_during_shutdown() -> None:
    """The /ready route should return 503 once shutdown has been marked."""

    lifecycle = LifecycleState()
    client, lifecycle = _build_streamable_http_app(lifecycle)

    lifecycle.mark_shutting_down()

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "research-intelligence-mcp",
        "checks": {"dependencies": "not_ready"},
    }
