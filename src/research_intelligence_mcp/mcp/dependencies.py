"""Application dependency composition for the MCP server."""

from __future__ import annotations

from dataclasses import dataclass

from research_intelligence_mcp.config.settings import (
    Settings,
)
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
from research_intelligence_mcp.services.search.aggregator import (
    SearchResultAggregator,
)
from research_intelligence_mcp.services.search.deduplicator import (
    PaperDeduplicator,
)
from research_intelligence_mcp.services.search.executor import (
    ProviderExecutor,
)
from research_intelligence_mcp.services.search.provider_registry import (
    ProviderRegistry,
)
from research_intelligence_mcp.services.search.ranker import (
    ResultRanker,
)
from research_intelligence_mcp.services.search.service import (
    FederatedSearchService,
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

    provider_registry: ProviderRegistry
    provider_executor: ProviderExecutor
    search_result_aggregator: SearchResultAggregator
    paper_deduplicator: PaperDeduplicator
    result_ranker: ResultRanker

    federated_search_service: FederatedSearchService

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
    """Build the complete application dependency graph."""

    semantic_scholar_provider = create_semantic_scholar_provider(settings)

    arxiv_provider = create_arxiv_provider(settings)

    provider_registry = ProviderRegistry(
        providers=(
            semantic_scholar_provider,
            arxiv_provider,
        )
    )

    provider_executor = ProviderExecutor(
        registry=provider_registry,
    )

    search_result_aggregator = SearchResultAggregator()

    paper_deduplicator = PaperDeduplicator()

    result_ranker = ResultRanker()

    federated_search_service = FederatedSearchService(
        executor=provider_executor,
        aggregator=search_result_aggregator,
        deduplicator=paper_deduplicator,
        ranker=result_ranker,
    )

    return AppDependencies(
        settings=settings,
        semantic_scholar_provider=(semantic_scholar_provider),
        arxiv_provider=arxiv_provider,
        provider_registry=provider_registry,
        provider_executor=provider_executor,
        search_result_aggregator=(search_result_aggregator),
        paper_deduplicator=paper_deduplicator,
        result_ranker=result_ranker,
        federated_search_service=(federated_search_service),
    )


def create_dependencies(
    *,
    settings: Settings,
) -> AppDependencies:
    """Create dependencies using the canonical composition function."""

    return build_dependencies(settings=settings)
