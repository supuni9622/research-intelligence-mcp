"""Semantic Scholar provider composition root."""

from __future__ import annotations

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.http import (
    create_async_http_client,
)
from research_intelligence_mcp.infrastructure.rate_limit import (
    AsyncRateLimiter,
)
from research_intelligence_mcp.providers.semantic_scholar.client import (
    SemanticScholarClient,
)
from research_intelligence_mcp.providers.semantic_scholar.provider import (
    SemanticScholarProvider,
)


def create_semantic_scholar_client(
    settings: Settings,
) -> SemanticScholarClient:
    """Create the fully configured Semantic Scholar API client."""

    graph_rate_limiter = AsyncRateLimiter(
        max_rate=(settings.semantic_scholar_rate_limit_requests),
        time_period_seconds=(settings.semantic_scholar_rate_limit_period_seconds),
    )

    recommendations_rate_limiter = AsyncRateLimiter(
        max_rate=(settings.semantic_scholar_rate_limit_requests),
        time_period_seconds=(settings.semantic_scholar_rate_limit_period_seconds),
    )

    graph_http_client = create_async_http_client(
        settings=settings,
        rate_limiter=graph_rate_limiter,
        base_url=str(settings.semantic_scholar_graph_base_url).rstrip("/"),
    )

    recommendations_http_client = create_async_http_client(
        settings=settings,
        rate_limiter=recommendations_rate_limiter,
        base_url=str(settings.semantic_scholar_recommendations_base_url).rstrip("/"),
    )

    return SemanticScholarClient(
        graph_http_client=graph_http_client,
        recommendations_http_client=(recommendations_http_client),
        settings=settings,
    )


def create_semantic_scholar_provider(
    settings: Settings,
) -> SemanticScholarProvider:
    """Create the canonical Semantic Scholar provider."""

    return SemanticScholarProvider(
        client=create_semantic_scholar_client(settings),
    )
