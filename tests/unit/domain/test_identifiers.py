"""Tests for canonical paper identifiers."""

import pytest
from pydantic import ValidationError

from research_intelligence_mcp.domain.identifiers import (
    PaperIdentifiers,
    normalize_arxiv_id,
    normalize_doi,
)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (
            "10.48550/ARXIV.2005.11401",
            "10.48550/arxiv.2005.11401",
        ),
        (
            "https://doi.org/10.1145/3290605.3300233",
            "10.1145/3290605.3300233",
        ),
        (
            "doi:10.1000/XYZ123",
            "10.1000/xyz123",
        ),
    ],
)
def test_normalize_doi(
    raw_value: str,
    expected: str,
) -> None:
    """DOIs should be normalized into canonical lowercase identifiers."""

    assert normalize_doi(raw_value) == expected


@pytest.mark.parametrize(
    "invalid_doi",
    [
        "",
        "not-a-doi",
        "https://example.com/paper",
        "11.1234/example",
    ],
)
def test_invalid_doi_is_rejected(invalid_doi: str) -> None:
    """Invalid DOI values should fail validation."""

    with pytest.raises(ValueError, match="Invalid DOI"):
        normalize_doi(invalid_doi)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("2005.11401", "2005.11401"),
        ("arXiv:2005.11401v4", "2005.11401"),
        (
            "https://arxiv.org/abs/1706.03762",
            "1706.03762",
        ),
        (
            "https://arxiv.org/pdf/cs/9901001v2.pdf",
            "cs/9901001",
        ),
    ],
)
def test_normalize_arxiv_id(
    raw_value: str,
    expected: str,
) -> None:
    """arXiv identifiers should lose URLs, prefixes, and versions."""

    assert normalize_arxiv_id(raw_value) == expected


@pytest.mark.parametrize(
    "invalid_arxiv_id",
    [
        "",
        "arxiv-paper",
        "2024.123",
        "https://example.com/2005.11401",
    ],
)
def test_invalid_arxiv_id_is_rejected(
    invalid_arxiv_id: str,
) -> None:
    """Malformed arXiv identifiers should be rejected."""

    with pytest.raises(ValueError, match="Invalid arXiv"):
        normalize_arxiv_id(invalid_arxiv_id)


def test_paper_identifiers_requires_at_least_one_identifier() -> None:
    """A canonical paper must have at least one stable identifier."""

    with pytest.raises(
        ValidationError,
        match="At least one paper identifier",
    ):
        PaperIdentifiers()


def test_paper_identifiers_normalizes_values() -> None:
    """Identifier fields should be normalized at model creation."""

    identifiers = PaperIdentifiers(
        doi="https://doi.org/10.1000/Example",
        arxiv_id="arXiv:2005.11401v2",
    )

    assert identifiers.doi == "10.1000/example"
    assert identifiers.arxiv_id == "2005.11401"


def test_preferred_identifier_prioritizes_doi() -> None:
    """DOI should be preferred over provider-specific identifiers."""

    identifiers = PaperIdentifiers(
        doi="10.1000/example",
        arxiv_id="2005.11401",
        semantic_scholar_id="a" * 40,
    )

    assert identifiers.preferred_identifier() == "doi:10.1000/example"


def test_arxiv_identifier_is_used_when_doi_is_missing() -> None:
    """arXiv should be preferred when no DOI exists."""

    identifiers = PaperIdentifiers(
        arxiv_id="2005.11401",
        semantic_scholar_id="a" * 40,
    )

    assert identifiers.preferred_identifier() == "arxiv:2005.11401"
