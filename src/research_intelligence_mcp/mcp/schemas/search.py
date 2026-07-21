"""Structured MCP input schemas for academic paper search tools."""

from __future__ import annotations

from typing import Self

from pydantic import Field, field_validator, model_validator

from research_intelligence_mcp.domain.base import DomainModel
from research_intelligence_mcp.domain.enums import (
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.domain.requests import SearchRequest


class SearchPapersInput(DomainModel):
    """Validated input for federated academic paper discovery.

    The schema is deliberately provider-neutral. It allows an MCP client to
    search Semantic Scholar, arXiv, or both without exposing provider-specific
    request formats.
    """

    query: str = Field(
        min_length=2,
        max_length=500,
        description=(
            "Natural-language research question, topic, paper title, "
            "author name, or keyword expression to search for."
        ),
        examples=[
            "retrieval augmented generation evaluation",
            "agentic search for scientific literature",
        ],
    )

    providers: tuple[ProviderName, ...] = Field(
        default=(
            ProviderName.SEMANTIC_SCHOLAR,
            ProviderName.ARXIV,
        ),
        min_length=1,
        max_length=2,
        description=(
            "Academic search providers to query. Select Semantic Scholar, "
            "arXiv, or both. When omitted, both providers are searched."
        ),
        examples=[
            [
                ProviderName.SEMANTIC_SCHOLAR,
                ProviderName.ARXIV,
            ]
        ],
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description=(
            "Maximum number of deduplicated papers returned after combining "
            "and ranking results from all selected providers."
        ),
        examples=[10],
    )

    offset: int = Field(
        default=0,
        ge=0,
        le=10_000,
        description=(
            "Zero-based result offset forwarded to providers that support "
            "pagination. Use zero for the first result page."
        ),
        examples=[0],
    )

    year_from: int | None = Field(
        default=None,
        ge=1400,
        le=2200,
        description=(
            "Optional inclusive earliest publication year. Omit when no "
            "minimum publication year is required."
        ),
        examples=[2020],
    )

    year_to: int | None = Field(
        default=None,
        ge=1400,
        le=2200,
        description=(
            "Optional inclusive latest publication year. Omit when no "
            "maximum publication year is required."
        ),
        examples=[2026],
    )

    fields_of_study: tuple[str, ...] = Field(
        default_factory=tuple,
        max_length=20,
        description=(
            "Optional academic subjects or arXiv categories used to narrow "
            "the search, such as 'Computer Science', 'cs.IR', or 'cs.CL'. "
            "Provider support may vary."
        ),
        examples=[
            [
                "Computer Science",
                "cs.IR",
            ]
        ],
    )

    open_access_only: bool = Field(
        default=False,
        description=(
            "When true, request papers with known open-access availability. "
            "Provider support and metadata completeness may vary."
        ),
        examples=[False],
    )

    sort: SearchSort = Field(
        default=SearchSort.RELEVANCE,
        description=(
            "Requested result ordering. Relevance is recommended for topical "
            "discovery. Other sort modes depend on provider support."
        ),
        examples=[SearchSort.RELEVANCE],
    )

    @field_validator("query")
    @classmethod
    def normalize_query(
        cls,
        value: str,
    ) -> str:
        """Normalize whitespace in the search query."""

        normalized = " ".join(value.split())

        if len(normalized) < 2:
            raise ValueError("Search query must contain at least two characters.")

        return normalized

    @field_validator("providers", mode="before")
    @classmethod
    def normalize_providers(
        cls,
        value: object,
    ) -> object:
        """Deduplicate provider names while preserving caller order."""

        if value is None:
            return (
                ProviderName.SEMANTIC_SCHOLAR,
                ProviderName.ARXIV,
            )

        if not isinstance(
            value,
            (list, tuple),
        ):
            raise ValueError("Providers must be supplied as a list or tuple.")

        deduplicated: list[object] = []

        for provider in value:
            if provider not in deduplicated:
                deduplicated.append(provider)

        if not deduplicated:
            raise ValueError("At least one search provider must be selected.")

        return tuple(deduplicated)

    @field_validator(
        "fields_of_study",
        mode="before",
    )
    @classmethod
    def normalize_fields_of_study(
        cls,
        value: object,
    ) -> object:
        """Normalize and deduplicate academic subject filters."""

        if value is None:
            return ()

        if not isinstance(
            value,
            (list, tuple),
        ):
            raise ValueError("Fields of study must be supplied as a list or tuple.")

        if not all(isinstance(item, str) for item in value):
            raise ValueError("Every field of study must be a string.")

        seen: set[str] = set()
        normalized_fields: list[str] = []

        for item in value:
            normalized = " ".join(item.split())

            if not normalized:
                continue

            comparison_key = normalized.casefold()

            if comparison_key in seen:
                continue

            seen.add(comparison_key)
            normalized_fields.append(normalized)

        return tuple(normalized_fields)

    @model_validator(mode="after")
    def validate_year_range(self) -> Self:
        """Ensure the publication-year range is valid."""

        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_from > self.year_to
        ):
            raise ValueError("year_from must be less than or equal to year_to.")

        return self

    def to_domain_request(self) -> SearchRequest:
        """Convert MCP input into the canonical service request."""

        return SearchRequest(
            query=self.query,
            providers=self.providers,
            limit=self.limit,
            offset=self.offset,
            year_from=self.year_from,
            year_to=self.year_to,
            fields_of_study=self.fields_of_study,
            open_access_only=self.open_access_only,
            sort=self.sort,
        )
