"""Shared test helpers for federated search services."""

from __future__ import annotations

from collections.abc import Sequence

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.domain.identifiers import PaperIdentifiers
from research_intelligence_mcp.domain.models import Paper, PaperReference
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    SearchRequest,
    SearchResult,
)
from research_intelligence_mcp.providers.errors import ProviderError


class StubProvider:
    """Configurable in-memory paper provider for service tests."""

    def __init__(
        self,
        *,
        name: ProviderName,
        result: SearchResult | None = None,
        error: Exception | None = None,
    ) -> None:
        """Initialize the provider."""

        self._name = name
        self._result = result
        self._error = error
        self.requests: list[SearchRequest] = []
        self.closed = False

    @property
    def name(self) -> ProviderName:
        """Return the provider identifier."""

        return self._name

    async def search_papers(
        self,
        request: SearchRequest,
    ) -> SearchResult:
        """Return the configured result or raise the configured error."""

        self.requests.append(request)

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise RuntimeError("StubProvider requires either a result or an error.")

        return self._result

    async def get_paper(
        self,
        paper_id: str,
    ) -> Paper:
        """Paper lookup is not required by these tests."""

        raise NotImplementedError

    async def get_citations(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Citation lookup is not required by these tests."""

        raise NotImplementedError

    async def get_references(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Reference lookup is not required by these tests."""

        raise NotImplementedError

    async def get_related_papers(
        self,
        paper_id: str,
        *,
        limit: int = 10,
        negative_paper_ids: list[str] | None = None,
    ) -> list[Paper]:
        """Related-paper lookup is not required by these tests."""

        raise NotImplementedError

    async def close(self) -> None:
        """Mark the provider as closed."""

        self.closed = True


def build_request(
    *,
    providers: tuple[ProviderName, ...] = (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    ),
    limit: int = 10,
    offset: int = 0,
) -> SearchRequest:
    """Build a canonical search request."""

    return SearchRequest(
        query="retrieval augmented generation",
        providers=providers,
        limit=limit,
        offset=offset,
    )


def build_paper(
    *,
    title: str,
    source: ProviderName,
    doi: str | None = None,
    arxiv_id: str | None = None,
    semantic_scholar_id: str | None = None,
    corpus_id: int | None = None,
    year: int | None = 2024,
    citation_count: int | None = 0,
    reference_count: int | None = 0,
    abstract: str | None = None,
) -> Paper:
    """Build a canonical paper."""

    if all(
        identifier is None
        for identifier in (
            doi,
            arxiv_id,
            semantic_scholar_id,
            corpus_id,
        )
    ):
        corpus_id = abs(hash((title, source.value))) % 1_000_000

    return Paper(
        identifiers=PaperIdentifiers(
            doi=doi,
            arxiv_id=arxiv_id,
            semantic_scholar_id=semantic_scholar_id,
            corpus_id=corpus_id,
        ),
        title=title,
        authors=(),
        abstract=abstract,
        publication_date=None,
        year=year,
        venue=None,
        fields_of_study=(),
        citation_count=citation_count,
        reference_count=reference_count,
        sources=(source,),
    )


def build_result(
    *,
    provider: ProviderName,
    papers: Sequence[Paper] = (),
    query: str = "retrieval augmented generation",
    total: int | None = None,
    has_more: bool = False,
    warnings: tuple[str, ...] = (),
) -> SearchResult:
    """Build a successful canonical provider result."""

    paper_tuple = tuple(papers)

    return SearchResult(
        query=query,
        papers=paper_tuple,
        pagination=PaginationMetadata(
            offset=0,
            limit=max(1, min(50, len(paper_tuple) or 10)),
            returned=len(paper_tuple),
            total=(total if total is not None else len(paper_tuple)),
            has_more=has_more,
        ),
        providers_requested=(provider,),
        providers_succeeded=(provider,),
        failures=(),
        warnings=warnings,
    )


def build_provider_error(
    *,
    provider: ProviderName,
) -> ProviderError:
    """Build a normalized retryable provider error."""

    return ProviderError(
        provider=provider,
        code="provider_unavailable",
        message="The provider is temporarily unavailable.",
        retryable=True,
        status_code=503,
    )
