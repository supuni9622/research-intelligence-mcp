"""Tests for the Semantic Scholar API client."""

from __future__ import annotations

import httpx
import pytest

from research_intelligence_mcp.config.settings import (
    Settings,
)
from research_intelligence_mcp.infrastructure.http import (
    create_async_http_client,
)
from research_intelligence_mcp.infrastructure.rate_limit import (
    UnlimitedRateLimiter,
)
from research_intelligence_mcp.providers.errors import (
    ProviderRateLimitError,
)
from research_intelligence_mcp.providers.semantic_scholar.client import (
    SemanticScholarClient,
)


def build_settings(
    *,
    api_key: str | None = None,
    retry_attempts: int = 1,
) -> Settings:
    """Build deterministic test settings."""

    values: dict[str, object] = {
        "_env_file": None,
        "SEMANTIC_SCHOLAR_MAX_RETRY_ATTEMPTS": (retry_attempts),
        "SEMANTIC_SCHOLAR_RETRY_MIN_SECONDS": 0,
        "SEMANTIC_SCHOLAR_RETRY_MAX_SECONDS": 1,
    }

    if api_key is not None:
        values["SEMANTIC_SCHOLAR_API_KEY"] = api_key

    return Settings(**values)


def build_client(
    handler: httpx.AsyncBaseTransport,
    *,
    settings: Settings | None = None,
) -> SemanticScholarClient:
    """Build a client backed by a mock transport."""

    resolved_settings = settings or build_settings()

    graph_client = create_async_http_client(
        settings=resolved_settings,
        rate_limiter=UnlimitedRateLimiter(),
        base_url="https://graph.example.test",
        transport=handler,
    )

    recommendations_client = create_async_http_client(
        settings=resolved_settings,
        rate_limiter=UnlimitedRateLimiter(),
        base_url="https://recommendations.example.test",
        transport=handler,
    )

    return SemanticScholarClient(
        graph_http_client=graph_client,
        recommendations_http_client=(recommendations_client),
        settings=resolved_settings,
    )


@pytest.mark.asyncio
async def test_search_papers() -> None:
    """Search should parse a typed provider response."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == "/paper/search"
        assert request.url.params["query"] == "RAG"

        return httpx.Response(
            status_code=200,
            json={
                "total": 1,
                "offset": 0,
                "next": 1,
                "data": [
                    {
                        "paperId": "paper-1",
                        "title": "RAG Paper",
                        "year": 2024,
                        "authors": [
                            {
                                "authorId": "author-1",
                                "name": "Ada Researcher",
                            }
                        ],
                    }
                ],
            },
        )

    client = build_client(httpx.MockTransport(handler))

    try:
        result = await client.search_papers(
            query="RAG",
            limit=10,
        )
    finally:
        await client.close()

    assert result.total == 1
    assert result.data[0].paper_id == "paper-1"


@pytest.mark.asyncio
async def test_api_key_is_added_conditionally() -> None:
    """Configured API keys should be sent using x-api-key."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"

        return httpx.Response(
            status_code=200,
            json={
                "paperId": "paper-1",
                "title": "Paper",
            },
        )

    client = build_client(
        httpx.MockTransport(handler),
        settings=build_settings(api_key="test-key"),
    )

    try:
        await client.get_paper(paper_id="paper-1")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_429_is_normalized() -> None:
    """Rate limits should become ProviderRateLimitError."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=429,
            headers={"Retry-After": "5"},
            json={
                "message": "Too Many Requests",
                "code": "429",
            },
        )

    client = build_client(httpx.MockTransport(handler))

    try:
        with pytest.raises(ProviderRateLimitError) as error_info:
            await client.search_papers(
                query="RAG",
                limit=10,
            )
    finally:
        await client.close()

    assert error_info.value.retryable is True
    assert error_info.value.retry_after_seconds == 5
