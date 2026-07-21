"""MCP tool registration functions."""

from research_intelligence_mcp.mcp.tools.health import (
    register_health_tools,
)
from research_intelligence_mcp.mcp.tools.search import (
    execute_search_papers,
    register_search_tools,
)

__all__ = [
    "execute_search_papers",
    "register_health_tools",
    "register_search_tools",
]
