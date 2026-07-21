"""Tests for paper-related MCP input schemas."""

import pytest
from pydantic import ValidationError

from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.mcp.schemas.paper import (
    GetPaperInput,
    GetRelatedPapersInput,
    PaperGraphInput,
)


def test_get_paper_input_accepts_valid_arxiv_identifier() -> None:
    """A valid arXiv identifier should be accepted."""

    model = GetPaperInput(
        provider=ProviderName.ARXIV,
        paper_id="2501.12345",
    )

    assert model.provider == ProviderName.ARXIV
    assert model.paper_id == "2501.12345"


def test_get_paper_input_strips_identifier_whitespace() -> None:
    """Paper identifiers should have surrounding whitespace removed."""

    model = GetPaperInput(
        provider=ProviderName.ARXIV,
        paper_id="  2501.12345  ",
    )

    assert model.paper_id == "2501.12345"


def test_get_paper_input_rejects_empty_identifier() -> None:
    """An empty paper identifier should be rejected."""

    with pytest.raises(ValidationError):
        GetPaperInput(
            provider=ProviderName.ARXIV,
            paper_id="",
        )


def test_get_paper_input_rejects_whitespace_identifier() -> None:
    """A whitespace-only paper identifier should be rejected."""

    with pytest.raises(ValidationError):
        GetPaperInput(
            provider=ProviderName.ARXIV,
            paper_id="   ",
        )


def test_paper_graph_input_applies_defaults() -> None:
    """Graph input should apply bounded pagination defaults."""

    model = PaperGraphInput(
        provider=ProviderName.SEMANTIC_SCHOLAR,
        paper_id="10.48550/arXiv.1706.03762",
    )

    assert model.limit == 20
    assert model.offset == 0


@pytest.mark.parametrize(
    (
        "limit",
        "offset",
    ),
    [
        (0, 0),
        (101, 0),
        (20, -1),
        (20, 10_001),
    ],
)
def test_paper_graph_input_rejects_invalid_pagination(
    limit: int,
    offset: int,
) -> None:
    """Graph pagination should remain inside configured MCP bounds."""

    with pytest.raises(ValidationError):
        PaperGraphInput(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            paper_id="10.48550/arXiv.1706.03762",
            limit=limit,
            offset=offset,
        )


def test_related_papers_input_normalizes_negative_ids() -> None:
    """Negative recommendation identifiers should be normalized."""

    model = GetRelatedPapersInput(
        provider=ProviderName.SEMANTIC_SCHOLAR,
        paper_id="positive-paper-id",
        negative_paper_ids=(
            " negative-one ",
            "negative-one",
            "NEGATIVE-ONE",
            "negative-two",
        ),
    )

    assert model.negative_paper_ids == (
        "negative-one",
        "negative-two",
    )


def test_related_papers_input_accepts_none_negative_ids() -> None:
    """None should normalize to an empty negative-paper tuple."""

    model = GetRelatedPapersInput(
        provider=ProviderName.SEMANTIC_SCHOLAR,
        paper_id="positive-paper-id",
        negative_paper_ids=None,
    )

    assert model.negative_paper_ids == ()


def test_related_papers_input_rejects_empty_negative_id() -> None:
    """Empty negative recommendation identifiers should be rejected."""

    with pytest.raises(ValidationError):
        GetRelatedPapersInput(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            paper_id="positive-paper-id",
            negative_paper_ids=(
                "negative-one",
                "",
            ),
        )


def test_related_papers_input_rejects_invalid_limit() -> None:
    """Related-paper limits should remain bounded."""

    with pytest.raises(ValidationError):
        GetRelatedPapersInput(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            paper_id="positive-paper-id",
            limit=101,
        )
