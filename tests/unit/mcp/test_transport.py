"""Tests for transport selection and streamable-http startup wiring."""

from __future__ import annotations

from typing import Any, ClassVar

import anyio
import pytest

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.lifecycle import (
    LifecycleState,
    LifespanShutdownMiddleware,
)
from research_intelligence_mcp.infrastructure.observability.http_middleware import (
    HttpMetricsMiddleware,
)
from research_intelligence_mcp.mcp import transport as transport_module
from research_intelligence_mcp.mcp.dependencies import build_dependencies
from research_intelligence_mcp.mcp.server import create_mcp_server
from research_intelligence_mcp.mcp.transport import run_server


class StubStdioServer:
    """Records the transport passed to ``run`` without starting anything."""

    def __init__(self) -> None:
        self.run_calls: list[str] = []

    def run(self, transport: str) -> None:
        self.run_calls.append(transport)


class StubUvicornServer:
    """Stands in for ``uvicorn.Server`` so tests never bind a real socket."""

    instances: ClassVar[list[StubUvicornServer]] = []

    def __init__(self, config: Any) -> None:
        self.config = config
        self.serve_calls = 0
        StubUvicornServer.instances.append(self)

    async def serve(self) -> None:
        self.serve_calls += 1


def test_run_server_stdio_delegates_to_fastmcp_run() -> None:
    """stdio transport should call FastMCP's own stdio runner unchanged."""

    settings = Settings(
        _env_file=None,
        APP_ENVIRONMENT="test",
        MCP_TRANSPORT="stdio",
    )
    lifecycle = LifecycleState()
    stub_server = StubStdioServer()

    run_server(
        server=stub_server,  # type: ignore[arg-type]
        dependencies=object(),  # type: ignore[arg-type]
        settings=settings,
        lifecycle=lifecycle,
    )

    assert stub_server.run_calls == ["stdio"]


def test_run_server_streamable_http_configures_uvicorn_with_wrapped_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """streamable-http should serve a metrics- and shutdown-wrapped app."""

    StubUvicornServer.instances = []
    monkeypatch.setattr(transport_module.uvicorn, "Server", StubUvicornServer)

    settings = Settings(
        _env_file=None,
        APP_ENVIRONMENT="test",
        MCP_TRANSPORT="streamable-http",
        MCP_HOST="127.0.0.1",
        MCP_PORT=9321,
    )
    dependencies = build_dependencies(settings=settings)
    lifecycle = LifecycleState()
    server = create_mcp_server(dependencies=dependencies, lifecycle=lifecycle)

    try:
        run_server(
            server=server,
            dependencies=dependencies,
            settings=settings,
            lifecycle=lifecycle,
        )
    finally:
        anyio.run(dependencies.close)

    assert len(StubUvicornServer.instances) == 1
    instance = StubUvicornServer.instances[0]

    assert instance.serve_calls == 1
    assert instance.config.host == "127.0.0.1"
    assert instance.config.port == 9321
    assert isinstance(instance.config.app, HttpMetricsMiddleware)
    assert isinstance(instance.config.app._app, LifespanShutdownMiddleware)
