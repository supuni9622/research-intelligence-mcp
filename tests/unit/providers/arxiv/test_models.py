"""Tests for arXiv provider response models."""

from datetime import UTC, datetime

from research_intelligence_mcp.providers.arxiv.models import (
    ArxivAuthorResponse,
    ArxivEntryResponse,
    ArxivFeedResponse,
)


def test_author_normalizes_name_and_affiliations() -> None:
    """Author strings should be normalized and deduplicated."""

    author = ArxivAuthorResponse.model_validate(
        {
            "name": "  Ada   Researcher  ",
            "affiliations": [
                " Example   University ",
                "example university",
                "",
                "AI Lab",
            ],
        }
    )

    assert author.name == "Ada Researcher"
    assert author.affiliations == [
        "Example University",
        "AI Lab",
    ]


def test_entry_normalizes_multiline_text() -> None:
    """Provider multiline text should become normalized strings."""

    entry = ArxivEntryResponse.model_validate(
        {
            "id": " https://arxiv.org/abs/2401.12345v1 ",
            "title": """
                Retrieval-Augmented
                Generation
            """,
            "summary": """
                This is a
                multiline abstract.
            """,
            "authors": [],
        }
    )

    assert entry.entry_id == "https://arxiv.org/abs/2401.12345v1"
    assert entry.title == "Retrieval-Augmented Generation"
    assert entry.summary == "This is a multiline abstract."


def test_feed_accepts_empty_entries() -> None:
    """Empty result feeds should remain valid provider responses."""

    feed = ArxivFeedResponse.model_validate(
        {
            "id": "https://arxiv.org/api/empty",
            "title": "arXiv Query Results",
            "updated": "2026-07-20T10:00:00Z",
            "total_results": 0,
            "start_index": 0,
            "items_per_page": 0,
            "entries": [],
        }
    )

    assert feed.total_results == 0
    assert feed.entries == []
    assert feed.updated == datetime(
        2026,
        7,
        20,
        10,
        0,
        tzinfo=UTC,
    )
