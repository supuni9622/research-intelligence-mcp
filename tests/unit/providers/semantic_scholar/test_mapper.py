"""Tests for Semantic Scholar canonical mapping."""

from research_intelligence_mcp.domain.enums import (
    AccessStatus,
    ProviderName,
)
from research_intelligence_mcp.providers.semantic_scholar.mapper import (
    SemanticScholarMapper,
)
from research_intelligence_mcp.providers.semantic_scholar.models import (
    SemanticScholarPaperResponse,
)

_VALID_SEMANTIC_SCHOLAR_ID = (
    "0796f6cd7f0403f4f5c1d1fdc9f7a3f1fdb4c5e0"
)


def test_maps_paper_to_canonical_model() -> None:
    """Provider paper responses should not leak into domain logic."""

    response = SemanticScholarPaperResponse.model_validate(
        {
            "paperId": _VALID_SEMANTIC_SCHOLAR_ID,
            "corpusId": 123,
            "title": "Retrieval-Augmented Generation",
            "abstract": "A paper about RAG.",
            "year": 2024,
            "venue": "Example Conference",
            "authors": [
                {
                    "authorId": "author-1",
                    "name": "Ada Researcher",
                }
            ],
            "externalIds": {
                "DOI": "10.1000/example",
                "ArXiv": "2401.00001",
            },
            "citationCount": 20,
            "referenceCount": 30,
            "fieldsOfStudy": [
                "Computer Science",
            ],
            "isOpenAccess": True,
            "openAccessPdf": {
                "url": "https://example.test/paper.pdf",
                "status": "GREEN",
                "license": "CC BY 4.0",
            },
        }
    )

    paper = SemanticScholarMapper.to_paper(
        response
    )

    assert (
        paper.title
        == "Retrieval-Augmented Generation"
    )
    assert (
        paper.identifiers.semantic_scholar_id
        == _VALID_SEMANTIC_SCHOLAR_ID
    )
    assert (
        paper.identifiers.corpus_id
        == 123
    )
    assert (
        paper.identifiers.doi
        == "10.1000/example"
    )
    assert (
        paper.identifiers.arxiv_id
        == "2401.00001"
    )
    assert (
        paper.authors[0].name
        == "Ada Researcher"
    )
    assert (
        paper.access.status
        == AccessStatus.OPEN_ACCESS
    )
    assert (
        paper.access.repository
        == ProviderName.SEMANTIC_SCHOLAR
    )
    assert paper.sources == (
        ProviderName.SEMANTIC_SCHOLAR,
    )


def test_maps_string_corpus_id_to_integer() -> None:
    """String CorpusId values should become canonical integers."""

    response = SemanticScholarPaperResponse.model_validate(
        {
            "paperId": _VALID_SEMANTIC_SCHOLAR_ID,
            "corpusId": 123,
            "title": "Example Paper",
            "externalIds": {
                "CorpusId": "456",
            },
        }
    )

    paper = SemanticScholarMapper.to_paper(
        response
    )

    assert (
        paper.identifiers.corpus_id
        == 456
    )


def test_ignores_invalid_semantic_scholar_id_when_corpus_id_exists() -> None:
    """Incomplete provider IDs should not invalidate usable papers."""

    response = SemanticScholarPaperResponse.model_validate(
        {
            "paperId": "s2-paper-1",
            "corpusId": 123,
            "title": "Example Paper",
        }
    )

    paper = SemanticScholarMapper.to_paper(
        response
    )

    assert (
        paper.identifiers.semantic_scholar_id
        is None
    )
    assert (
        paper.identifiers.corpus_id
        == 123
    )