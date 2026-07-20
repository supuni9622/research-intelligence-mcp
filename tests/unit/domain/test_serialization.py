"""Tests for canonical JSON serialization contracts."""

import json

from research_intelligence_mcp.domain.enums import (
    AccessStatus,
    ProviderName,
)
from research_intelligence_mcp.domain.identifiers import PaperIdentifiers
from research_intelligence_mcp.domain.models import Paper, PaperAccess
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    SearchResult,
)


def test_paper_serializes_to_json_compatible_values() -> None:
    """Canonical paper models should serialize safely for MCP output."""

    paper = Paper(
        identifiers=PaperIdentifiers(
            arxiv_id="2005.11401",
        ),
        title="Retrieval-Augmented Generation",
        access=PaperAccess(
            status=AccessStatus.OPEN_ACCESS,
            landing_page_url="https://arxiv.org/abs/2005.11401",
            pdf_url="https://arxiv.org/pdf/2005.11401",
            repository=ProviderName.ARXIV,
        ),
        sources=[ProviderName.ARXIV],
    )

    payload = paper.model_dump(mode="json")

    assert payload["identifiers"]["arxiv_id"] == "2005.11401"
    assert payload["access"]["status"] == "open_access"
    assert payload["access"]["repository"] == "arxiv"
    assert payload["sources"] == ["arxiv"]

    json.dumps(payload)


def test_search_result_json_round_trip() -> None:
    """Serialized search output should validate back into the same model."""

    paper = Paper(
        identifiers=PaperIdentifiers(
            arxiv_id="2005.11401",
        ),
        title="Retrieval-Augmented Generation",
        sources=[ProviderName.ARXIV],
    )

    result = SearchResult(
        query="retrieval augmented generation",
        papers=[paper],
        pagination=PaginationMetadata(
            offset=0,
            limit=10,
            returned=1,
            total=1,
            has_more=False,
        ),
        providers_requested=[ProviderName.ARXIV],
        providers_succeeded=[ProviderName.ARXIV],
    )

    serialized = result.model_dump_json()
    restored = SearchResult.model_validate_json(serialized)

    assert restored == result


def test_search_result_exposes_json_schema() -> None:
    """Search results should expose schemas usable by FastMCP."""

    schema = SearchResult.model_json_schema()

    assert schema["title"] == "SearchResult"
    assert "properties" in schema
    assert "papers" in schema["properties"]
    assert "pagination" in schema["properties"]
    assert "providers_requested" in schema["properties"]


def test_unknown_fields_are_rejected() -> None:
    """Provider-specific fields must not leak into canonical models."""

    payload = {
        "identifiers": {
            "arxiv_id": "2005.11401",
        },
        "title": "Retrieval-Augmented Generation",
        "sources": ["arxiv"],
        "semanticScholarRawPayload": {
            "unexpected": True,
        },
    }

    try:
        Paper.model_validate(payload)
    except ValueError as error:
        assert "Extra inputs are not permitted" in str(error)
    else:
        raise AssertionError("Unknown field should have been rejected.")
