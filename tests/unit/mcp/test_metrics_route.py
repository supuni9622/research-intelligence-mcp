"""Tests for the /metrics HTTP route."""

from __future__ import annotations

from starlette.testclient import TestClient

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.observability.metrics import (
    METRICS_CONTENT_TYPE,
)
from research_intelligence_mcp.mcp.dependencies import build_dependencies
from research_intelligence_mcp.mcp.server import create_mcp_server


def _build_client() -> TestClient:
    settings = Settings(_env_file=None, APP_ENVIRONMENT="test")
    dependencies = build_dependencies(settings=settings)
    server = create_mcp_server(dependencies=dependencies)

    return TestClient(server.streamable_http_app())


def test_metrics_route_returns_prometheus_text_format() -> None:
    """The /metrics route should return Prometheus-exposition-formatted text."""

    client = _build_client()

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"] == METRICS_CONTENT_TYPE
    assert "# HELP mcp_tool_requests_total" in response.text
    assert "# HELP provider_requests_total" in response.text
    assert "# HELP cache_hits_total" in response.text


def test_metrics_route_reflects_current_cache_state() -> None:
    """The /metrics route should refresh cache gauges from live cache stats."""

    settings = Settings(_env_file=None, APP_ENVIRONMENT="test")
    dependencies = build_dependencies(settings=settings)
    server = create_mcp_server(dependencies=dependencies)
    client = TestClient(server.streamable_http_app())

    response = client.get("/metrics")

    assert response.status_code == 200
    assert 'cache_current_entries{cache="search"} 0.0' in response.text
    assert 'cache_current_entries{cache="paper"} 0.0' in response.text
