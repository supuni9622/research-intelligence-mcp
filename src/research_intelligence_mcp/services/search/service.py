"""Federated academic-paper search orchestration."""

from __future__ import annotations

from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    SearchRequest,
    SearchResult,
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
from research_intelligence_mcp.services.search.ranker import ResultRanker


class FederatedSearchService:
    """Coordinate multi-provider paper search."""

    def __init__(
        self,
        *,
        executor: ProviderExecutor,
        aggregator: SearchResultAggregator,
        deduplicator: PaperDeduplicator,
        ranker: ResultRanker,
    ) -> None:
        """Initialize the federated search service."""

        self._executor = executor
        self._aggregator = aggregator
        self._deduplicator = deduplicator
        self._ranker = ranker

    async def search(
        self,
        request: SearchRequest,
    ) -> SearchResult:
        """Search providers and return one canonical result."""

        provider_results = await self._executor.execute(request)

        aggregated = self._aggregator.aggregate(provider_results)

        deduplicated = self._deduplicator.deduplicate(aggregated.papers)

        ranked = self._ranker.rank(deduplicated)

        final_papers = ranked[: request.limit]

        has_more = aggregated.has_more or len(ranked) > len(final_papers)

        total = aggregated.total

        if total is not None:
            total = max(total, len(final_papers))

        return SearchResult(
            query=request.query,
            papers=final_papers,
            pagination=PaginationMetadata(
                offset=request.offset,
                limit=request.limit,
                returned=len(final_papers),
                total=total,
                has_more=has_more,
            ),
            providers_requested=aggregated.providers_requested,
            providers_succeeded=aggregated.providers_succeeded,
            failures=aggregated.failures,
            warnings=aggregated.warnings,
        )
