"""Tests for canonical paper deduplication."""

from __future__ import annotations

from tests.unit.services.search.helpers import build_paper

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.services.search.deduplicator import (
    PaperDeduplicator,
)


def test_deduplicates_by_doi() -> None:
    """DOI should be the strongest duplicate identifier."""

    semantic_paper = build_paper(
        title="Paper from Semantic Scholar",
        source=ProviderName.SEMANTIC_SCHOLAR,
        doi="10.1000/example",
        corpus_id=1,
        abstract="Short abstract.",
        citation_count=10,
    )
    arxiv_paper = build_paper(
        title="Paper from arXiv",
        source=ProviderName.ARXIV,
        doi="10.1000/example",
        arxiv_id="2401.00001",
        abstract="A much longer and more complete abstract.",
        citation_count=20,
    )

    result = PaperDeduplicator().deduplicate(
        (
            semantic_paper,
            arxiv_paper,
        )
    )

    assert len(result) == 1

    merged = result[0]

    assert merged.sources == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )
    assert merged.abstract == "A much longer and more complete abstract."
    assert merged.citation_count == 20


def test_deduplicates_by_arxiv_id() -> None:
    """Matching arXiv IDs should merge records."""

    first = build_paper(
        title="First Title",
        source=ProviderName.SEMANTIC_SCHOLAR,
        arxiv_id="2401.00001",
    )
    second = build_paper(
        title="Second Title",
        source=ProviderName.ARXIV,
        arxiv_id="2401.00001",
    )

    result = PaperDeduplicator().deduplicate(
        (
            first,
            second,
        )
    )

    assert len(result) == 1
    assert result[0].sources == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )


def test_deduplicates_by_semantic_scholar_id() -> None:
    """Matching Semantic Scholar IDs should merge records."""

    semantic_scholar_id = "0796f6cd7f0403f4f5c1d1fdc9f7a3f1fdb4c5e0"

    first = build_paper(
        title="First Metadata Record",
        source=ProviderName.SEMANTIC_SCHOLAR,
        semantic_scholar_id=semantic_scholar_id,
    )
    second = build_paper(
        title="Second Metadata Record",
        source=ProviderName.ARXIV,
        semantic_scholar_id=semantic_scholar_id,
    )

    result = PaperDeduplicator().deduplicate(
        (
            first,
            second,
        )
    )

    assert len(result) == 1


def test_deduplicates_by_normalized_title_and_year() -> None:
    """Title and year should provide the final fallback key."""

    first = build_paper(
        title="Retrieval-Augmented Generation: A Survey",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=100,
        year=2024,
    )
    second = build_paper(
        title="Retrieval Augmented Generation A Survey",
        source=ProviderName.ARXIV,
        corpus_id=200,
        year=2024,
    )

    result = PaperDeduplicator().deduplicate(
        (
            first,
            second,
        )
    )

    assert len(result) == 1
    assert result[0].sources == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )


def test_does_not_merge_same_title_from_different_years() -> None:
    """Different publication years should remain separate."""

    first = build_paper(
        title="Shared Research Title",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=1,
        year=2023,
    )
    second = build_paper(
        title="Shared Research Title",
        source=ProviderName.ARXIV,
        corpus_id=2,
        year=2024,
    )

    result = PaperDeduplicator().deduplicate(
        (
            first,
            second,
        )
    )

    assert result == (
        first,
        second,
    )


def test_preserves_nonduplicate_input_order() -> None:
    """Nonduplicate papers should preserve insertion order."""

    first = build_paper(
        title="First Paper",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=1,
    )
    second = build_paper(
        title="Second Paper",
        source=ProviderName.ARXIV,
        arxiv_id="2401.00002",
    )

    result = PaperDeduplicator().deduplicate(
        (
            first,
            second,
        )
    )

    assert result == (
        first,
        second,
    )
