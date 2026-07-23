"""Transport selection and startup for the Research Intelligence MCP server.

Implements the "Streamable HTTP Transport" and "Graceful Shutdown" milestones
of ``docs/remote_mcp_deployment_prd.md``. The server factory
(``create_mcp_server``) registers every tool and HTTP route exactly once;
this module only decides how to *run* the resulting server for the
configured transport, so ``stdio`` behavior is unchanged from before these
milestones.
"""

from __future__ import annotations

import anyio
import uvicorn
from mcp.server.fastmcp import FastMCP

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.lifecycle import (
    LifecycleState,
    LifespanShutdownMiddleware,
)
from research_intelligence_mcp.infrastructure.logging import get_logger
from research_intelligence_mcp.infrastructure.observability.http_middleware import (
    HttpMetricsMiddleware,
)
from research_intelligence_mcp.mcp.dependencies import AppDependencies

logger = get_logger(__name__)


def run_server(
    *,
    server: FastMCP,
    dependencies: AppDependencies,
    settings: Settings,
    lifecycle: LifecycleState,
) -> None:
    """Run the MCP server using the transport selected by settings.

    ``stdio`` delegates directly to FastMCP's own stdio runner — identical
    to prior behavior. ``streamable-http`` builds FastMCP's Starlette app
    (which already carries ``/mcp`` plus the ``/health``, ``/ready``, and
    ``/metrics`` routes registered by ``create_mcp_server`` via
    ``custom_route``), wraps it with HTTP metrics and shutdown-aware
    middleware, and serves it with uvicorn — mirroring FastMCP's own
    ``run_streamable_http_async`` implementation, since that internal helper
    does not expose a hook for closing application dependencies on
    shutdown.
    """

    if settings.mcp_transport == "stdio":
        server.run(transport="stdio")
        return

    anyio.run(_serve_streamable_http, server, dependencies, settings, lifecycle)


async def _serve_streamable_http(
    server: FastMCP,
    dependencies: AppDependencies,
    settings: Settings,
    lifecycle: LifecycleState,
) -> None:
    """Serve the streamable-http transport until a shutdown signal arrives."""

    app = server.streamable_http_app()

    instrumented_app = HttpMetricsMiddleware(
        LifespanShutdownMiddleware(
            app,
            dependencies=dependencies,
            lifecycle=lifecycle,
        )
    )

    config = uvicorn.Config(
        instrumented_app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=settings.log_level.lower(),
    )
    uvicorn_server = uvicorn.Server(config)

    logger.info(
        "mcp_http_server_listening",
        host=settings.mcp_host,
        port=settings.mcp_port,
        path=server.settings.streamable_http_path,
    )

    await uvicorn_server.serve()
