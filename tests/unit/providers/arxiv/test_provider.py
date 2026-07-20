"""Tests for the canonical arXiv provider."""

from __future__ import annotations

from typing import Any, cast

import pytest

from research_intelligence_mcp.domain.enums import ProviderName, SearchSort
from research_intelligence_mcp.domain.requests import SearchRequest
from research_intelligence_mcp.providers.arxiv.client import ArxivClient
from research_intelligence_mcp.providers.arxiv.provider import ArxivProvider
from research_intelligence_mcp.providers.errors import (
    ProviderNotFoundError,
    ProviderRequestError,
)

SEARCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
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
        self, *, search_xml: str = SEARCH_XML, paper_xml: str = SEARCH_XML
    ) -> None:
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

    async def get_paper(self, *, arxiv_id: str) -> str:
        self.paper_calls.append(arxiv_id)
        return self.paper_xml

    async def close(self) -> None:
        self.closed = True


def build_provider(client: FakeArxivClient) -> ArxivProvider:
    """Build a provider around the typed fake client."""

    return ArxivProvider(client=cast(ArxivClient, client))


@pytest.mark.asyncio
async def test_search_papers() -> None:
    client = FakeArxivClient()
    provider = build_provider(client)
    request = SearchRequest(
        query="retrieval augmented generation",
        providers=(ProviderName.ARXIV,),
        limit=5,
        offset=10,
    )

    result = await provider.search_papers(request)

    assert result.papers[0].identifiers.arxiv_id == "2401.12345"
    assert client.search_calls == [
        {
            "search_query": '(all:"retrieval augmented generation")',
            "start": 10,
            "max_results": 5,
            "sort_by": "relevance",
            "sort_order": "descending",
        }
    ]


@pytest.mark.asyncio
async def test_search_builds_category_and_year_filters() -> None:
    client = FakeArxivClient()
    provider = build_provider(client)
    request = SearchRequest(
        query="retrieval augmented generation",
        providers=(ProviderName.ARXIV,),
        fields_of_study=("cs.IR", "cs.CL"),
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
async def test_get_paper() -> None:
    client = FakeArxivClient()
    provider = build_provider(client)

    paper = await provider.get_paper("2401.12345v3")

    assert paper.identifiers.arxiv_id == "2401.12345"
    assert client.paper_calls == ["2401.12345v3"]


@pytest.mark.asyncio
async def test_get_paper_not_found() -> None:
    provider = build_provider(FakeArxivClient(paper_xml=EMPTY_XML))

    with pytest.raises(ProviderNotFoundError) as error_info:
        await provider.get_paper("2401.12345")

    assert error_info.value.code == "arxiv_paper_not_found"


@pytest.mark.asyncio
async def test_get_citations_is_not_supported() -> None:
    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_citations("2401.12345")

    assert error_info.value.code == "arxiv_citations_not_supported"


@pytest.mark.asyncio
async def test_get_references_is_not_supported() -> None:
    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_references("2401.12345")

    assert error_info.value.code == "arxiv_references_not_supported"


@pytest.mark.asyncio
async def test_get_related_papers_is_not_supported() -> None:
    provider = build_provider(FakeArxivClient())

    with pytest.raises(ProviderRequestError) as error_info:
        await provider.get_related_papers("2401.12345")

    assert error_info.value.code == "arxiv_related_papers_not_supported"


@pytest.mark.asyncio
async def test_close() -> None:
    client = FakeArxivClient()
    provider = build_provider(client)

    await provider.close()

    assert client.closed is True
