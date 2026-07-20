"""Pydantic models for arXiv Atom API responses.

These models represent arXiv's external provider contract. They must not be
returned directly from MCP tools or exposed outside the provider layer.

The arXiv parser converts Atom XML into these response models. A separate
mapper later converts these provider models into canonical domain models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArxivResponseModel(BaseModel):
    """Base model for parsed arXiv API response objects."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ArxivAuthorResponse(ArxivResponseModel):
    """Author metadata embedded in an arXiv entry."""

    name: str = Field(
        min_length=1,
        description="Author display name.",
    )

    affiliations: list[str] = Field(
        default_factory=list,
        description="Author affiliations provided by arXiv.",
    )

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(
        cls,
        value: object,
    ) -> object:
        """Normalize whitespace in author names."""

        if isinstance(value, str):
            return " ".join(value.split())

        return value

    @field_validator("affiliations", mode="before")
    @classmethod
    def normalize_affiliations(
        cls,
        value: object,
    ) -> object:
        """Normalize affiliation collections."""

        if not isinstance(value, list):
            return value

        normalized: list[str] = []
        seen: set[str] = set()

        for item in value:
            if not isinstance(item, str):
                continue

            cleaned = " ".join(item.split())

            if not cleaned:
                continue

            key = cleaned.casefold()

            if key in seen:
                continue

            seen.add(key)
            normalized.append(cleaned)

        return normalized


class ArxivLinkResponse(ArxivResponseModel):
    """One link included in an arXiv Atom entry."""

    href: str = Field(
        min_length=1,
        description="Link destination.",
    )

    rel: str | None = Field(
        default=None,
        description="Atom link relationship.",
    )

    content_type: str | None = Field(
        default=None,
        alias="type",
        description="Linked resource media type.",
    )

    title: str | None = Field(
        default=None,
        description="Provider-supplied link title.",
    )


class ArxivCategoryResponse(ArxivResponseModel):
    """One arXiv subject category."""

    term: str = Field(
        min_length=1,
        description="arXiv category identifier.",
    )

    scheme: str | None = Field(
        default=None,
        description="Category scheme URL.",
    )

    label: str | None = Field(
        default=None,
        description="Optional human-readable category label.",
    )


class ArxivEntryResponse(ArxivResponseModel):
    """One paper entry parsed from an arXiv Atom feed."""

    entry_id: str = Field(
        alias="id",
        min_length=1,
        description="Atom entry identifier, normally an arXiv abstract URL.",
    )

    title: str = Field(
        min_length=1,
        description="Paper title.",
    )

    summary: str | None = Field(
        default=None,
        description="Paper abstract.",
    )

    published: datetime | None = Field(
        default=None,
        description="Initial publication timestamp.",
    )

    updated: datetime | None = Field(
        default=None,
        description="Most recent update timestamp.",
    )

    authors: list[ArxivAuthorResponse] = Field(
        default_factory=list,
        description="Authors in publication order.",
    )

    links: list[ArxivLinkResponse] = Field(
        default_factory=list,
        description="Landing-page, PDF, DOI, and related links.",
    )

    categories: list[ArxivCategoryResponse] = Field(
        default_factory=list,
        description="All arXiv categories assigned to the paper.",
    )

    primary_category: ArxivCategoryResponse | None = Field(
        default=None,
        description="Primary arXiv subject category.",
    )

    comment: str | None = Field(
        default=None,
        description="Author or submitter comments.",
    )

    journal_reference: str | None = Field(
        default=None,
        description="Published journal reference when available.",
    )

    doi: str | None = Field(
        default=None,
        description="Digital Object Identifier when available.",
    )

    @field_validator(
        "entry_id",
        "title",
        mode="before",
    )
    @classmethod
    def normalize_required_strings(
        cls,
        value: object,
    ) -> object:
        """Normalize required provider strings."""

        if isinstance(value, str):
            return " ".join(value.split())

        return value

    @field_validator(
        "summary",
        "comment",
        "journal_reference",
        "doi",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(
        cls,
        value: object,
    ) -> object:
        """Normalize optional provider strings and blanks."""

        if not isinstance(value, str):
            return value

        normalized = " ".join(value.split())

        return normalized or None


class ArxivFeedResponse(ArxivResponseModel):
    """Parsed arXiv Atom search or identifier-query response."""

    feed_id: str | None = Field(
        default=None,
        alias="id",
        description="Atom feed identifier.",
    )

    title: str | None = Field(
        default=None,
        description="Atom feed title.",
    )

    updated: datetime | None = Field(
        default=None,
        description="Feed update timestamp.",
    )

    total_results: int = Field(
        default=0,
        ge=0,
        description="Total number of matching records reported by arXiv.",
    )

    start_index: int = Field(
        default=0,
        ge=0,
        description="Zero-based index of the first returned result.",
    )

    items_per_page: int = Field(
        default=0,
        ge=0,
        description="Number of records represented by the current page.",
    )

    entries: list[ArxivEntryResponse] = Field(
        default_factory=list,
        description="Paper entries returned by arXiv.",
    )

    @field_validator(
        "feed_id",
        "title",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(
        cls,
        value: object,
    ) -> object:
        """Normalize optional feed strings."""

        if not isinstance(value, str):
            return value

        normalized = " ".join(value.split())

        return normalized or None
