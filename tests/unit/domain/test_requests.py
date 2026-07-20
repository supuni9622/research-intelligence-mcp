"""Tests for canonical search request and response contracts."""

import pytest
from pydantic import ValidationError

from research_intelligence_mcp.domain.enums import (
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.domain.identifiers import PaperIdentifiers
from research_intelligence_mcp.domain.models import Paper
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    ProviderFailure,
    SearchRequest,
    SearchResult,
)


def build_test_paper() -> Paper:
    """Build a minimal valid paper."""

    return Paper(
        identifiers=PaperIdentifiers(
            arxiv_id="2005.11401",
        ),
        title="Retrieval-Augmented Generation",
        sources=(ProviderName.ARXIV,),
    )


def test_search_request_defaults() -> None:
    """Search requests should provide safe bounded defaults."""

    request = SearchRequest(
        query="retrieval augmented generation",
    )

    assert request.providers == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )
    assert request.limit == 10
    assert request.offset == 0
    assert request.sort == SearchSort.RELEVANCE
    assert request.open_access_only is False


def test_search_request_normalizes_query_and_filters() -> None:
    """Search request strings and duplicates should be normalized."""

    request = SearchRequest(
        query="  agentic    RAG  ",
        providers=(
            ProviderName.ARXIV,
            ProviderName.ARXIV,
            ProviderName.SEMANTIC_SCHOLAR,
        ),
        fields_of_study=(
            "Computer Science",
            " computer science ",
            "Artificial Intelligence",
        ),
    )

    assert request.query == "agentic RAG"
    assert request.providers == (
        ProviderName.ARXIV,
        ProviderName.SEMANTIC_SCHOLAR,
    )
    assert request.fields_of_study == (
        "Computer Science",
        "Artificial Intelligence",
    )


def test_search_limit_is_bounded() -> None:
    """Search requests cannot ask for unbounded result counts."""

    with pytest.raises(ValidationError):
        SearchRequest(
            query="RAG",
            limit=51,
        )


def test_invalid_year_range_is_rejected() -> None:
    """year_from cannot be greater than year_to."""

    with pytest.raises(
        ValidationError,
        match="year_from must be less",
    ):
        SearchRequest(
            query="RAG",
            year_from=2025,
            year_to=2020,
        )


def test_pagination_rejects_returned_count_above_limit() -> None:
    """Pagination metadata should remain internally consistent."""

    with pytest.raises(
        ValidationError,
        match="cannot exceed the requested limit",
    ):
        PaginationMetadata(
            offset=0,
            limit=10,
            returned=11,
            total=100,
            has_more=True,
        )


def test_search_result_supports_partial_provider_failure() -> None:
    """One provider may fail without invalidating successful results."""

    paper = build_test_paper()

    result = SearchResult(
        query="retrieval augmented generation",
        papers=(paper,),
        pagination=PaginationMetadata(
            offset=0,
            limit=10,
            returned=1,
            total=None,
            has_more=False,
        ),
        providers_requested=(
            ProviderName.SEMANTIC_SCHOLAR,
            ProviderName.ARXIV,
        ),
        providers_succeeded=(ProviderName.ARXIV,),
        failures=(
            ProviderFailure(
                provider=ProviderName.SEMANTIC_SCHOLAR,
                code="provider_timeout",
                message="Semantic Scholar did not respond in time.",
                retryable=True,
            ),
        ),
    )

    assert len(result.papers) == 1
    assert result.providers_succeeded == (ProviderName.ARXIV,)
    assert result.failures[0].retryable is True


def test_provider_cannot_be_successful_and_failed() -> None:
    """Provider outcomes must not contradict each other."""

    with pytest.raises(
        ValidationError,
        match="both successful and failed",
    ):
        SearchResult(
            query="RAG",
            papers=(),
            pagination=PaginationMetadata(
                offset=0,
                limit=10,
                returned=0,
                total=0,
                has_more=False,
            ),
            providers_requested=(ProviderName.ARXIV,),
            providers_succeeded=(ProviderName.ARXIV,),
            failures=(
                ProviderFailure(
                    provider=ProviderName.ARXIV,
                    code="unexpected_error",
                    message="Unexpected provider error.",
                ),
            ),
        )


def test_pagination_returned_must_match_paper_count() -> None:
    """Search result pagination must match its papers."""

    with pytest.raises(
        ValidationError,
        match="must match the number of papers",
    ):
        SearchResult(
            query="RAG",
            papers=(build_test_paper(),),
            pagination=PaginationMetadata(
                offset=0,
                limit=10,
                returned=0,
                total=1,
                has_more=True,
            ),
            providers_requested=(ProviderName.ARXIV,),
            providers_succeeded=(ProviderName.ARXIV,),
        )
