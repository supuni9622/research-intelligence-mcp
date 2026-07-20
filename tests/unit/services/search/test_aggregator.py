"""Tests for provider-result aggregation."""

from __future__ import annotations

from tests.unit.services.search.helpers import (
    build_paper,
    build_result,
)

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    ProviderFailure,
    SearchResult,
)
from research_intelligence_mcp.services.search.aggregator import (
    SearchResultAggregator,
)


def test_combines_provider_results() -> None:
    """Papers and provider metadata should be combined."""

    semantic_paper = build_paper(
        title="Semantic Paper",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=1,
    )
    arxiv_paper = build_paper(
        title="arXiv Paper",
        source=ProviderName.ARXIV,
        arxiv_id="2401.00001",
    )

    semantic_result = build_result(
        provider=ProviderName.SEMANTIC_SCHOLAR,
        papers=(semantic_paper,),
        total=10,
    )
    arxiv_result = build_result(
        provider=ProviderName.ARXIV,
        papers=(arxiv_paper,),
        total=20,
        has_more=True,
    )

    aggregated = SearchResultAggregator().aggregate(
        (
            semantic_result,
            arxiv_result,
        )
    )

    assert aggregated.papers == (
        semantic_paper,
        arxiv_paper,
    )
    assert aggregated.providers_requested == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )
    assert aggregated.providers_succeeded == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )
    assert aggregated.total == 30
    assert aggregated.has_more is True


def test_aggregates_failures_and_warnings() -> None:
    """Failures and warnings should survive aggregation."""

    successful_result = build_result(
        provider=ProviderName.SEMANTIC_SCHOLAR,
        warnings=(
            "Provider warning.",
            "Shared warning.",
        ),
    )

    failed_result = SearchResult(
        query="retrieval augmented generation",
        papers=(),
        pagination=PaginationMetadata(
            offset=0,
            limit=10,
            returned=0,
            total=None,
            has_more=False,
        ),
        providers_requested=(ProviderName.ARXIV,),
        providers_succeeded=(),
        failures=(
            ProviderFailure(
                provider=ProviderName.ARXIV,
                code="provider_unavailable",
                message="Provider unavailable.",
                retryable=True,
            ),
        ),
        warnings=(
            "Shared warning.",
            "Failure warning.",
        ),
    )

    aggregated = SearchResultAggregator().aggregate(
        (
            successful_result,
            failed_result,
        )
    )

    assert len(aggregated.failures) == 1
    assert aggregated.failures[0].provider == ProviderName.ARXIV
    assert aggregated.warnings == (
        "Provider warning.",
        "Shared warning.",
        "Failure warning.",
    )


def test_deduplicates_provider_metadata() -> None:
    """Repeated provider metadata should appear only once."""

    first = build_result(
        provider=ProviderName.ARXIV,
    )
    second = build_result(
        provider=ProviderName.ARXIV,
    )

    aggregated = SearchResultAggregator().aggregate(
        (
            first,
            second,
        )
    )

    assert aggregated.providers_requested == (ProviderName.ARXIV,)
    assert aggregated.providers_succeeded == (ProviderName.ARXIV,)


def test_returns_unknown_total_when_no_provider_reports_total() -> None:
    """Unknown provider totals should remain unknown."""

    result = SearchResult(
        query="retrieval augmented generation",
        papers=(),
        pagination=PaginationMetadata(
            offset=0,
            limit=10,
            returned=0,
            total=None,
            has_more=False,
        ),
        providers_requested=(ProviderName.ARXIV,),
        providers_succeeded=(ProviderName.ARXIV,),
        failures=(),
        warnings=(),
    )

    aggregated = SearchResultAggregator().aggregate((result,))

    assert aggregated.total is None
