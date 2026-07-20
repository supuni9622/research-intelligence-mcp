"""Canonical Semantic Scholar paper provider."""

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
from research_intelligence_mcp.providers.semantic_scholar.client import (
    SemanticScholarClient,
)
from research_intelligence_mcp.providers.semantic_scholar.mapper import (
    SemanticScholarMapper,
)


class SemanticScholarProvider:
    """Semantic Scholar implementation of the paper-provider contract."""

    def __init__(
        self,
        *,
        client: SemanticScholarClient,
        mapper: SemanticScholarMapper | None = None,
    ) -> None:
        self._client = client
        self._mapper = mapper or SemanticScholarMapper()

    @property
    def name(self) -> ProviderName:
        """Return the canonical provider identifier."""

        return ProviderName.SEMANTIC_SCHOLAR

    async def search_papers(
        self,
        request: SearchRequest,
    ) -> SearchResult:
        """Search papers through Semantic Scholar."""

        response = await self._client.search_papers(
            query=request.query,
            limit=request.limit,
            offset=request.offset,
            year_from=request.year_from,
            year_to=request.year_to,
            open_access_only=request.open_access_only,
        )

        return self._mapper.to_search_result(
            request=request,
            response=response,
        )

    async def get_paper(
        self,
        paper_id: str,
    ) -> Paper:
        """Retrieve one canonical paper."""

        response = await self._client.get_paper(
            paper_id=paper_id,
        )

        return self._mapper.to_paper(response)

    async def get_citations(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Retrieve canonical citation relationships."""

        response = await self._client.get_citations(
            paper_id=paper_id,
            limit=limit,
            offset=offset,
        )

        return self._mapper.to_citations(response)

    async def get_references(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Retrieve canonical reference relationships."""

        response = await self._client.get_references(
            paper_id=paper_id,
            limit=limit,
            offset=offset,
        )

        return self._mapper.to_references(response)

    async def get_related_papers(
        self,
        paper_id: str,
        *,
        limit: int = 10,
        negative_paper_ids: list[str] | None = None,
    ) -> list[Paper]:
        """Retrieve recommendations related to a paper."""

        response = await self._client.get_recommendations(
            positive_paper_ids=[paper_id],
            negative_paper_ids=negative_paper_ids,
            limit=limit,
        )

        return [self._mapper.to_paper(item) for item in response.recommended_papers]

    async def close(self) -> None:
        """Close provider resources."""

        await self._client.close()
