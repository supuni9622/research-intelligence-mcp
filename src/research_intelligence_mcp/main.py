"""Research Intelligence MCP application entry point."""

from research_intelligence_mcp.config.settings import get_settings
from research_intelligence_mcp.infrastructure.logging import (
    configure_logging,
    get_logger,
)
from research_intelligence_mcp.mcp.dependencies import build_dependencies
from research_intelligence_mcp.mcp.server import create_mcp_server


def main() -> None:
    """Configure dependencies and run the MCP server."""

    settings = get_settings()

    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    logger = get_logger(__name__)

    dependencies = build_dependencies(settings=settings)
    server = create_mcp_server(dependencies=dependencies)

    logger.info(
        "mcp_server_starting",
        server_name=settings.mcp_server_name,
        version=settings.app_version,
        environment=settings.app_environment,
        transport=settings.mcp_transport,
    )

    try:
        server.run(
            transport=settings.mcp_transport,
        )
    except KeyboardInterrupt:
        logger.info(
            "mcp_server_stopped",
            reason="keyboard_interrupt",
        )


# Startup flow

# main()
#   │
#   ├── load settings
#   ├── configure stderr logging
#   ├── build dependency container
#   ├── create FastMCP server
#   ├── register tools
#   └── run stdio transport
