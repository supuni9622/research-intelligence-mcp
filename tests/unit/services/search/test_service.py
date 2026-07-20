"""Tests for federated search orchestration."""

from __future__ import annotations

import pytest
from tests.unit.services.search.helpers import (
    StubProvider,
    build_paper,
    build_provider_error,
    build_request,
    build_result,
)

from research_intelligence_mcp.domain.enums import ProviderName
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


def build_service(
    *providers: StubProvider,
) -> FederatedSearchService:
    """Build a complete federated search service."""

    registry = ProviderRegistry(providers=providers)

    return FederatedSearchService(
        executor=ProviderExecutor(
            registry=registry,
        ),
        aggregator=SearchResultAggregator(),
        deduplicator=PaperDeduplicator(),
        ranker=ResultRanker(),
    )


@pytest.mark.asyncio
async def test_runs_complete_federated_search_flow() -> None:
    """Service should execute, aggregate, rank, and paginate."""

    lower_ranked = build_paper(
        title="Lower Ranked",
        source=ProviderName.ARXIV,
        arxiv_id="2401.00001",
        citation_count=5,
    )
    higher_ranked = build_paper(
        title="Higher Ranked",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=2,
        citation_count=50,
    )

    semantic_scholar = StubProvider(
        name=ProviderName.SEMANTIC_SCHOLAR,
        result=build_result(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            papers=(higher_ranked,),
        ),
    )
    arxiv = StubProvider(
        name=ProviderName.ARXIV,
        result=build_result(
            provider=ProviderName.ARXIV,
            papers=(lower_ranked,),
        ),
    )

    result = await build_service(
        semantic_scholar,
        arxiv,
    ).search(build_request())

    assert result.papers == (
        higher_ranked,
        lower_ranked,
    )
    assert result.pagination.returned == 2
    assert result.providers_succeeded == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )


@pytest.mark.asyncio
async def test_deduplicates_cross_provider_results() -> None:
    """The same DOI from two providers should produce one paper."""

    semantic_version = build_paper(
        title="RAG Paper",
        source=ProviderName.SEMANTIC_SCHOLAR,
        doi="10.1000/rag",
        corpus_id=1,
        citation_count=10,
    )
    arxiv_version = build_paper(
        title="RAG Paper",
        source=ProviderName.ARXIV,
        doi="10.1000/rag",
        arxiv_id="2401.00001",
        citation_count=20,
    )

    semantic_scholar = StubProvider(
        name=ProviderName.SEMANTIC_SCHOLAR,
        result=build_result(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            papers=(semantic_version,),
        ),
    )
    arxiv = StubProvider(
        name=ProviderName.ARXIV,
        result=build_result(
            provider=ProviderName.ARXIV,
            papers=(arxiv_version,),
        ),
    )

    result = await build_service(
        semantic_scholar,
        arxiv,
    ).search(build_request())

    assert len(result.papers) == 1
    assert result.papers[0].sources == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )
    assert result.papers[0].citation_count == 20


@pytest.mark.asyncio
async def test_preserves_successful_results_during_partial_failure() -> None:
    """One failed provider should not discard successful papers."""

    paper = build_paper(
        title="Successful Paper",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=1,
    )

    semantic_scholar = StubProvider(
        name=ProviderName.SEMANTIC_SCHOLAR,
        result=build_result(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            papers=(paper,),
        ),
    )
    arxiv = StubProvider(
        name=ProviderName.ARXIV,
        error=build_provider_error(
            provider=ProviderName.ARXIV,
        ),
    )

    result = await build_service(
        semantic_scholar,
        arxiv,
    ).search(build_request())

    assert result.papers == (paper,)
    assert result.providers_succeeded == (ProviderName.SEMANTIC_SCHOLAR,)
    assert len(result.failures) == 1
    assert result.failures[0].provider == ProviderName.ARXIV


@pytest.mark.asyncio
async def test_enforces_final_result_limit() -> None:
    """Final combined results should respect request.limit."""

    papers = tuple(
        build_paper(
            title=f"Paper {index}",
            source=ProviderName.SEMANTIC_SCHOLAR,
            corpus_id=index + 1,
            citation_count=index,
        )
        for index in range(5)
    )

    provider = StubProvider(
        name=ProviderName.SEMANTIC_SCHOLAR,
        result=build_result(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            papers=papers,
            total=5,
        ),
    )

    result = await build_service(provider).search(
        build_request(
            providers=(ProviderName.SEMANTIC_SCHOLAR,),
            limit=2,
        )
    )

    assert len(result.papers) == 2
    assert result.pagination.limit == 2
    assert result.pagination.returned == 2
    assert result.pagination.has_more is True


@pytest.mark.asyncio
async def test_search_is_deterministic() -> None:
    """Equivalent searches should return identical ordering."""

    papers = (
        build_paper(
            title="Beta",
            source=ProviderName.ARXIV,
            arxiv_id="2401.00001",
            citation_count=10,
        ),
        build_paper(
            title="Alpha",
            source=ProviderName.ARXIV,
            arxiv_id="2401.00002",
            citation_count=10,
        ),
    )

    provider = StubProvider(
        name=ProviderName.ARXIV,
        result=build_result(
            provider=ProviderName.ARXIV,
            papers=papers,
        ),
    )

    service = build_service(provider)
    request = build_request(providers=(ProviderName.ARXIV,))

    first = await service.search(request)
    second = await service.search(request)

    assert first.papers == second.papers
    assert tuple(paper.title for paper in first.papers) == (
        "Alpha",
        "Beta",
    )
