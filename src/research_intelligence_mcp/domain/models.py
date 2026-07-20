"""Canonical provider-neutral academic paper models."""

from datetime import date
from typing import Self

from pydantic import AnyHttpUrl, Field, field_validator, model_validator

from research_intelligence_mcp.domain.base import DomainModel
from research_intelligence_mcp.domain.enums import (
    AccessStatus,
    PaperRelationType,
    ProviderName,
)
from research_intelligence_mcp.domain.identifiers import PaperIdentifiers


def _deduplicate_strings(values: list[str]) -> tuple[str, ...]:
    """Normalize and deduplicate strings while preserving order."""

    seen: set[str] = set()
    normalized_values: list[str] = []

    for value in values:
        normalized = " ".join(value.split())

        if not normalized:
            continue

        comparison_key = normalized.casefold()

        if comparison_key in seen:
            continue

        seen.add(comparison_key)
        normalized_values.append(normalized)

    return tuple(normalized_values)


class Author(DomainModel):
    """Canonical author information."""

    name: str = Field(
        min_length=1,
        max_length=300,
        description="Author's display name.",
    )

    semantic_scholar_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Semantic Scholar author identifier.",
    )

    affiliations: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Known institutional affiliations.",
    )

    homepage_url: AnyHttpUrl | None = Field(
        default=None,
        description="Author homepage when available.",
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Collapse repeated whitespace in author names."""

        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError("Author name cannot be empty.")

        return normalized

    @field_validator("affiliations", mode="before")
    @classmethod
    def normalize_affiliations(
        cls,
        value: object,
    ) -> object:
        """Normalize affiliation collections."""

        if value is None:
            return ()

        if not isinstance(value, (list, tuple)):
            raise ValueError("Affiliations must be a list or tuple.")

        if not all(isinstance(item, str) for item in value):
            raise ValueError("Every affiliation must be a string.")

        return _deduplicate_strings(list(value))


class PaperAccess(DomainModel):
    """Access and URL information associated with a paper."""

    status: AccessStatus = Field(
        default=AccessStatus.UNKNOWN,
        description="Known access status of the paper.",
    )

    landing_page_url: AnyHttpUrl | None = Field(
        default=None,
        description="Canonical abstract or publisher landing page.",
    )

    pdf_url: AnyHttpUrl | None = Field(
        default=None,
        description="Direct PDF URL when available.",
    )

    license: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Known publication or open-access license.",
    )

    repository: ProviderName | None = Field(
        default=None,
        description="Provider hosting the accessible copy.",
    )

    @model_validator(mode="after")
    def validate_access_consistency(self) -> Self:
        """Ensure access status is consistent with PDF availability."""

        if self.status == AccessStatus.CLOSED_ACCESS and self.pdf_url is not None:
            raise ValueError("A closed-access paper cannot expose a direct PDF URL.")

        return self


class Paper(DomainModel):
    """Canonical academic paper independent of provider schemas."""

    identifiers: PaperIdentifiers = Field(
        description="Stable identifiers associated with the paper.",
    )

    title: str = Field(
        min_length=1,
        max_length=1_000,
        description="Paper title.",
    )

    authors: tuple[Author, ...] = Field(
        default_factory=tuple,
        description="Paper authors in publication order.",
    )

    abstract: str | None = Field(
        default=None,
        max_length=100_000,
        description="Paper abstract when available.",
    )

    publication_date: date | None = Field(
        default=None,
        description="Known publication date.",
    )

    year: int | None = Field(
        default=None,
        ge=1400,
        le=2200,
        description="Publication year.",
    )

    venue: str | None = Field(
        default=None,
        max_length=500,
        description="Journal, conference, archive, or publication venue.",
    )

    fields_of_study: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Normalized academic subject areas.",
    )

    citation_count: int | None = Field(
        default=None,
        ge=0,
        description="Known citation count.",
    )

    reference_count: int | None = Field(
        default=None,
        ge=0,
        description="Known reference count.",
    )

    access: PaperAccess = Field(
        default_factory=PaperAccess,
        description="Paper access and URL information.",
    )

    sources: tuple[ProviderName, ...] = Field(
        min_length=1,
        description="Providers contributing metadata to this record.",
    )

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        """Collapse repeated whitespace in paper titles."""

        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError("Paper title cannot be empty.")

        return normalized

    @field_validator("abstract")
    @classmethod
    def normalize_abstract(cls, value: str | None) -> str | None:
        """Normalize empty abstract values to None."""

        if value is None:
            return None

        normalized = " ".join(value.split())

        return normalized or None

    @field_validator("venue")
    @classmethod
    def normalize_venue(cls, value: str | None) -> str | None:
        """Normalize empty venue values to None."""

        if value is None:
            return None

        normalized = " ".join(value.split())

        return normalized or None

    @field_validator("fields_of_study", mode="before")
    @classmethod
    def normalize_fields_of_study(
        cls,
        value: object,
    ) -> object:
        """Normalize and deduplicate fields of study."""

        if value is None:
            return ()

        if not isinstance(value, (list, tuple)):
            raise ValueError("Fields of study must be a list or tuple.")

        if not all(isinstance(item, str) for item in value):
            raise ValueError("Every field of study must be a string.")

        return _deduplicate_strings(list(value))

    @field_validator("sources", mode="before")
    @classmethod
    def normalize_sources(
        cls,
        value: object,
    ) -> object:
        """Deduplicate providers while preserving source order."""

        if not isinstance(value, (list, tuple)):
            raise ValueError("Sources must be a list or tuple.")

        deduplicated: list[object] = []

        for source in value:
            if source not in deduplicated:
                deduplicated.append(source)

        return tuple(deduplicated)

    @model_validator(mode="after")
    def validate_publication_date_and_year(self) -> Self:
        """Ensure publication date and publication year agree."""

        if (
            self.publication_date is not None
            and self.year is not None
            and self.publication_date.year != self.year
        ):
            raise ValueError("Publication date year must match the paper year.")

        return self


class PaperReference(DomainModel):
    """A paper connected to another paper through a graph relationship."""

    relation: PaperRelationType = Field(
        description="Relationship between the origin paper and this paper.",
    )

    paper: Paper = Field(
        description="The related, citing, or referenced paper.",
    )

    contexts: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Citation contexts returned by the provider.",
    )

    intents: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Provider-supplied citation intent labels.",
    )

    is_influential: bool | None = Field(
        default=None,
        description="Whether the provider marks the citation as influential.",
    )

    @field_validator("contexts", "intents", mode="before")
    @classmethod
    def normalize_string_collections(
        cls,
        value: object,
    ) -> object:
        """Normalize citation contexts and intent labels."""

        if value is None:
            return ()

        if not isinstance(value, (list, tuple)):
            raise ValueError("Value must be a list or tuple.")

        if not all(isinstance(item, str) for item in value):
            raise ValueError("Every value must be a string.")

        return _deduplicate_strings(list(value))
