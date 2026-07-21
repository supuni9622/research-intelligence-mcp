"""Tests for structured MCP search input schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from research_intelligence_mcp.domain.enums import (
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.mcp.schemas.search import (
    SearchPapersInput,
)


def test_builds_default_federated_search_input() -> None:
    """Both providers should be selected by default."""

    search_input = SearchPapersInput(
        query="retrieval augmented generation"
    )

    assert search_input.query == (
        "retrieval augmented generation"
    )
    assert search_input.providers == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )
    assert search_input.limit == 10
    assert search_input.offset == 0
    assert search_input.fields_of_study == ()
    assert search_input.open_access_only is False
    assert search_input.sort == SearchSort.RELEVANCE


def test_normalizes_query_whitespace() -> None:
    """Repeated query whitespace should be collapsed."""

    search_input = SearchPapersInput(
        query="  retrieval   augmented\n generation  "
    )

    assert search_input.query == (
        "retrieval augmented generation"
    )


def test_deduplicates_providers_in_order() -> None:
    """Duplicate providers should be removed deterministically."""

    search_input = SearchPapersInput(
        query="language models",
        providers=(
            ProviderName.ARXIV,
            ProviderName.SEMANTIC_SCHOLAR,
            ProviderName.ARXIV,
        ),
    )

    assert search_input.providers == (
        ProviderName.ARXIV,
        ProviderName.SEMANTIC_SCHOLAR,
    )


def test_normalizes_fields_of_study() -> None:
    """Field filters should be normalized and deduplicated."""

    search_input = SearchPapersInput(
        query="information retrieval",
        fields_of_study=(
            "  Computer   Science ",
            "computer science",
            "cs.IR",
            "",
        ),
    )

    assert search_input.fields_of_study == (
        "Computer Science",
        "cs.IR",
    )


def test_converts_to_canonical_search_request() -> None:
    """MCP input should convert without losing request information."""

    search_input = SearchPapersInput(
        query="agentic retrieval",
        providers=(ProviderName.ARXIV,),
        limit=5,
        offset=10,
        year_from=2022,
        year_to=2026,
        fields_of_study=("cs.IR",),
        open_access_only=True,
        sort=SearchSort.PUBLICATION_DATE,
    )

    request = search_input.to_domain_request()

    assert request.query == "agentic retrieval"
    assert request.providers == (
        ProviderName.ARXIV,
    )
    assert request.limit == 5
    assert request.offset == 10
    assert request.year_from == 2022
    assert request.year_to == 2026
    assert request.fields_of_study == (
        "cs.IR",
    )
    assert request.open_access_only is True
    assert request.sort == (
        SearchSort.PUBLICATION_DATE
    )


def test_rejects_empty_provider_selection() -> None:
    """At least one provider must be selected."""

    with pytest.raises(
        ValidationError,
        match="At least one search provider",
    ):
        SearchPapersInput(
            query="language models",
            providers=(),
        )


def test_rejects_invalid_year_range() -> None:
    """Earliest year cannot be after latest year."""

    with pytest.raises(
        ValidationError,
        match=(
            "year_from must be less than "
            "or equal to year_to"
        ),
    ):
        SearchPapersInput(
            query="language models",
            year_from=2026,
            year_to=2020,
        )


def test_rejects_limit_above_maximum() -> None:
    """Tool result limits must remain bounded."""

    with pytest.raises(
        ValidationError,
    ) as error_info:
        SearchPapersInput(
            query="language models",
            limit=51,
        )

    errors = error_info.value.errors()

    assert len(errors) == 1
    assert errors[0]["loc"] == (
        "limit",
    )
    assert errors[0]["type"] == (
        "less_than_equal"
    )


def test_rejects_too_short_query() -> None:
    """Queries shorter than two characters should be rejected."""

    with pytest.raises(
        ValidationError,
    ) as error_info:
        SearchPapersInput(
            query=" "
        )

    errors = error_info.value.errors()

    assert len(errors) == 1
    assert errors[0]["loc"] == (
        "query",
    )
    assert errors[0]["type"] == (
        "string_too_short"
    )