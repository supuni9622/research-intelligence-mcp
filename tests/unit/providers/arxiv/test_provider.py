"""Tests for the canonical arXiv provider."""

from __future__ import annotations

from typing import Any, cast

import pytest

from research_intelligence_mcp.domain.enums import (
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.domain.requests import (
    SearchRequest,
)
from research_intelligence_mcp.providers.arxiv.client import (
    ArxivClient,
)
from research_intelligence_mcp.providers.arxiv.provider import (
    ArxivProvider,
)
from research_intelligence_mcp.providers.errors import (
    ProviderNotFoundError,
    ProviderRequestError,
)

SEARCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>11</opensearch:totalResults>
  <opensearch:startIndex>10</opensearch:startIndex>
  <opensearch:itemsPerPage>1</opensearch:itemsPerPage>
  <entry>
    <id>https://arxiv.org/abs/2401.12345v3</id>
    <title>Retrieval-Augmented Generation for Research</title>
    <summary>A paper about retrieval-augmented generation.</summary>
    <published>2024-01-15T08:00:00Z</published>
    <updated>2024-03-05T12:30:00Z</updated>
    <author>
      <name>Ada Researcher</name>
      <arxiv:affiliation>Example University</arxiv:affiliation>
    </author>
    <link href="https://arxiv.org/abs/2401.12345v3"
          rel="alternate"
          type="text/html" />
    <link href="https://arxiv.org/pdf/2401.12345v3"
          rel="related"
          type="application/pdf"
          title="pdf" />
    <category term="cs.IR" />
    <arxiv:primary_category term="cs.IR" />
  </entry>
</feed>
"""

EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>0</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>0</opensearch:itemsPerPage>
</feed>
"""


class FakeArxivClient:
    """Deterministic fake client for provider unit tests."""

    def __init__(
        self,
        *,
        search_xml: str = SEARCH_XML,
        paper_xml: str = SEARCH_XML,
    ) -> None:
        """Initialize the fake client."""

        self.search_xml = search_xml
        self.paper_xml = paper_xml

        self.search_calls: list[dict[str, Any]] = []
        self.paper_calls: list[str] = []

        self.closed = False

    async def search(
        self,
        *,
        search_query: str,
        start: int = 0,
        max_results: int = 10,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> str:
        """Return the configured search response."""

        self.search_calls.append(
            {
                "search_query": search_query,
                "start": start,
                "max_results": max_results,
                "sort_by": sort_by,
                "sort_order": sort_order,
            }
        )

        return self.search_xml

    async def get_paper(
        self,
        *,
        arxiv_id: str,
    ) -> str:
        """Return the configured paper response."""

        self.paper_calls.append(arxiv_id)

        return self.paper_xml

    async def close(self) -> None:
        """Mark the fake client as closed."""

        self.closed = True


def build_provider(
    client: FakeArxivClient,
) -> ArxivProvider:
    """Build a provider around the typed fake client."""

    return ArxivProvider(
        client=cast(
            ArxivClient,
            client,
        )
    )


@pytest.mark.asyncio
async def test_search_papers() -> None:
    """Search should map results and forward pagination arguments."""

    client = FakeArxivClient()
    provider = build_provider(client)

    request = SearchRequest(
        query="retrieval augmented generation",
        providers=(ProviderName.ARXIV,),
        limit=5,
        offset=10,
    )

    result = await provider.search_papers(request)

    assert len(result.papers) == 1
    assert result.papers[0].identifiers.arxiv_id == "2401.12345"

    assert result.pagination.offset == 10
    assert result.pagination.limit == 5
    assert result.pagination.returned == 1
    assert result.pagination.total == 11
    assert result.pagination.has_more is False

    assert result.providers_requested == (ProviderName.ARXIV,)
    assert result.providers_succeeded == (ProviderName.ARXIV,)
    assert result.failures == ()

    assert client.search_calls == [
        {
            "search_query": ('(all:"retrieval augmented generation")'),
            "start": 10,
            "max_results": 5,
            "sort_by": "relevance",
            "sort_order": "descending",
        }
    ]


@pytest.mark.asyncio
async def test_search_builds_category_and_year_filters() -> None:
    """Search should translate category and year filters."""

    client = FakeArxivClient()
    provider = build_provider(client)

    request = SearchRequest(
        query="retrieval augmented generation",
        providers=(ProviderName.ARXIV,),
        fields_of_study=(
            "cs.IR",
            "cs.CL",
        ),
        year_from=2022,
        year_to=2025,
    )

    await provider.search_papers(request)

    assert client.search_calls[0]["search_query"] == (
        '(all:"retrieval augmented generation") AND '
        '(cat:"cs.IR" OR cat:"cs.CL") AND '
        "(submittedDate:[202201010000 TO 202512312359])"
    )


@pytest.mark.asyncio
async def test_search_uses_publication_date_sort() -> None:
    """Publication-date sorting should map to submittedDate."""

    client = FakeArxivClient()
    provider = build_provider(client)

    request = SearchRequest(
        query="transformers",
        providers=(ProviderName.ARXIV,),
        sort=SearchSort.PUBLICATION_DATE,
    )

    await provider.search_papers(request)

    assert client.search_calls[0]["sort_by"] == "submittedDate"
    assert client.search_calls[0]["sort_order"] == "descending"


@pytest.mark.asyncio
async def test_search_uses_relevance_sort_by_default() -> None:
    """Default canonical sorting should map to relevance."""

    client = FakeArxivClient()
    provider = build_provider(client)

    request = SearchRequest(
        query="transformers",
        providers=(ProviderName.ARXIV,),
    )

    await provider.search_papers(request)

    assert client.search_calls[0]["sort_by"] == "relevance"
    assert client.search_calls[0]["sort_order"] == "descending"


@pytest.mark.asyncio
async def test_get_paper() -> None:
    """Paper retrieval should return a canonical paper."""

    client = FakeArxivClient()
    provider = build_provider(client)

    paper = await provider.get_paper("2401.12345v3")

    assert paper.identifiers.arxiv_id == "2401.12345"
    assert client.paper_calls == ["2401.12345v3"]


@pytest.mark.asyncio
async def test_get_paper_not_found() -> None:
    """An empty feed should become a not-found error."""

    provider = build_provider(
        FakeArxivClient(
            paper_xml=EMPTY_XML,
        )
    )

    with pytest.raises(ProviderNotFoundError) as error_info:
        await provider.get_paper("2401.12345")

    assert error_info.value.code == "arxiv_paper_not_found"
    assert error_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_citations_is_not_supported() -> None:
    """Citation retrieval should fail with a stable code."""

    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_citations("2401.12345")

    assert error_info.value.code == "arxiv_citations_not_supported"
    assert error_info.value.retryable is False


@pytest.mark.asyncio
async def test_get_references_is_not_supported() -> None:
    """Reference retrieval should fail with a stable code."""

    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_references("2401.12345")

    assert error_info.value.code == "arxiv_references_not_supported"
    assert error_info.value.retryable is False


@pytest.mark.asyncio
async def test_get_related_papers_is_not_supported() -> None:
    """Related-paper retrieval should fail with a stable code."""

    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_related_papers("2401.12345")

    assert error_info.value.code == "arxiv_related_papers_not_supported"
    assert error_info.value.retryable is False


@pytest.mark.asyncio
async def test_rejects_empty_citation_paper_id() -> None:
    """Unsupported operations should still validate identifiers."""

    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_citations(" ")

    assert error_info.value.code == "arxiv_invalid_paper_id"


@pytest.mark.asyncio
async def test_rejects_invalid_reference_limit() -> None:
    """Unsupported graph operations should validate limits."""

    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_references(
            "2401.12345",
            limit=0,
        )

    assert error_info.value.code == "arxiv_invalid_graph_limit"


@pytest.mark.asyncio
async def test_rejects_invalid_reference_offset() -> None:
    """Unsupported graph operations should validate offsets."""

    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_references(
            "2401.12345",
            offset=-1,
        )

    assert error_info.value.code == "arxiv_invalid_graph_offset"


@pytest.mark.asyncio
async def test_rejects_invalid_related_limit() -> None:
    """Related-paper lookup should validate result limits."""

    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_related_papers(
            "2401.12345",
            limit=0,
        )

    assert error_info.value.code == "arxiv_invalid_related_limit"


@pytest.mark.asyncio
async def test_rejects_empty_negative_paper_id() -> None:
    """Related-paper lookup should validate negative IDs."""

    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_related_papers(
            "2401.12345",
            negative_paper_ids=[" "],
        )

    assert error_info.value.code == "arxiv_invalid_negative_paper_id"


@pytest.mark.asyncio
async def test_close() -> None:
    """Closing the provider should close its client."""

    client = FakeArxivClient()
    provider = build_provider(client)

    await provider.close()

    assert client.closed is True
