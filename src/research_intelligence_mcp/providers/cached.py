"""Caching decorator for canonical academic-paper providers."""

from __future__ import annotations

from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.domain.models import (
    Paper,
    PaperReference,
)
from research_intelligence_mcp.domain.requests import (
    SearchRequest,
    SearchResult,
)
from research_intelligence_mcp.infrastructure.cache.base import (
    AsyncCache,
)
from research_intelligence_mcp.infrastructure.cache.keys import (
    build_paper_cache_key,
    build_search_cache_key,
)
from research_intelligence_mcp.infrastructure.logging import (
    get_logger,
)
from research_intelligence_mcp.providers.base import (
    PaperProvider,
)

logger = get_logger(__name__)


class CachedPaperProvider:
    """Add bounded caching to a canonical paper provider.

    Successful search and single-paper results are cached. Exceptions are
    intentionally never cached.

    Citation graphs, references, recommendations, and access-resolution
    behavior continue through the wrapped provider without dedicated caching.
    Access resolution still benefits indirectly because it calls get_paper.
    """

    def __init__(
        self,
        *,
        provider: PaperProvider,
        search_cache: AsyncCache[str, SearchResult],
        paper_cache: AsyncCache[str, Paper],
        enabled: bool = True,
    ) -> None:
        """Initialize the provider caching decorator."""

        self._provider = provider
        self._search_cache = search_cache
        self._paper_cache = paper_cache
        self._enabled = enabled

    @property
    def name(self) -> ProviderName:
        """Return the wrapped provider identifier."""

        return self._provider.name

    async def search_papers(
        self,
        request: SearchRequest,
    ) -> SearchResult:
        """Search papers using the provider search cache."""

        if not self._enabled:
            return await self._provider.search_papers(request)

        cache_key = build_search_cache_key(
            provider=self.name,
            request=request,
        )

        cached_result = await self._search_cache.get(cache_key)

        if cached_result.found:
            if cached_result.value is None:
                raise RuntimeError(
                    "Search cache reported a hit without a cached value."
                )

            logger.debug(
                "provider_search_cache_hit",
                provider=self.name.value,
            )

            return cached_result.value

        logger.debug(
            "provider_search_cache_miss",
            provider=self.name.value,
        )

        result = await self._provider.search_papers(request)

        await self._search_cache.set(
            cache_key,
            result,
        )

        return result

    async def get_paper(
        self,
        paper_id: str,
    ) -> Paper:
        """Retrieve one paper using the provider paper cache."""

        if not self._enabled:
            return await self._provider.get_paper(paper_id)

        cache_key = build_paper_cache_key(
            provider=self.name,
            paper_id=paper_id,
        )

        cached_paper = await self._paper_cache.get(cache_key)

        if cached_paper.found:
            if cached_paper.value is None:
                raise RuntimeError("Paper cache reported a hit without a cached value.")

            logger.debug(
                "provider_paper_cache_hit",
                provider=self.name.value,
            )

            return cached_paper.value

        logger.debug(
            "provider_paper_cache_miss",
            provider=self.name.value,
        )

        paper = await self._provider.get_paper(paper_id)

        await self._paper_cache.set(
            cache_key,
            paper,
        )

        return paper

    async def get_citations(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Delegate citation retrieval without caching."""

        return await self._provider.get_citations(
            paper_id,
            limit=limit,
            offset=offset,
        )

    async def get_references(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Delegate reference retrieval without caching."""

        return await self._provider.get_references(
            paper_id,
            limit=limit,
            offset=offset,
        )

    async def get_related_papers(
        self,
        paper_id: str,
        *,
        limit: int = 10,
        negative_paper_ids: list[str] | None = None,
    ) -> list[Paper]:
        """Delegate related-paper retrieval without caching."""

        return await self._provider.get_related_papers(
            paper_id,
            limit=limit,
            negative_paper_ids=negative_paper_ids,
        )

    async def close(self) -> None:
        """Close the wrapped provider."""

        await self._provider.close()
