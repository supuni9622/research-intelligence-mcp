"""arXiv response-to-domain mapping.

This module converts parsed arXiv provider response models into canonical,
provider-neutral domain models.

No HTTP behavior, XML parsing, retries, or provider composition belongs in
this module.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Final

from pydantic import AnyHttpUrl, TypeAdapter, ValidationError

from research_intelligence_mcp.domain.enums import (
    AccessStatus,
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.domain.identifiers import (
    PaperIdentifiers,
    normalize_arxiv_id,
    normalize_doi,
)
from research_intelligence_mcp.domain.models import (
    Author,
    Paper,
    PaperAccess,
)
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    SearchRequest,
    SearchResult,
)
from research_intelligence_mcp.providers.arxiv.models import (
    ArxivAuthorResponse,
    ArxivCategoryResponse,
    ArxivEntryResponse,
    ArxivFeedResponse,
    ArxivLinkResponse,
)
from research_intelligence_mcp.providers.errors import (
    ProviderResponseError,
)

_PROVIDER: Final = ProviderName.ARXIV

_HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)

_ARXIV_FALLBACK_VENUE: Final = "arXiv"


class ArxivMapper:
    """Map parsed arXiv responses into canonical domain models."""

    @classmethod
    def to_author(
        cls,
        response: ArxivAuthorResponse,
    ) -> Author:
        """Map one arXiv author into a canonical author."""

        return Author(
            name=response.name,
            semantic_scholar_id=None,
            affiliations=tuple(response.affiliations),
            homepage_url=None,
        )

    @classmethod
    def to_identifiers(
        cls,
        response: ArxivEntryResponse,
    ) -> PaperIdentifiers:
        """Map arXiv and DOI identifiers into canonical identifiers."""

        arxiv_id = cls._extract_arxiv_id(response.entry_id)

        return PaperIdentifiers(
            doi=cls._normalize_optional_doi(response.doi),
            arxiv_id=arxiv_id,
            semantic_scholar_id=None,
            corpus_id=None,
            pmid=None,
        )

    @classmethod
    def to_access(
        cls,
        response: ArxivEntryResponse,
    ) -> PaperAccess:
        """Map arXiv landing-page and PDF access information."""

        landing_page_url = cls._resolve_landing_page_url(response)
        pdf_url = cls._resolve_pdf_url(response)

        return PaperAccess(
            status=AccessStatus.OPEN_ACCESS,
            landing_page_url=landing_page_url,
            pdf_url=pdf_url,
            license=None,
            repository=ProviderName.ARXIV,
        )

    @classmethod
    def to_paper(
        cls,
        response: ArxivEntryResponse,
    ) -> Paper:
        """Map one parsed arXiv entry into a canonical paper."""

        publication_date = cls._resolve_publication_date(response)
        year = publication_date.year if publication_date is not None else None

        authors = tuple(
            cls.to_author(author_response) for author_response in response.authors
        )

        return Paper(
            identifiers=cls.to_identifiers(response),
            title=response.title,
            authors=authors,
            abstract=cls._clean_optional_string(response.summary),
            publication_date=publication_date,
            year=year,
            venue=cls._resolve_venue(response),
            fields_of_study=tuple(cls._resolve_fields_of_study(response)),
            citation_count=None,
            reference_count=None,
            access=cls.to_access(response),
            sources=(ProviderName.ARXIV,),
        )

    @classmethod
    def to_search_result(
        cls,
        *,
        request: SearchRequest,
        response: ArxivFeedResponse,
    ) -> SearchResult:
        """Map an arXiv search feed into a canonical search result."""

        papers = tuple(
            cls.to_paper(entry) for entry in response.entries[: request.limit]
        )

        warnings = cls._build_search_warnings(request)

        returned = len(papers)
        total = max(response.total_results, returned)

        has_more = cls._resolve_has_more(
            offset=request.offset,
            returned=returned,
            total=total,
        )

        pagination = PaginationMetadata(
            offset=request.offset,
            limit=request.limit,
            returned=returned,
            total=total,
            has_more=has_more,
        )

        return SearchResult(
            query=request.query,
            papers=papers,
            pagination=pagination,
            providers_requested=request.providers,
            providers_succeeded=(ProviderName.ARXIV,),
            failures=(),
            warnings=tuple(warnings),
        )

    @classmethod
    def _extract_arxiv_id(
        cls,
        entry_id: str,
    ) -> str:
        """Extract and normalize an arXiv identifier from an entry URL."""

        try:
            return normalize_arxiv_id(entry_id)
        except ValueError as exc:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_invalid_entry_identifier",
                message=("arXiv returned a paper entry with an invalid identifier."),
                retryable=False,
                details={
                    "entry_id": entry_id,
                },
            ) from exc

    @classmethod
    def _resolve_landing_page_url(
        cls,
        response: ArxivEntryResponse,
    ) -> AnyHttpUrl | None:
        """Resolve the canonical arXiv abstract-page URL."""

        entry_url = cls._parse_http_url(response.entry_id)

        if entry_url is not None:
            return entry_url

        for link in response.links:
            if cls._is_landing_page_link(link):
                parsed_url = cls._parse_http_url(link.href)

                if parsed_url is not None:
                    return parsed_url

        return None

    @classmethod
    def _resolve_pdf_url(
        cls,
        response: ArxivEntryResponse,
    ) -> AnyHttpUrl | None:
        """Resolve the best available arXiv PDF URL."""

        for link in response.links:
            if not cls._is_pdf_link(link):
                continue

            parsed_url = cls._parse_http_url(link.href)

            if parsed_url is not None:
                return parsed_url

        arxiv_id = cls._extract_arxiv_id(response.entry_id)

        return cls._parse_http_url(
            f"https://arxiv.org/pdf/{arxiv_id}",
        )

    @classmethod
    def _resolve_fields_of_study(
        cls,
        response: ArxivEntryResponse,
    ) -> list[str]:
        """Resolve and deduplicate arXiv subject categories."""

        categories: list[ArxivCategoryResponse] = []

        if response.primary_category is not None:
            categories.append(response.primary_category)

        categories.extend(response.categories)

        return cls._deduplicate_strings(category.term for category in categories)

    @classmethod
    def _resolve_venue(
        cls,
        response: ArxivEntryResponse,
    ) -> str:
        """Resolve the best available publication venue."""

        journal_reference = cls._clean_optional_string(response.journal_reference)

        if journal_reference is not None:
            return journal_reference

        return _ARXIV_FALLBACK_VENUE

    @staticmethod
    def _resolve_publication_date(
        response: ArxivEntryResponse,
    ) -> date | None:
        """Resolve the canonical initial publication date."""

        if response.published is not None:
            return response.published.date()

        if response.updated is not None:
            return response.updated.date()

        return None

    @staticmethod
    def _resolve_has_more(
        *,
        offset: int,
        returned: int,
        total: int,
    ) -> bool:
        """Determine whether another provider result page exists."""

        if returned == 0:
            return False

        return offset + returned < total

    @staticmethod
    def _is_pdf_link(
        link: ArxivLinkResponse,
    ) -> bool:
        """Return whether an Atom link represents a PDF."""

        title = ArxivMapper._clean_optional_string(link.title)
        content_type = ArxivMapper._clean_optional_string(link.content_type)
        href = link.href.casefold()

        if title is not None and title.casefold() == "pdf":
            return True

        if content_type is not None and content_type.casefold() == "application/pdf":
            return True

        return "/pdf/" in href or href.endswith(".pdf")

    @staticmethod
    def _is_landing_page_link(
        link: ArxivLinkResponse,
    ) -> bool:
        """Return whether an Atom link represents an abstract page."""

        relation = ArxivMapper._clean_optional_string(link.rel)
        content_type = ArxivMapper._clean_optional_string(link.content_type)

        if relation is not None and relation.casefold() == "alternate":
            return True

        return content_type is not None and content_type.casefold() == "text/html"

    @staticmethod
    def _normalize_optional_doi(
        value: str | None,
    ) -> str | None:
        """Normalize a DOI while tolerating invalid upstream values."""

        cleaned = ArxivMapper._clean_optional_string(value)

        if cleaned is None:
            return None

        try:
            return normalize_doi(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _parse_http_url(
        value: str | None,
    ) -> AnyHttpUrl | None:
        """Parse a provider URL, omitting invalid URLs safely."""

        cleaned = ArxivMapper._clean_optional_string(value)

        if cleaned is None:
            return None

        try:
            return _HTTP_URL_ADAPTER.validate_python(cleaned)
        except ValidationError:
            return None

    @staticmethod
    def _clean_optional_string(
        value: str | None,
    ) -> str | None:
        """Normalize whitespace and convert blank strings to None."""

        if value is None:
            return None

        normalized = " ".join(value.split())

        return normalized or None

    @staticmethod
    def _deduplicate_strings(
        values: Iterable[str],
    ) -> list[str]:
        """Normalize and deduplicate strings while preserving order."""

        deduplicated: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = ArxivMapper._clean_optional_string(value)

            if normalized is None:
                continue

            comparison_key = normalized.casefold()

            if comparison_key in seen:
                continue

            seen.add(comparison_key)
            deduplicated.append(normalized)

        return deduplicated

    @staticmethod
    def _build_search_warnings(
        request: SearchRequest,
    ) -> list[str]:
        """Build warnings for unsupported or approximate search behavior."""

        warnings: list[str] = []

        if request.sort == SearchSort.CITATION_COUNT:
            warnings.append(
                "arXiv does not support citation-count sorting; "
                "results were ordered by relevance."
            )

        return warnings
