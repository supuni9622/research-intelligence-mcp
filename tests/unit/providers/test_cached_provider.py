"""Tests for the caching paper-provider decorator."""

from __future__ import annotations

import pytest

from research_intelligence_mcp.domain.enums import (
    PaperRelationType,
    ProviderName,
)
from research_intelligence_mcp.domain.identifiers import (
    PaperIdentifiers,
)
from research_intelligence_mcp.domain.models import (
    Paper,
    PaperReference,
)
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    SearchRequest,
    SearchResult,
)
from research_intelligence_mcp.infrastructure.cache.ttl import (
    AsyncBoundedTTLCache,
)
from research_intelligence_mcp.infrastructure.observability.metrics import (
    METRICS_REGISTRY,
)
from research_intelligence_mcp.providers.cached import (
    CachedPaperProvider,
)
from research_intelligence_mcp.providers.errors import (
    ProviderTransportError,
)


def build_paper() -> Paper:
    """Build one canonical test paper."""

    return Paper(
        identifiers=PaperIdentifiers(
            arxiv_id="1706.03762",
        ),
        title="Attention Is All You Need",
        sources=(ProviderName.ARXIV,),
    )


def build_search_result(
    request: SearchRequest,
) -> SearchResult:
    """Build one canonical search result."""

    paper = build_paper()

    return SearchResult(
        query=request.query,
        papers=(paper,),
        pagination=PaginationMetadata(
            offset=request.offset,
            limit=request.limit,
            returned=1,
            total=1,
            has_more=False,
        ),
        providers_requested=(ProviderName.ARXIV,),
        providers_succeeded=(ProviderName.ARXIV,),
    )


class StubProvider:
    """Counting provider used for cache tests."""

    name = ProviderName.ARXIV

    def __init__(self) -> None:
        self.search_calls = 0
        self.paper_calls = 0
        self.citation_calls = 0
        self.close_calls = 0
        self.fail_search = False

    async def search_papers(
        self,
        request: SearchRequest,
    ) -> SearchResult:
        """Return one search result or raise a transport error."""

        self.search_calls += 1

        if self.fail_search:
            raise ProviderTransportError(
                provider=self.name,
                code="test_transport_error",
                message="Provider unavailable.",
                retryable=True,
            )

        return build_search_result(request)

    async def get_paper(
        self,
        paper_id: str,
    ) -> Paper:
        """Return one paper."""

        self.paper_calls += 1

        return build_paper()

    async def get_citations(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Return one uncached citation relationship."""

        self.citation_calls += 1

        return [
            PaperReference(
                relation=PaperRelationType.CITATION,
                paper=build_paper(),
            )
        ]

    async def get_references(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Return no references."""

        return []

    async def get_related_papers(
        self,
        paper_id: str,
        *,
        limit: int = 10,
        negative_paper_ids: list[str] | None = None,
    ) -> list[Paper]:
        """Return no related papers."""

        return []

    async def close(self) -> None:
        """Record provider closure."""

        self.close_calls += 1


def build_cached_provider(
    provider: StubProvider,
    *,
    enabled: bool = True,
) -> CachedPaperProvider:
    """Build a cached provider with isolated test caches."""

    return CachedPaperProvider(
        provider=provider,
        search_cache=AsyncBoundedTTLCache(
            max_size=10,
            ttl_seconds=60,
        ),
        paper_cache=AsyncBoundedTTLCache(
            max_size=10,
            ttl_seconds=60,
        ),
        enabled=enabled,
    )


@pytest.mark.asyncio
async def test_search_result_is_cached() -> None:
    """Repeated equivalent searches should execute the provider once."""

    provider = StubProvider()
    cached_provider = build_cached_provider(provider)

    request = SearchRequest(
        query="attention mechanisms",
        providers=(ProviderName.ARXIV,),
    )

    first = await cached_provider.search_papers(request)
    second = await cached_provider.search_papers(request)

    assert first == second
    assert provider.search_calls == 1


@pytest.mark.asyncio
async def test_paper_is_cached() -> None:
    """Repeated paper retrieval should execute the provider once."""

    provider = StubProvider()
    cached_provider = build_cached_provider(provider)

    first = await cached_provider.get_paper("1706.03762")
    second = await cached_provider.get_paper(" 1706.03762 ")

    assert first == second
    assert provider.paper_calls == 1


@pytest.mark.asyncio
async def test_failures_are_not_cached() -> None:
    """Provider errors must not be written into the search cache."""

    provider = StubProvider()
    provider.fail_search = True

    cached_provider = build_cached_provider(provider)

    request = SearchRequest(
        query="temporary provider failure",
        providers=(ProviderName.ARXIV,),
    )

    with pytest.raises(ProviderTransportError):
        await cached_provider.search_papers(request)

    with pytest.raises(ProviderTransportError):
        await cached_provider.search_papers(request)

    assert provider.search_calls == 2


@pytest.mark.asyncio
async def test_disabled_cache_always_calls_provider() -> None:
    """Disabled caching should bypass cache reads and writes."""

    provider = StubProvider()

    cached_provider = build_cached_provider(
        provider,
        enabled=False,
    )

    request = SearchRequest(
        query="attention mechanisms",
        providers=(ProviderName.ARXIV,),
    )

    await cached_provider.search_papers(request)
    await cached_provider.search_papers(request)

    assert provider.search_calls == 2


@pytest.mark.asyncio
async def test_graph_operations_are_not_cached() -> None:
    """Citation operations should delegate on every invocation."""

    provider = StubProvider()
    cached_provider = build_cached_provider(provider)

    await cached_provider.get_citations(
        "1706.03762",
    )

    await cached_provider.get_citations(
        "1706.03762",
    )

    assert provider.citation_calls == 2


@pytest.mark.asyncio
async def test_close_delegates_to_provider() -> None:
    """Closing the decorator should close its wrapped provider."""

    provider = StubProvider()
    cached_provider = build_cached_provider(provider)

    await cached_provider.close()

    assert provider.close_calls == 1


@pytest.mark.asyncio
async def test_search_records_provider_metrics_only_on_cache_miss() -> None:
    """provider_requests_total should count real provider calls, not cache hits."""

    provider = StubProvider()
    cached_provider = build_cached_provider(provider)

    request = SearchRequest(
        query="metrics test query",
        providers=(ProviderName.ARXIV,),
    )

    before = (
        METRICS_REGISTRY.get_sample_value(
            "provider_requests_total",
            {"provider": "arxiv", "operation": "search", "status": "success"},
        )
        or 0.0
    )

    await cached_provider.search_papers(request)
    await cached_provider.search_papers(request)

    after = METRICS_REGISTRY.get_sample_value(
        "provider_requests_total",
        {"provider": "arxiv", "operation": "search", "status": "success"},
    )

    assert after == before + 1.0
    assert provider.search_calls == 1


@pytest.mark.asyncio
async def test_search_failure_records_provider_failure_metric() -> None:
    """A raised provider error should be recorded as a provider failure."""

    provider = StubProvider()
    provider.fail_search = True
    cached_provider = build_cached_provider(provider)

    request = SearchRequest(
        query="metrics failure query",
        providers=(ProviderName.ARXIV,),
    )

    before = (
        METRICS_REGISTRY.get_sample_value(
            "provider_failures_total",
            {
                "provider": "arxiv",
                "operation": "search",
                "error_type": "ProviderTransportError",
            },
        )
        or 0.0
    )

    with pytest.raises(ProviderTransportError):
        await cached_provider.search_papers(request)

    after = METRICS_REGISTRY.get_sample_value(
        "provider_failures_total",
        {
            "provider": "arxiv",
            "operation": "search",
            "error_type": "ProviderTransportError",
        },
    )

    assert after == before + 1.0


@pytest.mark.asyncio
async def test_get_citations_records_provider_result_count() -> None:
    """Uncached graph operations should record provider result counts."""

    provider = StubProvider()
    cached_provider = build_cached_provider(provider)

    before = (
        METRICS_REGISTRY.get_sample_value(
            "provider_results_total",
            {"provider": "arxiv", "operation": "get_citations"},
        )
        or 0.0
    )

    await cached_provider.get_citations("1706.03762")

    after = METRICS_REGISTRY.get_sample_value(
        "provider_results_total",
        {"provider": "arxiv", "operation": "get_citations"},
    )

    assert after == before + 1.0
