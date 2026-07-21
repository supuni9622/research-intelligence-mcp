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
        A fully configured FastMCP server with academic paper discovery,
        metadata retrieval, citation graph, reference graph, recommendation,
        and access-resolution capabilities.
    """

    settings = dependencies.settings

    server = FastMCP(
        name=settings.mcp_server_name,
        instructions=(
            "Research Intelligence MCP provides provider-neutral academic "
            "research tools backed by Semantic Scholar and arXiv. "
            "Use search_papers to discover academic literature by topic, "
            "keywords, title, author, publication year, or academic field. "
            "Use get_paper to retrieve canonical metadata for one paper. "
            "Use get_paper_citations to find papers that cite an origin paper. "
            "Use get_paper_references to retrieve papers referenced by an "
            "origin paper. "
            "Use get_related_papers to discover recommendations related to a "
            "seed paper. "
            "Use resolve_paper_access to determine known access status, "
            "landing-page URLs, PDF URLs, licenses, and repository metadata. "
            "Semantic Scholar supports citation graphs, reference graphs, and "
            "related-paper recommendations. arXiv supports search, individual "
            "paper metadata, and open-access metadata, but does not expose "
            "citation, reference, or recommendation APIs. "
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