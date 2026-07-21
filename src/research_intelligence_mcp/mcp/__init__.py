"""MCP tool registration and execution functions."""

from research_intelligence_mcp.mcp.tools.health import (
    register_health_tools,
)
from research_intelligence_mcp.mcp.tools.paper import (
    execute_get_paper,
    execute_get_paper_citations,
    execute_get_paper_references,
    execute_get_related_papers,
    execute_resolve_paper_access,
    register_paper_tools,
)
from research_intelligence_mcp.mcp.tools.search import (
    execute_search_papers,
    register_search_tools,
)

__all__ = [
    "execute_get_paper",
    "execute_get_paper_citations",
    "execute_get_paper_references",
    "execute_get_related_papers",
    "execute_resolve_paper_access",
    "execute_search_papers",
    "register_health_tools",
    "register_paper_tools",
    "register_search_tools",
]
