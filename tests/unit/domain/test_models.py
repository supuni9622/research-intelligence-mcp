"""Tests for canonical academic paper models."""

from datetime import date

import pytest
from pydantic import AnyHttpUrl, ValidationError

from research_intelligence_mcp.domain.enums import (
    AccessStatus,
    PaperRelationType,
    ProviderName,
)
from research_intelligence_mcp.domain.identifiers import PaperIdentifiers
from research_intelligence_mcp.domain.models import (
    Author,
    Paper,
    PaperAccess,
    PaperReference,
)


def build_test_paper() -> Paper:
    """Build a valid paper for unit tests."""

    return Paper(
        identifiers=PaperIdentifiers(
            arxiv_id="1706.03762",
        ),
        title="Attention Is All You Need",
        authors=(
            Author(name="Ashish Vaswani"),
            Author(name="Noam Shazeer"),
        ),
        abstract="A sequence transduction architecture based on attention.",
        publication_date=date(2017, 6, 12),
        year=2017,
        venue="NeurIPS",
        fields_of_study=(
            "Computer Science",
            "Machine Learning",
        ),
        citation_count=100_000,
        reference_count=39,
        access=PaperAccess(
            status=AccessStatus.OPEN_ACCESS,
            landing_page_url=AnyHttpUrl("https://arxiv.org/abs/1706.03762"),
            pdf_url=AnyHttpUrl("https://arxiv.org/pdf/1706.03762"),
            repository=ProviderName.ARXIV,
        ),
        sources=(
            ProviderName.ARXIV,
            ProviderName.SEMANTIC_SCHOLAR,
        ),
    )


def test_author_name_and_affiliations_are_normalized() -> None:
    """Author fields should be normalized and deduplicated."""

    author = Author(
        name="  Jane   Doe  ",
        affiliations=(
            "Example University",
            " example university ",
            "Research Lab",
        ),
    )

    assert author.name == "Jane Doe"
    assert author.affiliations == (
        "Example University",
        "Research Lab",
    )


def test_paper_is_created_with_canonical_data() -> None:
    """A complete canonical paper should validate successfully."""

    paper = build_test_paper()

    assert paper.title == "Attention Is All You Need"
    assert paper.year == 2017
    assert len(paper.authors) == 2
    assert paper.access.status == AccessStatus.OPEN_ACCESS
    assert paper.sources == (
        ProviderName.ARXIV,
        ProviderName.SEMANTIC_SCHOLAR,
    )


def test_paper_title_is_normalized() -> None:
    """Repeated title whitespace should be collapsed."""

    paper = build_test_paper().model_copy(
        update={
            "title": "  Attention   Is   All   You   Need  ",
        }
    )

    validated = Paper.model_validate(paper.model_dump())

    assert validated.title == "Attention Is All You Need"


def test_paper_year_must_match_publication_date() -> None:
    """Conflicting publication dates and years should fail."""

    with pytest.raises(
        ValidationError,
        match="Publication date year must match",
    ):
        Paper(
            identifiers=PaperIdentifiers(
                arxiv_id="1706.03762",
            ),
            title="Attention Is All You Need",
            publication_date=date(2017, 6, 12),
            year=2018,
            sources=(ProviderName.ARXIV,),
        )


def test_negative_citation_count_is_rejected() -> None:
    """Citation counts cannot be negative."""

    with pytest.raises(ValidationError):
        Paper(
            identifiers=PaperIdentifiers(
                arxiv_id="1706.03762",
            ),
            title="Attention Is All You Need",
            citation_count=-1,
            sources=(ProviderName.ARXIV,),
        )


def test_closed_access_cannot_have_direct_pdf() -> None:
    """Closed-access records cannot advertise direct PDFs."""

    with pytest.raises(
        ValidationError,
        match="closed-access paper",
    ):
        PaperAccess(
            status=AccessStatus.CLOSED_ACCESS,
            pdf_url=AnyHttpUrl("https://example.com/paper.pdf"),
        )


def test_paper_requires_a_source_provider() -> None:
    """Every canonical paper must retain provider provenance."""

    with pytest.raises(ValidationError):
        Paper(
            identifiers=PaperIdentifiers(
                arxiv_id="1706.03762",
            ),
            title="Attention Is All You Need",
            sources=(),
        )


def test_paper_reference_normalizes_contexts() -> None:
    """Citation contexts and intents should be deduplicated."""

    reference = PaperReference(
        relation=PaperRelationType.CITATION,
        paper=build_test_paper(),
        contexts=(
            "Uses the Transformer architecture.",
            " Uses the Transformer architecture. ",
        ),
        intents=(
            "background",
            "Background",
            "methodology",
        ),
        is_influential=True,
    )

    assert reference.contexts == ("Uses the Transformer architecture.",)
    assert reference.intents == (
        "background",
        "methodology",
    )


def test_domain_models_are_immutable() -> None:
    """Canonical models should not be mutated after validation."""

    paper = build_test_paper()

    with pytest.raises(ValidationError):
        paper.title = "Changed title"  # type: ignore[misc]
