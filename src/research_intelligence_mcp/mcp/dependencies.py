"""Application dependency composition for the MCP server."""

from __future__ import annotations

from dataclasses import dataclass

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.providers.arxiv.create import (
    create_arxiv_provider,
)
from research_intelligence_mcp.providers.arxiv.provider import (
    ArxivProvider,
)
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
    arxiv_provider: ArxivProvider

    async def close(self) -> None:
        """Release all managed provider resources."""

        semantic_scholar_error: Exception | None = None

        try:
            await self.semantic_scholar_provider.close()
        except Exception as exc:
            semantic_scholar_error = exc

        try:
            await self.arxiv_provider.close()
        except Exception as arxiv_error:
            if semantic_scholar_error is not None:
                raise ExceptionGroup(
                    "Multiple provider resources failed to close.",
                    [
                        semantic_scholar_error,
                        arxiv_error,
                    ],
                ) from arxiv_error

            raise

        if semantic_scholar_error is not None:
            raise semantic_scholar_error


def build_dependencies(
    *,
    settings: Settings,
) -> AppDependencies:
    """Build application dependencies.

    This function retains the existing ``build_dependencies`` name used by
    the application entry point.
    """

    return AppDependencies(
        settings=settings,
        semantic_scholar_provider=(create_semantic_scholar_provider(settings)),
        arxiv_provider=create_arxiv_provider(settings),
    )


def create_dependencies(
    *,
    settings: Settings,
) -> AppDependencies:
    """Create dependencies using the canonical composition function.

    This alias supports code that prefers the ``create_*`` naming convention.
    """

    return build_dependencies(settings=settings)
