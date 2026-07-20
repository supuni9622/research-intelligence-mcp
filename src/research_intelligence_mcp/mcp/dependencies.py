"""Application dependency container.

The container owns dependencies shared by MCP tools. Dependencies are created
outside the tool layer and passed explicitly into tool registration functions.

As the project grows, this container will own provider clients, caches,
rate limiters, and application services.
"""

from dataclasses import dataclass

from research_intelligence_mcp.config.settings import Settings


@dataclass(frozen=True, slots=True)
class AppDependencies:
    """Dependencies available to the MCP server and its tools."""

    settings: Settings


def build_dependencies(settings: Settings) -> AppDependencies:
    """Build the application dependency container.

    Args:
        settings: Validated application configuration.

    Returns:
        An immutable container holding application dependencies.
    """

    return AppDependencies(settings=settings)
