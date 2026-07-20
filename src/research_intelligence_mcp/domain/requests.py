"""Canonical search request and response contracts."""

from typing import Self

from pydantic import Field, field_validator, model_validator

from research_intelligence_mcp.domain.base import DomainModel
from research_intelligence_mcp.domain.enums import ProviderName, SearchSort
from research_intelligence_mcp.domain.models import Paper


class SearchRequest(DomainModel):
    """Validated request for academic paper search."""

    query: str = Field(
        min_length=2,
        max_length=500,
        description="Natural-language or keyword paper search query.",
        examples=["agentic retrieval augmented generation"],
    )

    providers: tuple[ProviderName, ...] = Field(
        default=(
            ProviderName.SEMANTIC_SCHOLAR,
            ProviderName.ARXIV,
        ),
        min_length=1,
        description="Providers to query.",
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of final combined results.",
    )

    offset: int = Field(
        default=0,
        ge=0,
        le=10_000,
        description="Result offset for provider-supported pagination.",
    )

    year_from: int | None = Field(
        default=None,
        ge=1400,
        le=2200,
        description="Inclusive minimum publication year.",
    )

    year_to: int | None = Field(
        default=None,
        ge=1400,
        le=2200,
        description="Inclusive maximum publication year.",
    )

    fields_of_study: tuple[str, ...] = Field(
        default_factory=tuple,
        max_length=20,
        description="Optional academic subject filters.",
    )

    open_access_only: bool = Field(
        default=False,
        description="Return only papers with known open access.",
    )

    sort: SearchSort = Field(
        default=SearchSort.RELEVANCE,
        description="Requested result ordering.",
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        """Normalize repeated whitespace in search queries."""

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
        """Remove duplicate providers while preserving order."""

        if not isinstance(value, (list, tuple)):
            raise ValueError("Providers must be a list or tuple.")

        deduplicated: list[object] = []

        for provider in value:
            if provider not in deduplicated:
                deduplicated.append(provider)

        if not deduplicated:
            raise ValueError("At least one provider must be selected.")

        return tuple(deduplicated)

    @field_validator("fields_of_study", mode="before")
    @classmethod
    def normalize_fields_of_study(
        cls,
        value: object,
    ) -> object:
        """Normalize and deduplicate field filters."""

        if value is None:
            return ()

        if not isinstance(value, (list, tuple)):
            raise ValueError("Fields of study must be a list or tuple.")

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
        """Ensure publication year filters form a valid range."""

        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_from > self.year_to
        ):
            raise ValueError("year_from must be less than or equal to year_to.")

        return self


class PaginationMetadata(DomainModel):
    """Pagination information for a search response."""

    offset: int = Field(
        ge=0,
        description="Offset used for this result page.",
    )

    limit: int = Field(
        ge=1,
        le=50,
        description="Requested result limit.",
    )

    returned: int = Field(
        ge=0,
        description="Number of records returned in this response.",
    )

    total: int | None = Field(
        default=None,
        ge=0,
        description="Provider-reported total result count when available.",
    )

    has_more: bool = Field(
        description="Whether another page may be available.",
    )

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        """Validate pagination count relationships."""

        if self.returned > self.limit:
            raise ValueError("Returned result count cannot exceed the requested limit.")

        if self.total is not None and self.offset + self.returned > self.total:
            raise ValueError("Offset plus returned count cannot exceed total results.")

        return self


class ProviderFailure(DomainModel):
    """Safe normalized description of a provider failure."""

    provider: ProviderName = Field(
        description="Provider that failed.",
    )

    code: str = Field(
        min_length=1,
        max_length=100,
        description="Stable internal error classification.",
    )

    message: str = Field(
        min_length=1,
        max_length=1_000,
        description="Safe user-facing error description.",
    )

    retryable: bool = Field(
        default=False,
        description="Whether retrying may succeed.",
    )


class SearchResult(DomainModel):
    """Provider-neutral federated search response."""

    query: str = Field(
        min_length=2,
        max_length=500,
        description="Normalized search query.",
    )

    papers: tuple[Paper, ...] = Field(
        default_factory=tuple,
        description="Canonical search results.",
    )

    pagination: PaginationMetadata = Field(
        description="Pagination information.",
    )

    providers_requested: tuple[ProviderName, ...] = Field(
        min_length=1,
        description="Providers requested by the caller.",
    )

    providers_succeeded: tuple[ProviderName, ...] = Field(
        default_factory=tuple,
        description="Providers that completed successfully.",
    )

    failures: tuple[ProviderFailure, ...] = Field(
        default_factory=tuple,
        description="Normalized partial provider failures.",
    )

    warnings: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Non-fatal result warnings.",
    )

    @model_validator(mode="after")
    def validate_provider_outcomes(self) -> Self:
        """Ensure provider outcomes correspond to requested providers."""

        requested = set(self.providers_requested)
        succeeded = set(self.providers_succeeded)
        failed = {failure.provider for failure in self.failures}

        if not succeeded.issubset(requested):
            raise ValueError(
                "Successful providers must be part of providers_requested."
            )

        if not failed.issubset(requested):
            raise ValueError("Failed providers must be part of providers_requested.")

        if succeeded.intersection(failed):
            raise ValueError("A provider cannot be both successful and failed.")

        if len(self.papers) != self.pagination.returned:
            raise ValueError(
                "Pagination returned count must match the number of papers."
            )

        return self
