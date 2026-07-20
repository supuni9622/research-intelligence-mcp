"""Concurrent execution of provider searches."""

from __future__ import annotations

import asyncio

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    ProviderFailure,
    SearchRequest,
    SearchResult,
)
from research_intelligence_mcp.providers.errors import ProviderError
from research_intelligence_mcp.services.search.provider_registry import (
    ProviderRegistry,
)


class ProviderExecutor:
    """Execute selected paper providers concurrently."""

    def __init__(
        self,
        registry: ProviderRegistry,
    ) -> None:
        """Initialize the executor."""

        self._registry = registry

    async def execute(
        self,
        request: SearchRequest,
    ) -> tuple[SearchResult, ...]:
        """Execute searches while isolating provider failures."""

        tasks = tuple(
            self._execute_provider(
                request=request,
                provider_name=provider_name,
            )
            for provider_name in request.providers
        )

        results = await asyncio.gather(*tasks)

        return tuple(results)

    async def _execute_provider(
        self,
        *,
        request: SearchRequest,
        provider_name: ProviderName,
    ) -> SearchResult:
        """Execute one provider and normalize failures."""

        provider = self._registry.get(provider_name)

        try:
            return await provider.search_papers(request)
        except ProviderError as exc:
            return self._failure_result(
                request=request,
                failure=ProviderFailure(
                    provider=provider.name,
                    code=exc.code,
                    message=exc.message,
                    retryable=exc.retryable,
                ),
            )
        except Exception:
            return self._failure_result(
                request=request,
                failure=ProviderFailure(
                    provider=provider.name,
                    code="unexpected_provider_error",
                    message=(f"{provider.name.value} failed with an unexpected error."),
                    retryable=False,
                ),
            )

    @staticmethod
    def _failure_result(
        *,
        request: SearchRequest,
        failure: ProviderFailure,
    ) -> SearchResult:
        """Create a canonical failed-provider search result."""

        return SearchResult(
            query=request.query,
            papers=(),
            pagination=PaginationMetadata(
                offset=request.offset,
                limit=request.limit,
                returned=0,
                total=None,
                has_more=False,
            ),
            providers_requested=(failure.provider,),
            providers_succeeded=(),
            failures=(failure,),
            warnings=(),
        )
