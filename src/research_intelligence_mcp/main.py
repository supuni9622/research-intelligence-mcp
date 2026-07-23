"""Research Intelligence MCP application entry point."""

import anyio

from research_intelligence_mcp.config.settings import (
    get_settings,
)
from research_intelligence_mcp.infrastructure.lifecycle import (
    LifecycleState,
)
from research_intelligence_mcp.infrastructure.logging import (
    configure_logging,
    get_logger,
)
from research_intelligence_mcp.mcp.dependencies import (
    build_dependencies,
)
from research_intelligence_mcp.mcp.server import (
    create_mcp_server,
)
from research_intelligence_mcp.mcp.transport import (
    run_server,
)


def main() -> None:
    """Configure dependencies and run the MCP server."""

    settings = get_settings()

    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    logger = get_logger(__name__)

    dependencies = build_dependencies(settings=settings)
    lifecycle = LifecycleState()

    server = create_mcp_server(
        dependencies=dependencies,
        lifecycle=lifecycle,
    )

    logger.info(
        "mcp_server_starting",
        server_name=(settings.mcp_server_name),
        version=settings.app_version,
        environment=(settings.app_environment),
        transport=settings.mcp_transport,
        auth_enabled=settings.auth_enabled,
    )

    try:
        run_server(
            server=server,
            dependencies=dependencies,
            settings=settings,
            lifecycle=lifecycle,
        )
    except KeyboardInterrupt:
        logger.info(
            "mcp_server_stopped",
            reason="keyboard_interrupt",
        )
    finally:
        # The streamable-http transport closes dependencies itself from its
        # ASGI lifespan shutdown handler (LifespanShutdownMiddleware), since
        # that is the only place graceful shutdown can be observed for that
        # transport. stdio has no such hook, so close explicitly here.
        if settings.mcp_transport == "stdio":
            anyio.run(dependencies.close)

        logger.info("mcp_server_shutdown_complete")


if __name__ == "__main__":
    main()


# Startup flow

# main()
#   │
#   ├── load settings
#   ├── configure stderr logging
#   ├── build dependency container
#   ├── create lifecycle state
#   ├── create FastMCP server, register tools + health/ready/metrics routes
#   ├── run selected transport (stdio, or streamable-http via uvicorn)
#   └── close dependencies on shutdown
