"""Application dependency composition for the MCP server."""

from __future__ import annotations

from dataclasses import dataclass

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.providers.semantic_scholar.create import (
    create_semantic_scholar_provider,
)
from research_intelligence_mcp.providers.semantic_scholar.provider import (
    SemanticScholarProvider,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AppDependencies:
    """Long-lived dependencies shared by MCP tools."""

    settings: Settings
    semantic_scholar_provider: SemanticScholarProvider

    async def close(self) -> None:
        """Release managed provider resources."""

        await self.semantic_scholar_provider.close()


def build_dependencies(
    *,
    settings: Settings,
) -> AppDependencies:
    """Build application dependencies.

    This function retains the existing `build_dependencies` name used by
    the application entry point.
    """

    return AppDependencies(
        settings=settings,
        semantic_scholar_provider=(create_semantic_scholar_provider(settings)),
    )


def create_dependencies(
    *,
    settings: Settings,
) -> AppDependencies:
    """Create dependencies using the canonical composition function.

    This alias supports code that prefers the `create_*` naming convention.
    """

    return build_dependencies(settings=settings)
