"""Semantic Scholar response-to-domain mapping.

This module converts Semantic Scholar response models into canonical
provider-neutral domain models.

No HTTP, retry, or provider-client behavior belongs in this module.
"""

from __future__ import annotations

from pydantic import AnyHttpUrl, TypeAdapter, ValidationError

from research_intelligence_mcp.domain.enums import (
    AccessStatus,
    PaperRelationType,
    ProviderName,
)
from research_intelligence_mcp.domain.identifiers import (
    PaperIdentifiers,
)
from research_intelligence_mcp.domain.models import (
    Author,
    Paper,
    PaperAccess,
    PaperReference,
)
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    SearchRequest,
    SearchResult,
)
from research_intelligence_mcp.providers.semantic_scholar.models import (
    SemanticScholarAuthorResponse,
    SemanticScholarCitationEdgeResponse,
    SemanticScholarCitationsResponse,
    SemanticScholarExternalIdsResponse,
    SemanticScholarOpenAccessPdfResponse,
    SemanticScholarPaperResponse,
    SemanticScholarReferenceEdgeResponse,
    SemanticScholarReferencesResponse,
    SemanticScholarSearchResponse,
)

_HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)


class SemanticScholarMapper:
    """Map Semantic Scholar responses to canonical domain models."""

    @classmethod
    def to_author(
        cls,
        response: SemanticScholarAuthorResponse,
    ) -> Author | None:
        """Map one Semantic Scholar author."""

        name = cls._clean_optional_string(response.name)

        if name is None:
            return None

        return Author(
            name=name,
            semantic_scholar_id=cls._clean_optional_string(
                response.author_id
            ),
            affiliations=(),
            homepage_url=None,
        )

    @classmethod
    def to_identifiers(
        cls,
        response: SemanticScholarPaperResponse,
    ) -> PaperIdentifiers:
        """Map Semantic Scholar and external paper identifiers."""

        external_ids = (
            response.external_ids
            or SemanticScholarExternalIdsResponse()
        )

        raw_corpus_id: int | str | None = (
            external_ids.corpus_id
            if external_ids.corpus_id is not None
            else response.corpus_id
        )

        corpus_id = cls._normalize_corpus_id(
            raw_corpus_id
        )

        semantic_scholar_id = (
            cls._normalize_semantic_scholar_id(
                response.paper_id
            )
        )

        return PaperIdentifiers(
            doi=cls._clean_optional_string(
                external_ids.doi
            ),
            arxiv_id=cls._clean_optional_string(
                external_ids.arxiv
            ),
            semantic_scholar_id=semantic_scholar_id,
            corpus_id=corpus_id,
            pmid=cls._clean_optional_string(
                external_ids.pubmed
            ),
        )

    @classmethod
    def to_access(
        cls,
        response: SemanticScholarPaperResponse,
    ) -> PaperAccess:
        """Map open-access and provider URL metadata."""

        open_access_pdf = response.open_access_pdf

        pdf_url_value = (
            cls._clean_optional_string(
                open_access_pdf.url
            )
            if open_access_pdf is not None
            else None
        )

        landing_page_url_value = (
            cls._clean_optional_string(
                response.url
            )
        )

        license_name = (
            cls._clean_optional_string(
                open_access_pdf.license
            )
            if open_access_pdf is not None
            else None
        )

        status = cls._resolve_access_status(
            is_open_access=response.is_open_access,
            open_access_pdf=open_access_pdf,
        )

        return PaperAccess(
            status=status,
            landing_page_url=cls._parse_http_url(
                landing_page_url_value
            ),
            pdf_url=cls._parse_http_url(
                pdf_url_value
            ),
            license=license_name,
            repository=(
                ProviderName.SEMANTIC_SCHOLAR
                if pdf_url_value is not None
                else None
            ),
        )

    @classmethod
    def to_paper(
        cls,
        response: SemanticScholarPaperResponse,
    ) -> Paper:
        """Map one Semantic Scholar paper."""

        title = cls._clean_optional_string(
            response.title
        )

        if title is None:
            title = "Untitled paper"

        authors = tuple(
            author
            for item in response.authors
            if (
                author := cls.to_author(item)
            )
            is not None
        )

        return Paper(
            identifiers=cls.to_identifiers(response),
            title=title,
            authors=authors,
            abstract=cls._clean_optional_string(
                response.abstract
            ),
            publication_date=response.publication_date,
            year=response.year,
            venue=cls._resolve_venue(response),
            fields_of_study=tuple(
                cls._resolve_fields_of_study(
                    response
                )
            ),
            citation_count=response.citation_count,
            reference_count=response.reference_count,
            access=cls.to_access(response),
            sources=(
                ProviderName.SEMANTIC_SCHOLAR,
            ),
        )

    @classmethod
    def citation_to_reference(
        cls,
        response: SemanticScholarCitationEdgeResponse,
    ) -> PaperReference | None:
        """Map a Semantic Scholar citation edge."""

        if response.citing_paper is None:
            return None

        return PaperReference(
            relation=PaperRelationType.CITATION,
            paper=cls.to_paper(
                response.citing_paper
            ),
            contexts=tuple(
                cls._clean_string_collection(
                    response.contexts
                )
            ),
            intents=tuple(
                cls._clean_string_collection(
                    response.intents
                )
            ),
            is_influential=response.is_influential,
        )

    @classmethod
    def reference_to_reference(
        cls,
        response: SemanticScholarReferenceEdgeResponse,
    ) -> PaperReference | None:
        """Map a Semantic Scholar reference edge."""

        if response.cited_paper is None:
            return None

        return PaperReference(
            relation=PaperRelationType.REFERENCE,
            paper=cls.to_paper(
                response.cited_paper
            ),
            contexts=tuple(
                cls._clean_string_collection(
                    response.contexts
                )
            ),
            intents=tuple(
                cls._clean_string_collection(
                    response.intents
                )
            ),
            is_influential=response.is_influential,
        )

    @classmethod
    def to_citations(
        cls,
        response: SemanticScholarCitationsResponse,
    ) -> list[PaperReference]:
        """Map all valid citation edges."""

        return [
            reference
            for edge in response.data
            if (
                reference
                := cls.citation_to_reference(edge)
            )
            is not None
        ]

    @classmethod
    def to_references(
        cls,
        response: SemanticScholarReferencesResponse,
    ) -> list[PaperReference]:
        """Map all valid reference edges."""

        return [
            reference
            for edge in response.data
            if (
                reference
                := cls.reference_to_reference(edge)
            )
            is not None
        ]

    @classmethod
    def to_search_result(
        cls,
        *,
        request: SearchRequest,
        response: SemanticScholarSearchResponse,
    ) -> SearchResult:
        """Map a Semantic Scholar search response."""

        papers = [
            cls.to_paper(item)
            for item in response.data
        ]

        warnings: list[str] = []

        if request.fields_of_study:
            warnings.append(
                "Semantic Scholar field-of-study filtering "
                "was applied locally."
            )

            requested_fields = {
                field.casefold()
                for field in request.fields_of_study
            }

            papers = [
                paper
                for paper in papers
                if requested_fields.intersection(
                    field.casefold()
                    for field in paper.fields_of_study
                )
            ]

        pagination = PaginationMetadata(
            offset=response.offset,
            limit=request.limit,
            returned=len(papers),
            total=response.total,
            has_more=(
                response.next_offset is not None
            ),
        )

        return SearchResult(
            query=request.query,
            papers=tuple(papers),
            pagination=pagination,
            providers_requested=request.providers,
            providers_succeeded=(
                ProviderName.SEMANTIC_SCHOLAR,
            ),
            failures=(),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _normalize_corpus_id(
        value: int | str | None,
    ) -> int | None:
        """Normalize provider CorpusId values to canonical integers."""

        if value is None:
            return None

        if isinstance(value, int):
            return value

        normalized = value.strip()

        if not normalized:
            return None

        try:
            corpus_id = int(normalized)
        except ValueError:
            return None

        if corpus_id < 0:
            return None

        return corpus_id

    @staticmethod
    def _normalize_semantic_scholar_id(
        value: str | None,
    ) -> str | None:
        """Return a valid canonical Semantic Scholar identifier.

        Semantic Scholar normally returns a long hexadecimal paper ID.
        Invalid or incomplete IDs are excluded so another identifier such as
        DOI, arXiv ID, CorpusId, or PMID can identify the paper.
        """

        normalized = (
            SemanticScholarMapper
            ._clean_optional_string(value)
        )

        if normalized is None:
            return None

        if not 20 <= len(normalized) <= 64:
            return None

        if not normalized.isalnum():
            return None

        return normalized

    @staticmethod
    def _resolve_access_status(
        *,
        is_open_access: bool | None,
        open_access_pdf: (
            SemanticScholarOpenAccessPdfResponse
            | None
        ),
    ) -> AccessStatus:
        """Resolve canonical paper access status."""

        has_pdf = (
            open_access_pdf is not None
            and bool(
                SemanticScholarMapper
                ._clean_optional_string(
                    open_access_pdf.url
                )
            )
        )

        if is_open_access is True or has_pdf:
            return AccessStatus.OPEN_ACCESS

        if is_open_access is False:
            return AccessStatus.CLOSED_ACCESS

        return AccessStatus.UNKNOWN

    @classmethod
    def _resolve_venue(
        cls,
        response: SemanticScholarPaperResponse,
    ) -> str | None:
        """Resolve the best available venue name."""

        venue = cls._clean_optional_string(
            response.venue
        )

        if venue is not None:
            return venue

        if response.publication_venue is not None:
            publication_venue_name = (
                cls._clean_optional_string(
                    response.publication_venue.name
                )
            )

            if publication_venue_name is not None:
                return publication_venue_name

        if response.journal is not None:
            return cls._clean_optional_string(
                response.journal.name
            )

        return None

    @classmethod
    def _resolve_fields_of_study(
        cls,
        response: SemanticScholarPaperResponse,
    ) -> list[str]:
        """Resolve and deduplicate paper fields of study."""

        fields = list(
            response.fields_of_study
        )

        for item in response.s2_fields_of_study:
            category = item.get("category")

            if isinstance(category, str):
                fields.append(category)

        return cls._clean_string_collection(
            fields
        )

    @staticmethod
    def _parse_http_url(
        value: str | None,
    ) -> AnyHttpUrl | None:
        """Parse a provider URL into a canonical HTTP URL.

        Invalid provider URLs are omitted instead of breaking an otherwise
        usable paper response.
        """

        if value is None:
            return None

        try:
            return _HTTP_URL_ADAPTER.validate_python(
                value
            )
        except ValidationError:
            return None

    @staticmethod
    def _clean_optional_string(
        value: str | None,
    ) -> str | None:
        """Strip a string and normalize blanks to None."""

        if value is None:
            return None

        cleaned = " ".join(
            value.split()
        )

        return cleaned or None

    @classmethod
    def _clean_string_collection(
        cls,
        values: list[str],
    ) -> list[str]:
        """Normalize and deduplicate strings while preserving order."""

        cleaned_values: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = cls._clean_optional_string(
                value
            )

            if cleaned is None:
                continue

            key = cleaned.casefold()

            if key in seen:
                continue

            seen.add(key)
            cleaned_values.append(cleaned)

        return cleaned_values