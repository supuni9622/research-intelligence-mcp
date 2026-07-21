"""FastMCP server construction."""

from mcp.server.fastmcp import FastMCP

from research_intelligence_mcp.mcp.dependencies import (
    AppDependencies,
)
from research_intelligence_mcp.mcp.tools.health import (
    register_health_tools,
)
from research_intelligence_mcp.mcp.tools.paper import (
    register_paper_tools,
)
from research_intelligence_mcp.mcp.tools.search import (
    register_search_tools,
)


def create_mcp_server(
    dependencies: AppDependencies,
) -> FastMCP:
    """Create and configure the Research Intelligence MCP server.

    Args:
        dependencies:
            Long-lived application dependencies shared by registered tools.

    Returns:
        A fully configured FastMCP server with health and academic research
        discovery capabilities.
    """

    settings = dependencies.settings

    server = FastMCP(
        name=settings.mcp_server_name,
        instructions=(
            "Research Intelligence MCP provides provider-neutral academic "
            "research tools backed by Semantic Scholar and arXiv. "
            "Use search_papers to discover academic literature by topic, "
            "keywords, title, author, publication year, or academic field. "
            "The search tool can query one or both providers, merges duplicate "
            "papers, preserves source provenance, and reports partial provider "
            "failures without discarding successful results. "
            "Use health_check only to verify server availability. "
            "The server retrieves structured research metadata; it does not "
            "perform autonomous research synthesis or generate reports."
        ),
    )

    register_health_tools(
        server=server,
        dependencies=dependencies,
    )

    register_search_tools(
        server=server,
        dependencies=dependencies,
    )
    register_paper_tools(
    server=server,
    dependencies=dependencies,
    )

    return server
