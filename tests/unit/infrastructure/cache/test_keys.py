"""Tests for deterministic provider cache keys."""

from research_intelligence_mcp.domain.enums import (
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.domain.requests import (
    SearchRequest,
)
from research_intelligence_mcp.infrastructure.cache.keys import (
    build_paper_cache_key,
    build_search_cache_key,
)


def test_equivalent_search_requests_produce_same_key() -> None:
    """Equivalent canonical requests should share a cache key."""

    first = SearchRequest(
        query="retrieval augmented generation",
        providers=(ProviderName.ARXIV,),
        limit=10,
        offset=0,
        year_from=2023,
        fields_of_study=("cs.IR",),
        sort=SearchSort.RELEVANCE,
    )

    second = SearchRequest(
        query="retrieval augmented generation",
        providers=(ProviderName.ARXIV,),
        limit=10,
        offset=0,
        year_from=2023,
        fields_of_study=("cs.IR",),
        sort=SearchSort.RELEVANCE,
    )

    assert build_search_cache_key(
        provider=ProviderName.ARXIV,
        request=first,
    ) == build_search_cache_key(
        provider=ProviderName.ARXIV,
        request=second,
    )


def test_different_providers_produce_different_search_keys() -> None:
    """Provider identity must be part of a search cache key."""

    request = SearchRequest(
        query="large language models",
    )

    arxiv_key = build_search_cache_key(
        provider=ProviderName.ARXIV,
        request=request,
    )

    semantic_scholar_key = build_search_cache_key(
        provider=ProviderName.SEMANTIC_SCHOLAR,
        request=request,
    )

    assert arxiv_key != semantic_scholar_key


def test_search_filters_change_cache_key() -> None:
    """Different search constraints must not share cached results."""

    first = SearchRequest(
        query="large language models",
        year_from=2022,
    )

    second = SearchRequest(
        query="large language models",
        year_from=2024,
    )

    assert build_search_cache_key(
        provider=ProviderName.ARXIV,
        request=first,
    ) != build_search_cache_key(
        provider=ProviderName.ARXIV,
        request=second,
    )


def test_paper_key_normalizes_case_and_whitespace() -> None:
    """Equivalent paper identifiers should share a cache key."""

    first = build_paper_cache_key(
        provider=ProviderName.SEMANTIC_SCHOLAR,
        paper_id=" DOI:10.48550/ARXIV.1706.03762 ",
    )

    second = build_paper_cache_key(
        provider=ProviderName.SEMANTIC_SCHOLAR,
        paper_id="doi:10.48550/arxiv.1706.03762",
    )

    assert first == second


def test_paper_key_is_provider_specific() -> None:
    """The same identifier must remain isolated by provider."""

    arxiv_key = build_paper_cache_key(
        provider=ProviderName.ARXIV,
        paper_id="1706.03762",
    )

    semantic_scholar_key = build_paper_cache_key(
        provider=ProviderName.SEMANTIC_SCHOLAR,
        paper_id="1706.03762",
    )

    assert arxiv_key != semantic_scholar_key
