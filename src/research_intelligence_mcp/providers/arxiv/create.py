"""arXiv provider infrastructure composition."""

from __future__ import annotations

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.http import (
    create_async_http_client,
)
from research_intelligence_mcp.infrastructure.rate_limit import (
    AsyncRateLimiter,
)
from research_intelligence_mcp.providers.arxiv.client import (
    ArxivClient,
)
from research_intelligence_mcp.providers.arxiv.provider import (
    ArxivProvider,
)


def create_arxiv_client(
    settings: Settings,
) -> ArxivClient:
    """Create the fully configured arXiv API client."""

    rate_limiter = AsyncRateLimiter(
        max_rate=settings.arxiv_rate_limit_requests,
        time_period_seconds=settings.arxiv_rate_limit_period_seconds,
    )

    http_client = create_async_http_client(
        settings=settings,
        rate_limiter=rate_limiter,
        base_url=str(settings.arxiv_base_url).rstrip("/"),
        default_headers={
            "Accept": "application/atom+xml, application/xml;q=0.9",
        },
    )

    return ArxivClient(
        http_client=http_client,
        settings=settings,
    )


def create_arxiv_provider(
    settings: Settings,
) -> ArxivProvider:
    """Create the canonical arXiv paper provider."""

    return ArxivProvider(
        client=create_arxiv_client(settings),
    )
