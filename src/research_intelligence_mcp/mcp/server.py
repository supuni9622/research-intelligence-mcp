"""FastMCP server construction."""

from mcp.server.fastmcp import FastMCP

from research_intelligence_mcp.mcp.dependencies import AppDependencies
from research_intelligence_mcp.mcp.tools.health import register_health_tools


def create_mcp_server(
    dependencies: AppDependencies,
) -> FastMCP:
    """Create and configure the Research Intelligence MCP server.

    Args:
        dependencies: Dependencies shared by the server's tool registrations.

    Returns:
        A fully configured FastMCP server.
    """

    settings = dependencies.settings

    server = FastMCP(
        name=settings.mcp_server_name,
        instructions=(
            "Research Intelligence MCP provides provider-neutral tools for "
            "academic paper discovery, metadata retrieval, citation graph "
            "navigation, related-paper discovery, and open-access resolution. "
            "Use health_check to verify that the server is operational."
        ),
    )

    register_health_tools(
        server=server,
        dependencies=dependencies,
    )

    return server
