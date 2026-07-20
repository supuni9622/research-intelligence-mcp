"""FastMCP server construction."""

from mcp.server.fastmcp import FastMCP

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.mcp.tools.health import register_health_tools


def create_mcp_server(settings: Settings) -> FastMCP:
    """Create and configure the Research Intelligence MCP server."""

    server = FastMCP(
        name=settings.mcp_server_name,
        instructions=(
            "Research Intelligence MCP provides tools for academic paper "
            "discovery, metadata retrieval, citation exploration, related-paper "
            "discovery, and open-access resolution."
        ),
    )

    register_health_tools(
        server=server,
        settings=settings,
    )

    return server
