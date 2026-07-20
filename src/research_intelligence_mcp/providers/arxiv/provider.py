"""Canonical arXiv paper provider.

This module implements the provider-neutral PaperProvider contract using the
arXiv client, secure Atom parser, and canonical mapper.

The provider also owns translation from canonical SearchRequest values into
arXiv-specific query syntax.
"""

from __future__ import annotations

from typing import Final

from research_intelligence_mcp.domain.enums import (
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.domain.models import (
    Paper,
    PaperReference,
)
from research_intelligence_mcp.domain.requests import (
    SearchRequest,
    SearchResult,
)
from research_intelligence_mcp.providers.arxiv.client import (
    ArxivClient,
)
from research_intelligence_mcp.providers.arxiv.mapper import (
    ArxivMapper,
)
from research_intelligence_mcp.providers.arxiv.parser import (
    ArxivParser,
)
from research_intelligence_mcp.providers.errors import (
    ProviderNotFoundError,
    ProviderRequestError,
)

_PROVIDER: Final = ProviderName.ARXIV

_ARXIV_SORT_RELEVANCE: Final = "relevance"
_ARXIV_SORT_SUBMITTED_DATE: Final = "submittedDate"
_ARXIV_SORT_DESCENDING: Final = "descending"

_MINIMUM_YEAR: Final = 1400
_MAXIMUM_YEAR: Final = 2200


class ArxivProvider:
    """arXiv implementation of the canonical paper-provider contract."""

    def __init__(
        self,
        *,
        client: ArxivClient,
        parser: ArxivParser | None = None,
        mapper: ArxivMapper | None = None,
    ) -> None:
        """Initialize the arXiv provider."""

        self._client = client
        self._parser = parser or ArxivParser()
        self._mapper = mapper or ArxivMapper()

    @property
    def name(self) -> ProviderName:
        """Return the canonical provider identifier."""

        return ProviderName.ARXIV

    async def search_papers(
        self,
        request: SearchRequest,
    ) -> SearchResult:
        """Search papers through the arXiv Atom API."""

        search_query = self._build_search_query(request)

        sort_by, sort_order = self._resolve_sort(request.sort)

        raw_xml = await self._client.search(
            search_query=search_query,
            start=request.offset,
            max_results=request.limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        response = self._parser.parse_feed(raw_xml)

        return self._mapper.to_search_result(
            request=request,
            response=response,
        )

    async def get_paper(
        self,
        paper_id: str,
    ) -> Paper:
        """Retrieve one canonical paper by arXiv identifier."""

        raw_xml = await self._client.get_paper(
            arxiv_id=paper_id,
        )

        response = self._parser.parse_feed(raw_xml)

        if not response.entries:
            raise ProviderNotFoundError(
                provider=_PROVIDER,
                code="arxiv_paper_not_found",
                message="The requested arXiv paper was not found.",
                retryable=False,
                status_code=404,
                details={
                    "paper_id": paper_id,
                },
            )

        return self._mapper.to_paper(response.entries[0])

    async def get_citations(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Reject citation retrieval because arXiv has no citation graph API."""

        self._validate_unsupported_operation_arguments(
            paper_id=paper_id,
            limit=limit,
            offset=offset,
        )

        raise ProviderRequestError(
            provider=_PROVIDER,
            code="arxiv_citations_not_supported",
            message=(
                "arXiv does not provide a citation graph API. "
                "Use Semantic Scholar for citation retrieval."
            ),
            retryable=False,
        )

    async def get_references(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Reject reference retrieval because arXiv has no reference graph API."""

        self._validate_unsupported_operation_arguments(
            paper_id=paper_id,
            limit=limit,
            offset=offset,
        )

        raise ProviderRequestError(
            provider=_PROVIDER,
            code="arxiv_references_not_supported",
            message=(
                "arXiv does not provide a reference graph API. "
                "Use Semantic Scholar for reference retrieval."
            ),
            retryable=False,
        )

    async def get_related_papers(
        self,
        paper_id: str,
        *,
        limit: int = 10,
        negative_paper_ids: list[str] | None = None,
    ) -> list[Paper]:
        """Reject recommendation retrieval because arXiv has no related API."""

        normalized_paper_id = paper_id.strip()

        if not normalized_paper_id:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_paper_id",
                message="Paper identifier cannot be empty.",
                retryable=False,
            )

        if limit < 1:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_related_limit",
                message="Related-paper limit must be at least one.",
                retryable=False,
            )

        if negative_paper_ids is not None:
            for negative_paper_id in negative_paper_ids:
                if not negative_paper_id.strip():
                    raise ProviderRequestError(
                        provider=_PROVIDER,
                        code="arxiv_invalid_negative_paper_id",
                        message=("Negative paper identifiers cannot be empty."),
                        retryable=False,
                    )

        raise ProviderRequestError(
            provider=_PROVIDER,
            code="arxiv_related_papers_not_supported",
            message=(
                "arXiv does not provide a related-paper recommendation API. "
                "Use Semantic Scholar for related-paper discovery."
            ),
            retryable=False,
        )

    async def close(self) -> None:
        """Close managed arXiv resources."""

        await self._client.close()

    @classmethod
    def _build_search_query(
        cls,
        request: SearchRequest,
    ) -> str:
        """Translate a canonical request into arXiv query syntax."""

        expressions: list[str] = [
            cls._build_text_expression(request.query),
        ]

        category_expression = cls._build_category_expression(request.fields_of_study)

        if category_expression is not None:
            expressions.append(category_expression)

        date_expression = cls._build_date_expression(
            year_from=request.year_from,
            year_to=request.year_to,
        )

        if date_expression is not None:
            expressions.append(date_expression)

        return " AND ".join(f"({expression})" for expression in expressions)

    @classmethod
    def _build_text_expression(
        cls,
        query: str,
    ) -> str:
        """Build an arXiv all-fields text expression."""

        escaped_query = cls._escape_query_phrase(query)

        return f'all:"{escaped_query}"'

    @classmethod
    def _build_category_expression(
        cls,
        fields_of_study: tuple[str, ...],
    ) -> str | None:
        """Build an OR expression for requested arXiv categories."""

        categories = [
            cls._build_single_category_expression(field)
            for field in fields_of_study
            if field.strip()
        ]

        if not categories:
            return None

        return " OR ".join(categories)

    @classmethod
    def _build_single_category_expression(
        cls,
        value: str,
    ) -> str:
        """Build one escaped arXiv category expression."""

        normalized = " ".join(value.split())
        escaped = cls._escape_query_phrase(normalized)

        return f'cat:"{escaped}"'

    @staticmethod
    def _build_date_expression(
        *,
        year_from: int | None,
        year_to: int | None,
    ) -> str | None:
        """Build an inclusive submitted-date range expression."""

        if year_from is None and year_to is None:
            return None

        resolved_year_from = year_from or _MINIMUM_YEAR
        resolved_year_to = year_to or _MAXIMUM_YEAR

        start = f"{resolved_year_from:04d}01010000"
        end = f"{resolved_year_to:04d}12312359"

        return f"submittedDate:[{start} TO {end}]"

    @staticmethod
    def _resolve_sort(
        sort: SearchSort,
    ) -> tuple[str, str]:
        """Translate canonical sorting into arXiv sorting."""

        if sort == SearchSort.PUBLICATION_DATE:
            return (
                _ARXIV_SORT_SUBMITTED_DATE,
                _ARXIV_SORT_DESCENDING,
            )

        return (
            _ARXIV_SORT_RELEVANCE,
            _ARXIV_SORT_DESCENDING,
        )

    @staticmethod
    def _escape_query_phrase(
        value: str,
    ) -> str:
        """Escape characters that could break an arXiv quoted expression."""

        normalized = " ".join(value.split())

        return normalized.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _validate_unsupported_operation_arguments(
        *,
        paper_id: str,
        limit: int,
        offset: int,
    ) -> None:
        """Validate shared citation/reference operation arguments."""

        if not paper_id.strip():
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_paper_id",
                message="Paper identifier cannot be empty.",
                retryable=False,
            )

        if limit < 1:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_graph_limit",
                message="Result limit must be at least one.",
                retryable=False,
            )

        if offset < 0:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_graph_offset",
                message="Result offset cannot be negative.",
                retryable=False,
            )
