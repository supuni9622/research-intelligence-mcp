"""Integration tests for the complete arXiv provider flow."""

from __future__ import annotations

import httpx
import pytest

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.domain.enums import ProviderName, SearchSort
from research_intelligence_mcp.domain.requests import SearchRequest
from research_intelligence_mcp.infrastructure.http import create_async_http_client
from research_intelligence_mcp.infrastructure.rate_limit import UnlimitedRateLimiter
from research_intelligence_mcp.providers.arxiv.client import ArxivClient
from research_intelligence_mcp.providers.arxiv.provider import ArxivProvider
from research_intelligence_mcp.providers.errors import (
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUpstreamError,
)

SEARCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>2</opensearch:totalResults>
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
    <category term="cs.CL" />
    <arxiv:primary_category term="cs.IR" />
    <arxiv:journal_ref>Journal of Research Systems 10 (2024)</arxiv:journal_ref>
    <arxiv:doi>10.1000/example-rag</arxiv:doi>
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


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        APP_ENVIRONMENT="test",
        ARXIV_MAX_RETRY_ATTEMPTS=1,
        ARXIV_RETRY_MIN_SECONDS=0,
        ARXIV_RETRY_MAX_SECONDS=1,
    )


def build_provider(transport: httpx.AsyncBaseTransport) -> ArxivProvider:
    settings = build_settings()
    http_client = create_async_http_client(
        settings=settings,
        rate_limiter=UnlimitedRateLimiter(),
        base_url="https://export.arxiv.example.test/api",
        transport=transport,
    )
    return ArxivProvider(client=ArxivClient(http_client=http_client, settings=settings))


@pytest.mark.asyncio
async def test_complete_search_flow() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/query"
        assert request.url.params["search_query"] == (
            '(all:"retrieval augmented generation") AND '
            '(cat:"cs.IR") AND '
            "(submittedDate:[202201010000 TO 202512312359])"
        )
        assert request.url.params["sortBy"] == "submittedDate"
        assert request.url.params["sortOrder"] == "descending"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/atom+xml"},
            text=SEARCH_XML,
        )

    provider = build_provider(httpx.MockTransport(handler))
    try:
        result = await provider.search_papers(
            SearchRequest(
                query="retrieval augmented generation",
                providers=(ProviderName.ARXIV,),
                limit=5,
                fields_of_study=("cs.IR",),
                year_from=2022,
                year_to=2025,
                sort=SearchSort.PUBLICATION_DATE,
            )
        )
    finally:
        await provider.close()

    assert result.papers[0].identifiers.arxiv_id == "2401.12345"
    assert result.papers[0].identifiers.doi == "10.1000/example-rag"
    assert result.papers[0].fields_of_study == ("cs.IR", "cs.CL")
    assert result.pagination.total == 2
    assert result.pagination.has_more is True


@pytest.mark.asyncio
async def test_complete_get_paper_flow() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["id_list"] == "2401.12345v3"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/atom+xml"},
            text=SEARCH_XML,
        )

    provider = build_provider(httpx.MockTransport(handler))
    try:
        paper = await provider.get_paper("2401.12345v3")
    finally:
        await provider.close()

    assert paper.identifiers.arxiv_id == "2401.12345"


@pytest.mark.asyncio
async def test_empty_search_and_missing_paper_flows() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/atom+xml"},
            text=EMPTY_XML,
        )

    provider = build_provider(httpx.MockTransport(handler))
    try:
        result = await provider.search_papers(
            SearchRequest(
                query="nonexistent research topic",
                providers=(ProviderName.ARXIV,),
            )
        )
        assert result.papers == ()

        with pytest.raises(ProviderNotFoundError):
            await provider.get_paper("2401.12345")
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_malformed_xml_flow() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/atom+xml"},
            text="<feed><entry>",
        )

    provider = build_provider(httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderResponseError) as error_info:
            await provider.search_papers(
                SearchRequest(
                    query="retrieval augmented generation",
                    providers=(ProviderName.ARXIV,),
                )
            )
    finally:
        await provider.close()

    assert error_info.value.code == "arxiv_malformed_xml"


@pytest.mark.asyncio
async def test_rate_limit_flow() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "5", "Content-Type": "application/xml"},
            text="<error>Too Many Requests</error>",
        )

    provider = build_provider(httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderRateLimitError) as error_info:
            await provider.search_papers(
                SearchRequest(
                    query="retrieval augmented generation",
                    providers=(ProviderName.ARXIV,),
                )
            )
    finally:
        await provider.close()

    assert error_info.value.retry_after_seconds == 5


@pytest.mark.asyncio
async def test_upstream_failure_flow() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            headers={"Content-Type": "application/xml"},
            text="<error>Internal Server Error</error>",
        )

    provider = build_provider(httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderUpstreamError) as error_info:
            await provider.search_papers(
                SearchRequest(
                    query="retrieval augmented generation",
                    providers=(ProviderName.ARXIV,),
                )
            )
    finally:
        await provider.close()

    assert error_info.value.code == "arxiv_upstream_failure"
