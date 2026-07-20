"""Tests for the secure arXiv Atom parser."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from research_intelligence_mcp.providers.arxiv.parser import (
    ArxivParser,
)
from research_intelligence_mcp.providers.errors import (
    ProviderResponseError,
)

FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"


def load_fixture(
    filename: str,
) -> str:
    """Load one XML test fixture."""

    return (FIXTURES_DIRECTORY / filename).read_text(encoding="utf-8")


def test_parses_search_feed() -> None:
    """A complete arXiv search response should be parsed."""

    feed = ArxivParser.parse_feed(load_fixture("search.xml"))

    assert feed.feed_id == "https://arxiv.org/api/test-search"
    assert feed.total_results == 2
    assert feed.start_index == 0
    assert feed.items_per_page == 2
    assert len(feed.entries) == 2

    first_entry = feed.entries[0]

    assert first_entry.entry_id == "https://arxiv.org/abs/2401.12345v3"
    assert first_entry.title == "Retrieval-Augmented Generation for Research"
    assert first_entry.summary == (
        "This paper studies retrieval-augmented generation "
        "for academic research systems."
    )
    assert first_entry.published == datetime(
        2024,
        1,
        15,
        8,
        0,
        tzinfo=UTC,
    )
    assert first_entry.updated == datetime(
        2024,
        3,
        5,
        12,
        30,
        tzinfo=UTC,
    )


def test_parses_authors_and_affiliations() -> None:
    """Author order and affiliations should be preserved."""

    feed = ArxivParser.parse_feed(load_fixture("search.xml"))

    authors = feed.entries[0].authors

    assert len(authors) == 2
    assert authors[0].name == "Ada Researcher"
    assert authors[0].affiliations == [
        "Example University",
        "AI Research Lab",
    ]
    assert authors[1].name == "Grace Scientist"
    assert authors[1].affiliations == []


def test_parses_links() -> None:
    """Atom links should retain relationship and media metadata."""

    feed = ArxivParser.parse_feed(load_fixture("search.xml"))

    links = feed.entries[0].links

    assert len(links) == 3

    pdf_link = next(link for link in links if link.title == "pdf")

    assert pdf_link.href == "https://arxiv.org/pdf/2401.12345v3"
    assert pdf_link.rel == "related"
    assert pdf_link.content_type == "application/pdf"


def test_parses_categories_and_primary_category() -> None:
    """All categories and the primary category should be parsed."""

    feed = ArxivParser.parse_feed(load_fixture("search.xml"))

    entry = feed.entries[0]

    assert [category.term for category in entry.categories] == [
        "cs.IR",
        "cs.CL",
    ]

    assert entry.primary_category is not None
    assert entry.primary_category.term == "cs.IR"


def test_parses_arxiv_extension_fields() -> None:
    """arXiv extension metadata should be retained."""

    feed = ArxivParser.parse_feed(load_fixture("search.xml"))

    entry = feed.entries[0]

    assert entry.comment == "20 pages, 4 figures"
    assert entry.journal_reference == "Journal of Research Systems 10 (2024)"
    assert entry.doi == "10.1000/example-rag"


def test_parses_single_paper_feed() -> None:
    """Identifier queries should use the same feed parser."""

    feed = ArxivParser.parse_feed(load_fixture("paper.xml"))

    assert feed.total_results == 1
    assert len(feed.entries) == 1

    paper = feed.entries[0]

    assert paper.title == "Attention Is All You Need"
    assert paper.entry_id == "https://arxiv.org/abs/1706.03762v7"
    assert paper.primary_category is not None
    assert paper.primary_category.term == "cs.CL"


def test_parses_empty_feed() -> None:
    """Empty arXiv search results should not be treated as errors."""

    feed = ArxivParser.parse_feed(load_fixture("empty.xml"))

    assert feed.total_results == 0
    assert feed.start_index == 0
    assert feed.items_per_page == 0
    assert feed.entries == []


def test_parses_minimal_entry() -> None:
    """Missing optional provider fields should remain valid."""

    feed = ArxivParser.parse_feed(load_fixture("minimal.xml"))

    assert feed.total_results == 1
    assert feed.items_per_page == 1
    assert len(feed.entries) == 1

    entry = feed.entries[0]

    assert entry.title == "Minimal Paper"
    assert entry.summary is None
    assert entry.published is None
    assert entry.updated is None
    assert entry.comment is None
    assert entry.journal_reference is None
    assert entry.doi is None
    assert entry.primary_category is None
    assert entry.authors[0].name == "Minimal Author"


def test_rejects_empty_xml() -> None:
    """Blank XML documents should be rejected explicitly."""

    with pytest.raises(ProviderResponseError) as error_info:
        ArxivParser.parse_feed("   ")

    assert error_info.value.code == "arxiv_empty_xml"
    assert error_info.value.retryable is False


def test_rejects_malformed_xml() -> None:
    """Malformed XML should become a normalized provider error."""

    with pytest.raises(ProviderResponseError) as error_info:
        ArxivParser.parse_feed(load_fixture("malformed.xml"))

    assert error_info.value.code == "arxiv_malformed_xml"


def test_rejects_unsafe_xml_entities() -> None:
    """External and custom entities should be blocked."""

    with pytest.raises(ProviderResponseError) as error_info:
        ArxivParser.parse_feed(load_fixture("unsafe.xml"))

    assert error_info.value.code == "arxiv_unsafe_xml"
    assert error_info.value.retryable is False


def test_rejects_unexpected_root_element() -> None:
    """Non-Atom-feed XML should be rejected."""

    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<response>
    <message>Not an Atom feed</message>
</response>
"""

    with pytest.raises(ProviderResponseError) as error_info:
        ArxivParser.parse_feed(xml)

    assert error_info.value.code == "arxiv_unexpected_xml_root"


def test_rejects_entry_without_identifier() -> None:
    """Required entry fields should be validated."""

    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed
    xmlns="http://www.w3.org/2005/Atom"
    xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
>
    <opensearch:totalResults>1</opensearch:totalResults>

    <entry>
        <title>Paper Without Identifier</title>
    </entry>
</feed>
"""

    with pytest.raises(ProviderResponseError) as error_info:
        ArxivParser.parse_feed(xml)

    assert error_info.value.code == "arxiv_invalid_entry"


def test_rejects_invalid_datetime() -> None:
    """Invalid provider timestamps should be normalized."""

    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed
    xmlns="http://www.w3.org/2005/Atom"
>
    <entry>
        <id>https://arxiv.org/abs/2401.12345</id>
        <title>Example Paper</title>
        <published>not-a-date</published>
    </entry>
</feed>
"""

    with pytest.raises(ProviderResponseError) as error_info:
        ArxivParser.parse_feed(xml)

    assert error_info.value.code == "arxiv_invalid_datetime"


def test_rejects_invalid_pagination_metadata() -> None:
    """Non-integer OpenSearch values should be rejected."""

    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed
    xmlns="http://www.w3.org/2005/Atom"
    xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
>
    <opensearch:totalResults>many</opensearch:totalResults>
</feed>
"""

    with pytest.raises(ProviderResponseError) as error_info:
        ArxivParser.parse_feed(xml)

    assert error_info.value.code == "arxiv_invalid_pagination"
