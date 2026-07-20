"""Tests for arXiv canonical response mapping."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from research_intelligence_mcp.domain.enums import (
    AccessStatus,
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.domain.requests import SearchRequest
from research_intelligence_mcp.providers.arxiv.mapper import ArxivMapper
from research_intelligence_mcp.providers.arxiv.models import (
    ArxivEntryResponse,
    ArxivFeedResponse,
)
from research_intelligence_mcp.providers.errors import ProviderResponseError


def build_entry(**overrides: object) -> ArxivEntryResponse:
    """Build a valid arXiv entry for mapper tests."""

    payload: dict[str, object] = {
        "id": "https://arxiv.org/abs/2401.12345v3",
        "title": "Retrieval-Augmented Generation for Research",
        "summary": "A paper about retrieval-augmented generation.",
        "published": "2024-01-15T08:00:00Z",
        "updated": "2024-03-05T12:30:00Z",
        "authors": [
            {
                "name": "Ada Researcher",
                "affiliations": ["Example University", "AI Lab"],
            }
        ],
        "links": [
            {
                "href": "https://arxiv.org/abs/2401.12345v3",
                "rel": "alternate",
                "type": "text/html",
            },
            {
                "href": "https://arxiv.org/pdf/2401.12345v3",
                "rel": "related",
                "type": "application/pdf",
                "title": "pdf",
            },
        ],
        "categories": [{"term": "cs.IR"}, {"term": "cs.CL"}],
        "primary_category": {"term": "cs.IR"},
        "journal_reference": "Journal of Research Systems 10 (2024)",
        "doi": "10.1000/example-rag",
    }
    payload.update(overrides)
    return ArxivEntryResponse.model_validate(payload)


def test_maps_entry_to_canonical_paper() -> None:
    paper = ArxivMapper.to_paper(build_entry())

    assert paper.identifiers.arxiv_id == "2401.12345"
    assert paper.identifiers.doi == "10.1000/example-rag"
    assert paper.title == "Retrieval-Augmented Generation for Research"
    assert paper.abstract == "A paper about retrieval-augmented generation."
    assert paper.publication_date == datetime(2024, 1, 15, 8, 0, tzinfo=UTC).date()
    assert paper.year == 2024
    assert paper.venue == "Journal of Research Systems 10 (2024)"
    assert paper.fields_of_study == ("cs.IR", "cs.CL")
    assert paper.citation_count is None
    assert paper.reference_count is None
    assert paper.sources == (ProviderName.ARXIV,)


def test_maps_author_and_affiliations() -> None:
    paper = ArxivMapper.to_paper(build_entry())

    assert paper.authors[0].name == "Ada Researcher"
    assert paper.authors[0].affiliations == ("Example University", "AI Lab")
    assert paper.authors[0].semantic_scholar_id is None


def test_maps_open_access_urls() -> None:
    paper = ArxivMapper.to_paper(build_entry())

    assert paper.access.status == AccessStatus.OPEN_ACCESS
    assert paper.access.repository == ProviderName.ARXIV
    assert str(paper.access.landing_page_url) == "https://arxiv.org/abs/2401.12345v3"
    assert str(paper.access.pdf_url) == "https://arxiv.org/pdf/2401.12345v3"


def test_builds_fallback_pdf_url() -> None:
    entry = build_entry(
        links=[
            {
                "href": "https://arxiv.org/abs/2401.12345v3",
                "rel": "alternate",
                "type": "text/html",
            }
        ]
    )

    paper = ArxivMapper.to_paper(entry)

    assert str(paper.access.pdf_url) == "https://arxiv.org/pdf/2401.12345"


def test_uses_arxiv_as_fallback_venue() -> None:
    paper = ArxivMapper.to_paper(build_entry(journal_reference=None))
    assert paper.venue == "arXiv"


def test_uses_updated_date_when_published_is_missing() -> None:
    paper = ArxivMapper.to_paper(
        build_entry(published=None, updated="2025-02-10T09:15:00Z")
    )

    assert paper.publication_date == datetime(2025, 2, 10, 9, 15, tzinfo=UTC).date()
    assert paper.year == 2025


def test_ignores_invalid_doi() -> None:
    paper = ArxivMapper.to_paper(build_entry(doi="not-a-doi"))

    assert paper.identifiers.doi is None
    assert paper.identifiers.arxiv_id == "2401.12345"


def test_deduplicates_primary_and_secondary_categories() -> None:
    paper = ArxivMapper.to_paper(
        build_entry(
            categories=[{"term": "cs.IR"}, {"term": "CS.ir"}, {"term": "cs.CL"}],
            primary_category={"term": "cs.IR"},
        )
    )

    assert paper.fields_of_study == ("cs.IR", "cs.CL")


def test_maps_search_result_pagination() -> None:
    request = SearchRequest(
        query="retrieval augmented generation",
        providers=(ProviderName.ARXIV,),
        limit=10,
        offset=20,
    )
    response = ArxivFeedResponse(
        total_results=100,
        start_index=20,
        items_per_page=1,
        entries=[build_entry()],
    )

    result = ArxivMapper.to_search_result(request=request, response=response)

    assert len(result.papers) == 1
    assert result.pagination.offset == 20
    assert result.pagination.returned == 1
    assert result.pagination.total == 100
    assert result.pagination.has_more is True
    assert result.providers_succeeded == (ProviderName.ARXIV,)


def test_maps_empty_search_result() -> None:
    request = SearchRequest(
        query="nonexistent research topic",
        providers=(ProviderName.ARXIV,),
    )
    response = ArxivFeedResponse(
        total_results=0,
        start_index=0,
        items_per_page=0,
        entries=[],
    )

    result = ArxivMapper.to_search_result(request=request, response=response)

    assert result.papers == ()
    assert result.pagination.returned == 0
    assert result.pagination.total == 0
    assert result.pagination.has_more is False


def test_adds_warning_for_citation_count_sort() -> None:
    request = SearchRequest(
        query="retrieval augmented generation",
        providers=(ProviderName.ARXIV,),
        sort=SearchSort.CITATION_COUNT,
    )
    response = ArxivFeedResponse(
        total_results=1,
        start_index=0,
        items_per_page=1,
        entries=[build_entry()],
    )

    result = ArxivMapper.to_search_result(request=request, response=response)

    assert result.warnings == (
    (
        "arXiv does not support citation-count sorting; "
        "results were ordered by relevance."
    ),
)


def test_rejects_invalid_entry_identifier() -> None:
    entry = build_entry(id="https://example.test/not-an-arxiv-paper")

    with pytest.raises(ProviderResponseError) as error_info:
        ArxivMapper.to_paper(entry)

    assert error_info.value.code == "arxiv_invalid_entry_identifier"
