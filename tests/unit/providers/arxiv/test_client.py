"""Tests for the raw arXiv API client."""

from __future__ import annotations

import httpx
import pytest

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.http import (
    create_async_http_client,
)
from research_intelligence_mcp.infrastructure.rate_limit import (
    UnlimitedRateLimiter,
)
from research_intelligence_mcp.providers.arxiv.client import ArxivClient
from research_intelligence_mcp.providers.errors import (
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTransportError,
)

ATOM_FEED = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>https://arxiv.org/api/test</id>
  <title>arXiv Query Results</title>
  <updated>2026-07-20T00:00:00Z</updated>
</feed>
"""


def build_settings(
    *,
    retry_attempts: int = 1,
    max_results_per_request: int = 50,
) -> Settings:
    """Build deterministic arXiv test settings."""

    return Settings(
        _env_file=None,
        ARXIV_MAX_RETRY_ATTEMPTS=retry_attempts,
        ARXIV_RETRY_MIN_SECONDS=0,
        ARXIV_RETRY_MAX_SECONDS=1,
        ARXIV_MAX_RESULTS_PER_REQUEST=max_results_per_request,
    )


def build_client(
    transport: httpx.AsyncBaseTransport,
    *,
    settings: Settings | None = None,
) -> ArxivClient:
    """Build an arXiv client backed by a mock transport."""

    resolved_settings = settings or build_settings()

    http_client = create_async_http_client(
        settings=resolved_settings,
        rate_limiter=UnlimitedRateLimiter(),
        base_url="https://export.arxiv.example.test/api",
        transport=transport,
    )

    return ArxivClient(
        http_client=http_client,
        settings=resolved_settings,
    )


@pytest.mark.asyncio
async def test_search_returns_raw_atom_xml() -> None:
    """Search should return raw Atom XML for parser-layer processing."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == "/api/query"
        assert request.url.params["search_query"] == "all:RAG"
        assert request.url.params["start"] == "0"
        assert request.url.params["max_results"] == "10"
        assert request.url.params["sortBy"] == "relevance"
        assert request.url.params["sortOrder"] == "descending"

        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/atom+xml; charset=utf-8",
            },
            text=ATOM_FEED,
        )

    client = build_client(httpx.MockTransport(handler))

    try:
        result = await client.search(
            search_query="all:RAG",
            start=0,
            max_results=10,
            sort_by="relevance",
            sort_order="descending",
        )
    finally:
        await client.close()

    assert result == ATOM_FEED.strip()


@pytest.mark.asyncio
async def test_get_paper_preserves_version_suffix() -> None:
    """Versioned IDs should remain versioned in the provider request."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.params["id_list"] == "2401.12345v3"
        assert request.url.params["max_results"] == "1"

        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/atom+xml",
            },
            text=ATOM_FEED,
        )

    client = build_client(httpx.MockTransport(handler))

    try:
        await client.get_paper(arxiv_id="https://arxiv.org/abs/2401.12345v3")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_paper_accepts_legacy_identifier() -> None:
    """Legacy category-prefixed arXiv identifiers should be accepted."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.params["id_list"] == "hep-th/9901001v2"

        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/atom+xml",
            },
            text=ATOM_FEED,
        )

    client = build_client(httpx.MockTransport(handler))

    try:
        await client.get_paper(arxiv_id="arXiv:hep-th/9901001v2")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_papers_deduplicates_identifiers() -> None:
    """Duplicate identifiers should only be sent once."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.params["id_list"] == "2401.12345v2,2402.54321"
        assert request.url.params["max_results"] == "2"

        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/atom+xml",
            },
            text=ATOM_FEED,
        )

    client = build_client(httpx.MockTransport(handler))

    try:
        await client.get_papers(
            arxiv_ids=[
                "2401.12345v2",
                "2401.12345v2",
                "https://arxiv.org/abs/2402.54321",
            ]
        )
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_search_rejects_empty_query() -> None:
    """Empty search expressions should fail before an HTTP request."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise AssertionError("HTTP request should not be executed.")

    client = build_client(httpx.MockTransport(handler))

    try:
        with pytest.raises(ProviderRequestError) as error_info:
            await client.search(
                search_query="   ",
            )
    finally:
        await client.close()

    assert error_info.value.code == "arxiv_empty_search_query"
    assert error_info.value.retryable is False


@pytest.mark.asyncio
async def test_search_rejects_excessive_result_count() -> None:
    """Configured per-request result limits should be enforced."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise AssertionError("HTTP request should not be executed.")

    client = build_client(
        httpx.MockTransport(handler),
        settings=build_settings(
            max_results_per_request=25,
        ),
    )

    try:
        with pytest.raises(ProviderRequestError) as error_info:
            await client.search(
                search_query="all:RAG",
                max_results=26,
            )
    finally:
        await client.close()

    assert error_info.value.code == "arxiv_max_results_exceeded"


@pytest.mark.asyncio
async def test_get_paper_rejects_invalid_identifier() -> None:
    """Malformed arXiv identifiers should fail locally."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise AssertionError("HTTP request should not be executed.")

    client = build_client(httpx.MockTransport(handler))

    try:
        with pytest.raises(ProviderRequestError) as error_info:
            await client.get_paper(
                arxiv_id="not-an-arxiv-id",
            )
    finally:
        await client.close()

    assert error_info.value.code == "arxiv_invalid_paper_id"


@pytest.mark.asyncio
async def test_429_is_normalized() -> None:
    """Rate-limit responses should become ProviderRateLimitError."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=429,
            headers={
                "Retry-After": "6",
                "Content-Type": "application/atom+xml",
            },
            text="<error>Too Many Requests</error>",
        )

    client = build_client(httpx.MockTransport(handler))

    try:
        with pytest.raises(ProviderRateLimitError) as error_info:
            await client.search(
                search_query="all:RAG",
            )
    finally:
        await client.close()

    assert error_info.value.retryable is True
    assert error_info.value.status_code == 429
    assert error_info.value.retry_after_seconds == 6


@pytest.mark.asyncio
async def test_invalid_content_type_is_rejected() -> None:
    """Successful non-XML responses should not reach the parser layer."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "text/html",
            },
            text="<html>Unexpected page</html>",
        )

    client = build_client(httpx.MockTransport(handler))

    try:
        with pytest.raises(ProviderResponseError) as error_info:
            await client.search(
                search_query="all:RAG",
            )
    finally:
        await client.close()

    assert error_info.value.code == "arxiv_unexpected_content_type"


@pytest.mark.asyncio
async def test_empty_success_response_is_rejected() -> None:
    """Empty successful responses should become response errors."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/atom+xml",
            },
            text="",
        )

    client = build_client(httpx.MockTransport(handler))

    try:
        with pytest.raises(ProviderResponseError) as error_info:
            await client.search(
                search_query="all:RAG",
            )
    finally:
        await client.close()

    assert error_info.value.code == "arxiv_empty_response"


@pytest.mark.asyncio
async def test_timeout_is_normalized_after_retry_exhaustion() -> None:
    """Repeated timeouts should become ProviderTransportError."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ReadTimeout(
            "Timed out",
            request=request,
        )

    client = build_client(
        httpx.MockTransport(handler),
        settings=build_settings(
            retry_attempts=1,
        ),
    )

    try:
        with pytest.raises(ProviderTransportError) as error_info:
            await client.search(
                search_query="all:RAG",
            )
    finally:
        await client.close()

    assert error_info.value.code == "arxiv_timeout"
    assert error_info.value.retryable is True


@pytest.mark.asyncio
async def test_retryable_failure_is_retried() -> None:
    """Temporary upstream failures should be retried."""

    call_count = 0

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal call_count

        call_count += 1

        if call_count == 1:
            return httpx.Response(
                status_code=503,
                headers={
                    "Retry-After": "0",
                    "Content-Type": "application/atom+xml",
                },
                text="<error>Unavailable</error>",
            )

        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/atom+xml",
            },
            text=ATOM_FEED,
        )

    client = build_client(
        httpx.MockTransport(handler),
        settings=build_settings(
            retry_attempts=2,
        ),
    )

    try:
        result = await client.search(
            search_query="all:RAG",
        )
    finally:
        await client.close()

    assert call_count == 2
    assert result == ATOM_FEED.strip()
